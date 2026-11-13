"""Collections: named sets of uploaded documents that can be asked questions.

A collection is the upload-driven counterpart of a domain pack. On disk:

    data/collections/<slug>/
      collection.json            name, description and one record per file (with its parse report)
      files/<id>.<ext>           the originals, as uploaded
      parsed/<id>.json           the extracted units (pages, slides, sheets, sections)
      index-<embedder>/<id>/     chunks.jsonl + embeddings.npy for that one file

      runs/<id>.json             saved event logs of recent answers, for replay

The index is kept per file. Adding a document embeds only that document, removing one
deletes a folder, and the collection's retriever searches the files' indexes together.

Those paths are keys in a BlobStore (a local folder today), and the vectors and keyword
index live in a VectorStore and a LexicalStore, so hosted stores can replace the local
ones without this module changing (plan v2, A7).
"""

import hashlib
import io
import json
import re
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from hyper_rag.chunking import chunk_documents
from hyper_rag.config import Settings
from hyper_rag.parsing import SUPPORTED, Ocr, ParseError, build_ocr, parse_file
from hyper_rag.retrieval.embedders import Embedder, build_embedder
from hyper_rag.retrieval.rerank import Reranker, build_reranker
from hyper_rag.retrieval.retriever import Retriever
from hyper_rag.stores import (
    BlobStore,
    LexicalStore,
    VectorStore,
    build_blob_store,
    build_lexical_store,
    build_vector_store,
)
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


class _Positions:
    """Adapts a namespaced store, which answers with chunk ids, to the retriever, which
    works with positions in its list of chunks."""

    def __init__(self, store: VectorStore | LexicalStore, namespace: str, chunks: list[Chunk]):
        self.store = store
        self.namespace = namespace
        self.position = {chunk.id: row for row, chunk in enumerate(chunks)}

    def search(self, query, k: int) -> list[tuple[int, float]]:
        hits = self.store.search(self.namespace, query, k)
        return [(self.position[cid], score) for cid, score in hits if cid in self.position]


class CollectionStore:
    def __init__(
        self,
        settings: Settings,
        ocr: Ocr | None = None,
        embedder: Embedder | None = None,
        reranker: Reranker | None = None,
        blobs: BlobStore | None = None,
        vectors: VectorStore | None = None,
        lexical: LexicalStore | None = None,
    ):
        self.settings = settings
        self.root = settings.data_dir / "collections"
        self.blobs = blobs or build_blob_store(settings)
        self.vectors = vectors or build_vector_store(settings)
        self.lexical = lexical or build_lexical_store(settings)
        self._ocr = ocr
        self._embedder = embedder
        self._reranker = reranker
        # Uploads arrive on worker threads; one writer at a time keeps collection.json whole.
        self._lock = threading.RLock()
        self._retrievers: dict[str, tuple[str, Retriever]] = {}
        self._chunks: dict[str, list[Chunk]] = {}  # per-file chunk lists, by index key

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

    def _key(self, slug: str, *parts: str) -> str:
        # A slug only ever contains [a-z0-9-], so it cannot climb out of the root folder.
        if not slug or slugify(slug) != slug:
            raise CollectionNotFound(f"No collection '{slug}'")
        return "/".join(["collections", slug, *parts])

    def path(self, slug: str) -> Path:
        """The collection's local working folder (evaluation files live here)."""
        return self.settings.data_dir / self._key(slug)

    def _meta_key(self, slug: str) -> str:
        return self._key(slug, "collection.json")

    def get(self, slug: str) -> dict:
        try:
            return json.loads(self.blobs.read_bytes(self._meta_key(slug)))
        except KeyError:
            raise CollectionNotFound(f"No collection '{slug}'") from None

    def _save(self, meta: dict) -> None:
        meta["updated"] = _now()
        data = json.dumps(meta, indent=2, ensure_ascii=False).encode("utf-8")
        self.blobs.write_bytes(self._meta_key(meta["slug"]), data)  # atomic
        self._retrievers.pop(meta["slug"], None)

    def all(self) -> list[dict]:
        keys = [k for k in self.blobs.list("collections") if k.count("/") == 2]
        metas = [
            json.loads(self.blobs.read_bytes(key))
            for key in keys
            if key.endswith("/collection.json")
        ]
        return sorted(metas, key=lambda meta: meta["created"])

    def create(self, name: str, description: str = "") -> dict:
        name = " ".join(name.split())
        slug = slugify(name)
        if not slug:
            raise CollectionError("A collection name needs at least one letter or digit.")
        with self._lock:
            if self.blobs.exists(self._meta_key(slug)):
                raise CollectionError(f"A collection named '{name}' already exists.")
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
            self.blobs.delete_prefix(self._key(slug))
            for namespace in self._namespaces(slug):
                self.vectors.drop(namespace)
                self.lexical.drop(namespace)
            self._retrievers.pop(slug, None)
            prefix = self._key(slug) + "/"
            for key in [k for k in self._chunks if k.startswith(prefix)]:
                del self._chunks[key]

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

    def _original_key(self, slug: str, record: dict) -> str:
        return self._key(slug, "files", f"{record['id']}{record['suffix']}")

    def file_path(self, slug: str, file_id: str) -> Path:
        """A local file holding the original upload (downloaded first by a remote store)."""
        return self.blobs.local_path(self._original_key(slug, self.file_record(slug, file_id)))

    def _parsed_key(self, slug: str, file_id: str) -> str:
        return self._key(slug, "parsed", f"{file_id}.json")

    def _index_key(self, slug: str, file_id: str) -> str:
        return self._key(slug, f"index-{self.embedder.name}", file_id)

    def _namespace(self, slug: str) -> str:
        # Vectors from different embedding models are not comparable: one namespace each.
        return f"{slug}:{self.embedder.name}"

    def _namespaces(self, slug: str) -> set[str]:
        """Every namespace this collection may have in the stores, whatever the embedder."""
        names = {key.split("/")[2] for key in self.blobs.list(self._key(slug))}
        embedders = {name[len("index-") :] for name in names if name.startswith("index-")}
        return {f"{slug}:{embedder}" for embedder in embedders} | {self._namespace(slug)}

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
            original_key = self._key(slug, "files", f"{file_id}{suffix}")
            self.blobs.write_bytes(original_key, data)

            started = time.monotonic()
            try:
                parsed = parse_file(
                    self.blobs.local_path(original_key),
                    self.ocr,
                    self.settings.max_units_per_file,
                )
            except ParseError as error:
                self.blobs.delete(original_key)
                raise CollectionError(f"'{name}': {error}") from error
            report = parsed.report()
            if report["characters"] == 0:
                report["warnings"].append(
                    "No text could be extracted, so this file cannot be searched."
                )
            units = [unit.to_dict() for unit in parsed.units]
            parsed_json = json.dumps(
                {"unit_name": parsed.unit_name, "units": units}, ensure_ascii=False
            )
            self.blobs.write_bytes(self._parsed_key(slug, file_id), parsed_json.encode("utf-8"))
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
            try:
                record["chunks"] = len(self._build_index(slug, record)[0])
            except Exception:
                self._discard(slug, record)  # no orphaned files for a file that never got listed
                raise
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
        file_id = record["id"]
        self.blobs.delete(self._original_key(slug, record))
        self.blobs.delete(self._parsed_key(slug, file_id))
        for namespace in self._namespaces(slug):
            embedder = namespace.split(":", 1)[1]
            index_key = self._key(slug, f"index-{embedder}", file_id)
            self.blobs.delete_prefix(index_key)
            self._chunks.pop(index_key, None)
            self.vectors.remove(namespace, file_id)
            self.lexical.remove(namespace, file_id)

    def units(self, slug: str, file_id: str) -> tuple[str, list[dict]]:
        parsed = json.loads(self.blobs.read_bytes(self._parsed_key(slug, file_id)))
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
        index_key = self._index_key(slug, record["id"])
        lines = "".join(json.dumps(c.to_dict(), ensure_ascii=False) + "\n" for c in chunks)
        self.blobs.write_bytes(f"{index_key}/chunks.jsonl", lines.encode("utf-8"))
        buffer = io.BytesIO()
        np.save(buffer, embeddings)
        self.blobs.write_bytes(f"{index_key}/embeddings.npy", buffer.getvalue())
        self._register(slug, record["id"], chunks, embeddings)
        return chunks, embeddings

    def _register(
        self, slug: str, file_id: str, chunks: list[Chunk], embeddings: np.ndarray
    ) -> None:
        """Put one file's index into the vector and keyword stores."""
        namespace = self._namespace(slug)
        ids = [chunk.id for chunk in chunks]
        self.vectors.add(namespace, file_id, ids, embeddings if chunks else embeddings[:0])
        self.lexical.add(namespace, file_id, ids, [chunk.text for chunk in chunks])
        self._chunks[self._index_key(slug, file_id)] = chunks

    def _file_chunks(self, slug: str, record: dict) -> list[Chunk]:
        """One file's chunks, making sure the stores hold its index for this embedder."""
        index_key = self._index_key(slug, record["id"])
        namespace = self._namespace(slug)
        cached = self._chunks.get(index_key)
        if (
            cached is not None
            and self.vectors.has(namespace, record["id"])
            and self.lexical.has(namespace, record["id"])
        ):
            return cached
        if not self.blobs.exists(f"{index_key}/chunks.jsonl"):
            # The file was indexed with a different embedding model: index it for this one.
            return self._build_index(slug, record)[0]
        lines = self.blobs.read_bytes(f"{index_key}/chunks.jsonl").decode("utf-8").splitlines()
        chunks = [Chunk(**json.loads(line)) for line in lines]
        embeddings = np.load(io.BytesIO(self.blobs.read_bytes(f"{index_key}/embeddings.npy")))
        self._register(slug, record["id"], chunks, embeddings)
        return chunks

    def retriever(self, slug: str) -> Retriever:
        with self._lock:
            meta = self.get(slug)
            cached = self._retrievers.get(slug)
            if cached and cached[0] == meta["updated"]:
                return cached[1]
            chunks: list[Chunk] = []
            for record in meta["files"]:
                chunks.extend(self._file_chunks(slug, record))
            if not chunks:
                raise CollectionError(
                    f"Collection '{meta['name']}' has no searchable text yet. Upload a document."
                )
            namespace = self._namespace(slug)
            retriever = Retriever(
                chunks=chunks,
                dense=_Positions(self.vectors, namespace, chunks),
                bm25=_Positions(self.lexical, namespace, chunks),
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
        chunks = self._file_chunks(slug, record)
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

    # --- saved runs: the event log of each recent answer, for replay -------------------

    def save_run(self, slug: str, run: dict) -> str:
        """Keep the events of one answered question. Returns the run id.

        Ids sort by time, so the newest runs are the last keys; only the newest
        `runs_kept` are kept.
        """
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        run_id = f"{stamp}-{uuid.uuid4().hex[:6]}"
        self.get(slug)  # the collection must exist
        body = json.dumps({"id": run_id, "created": _now(), **run}, ensure_ascii=False)
        self.blobs.write_bytes(self._key(slug, "runs", f"{run_id}.json"), body.encode("utf-8"))
        for old in self.blobs.list(self._key(slug, "runs"))[: -self.settings.runs_kept]:
            self.blobs.delete(old)
        return run_id

    def runs(self, slug: str) -> list[dict]:
        """Summaries of the saved runs, newest first."""
        self.get(slug)
        summaries = []
        for key in reversed(self.blobs.list(self._key(slug, "runs"))):
            run = json.loads(self.blobs.read_bytes(key))
            answer = run.get("answer") or {}
            summaries.append(
                {
                    "id": run["id"],
                    "created": run["created"],
                    "question": answer.get("question", ""),
                    "refused": answer.get("refused"),
                    "events": len(run.get("events", [])),
                }
            )
        return summaries

    def run(self, slug: str, run_id: str) -> dict:
        if not re.fullmatch(r"\d{8}T\d{12}-[0-9a-f]{6}", run_id):
            raise CollectionNotFound(f"No run '{run_id}'")
        try:
            return json.loads(self.blobs.read_bytes(self._key(slug, "runs", f"{run_id}.json")))
        except KeyError:
            raise CollectionNotFound(f"No run '{run_id}'") from None


def _first_headings(units: list[dict], limit: int = 6) -> list[str]:
    headings = []
    for unit in units:
        for line in unit["text"].splitlines():
            if line.startswith("#") and len(headings) < limit:
                headings.append(line.lstrip("#").strip()[:60])
    return headings
