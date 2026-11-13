"""Collections: named sets of uploaded documents that can be asked questions.

A collection is the upload-driven counterpart of a domain pack. On disk:

    data/collections/<slug>/
      collection.json            name, description and one record per file (with its parse report)
      files/<id>.<ext>           the originals, as uploaded
      parsed/<id>.json           the extracted units (pages, slides, sheets, sections)
      index-<embedder>/<id>/     chunks.jsonl + embeddings.npy for that one file

The index is kept per file. Adding a document embeds only that document, removing one
deletes a folder, and the collection's retriever is the files' indexes stacked together.
"""

import hashlib
import json
import re
import shutil
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from hyper_rag.chunking import chunk_documents
from hyper_rag.config import Settings
from hyper_rag.parsing import SUPPORTED, Ocr, ParseError, build_ocr, parse_file
from hyper_rag.retrieval.bm25 import BM25Index
from hyper_rag.retrieval.dense import DenseIndex
from hyper_rag.retrieval.embedders import Embedder, build_embedder
from hyper_rag.retrieval.rerank import Reranker, build_reranker
from hyper_rag.retrieval.retriever import Retriever
from hyper_rag.text import split_sentences
from hyper_rag.types import Chunk, Document

_IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


class CollectionError(Exception):
    """A request that cannot be carried out; the message is safe to show to the user."""


class CollectionNotFound(CollectionError):
    pass


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:48]


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def mark_lines(unit_text: str, chunk_text: str) -> list[list[dict]]:
    """Split a unit into lines of sentences and flag the ones the cited passage contains.

    This is what lets a citation open its page with the passage highlighted. Matching is
    done per sentence on whitespace-normalised text, so it survives the chunker's
    re-joining of paragraphs and its cuts in the middle of a long paragraph.
    """
    haystack = _squash(chunk_text)
    lines = []
    for line in unit_text.splitlines():
        if not line.strip():
            continue
        spans = []
        for sentence in split_sentences(line):
            needle = _squash(sentence.lstrip("#").strip())
            spans.append({"text": sentence, "hit": len(needle) >= 4 and needle in haystack})
        lines.append(spans)
    return lines


class CollectionStore:
    def __init__(
        self,
        settings: Settings,
        ocr: Ocr | None = None,
        embedder: Embedder | None = None,
        reranker: Reranker | None = None,
    ):
        self.settings = settings
        self.root = settings.data_dir / "collections"
        self._ocr = ocr
        self._embedder = embedder
        self._reranker = reranker
        # Uploads arrive on worker threads; one writer at a time keeps collection.json whole.
        self._lock = threading.RLock()
        self._retrievers: dict[str, tuple[str, Retriever]] = {}

    # --- lazily built components (each loads a model, so only when first needed) ----------

    @property
    def ocr(self) -> Ocr:
        if self._ocr is None:
            self._ocr = build_ocr(self.settings.ocr)
        return self._ocr

    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = build_embedder(self.settings)
        return self._embedder

    @property
    def reranker(self) -> Reranker:
        if self._reranker is None:
            self._reranker = build_reranker(self.settings)
        return self._reranker

    # --- collections ---------------------------------------------------------------------

    def path(self, slug: str) -> Path:
        # A slug only ever contains [a-z0-9-], so it cannot climb out of the root folder.
        if not slug or slugify(slug) != slug:
            raise CollectionNotFound(f"No collection '{slug}'")
        return self.root / slug

    def _meta_path(self, slug: str) -> Path:
        return self.path(slug) / "collection.json"

    def get(self, slug: str) -> dict:
        meta_path = self._meta_path(slug)
        if not meta_path.exists():
            raise CollectionNotFound(f"No collection '{slug}'")
        return json.loads(meta_path.read_text(encoding="utf-8"))

    def _save(self, meta: dict) -> None:
        meta["updated"] = _now()
        meta_path = self._meta_path(meta["slug"])
        temporary = meta_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(meta_path)  # atomic: a crash never leaves half a file
        self._retrievers.pop(meta["slug"], None)

    def all(self) -> list[dict]:
        if not self.root.exists():
            return []
        metas = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(self.root.glob("*/collection.json"))
        ]
        return sorted(metas, key=lambda meta: meta["created"])

    def create(self, name: str, description: str = "") -> dict:
        name = " ".join(name.split())
        slug = slugify(name)
        if not slug:
            raise CollectionError("A collection name needs at least one letter or digit.")
        with self._lock:
            if self._meta_path(slug).exists():
                raise CollectionError(f"A collection named '{name}' already exists.")
            self.path(slug).mkdir(parents=True)
            meta = {
                "slug": slug,
                "name": name,
                "description": description.strip(),
                "created": _now(),
                "files": [],
            }
            self._save(meta)
        return meta

    def delete(self, slug: str) -> None:
        with self._lock:
            self.get(slug)
            shutil.rmtree(self.path(slug))
            self._retrievers.pop(slug, None)

    def description(self, slug: str) -> str:
        """What the agent's router is told this collection is about.

        Built from the file names and their first headings, because a user who drops in
        ten files should not have to write a summary before asking a question.
        """
        meta = self.get(slug)
        parts = [meta["description"]] if meta["description"] else []
        names = [record["name"] for record in meta["files"]]
        parts.append("Documents uploaded by the user: " + ", ".join(names[:25]) + ".")
        headings = [h for record in meta["files"] for h in record.get("headings", [])][:20]
        if headings:
            parts.append("Their sections include: " + "; ".join(headings) + ".")
        return " ".join(parts)

    # --- files ---------------------------------------------------------------------------

    def file_record(self, slug: str, file_id: str) -> dict:
        for record in self.get(slug)["files"]:
            if record["id"] == file_id:
                return record
        raise CollectionNotFound(f"No file '{file_id}' in collection '{slug}'")

    def file_path(self, slug: str, file_id: str) -> Path:
        record = self.file_record(slug, file_id)
        return self.path(slug) / "files" / f"{record['id']}{record['suffix']}"

    def _parsed_path(self, slug: str, file_id: str) -> Path:
        return self.path(slug) / "parsed" / f"{file_id}.json"

    def _index_dir(self, slug: str, file_id: str) -> Path:
        return self.path(slug) / f"index-{self.embedder.name}" / file_id

    def add_file(self, slug: str, filename: str, data: bytes) -> dict:
        """Store, parse, chunk and embed one uploaded file. Returns its record."""
        name = re.sub(r"[\x00-\x1f]", "", Path(filename.replace("\\", "/")).name)[:120]
        suffix = Path(name).suffix.lower()
        if suffix not in SUPPORTED:
            # parse_file writes the helpful message (legacy formats, list of supported types).
            try:
                parse_file(Path(name or "file"), self.ocr)
            except ParseError as error:
                raise CollectionError(str(error)) from error
        if not data:
            raise CollectionError(f"'{name}' is empty.")
        limit = self.settings.max_upload_mb * 1024 * 1024
        if len(data) > limit:
            raise CollectionError(
                f"'{name}' is larger than the {self.settings.max_upload_mb} MB upload limit."
            )

        digest = hashlib.sha256(data).hexdigest()
        with self._lock:
            meta = self.get(slug)
            for record in meta["files"]:
                if record["sha256"] == digest:
                    return {**record, "duplicate": True}  # identical bytes: nothing to do
            replaced = [record for record in meta["files"] if record["name"] == name]

            file_id = digest[:12]
            directory = self.path(slug)
            (directory / "files").mkdir(exist_ok=True)
            (directory / "parsed").mkdir(exist_ok=True)
            original = directory / "files" / f"{file_id}{suffix}"
            original.write_bytes(data)

            started = time.monotonic()
            try:
                parsed = parse_file(original, self.ocr, self.settings.max_units_per_file)
            except ParseError as error:
                original.unlink(missing_ok=True)
                raise CollectionError(f"'{name}': {error}") from error
            report = parsed.report()
            if report["characters"] == 0:
                report["warnings"].append(
                    "No text could be extracted, so this file cannot be searched."
                )
            units = [unit.to_dict() for unit in parsed.units]
            self._parsed_path(slug, file_id).write_text(
                json.dumps({"unit_name": parsed.unit_name, "units": units}, ensure_ascii=False),
                encoding="utf-8",
            )
            record = {
                "id": file_id,
                "name": name,
                "suffix": suffix,
                "kind": parsed.kind,
                "size": len(data),
                "sha256": digest,
                "added": _now(),
                "headings": _first_headings(units),
                "report": report,
            }
            record["chunks"] = len(self._build_index(slug, record)[0])
            record["seconds"] = round(time.monotonic() - started, 2)

            # Uploading a file with the name of an existing one replaces it: the usual
            # reason is a newer version of the same document.
            for old in replaced:
                self._discard(slug, old)
            meta["files"] = [r for r in meta["files"] if r["name"] != name] + [record]
            self._save(meta)
        return {**record, "replaced": bool(replaced)}

    def remove_file(self, slug: str, file_id: str) -> None:
        with self._lock:
            meta = self.get(slug)
            record = self.file_record(slug, file_id)
            self._discard(slug, record)
            meta["files"] = [r for r in meta["files"] if r["id"] != file_id]
            self._save(meta)

    def _discard(self, slug: str, record: dict) -> None:
        directory = self.path(slug)
        (directory / "files" / f"{record['id']}{record['suffix']}").unlink(missing_ok=True)
        self._parsed_path(slug, record["id"]).unlink(missing_ok=True)
        for index_dir in directory.glob(f"index-*/{record['id']}"):
            shutil.rmtree(index_dir)

    def units(self, slug: str, file_id: str) -> tuple[str, list[dict]]:
        parsed = json.loads(self._parsed_path(slug, file_id).read_text(encoding="utf-8"))
        return parsed["unit_name"], parsed["units"]

    # --- index ---------------------------------------------------------------------------

    def _documents(self, slug: str, record: dict) -> list[Document]:
        """One Document per unit, so a citation resolves to a page, slide or sheet."""
        unit_name, units = self.units(slug, record["id"])
        documents = []
        for unit in units:
            if not unit["text"].strip():
                continue
            # A Word section's label is its own heading, which the chunker adds anyway.
            labelled = unit["label"] and unit_name != "section"
            url = f"/collections/{slug}/files/{record['id']}"
            if record["kind"] == "pdf":
                url += f"#page={unit['number']}"  # browsers open a PDF at this page
            documents.append(
                Document(
                    id=f"{record['id']}/{unit['number']}",
                    title=f"{record['name']} ({unit['label']})" if labelled else record["name"],
                    url=url,
                    text=unit["text"],
                )
            )
        return documents

    def _build_index(self, slug: str, record: dict) -> tuple[list[Chunk], np.ndarray]:
        chunks = chunk_documents(
            self._documents(slug, record),
            self.settings.upload_chunk_size,
            self.settings.upload_chunk_overlap,
            structured=True,
        )
        if chunks:
            embeddings = self.embedder.embed_documents([chunk.text for chunk in chunks])
        else:
            embeddings = np.zeros((0, 1), dtype=np.float32)
        index_dir = self._index_dir(slug, record["id"])
        index_dir.mkdir(parents=True, exist_ok=True)
        with (index_dir / "chunks.jsonl").open("w", encoding="utf-8") as handle:
            for chunk in chunks:
                handle.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
        np.save(index_dir / "embeddings.npy", embeddings)
        return chunks, embeddings

    def _load_index(self, slug: str, record: dict) -> tuple[list[Chunk], np.ndarray]:
        index_dir = self._index_dir(slug, record["id"])
        if not (index_dir / "chunks.jsonl").exists():
            # The file was indexed with a different embedding model: index it for this one.
            return self._build_index(slug, record)
        lines = (index_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
        return [Chunk(**json.loads(line)) for line in lines], np.load(index_dir / "embeddings.npy")

    def retriever(self, slug: str) -> Retriever:
        with self._lock:
            meta = self.get(slug)
            cached = self._retrievers.get(slug)
            if cached and cached[0] == meta["updated"]:
                return cached[1]
            chunks: list[Chunk] = []
            matrices = []
            for record in meta["files"]:
                file_chunks, embeddings = self._load_index(slug, record)
                if file_chunks:
                    chunks.extend(file_chunks)
                    matrices.append(embeddings)
            if not chunks:
                raise CollectionError(
                    f"Collection '{meta['name']}' has no searchable text yet. Upload a document."
                )
            retriever = Retriever(
                chunks=chunks,
                dense=DenseIndex(np.vstack(matrices)),
                bm25=BM25Index([chunk.text for chunk in chunks]),
                embedder=self.embedder,
                reranker=self.reranker,
                settings=self.settings,
            )
            self._retrievers[slug] = (meta["updated"], retriever)
            return retriever

    # --- click-through citations ---------------------------------------------------------

    def source(self, slug: str, chunk_id: str) -> dict:
        """Everything the UI needs to show where a cited passage came from."""
        match = re.fullmatch(r"([0-9a-f]{12})/(\d+)#(\d+)", chunk_id)
        if not match:
            raise CollectionNotFound(f"No passage '{chunk_id}'")
        file_id, unit_number = match.group(1), int(match.group(2))
        record = self.file_record(slug, file_id)
        unit_name, units = self.units(slug, file_id)
        unit = next((u for u in units if u["number"] == unit_number), None)
        chunks, _ = self._load_index(slug, record)
        chunk = next((c for c in chunks if c.id == chunk_id), None)
        if unit is None or chunk is None:
            raise CollectionNotFound(f"No passage '{chunk_id}'")
        has_preview = record["kind"] in ("pdf", "image")
        base = f"/collections/{slug}/files/{file_id}"
        return {
            "file_id": file_id,
            "file_name": record["name"],
            "kind": record["kind"],
            "unit_name": unit_name,
            "unit_number": unit_number,
            "unit_label": unit["label"],
            "read_by_ocr": unit["ocr"],
            "file_url": base + (f"#page={unit_number}" if record["kind"] == "pdf" else ""),
            "preview_url": f"{base}/preview/{unit_number}" if has_preview else None,
            "lines": mark_lines(unit["text"], chunk.text),
        }

    def preview(self, slug: str, file_id: str, unit_number: int) -> tuple[bytes, str]:
        """An image of the cited page: the rendered PDF page, or the uploaded image itself."""
        record = self.file_record(slug, file_id)
        path = self.file_path(slug, file_id)
        if record["kind"] == "image":
            return path.read_bytes(), _IMAGE_TYPES.get(record["suffix"], "image/png")
        if record["kind"] != "pdf":
            raise CollectionNotFound("This file type has no page preview.")
        import io

        import pypdfium2

        pdf = pypdfium2.PdfDocument(str(path))
        try:
            if not 1 <= unit_number <= len(pdf):
                raise CollectionNotFound(f"No page {unit_number}")
            image = pdf[unit_number - 1].render(scale=1.6).to_pil()
        finally:
            pdf.close()
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue(), "image/png"


def _first_headings(units: list[dict], limit: int = 6) -> list[str]:
    headings = []
    for unit in units:
        for line in unit["text"].splitlines():
            if line.startswith("#") and len(headings) < limit:
                headings.append(line.lstrip("#").strip()[:60])
    return headings
