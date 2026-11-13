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
from functools import partial
from pathlib import Path

import numpy as np

from hyper_rag.chunking import chunk_documents
from hyper_rag.config import Settings
from hyper_rag.events import EventSink, elapsed_ms, emit
from hyper_rag.parsing import SUPPORTED, Ocr, ParseError, Unit, build_ocr, parse_file
from hyper_rag.parsing.pdf import parse_pdf_pages
from hyper_rag.parsing.xray import PDFIUM_LOCK, PageInfo, XRay, xray_pdf
from hyper_rag.retrieval.bm25 import BM25Index
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
from hyper_rag.stores.cache import EmbeddingCache, PageCache
from hyper_rag.structure import (
    Section,
    body_sentences,
    chapter_numbers,
    common_shapes,
    extractive_summary,
    outline_entries,
    page_paths,
    sections,
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
        self._chunks: dict[str, list[Chunk]] = {}  # per-window chunk lists, by blob key
        self._priority: dict[tuple[str, str], set[int]] = {}  # windows a question asked for
        self._tier0: dict[tuple[str, str], BM25Index] = {}
        self._maps: dict[str, tuple[str, dict]] = {}  # Galaxy layouts, by collection
        self.embedding_cache = EmbeddingCache(settings.data_dir / "cache" / "embeddings.sqlite3")

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
    #
    # A file goes through two steps. `stage_file` checks it, stores the original and lists
    # it with status "queued"; it is quick and holds the lock only to update the listing.
    # `ingest_file` then reads it a window of pages at a time (plan v2, A3): parse, chunk,
    # embed, write, and register with the search stores. A window's chunk file is written
    # last, so it doubles as the checkpoint: a restart skips the windows that have one, and
    # search sees each window the moment it is written (A4). Parsing and embedding hold no
    # lock, so questions and other uploads never wait for a big file.

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

    def _legacy_parsed_key(self, slug: str, file_id: str) -> str:
        return self._key(slug, "parsed", f"{file_id}.json")  # one file per upload (before v2)

    def _parsed_prefix(self, slug: str, file_id: str) -> str:
        return self._key(slug, "parsed", file_id)

    def _window_units_key(self, slug: str, file_id: str, window: int) -> str:
        return f"{self._parsed_prefix(slug, file_id)}/w{window:05d}.json"

    def _xray_key(self, slug: str, file_id: str) -> str:
        return f"{self._parsed_prefix(slug, file_id)}/xray.json"

    def _index_key(self, slug: str, file_id: str) -> str:
        return self._key(slug, f"index-{self.embedder.name}", file_id)

    def _window_index_key(self, slug: str, file_id: str, window: int | str, ext: str) -> str:
        """A window's index ("w00003"), or a summary part ("s00000" sections, "s00001"
        chapters), which is indexed the same way."""
        part = window if isinstance(window, str) else f"w{window:05d}"
        return f"{self._index_key(slug, file_id)}/{part}.{ext}"

    def _summaries_key(self, slug: str, file_id: str) -> str:
        return f"{self._parsed_prefix(slug, file_id)}/summaries.json"

    def _tier0_key(self, slug: str, file_id: str) -> str:
        return f"{self._parsed_prefix(slug, file_id)}/tier0.json"

    def _namespace(self, slug: str) -> str:
        # Vectors from different embedding models are not comparable: one namespace each.
        return f"{slug}:{self.embedder.name}"

    def _namespaces(self, slug: str) -> set[str]:
        """Every namespace this collection may have in the stores, whatever the embedder."""
        names = {key.split("/")[2] for key in self.blobs.list(self._key(slug))}
        embedders = {name[len("index-") :] for name in names if name.startswith("index-")}
        return {f"{slug}:{embedder}" for embedder in embedders} | {self._namespace(slug)}

    def _update_record(self, slug: str, file_id: str, change) -> dict:
        """Read-modify-write one file's record under the lock. Returns the new record."""
        with self._lock:
            meta = self.get(slug)
            for position, record in enumerate(meta["files"]):
                if record["id"] == file_id:
                    meta["files"][position] = change(dict(record))
                    self._save(meta)
                    return meta["files"][position]
        raise CollectionNotFound(f"No file '{file_id}' in collection '{slug}'")

    def check_upload(self, slug: str, filename: str, size: int) -> tuple[str, str]:
        """Validate a name and size before any bytes are stored. Returns (name, suffix)."""
        name = re.sub(r"[\x00-\x1f]", "", Path(filename.replace("\\", "/")).name)[:120]
        suffix = Path(name).suffix.lower()
        if suffix not in SUPPORTED:
            # parse_file writes the helpful message (legacy formats, list of supported types).
            try:
                parse_file(Path(name or "file"), self.ocr)
            except ParseError as error:
                raise CollectionError(str(error)) from error
        if size <= 0:
            raise CollectionError(f"'{name}' is empty.")
        if size > self.settings.max_file_mb * 1024 * 1024:
            raise CollectionError(
                f"'{name}' is larger than the {self.settings.max_file_mb} MB limit per file."
            )
        used = sum(record["size"] for record in self.get(slug)["files"])
        if used + size > self.settings.max_collection_mb * 1024 * 1024:
            raise CollectionError(
                f"'{name}' would take this collection past its "
                f"{self.settings.max_collection_mb} MB storage budget."
            )
        return name, suffix

    def stage_file(self, slug: str, filename: str, source: Path, move: bool = False) -> dict:
        """Check a file, store the original and list it as "queued". Returns its record;
        identical bytes already in the collection return that record with duplicate=True."""
        name, suffix = self.check_upload(slug, filename, source.stat().st_size)
        digest = hashlib.sha256()
        with source.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        digest = digest.hexdigest()
        with self._lock:
            meta = self.get(slug)
            for record in meta["files"]:
                if record["sha256"] == digest:
                    if move:
                        source.unlink(missing_ok=True)
                    return {**record, "duplicate": True}  # identical bytes: nothing to do
            record = {
                "id": digest[:12],
                "name": name,
                "suffix": suffix,
                "kind": SUPPORTED[suffix],
                "size": source.stat().st_size,
                "sha256": digest,
                "added": _now(),
                "status": "queued",
                "pages_total": None,
                "pages_done": 0,
                "windows_total": None,
                "windows_done": 0,
                "chunks": 0,
                "headings": [],
                "report": None,
                "xray": None,
                "error": None,
                # Uploading a file with the name of an existing one replaces it once the new
                # one is ready: the usual reason is a newer version of the same document.
                "replaces": [r["id"] for r in meta["files"] if r["name"] == name],
            }
            self.blobs.write_file(self._original_key(slug, record), source, move=move)
            meta["files"].append(record)
            self._save(meta)
        return record

    def add_file(self, slug: str, filename: str, data: bytes) -> dict:
        """Store, parse, chunk and embed one small upload now. Returns its record.

        The direct upload endpoint and the CLI use this; big files go through a resumable
        upload and a background job, which run the same two steps.
        """
        self.get(slug)
        limit = self.settings.max_upload_mb * 1024 * 1024
        if len(data) > limit:
            name = Path(filename.replace("\\", "/")).name
            raise CollectionError(
                f"'{name}' is larger than the {self.settings.max_upload_mb} MB upload limit."
            )
        temporary = self.incoming_path()
        temporary.write_bytes(data)
        return self.add_path(slug, filename, temporary)

    def incoming_path(self) -> Path:
        """A fresh local path for an upload on its way in."""
        incoming = self.settings.data_dir / "incoming"
        incoming.mkdir(parents=True, exist_ok=True)
        return incoming / f"direct-{uuid.uuid4().hex}"

    def add_path(self, slug: str, filename: str, path: Path) -> dict:
        """Stage and read a file that is already on local disk (it is consumed)."""
        try:
            record = self.stage_file(slug, filename, path, move=True)
        finally:
            path.unlink(missing_ok=True)
        if record.get("duplicate"):
            return record
        record = self.ingest_file(slug, record["id"], keep_failed=False)
        return {**record, "replaced": bool(record.get("replaced"))}

    def ingest_file(
        self,
        slug: str,
        file_id: str,
        on_event: EventSink | None = None,
        keep_failed: bool = True,
    ) -> dict:
        """Read a staged file window by window, resuming after the last committed window.

        Returns the finished record. On failure the record says why (status "failed"), or,
        with keep_failed=False, the file is removed and CollectionError raised.
        """
        record = self.file_record(slug, file_id)
        started = time.monotonic()
        try:
            plan = self._plan_windows(slug, record)
            record = self._update_record(
                slug,
                file_id,
                lambda r: {
                    **r,
                    "status": "reading",
                    "pages_total": plan["pages_total"],
                    "windows_total": len(plan["windows"]),
                    "window_pages": plan["window_pages"],
                    "xray": plan["xray"],
                    "report": r["report"] or _empty_report(plan["kind"], plan["unit_name"]),
                },
            )
            emit(on_event, "ingest.triage", file=file_id, **(plan["xray"] or {}))
            for window, units, warnings, ms in self._parsed_windows(slug, record, plan):
                if not self._still_listed(slug, file_id):
                    return {**record, "status": "removed"}
                chunks = self._commit_window(slug, record, window, units, warnings, ms, plan)
                counted = partial(
                    _count_window,
                    units=units,
                    warnings=warnings,
                    chunks=len(chunks),
                    unit_name=plan["unit_name"],
                )
                record = self._update_record(slug, file_id, counted)
                _release_memory()
                emit(
                    on_event,
                    "ingest.commit",
                    file=file_id,
                    window=window,
                    pages=[u.number for u in units],
                    chunks=len(chunks),
                    ms=ms,
                    searchable_pages=record["pages_done"],
                )
            record = self._finish(slug, record, started)
            emit(on_event, "ingest.done", file=file_id, chunks=record["chunks"])
            return record
        except Exception as error:
            message = (
                str(error)
                if isinstance(error, ParseError | CollectionError)
                else (f"{type(error).__name__}: {error}")
            )
            emit(on_event, "ingest.failed", file=file_id, error=message)
            if not self._still_listed(slug, file_id):
                raise
            if keep_failed:
                return self._update_record(
                    slug, file_id, lambda r: {**r, "status": "failed", "error": message}
                )
            self.remove_file(slug, file_id)  # no orphaned files for a file that never got listed
            if isinstance(error, ParseError):
                raise CollectionError(f"'{record['name']}': {error}") from error
            raise

    def _still_listed(self, slug: str, file_id: str) -> bool:
        try:
            self.file_record(slug, file_id)
            return True
        except CollectionError:
            return False

    def _plan_windows(self, slug: str, record: dict) -> dict:
        """Decide the windows. PDFs are X-rayed (once; the result is kept for a resume);
        other formats are read whole, as one window."""
        if record["kind"] != "pdf":
            return {
                "kind": record["kind"],
                "unit_name": None,
                "pages_total": None,
                "window_pages": None,
                "xray": None,
                "windows": [None],
                "boilerplate": [],
            }
        key = self._xray_key(slug, record["id"])
        if self.blobs.exists(key):
            saved = json.loads(self.blobs.read_bytes(key))
            xray = XRay(
                pages=[PageInfo(**page) for page in saved["pages"]],
                outline=saved["outline"],
                boilerplate=saved["boilerplate"],
            )
        else:
            xray = xray_pdf(self.file_path(slug, record["id"]))
            body = {
                "pages": [page.to_dict() for page in xray.pages],
                "outline": xray.outline,
                "boilerplate": xray.boilerplate,
            }
            # Tier 0 (plan v2, A5): the text layer of every page, searchable within seconds
            # of the upload, so a question can say which pages to read first.
            tier0 = json.dumps([text[:TIER0_CHARS] for text in xray.texts], ensure_ascii=False)
            self.blobs.write_bytes(self._tier0_key(slug, record["id"]), tier0.encode("utf-8"))
            self.blobs.write_bytes(key, json.dumps(body).encode("utf-8"))
        pages = xray.pages
        # The page budget replaces the old 300-page cap: a safety valve on a free tier.
        others = sum(
            r.get("pages_total") or 0
            for r in self.get(slug)["files"]
            if r["id"] != record["id"] and r["id"] not in record.get("replaces", [])
        )
        allowed = max(self.settings.max_collection_pages - others, 0)
        warning = None
        if len(pages) > allowed:
            warning = (
                f"Only the first {allowed} of {len(pages)} pages were read: the collection's "
                f"page budget is {self.settings.max_collection_pages}."
            )
            pages = pages[:allowed]
        size = self.settings.window_pages
        summary = xray.summary()
        if warning:
            summary["warning"] = warning
        return {
            "kind": "pdf",
            "unit_name": "page",
            "pages_total": len(pages),
            "window_pages": size,
            "xray": summary,
            "windows": [pages[i : i + size] for i in range(0, len(pages), size)],
            "boilerplate": xray.boilerplate,
            "warning": warning,
            "paths": page_paths(xray.outline, len(pages)) if xray.outline else {},
        }

    def _parsed_windows(self, slug: str, record: dict, plan: dict):
        """Yield (window, units, warnings, ms) for every window not yet committed, in order.

        With settings.ingest_processes > 0 the next windows are parsed in worker processes
        while this one is being embedded; otherwise they are parsed here, one by one.
        """
        file_id = record["id"]
        todo = [
            (window, pages)
            for window, pages in enumerate(plan["windows"])
            if not self.blobs.exists(self._window_index_key(slug, file_id, window, "chunks.jsonl"))
        ]
        path = self.file_path(slug, file_id)
        if plan["kind"] != "pdf":
            for window, _ in todo:
                started = time.perf_counter()
                parsed = parse_file(path, self.ocr)
                plan["unit_name"] = parsed.unit_name
                yield window, parsed.units, parsed.warnings, elapsed_ms(started)
            return
        processes = self.settings.ingest_processes
        ocr_name = self.settings.ocr if processes > 0 else self.ocr.name
        cache = PageCache(self.blobs, ocr_name, plan["boilerplate"])
        priority = self._priority.setdefault((slug, file_id), set())

        def next_window(remaining: dict):
            # A question may have asked for some windows first (plan v2, A5).
            wanted = sorted(w for w in priority if w in remaining)
            window = wanted[0] if wanted else min(remaining)
            priority.discard(window)
            return window, remaining.pop(window)

        if processes <= 0:
            remaining = dict(todo)
            while remaining:
                window, pages = next_window(remaining)
                started = time.perf_counter()
                cached, missing = _from_cache(cache, pages)
                units, warnings = parse_pdf_pages(path, missing, self.ocr, plan["boilerplate"])
                _to_cache(cache, missing, units, warnings)
                plan.setdefault("cache", {})[window] = len(cached)
                yield window, _merge(pages, cached, units), warnings, elapsed_ms(started)
            return
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(max_workers=processes) as pool:
            ahead = []
            queue = dict(todo)
            while queue or ahead:
                while queue and len(ahead) < processes + 1:
                    window, pages = next_window(queue)
                    cached, missing = _from_cache(cache, pages)
                    future = pool.submit(
                        parse_window_in_process,
                        str(path),
                        [page.to_dict() for page in missing],
                        self.settings.ocr,
                        plan["boilerplate"],
                    )
                    ahead.append((window, pages, cached, missing, future))
                window, pages, cached, missing, future = ahead.pop(0)
                units, warnings, ms = future.result()
                _to_cache(cache, missing, units, warnings)
                plan.setdefault("cache", {})[window] = len(cached)
                yield window, _merge(pages, cached, units), warnings, ms

    def _commit_window(
        self,
        slug: str,
        record: dict,
        window: int,
        units: list[Unit],
        warnings: list[str],
        ms: float,
        plan: dict,
    ) -> list[Chunk]:
        file_id = record["id"]
        unit_name = plan["unit_name"]
        unit_dicts = [unit.to_dict() for unit in units]
        routes = {}
        if plan["kind"] == "pdf":
            routes = {str(p.number): p.route for p in plan["windows"][window]}
        body = {
            "unit_name": unit_name,
            "units": unit_dicts,
            "warnings": warnings,
            "ms": ms,
            "routes": routes,
            "cached_pages": plan.get("cache", {}).get(window, 0),
        }
        self.blobs.write_bytes(
            self._window_units_key(slug, file_id, window),
            json.dumps(body, ensure_ascii=False).encode("utf-8"),
        )
        chunks = chunk_documents(
            self._documents(slug, record, unit_name, unit_dicts, plan.get("paths")),
            self.settings.upload_chunk_size,
            self.settings.upload_chunk_overlap,
            structured=True,
        )
        self._write_window_index(slug, file_id, window, chunks)
        return chunks

    def _write_window_index(
        self, slug: str, file_id: str, window: int | str, chunks: list[Chunk]
    ) -> None:
        if chunks:
            embeddings, _ = self.embedding_cache.embed(
                self.embedder, [chunk.text for chunk in chunks]
            )
        else:
            embeddings = np.zeros((0, 1), dtype=np.float32)
        buffer = io.BytesIO()
        np.save(buffer, embeddings)
        self.blobs.write_bytes(
            self._window_index_key(slug, file_id, window, "npy"), buffer.getvalue()
        )
        # The chunk file last: its presence is what marks the window as committed.
        lines = "".join(json.dumps(c.to_dict(), ensure_ascii=False) + "\n" for c in chunks)
        chunks_key = self._window_index_key(slug, file_id, window, "chunks.jsonl")
        self.blobs.write_bytes(chunks_key, lines.encode("utf-8"))
        part = window if isinstance(window, str) else f"w{window:05d}"
        self._register(slug, f"{file_id}#{part}", chunks_key, chunks, embeddings)

    def _finish(self, slug: str, record: dict, started: float) -> dict:
        file_id = record["id"]
        replaces = set(record.get("replaces") or [])
        headings = []
        for window in range(record["windows_total"] or 0):
            if len(headings) >= 6:
                break
            _, units = self._window_units(slug, file_id, window)
            headings += _first_headings(units, 6 - len(headings))

        def finish(r: dict) -> dict:
            report = dict(r["report"])
            if report["characters"] == 0:
                report["warnings"] = [
                    *report["warnings"],
                    "No text could be extracted, so this file cannot be searched.",
                ]
            if r.get("xray", {}) and r["xray"].get("warning"):
                report["warnings"] = [r["xray"]["warning"], *report["warnings"]]
            return {
                **r,
                "status": "ready",
                "headings": headings,
                "report": report,
                "seconds": round(r.get("seconds", 0) + time.monotonic() - started, 2),
                "replaced": bool(r.get("replaces")),
                "replaces": [],
            }

        record = self._update_record(slug, file_id, finish)
        if self.settings.book_structure and record["kind"] == "pdf":
            try:
                count = self.build_summaries(slug, record)
                if count:
                    record = self._update_record(slug, file_id, lambda r: {**r, "sections": count})
            except Exception as error:  # summaries help; their failure must not fail the file
                note = f"No summaries: {error}"
                record = self._update_record(
                    slug,
                    file_id,
                    lambda r: {
                        **r,
                        "report": {**r["report"], "warnings": [*r["report"]["warnings"], note]},
                    },
                )
        with self._lock:
            meta = self.get(slug)
            old = [r for r in meta["files"] if r["id"] in replaces and r["id"] != file_id]
            for gone in old:
                self._discard(slug, gone)
            if old:
                meta["files"] = [r for r in meta["files"] if r not in old]
                self._save(meta)
        return record

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
        self.blobs.delete(self._legacy_parsed_key(slug, file_id))
        self.blobs.delete_prefix(self._parsed_prefix(slug, file_id))
        for namespace in self._namespaces(slug):
            embedder = namespace.split(":", 1)[1]
            index_key = self._key(slug, f"index-{embedder}", file_id)
            self.blobs.delete_prefix(index_key)
            for key in [k for k in self._chunks if k.startswith(index_key + "/")]:
                del self._chunks[key]
            self.vectors.remove(namespace, file_id)
            self.lexical.remove(namespace, file_id)

    def _window_units(self, slug: str, file_id: str, window: int) -> tuple[str, list[dict]]:
        parsed = json.loads(self.blobs.read_bytes(self._window_units_key(slug, file_id, window)))
        return parsed["unit_name"], parsed["units"]

    def units(self, slug: str, file_id: str) -> tuple[str, list[dict]]:
        """Every unit of a file read so far, in order."""
        legacy = self._legacy_parsed_key(slug, file_id)
        if self.blobs.exists(legacy):
            parsed = json.loads(self.blobs.read_bytes(legacy))
            return parsed["unit_name"], parsed["units"]
        unit_name, units = "page", []
        for key in self.blobs.list(self._parsed_prefix(slug, file_id)):
            if re.search(r"/w\d{5}\.json$", key):
                parsed = json.loads(self.blobs.read_bytes(key))
                unit_name = parsed["unit_name"] or unit_name
                units.extend(parsed["units"])
        return unit_name, units

    def unit(self, slug: str, file_id: str, number: int) -> tuple[str, dict | None]:
        """One unit, reading only the window that holds it (a citation click on a book)."""
        record = self.file_record(slug, file_id)
        size = record.get("window_pages")
        legacy = self.blobs.exists(self._legacy_parsed_key(slug, file_id))
        if size and not legacy:
            key = self._window_units_key(slug, file_id, (number - 1) // size)
            if not self.blobs.exists(key):
                return "page", None
            unit_name, units = self._window_units(slug, file_id, (number - 1) // size)
        else:
            unit_name, units = self.units(slug, file_id)
        return unit_name, next((u for u in units if u["number"] == number), None)

    def pages(self, slug: str, file_id: str) -> dict:
        """Per-page routes and progress of a PDF, for the page grid."""
        record = self.file_record(slug, file_id)
        if record["kind"] != "pdf" or not self.blobs.exists(self._xray_key(slug, file_id)):
            return {"file_id": file_id, "pages": [], "window_pages": None}
        xray = json.loads(self.blobs.read_bytes(self._xray_key(slug, file_id)))
        size = record.get("window_pages") or self.settings.window_pages
        committed = {
            int(match.group(1))
            for key in self.blobs.list(self._index_key(slug, file_id))
            if (match := re.search(r"/w(\d{5})\.chunks\.jsonl$", key))
        }
        pages = []
        for page in xray["pages"][: record.get("pages_total") or None]:
            window = (page["number"] - 1) // size
            pages.append(
                {
                    "number": page["number"],
                    "route": page["route"],
                    "reason": page["reason"],
                    "chars": page["chars"],
                    "window": window,
                    "done": window in committed,
                }
            )
        return {"file_id": file_id, "window_pages": size, "pages": pages}

    def coverage(self, slug: str) -> list[dict]:
        """Files still being read, and how much of each is searchable already."""
        return [
            {
                "file_id": r["id"],
                "name": r["name"],
                "status": r.get("status", "ready"),
                "pages_done": r.get("pages_done", 0),
                "pages_total": r.get("pages_total"),
            }
            for r in self.get(slug)["files"]
            if r.get("status", "ready") in ("queued", "reading")
        ]

    # --- book structure (plan v2 phase 5) --------------------------------------------------

    def _saved_sections(self, slug: str, file_id: str) -> list[dict]:
        key = self._summaries_key(slug, file_id)
        return json.loads(self.blobs.read_bytes(key))["sections"] if self.blobs.exists(key) else []

    def build_summaries(self, slug: str, record: dict) -> int:
        """Section summaries for a finished PDF, extractive and free, indexed with its
        passages. Returns how many sections were summarised (0 if it has no structure)."""
        file_id = record["id"]
        _, units = self.units(slug, file_id)
        xray = json.loads(self.blobs.read_bytes(self._xray_key(slug, file_id)))
        found = sections(outline_entries(xray["outline"], units), len(units))
        if len(found) < 2 or len(units) < self.settings.summary_min_pages:
            return 0  # a short document is its own summary
        by_page = {unit["number"]: unit for unit in units}
        texts = [
            body_sentences([by_page[n] for n in range(sec.start, sec.end + 1) if n in by_page])
            for sec in found
        ]
        common = common_shapes(texts)
        for section, sentences in zip(found, texts, strict=True):
            section.text = extractive_summary(self.embedder, sentences, common=common)
        found = [section for section in found if section.text]
        body = {"sections": [section.to_dict() for section in found]}
        self.blobs.write_bytes(self._summaries_key(slug, file_id), json.dumps(body).encode())
        self._index_summaries(slug, record, list(enumerate(found)), "s00000", "s")
        return len(found)

    def _index_summaries(
        self, slug: str, record: dict, found: list[tuple[int, Section]], part: str, marker: str
    ) -> None:
        """Index summaries as passages. A chapter summary's id ends in "#c<chapter - 1>", so a
        question naming chapter 3 can find it."""
        url = f"/collections/{slug}/files/{record['id']}"
        chunks = []
        for number, section in found:
            kind = "chapter summary" if marker == "c" else "summary"
            title = (
                f"{record['name']} › {section.path} ({kind}, pages {section.start}–{section.end})"
            )
            chunks.append(
                Chunk(
                    id=f"{record['id']}/{section.start}#{marker}{number}",
                    doc_id=f"{record['id']}/{section.start}",
                    title=title,
                    url=f"{url}#page={section.start}",
                    text=f"{title}\n{section.text}",
                )
            )
        self._write_window_index(slug, record["id"], part, chunks)
        with self._lock:  # the collection changed: rebuild its retriever on the next search
            self._retrievers.pop(slug, None)

    def ensure_chapter_summaries(
        self, slug: str, llm, wanted: set[int] | None = None, on_event: EventSink | None = None
    ) -> int:
        """Write the chapter summaries a question needs, one LLM call each, from the sections'
        extractive summaries; kept for every later question. Returns the calls made."""
        from hyper_rag.llm import complete_with_usage
        from hyper_rag.prompts import chapter_summary_prompt

        budget = self.settings.max_chapter_summaries
        calls = 0
        for record in self.get(slug)["files"]:
            saved = self._saved_sections(slug, record["id"])
            chapters = [s for s in saved if s["level"] == 0]
            if not chapters:
                continue
            changed = False
            for ordinal, chapter in enumerate(chapters, start=1):
                if chapter.get("llm") or (wanted and ordinal not in wanted) or calls >= budget:
                    continue
                notes = [chapter["text"]] + [
                    s["text"]
                    for s in saved
                    if s["level"] == 1 and chapter["start"] <= s["start"] <= chapter["end"]
                ]
                started = time.perf_counter()
                reply, usage = complete_with_usage(
                    llm, chapter_summary_prompt(chapter["title"], notes)
                )
                chapter["llm"] = " ".join(reply.split())
                calls += 1
                changed = True
                emit(
                    on_event,
                    "a.summarize",
                    file=record["id"],
                    chapter=ordinal,
                    title=chapter["title"],
                    ms=elapsed_ms(started),
                    model=usage.get("model", llm.name),
                )
            if changed:
                self.blobs.write_bytes(
                    self._summaries_key(slug, record["id"]),
                    json.dumps({"sections": saved}).encode(),
                )
                written = [
                    (ordinal - 1, Section(0, c["title"], c["start"], c["end"], c["path"], c["llm"]))
                    for ordinal, c in enumerate(chapters, start=1)
                    if c.get("llm")
                ]
                self._index_summaries(slug, record, written, "s00001", "c")
        return calls

    def promote(self, slug: str, question: str) -> list[dict]:
        """Move the windows a question probably needs to the front of the reading queue.

        The X-ray's text layer (tier 0) is searched with BM25 as soon as a file is uploaded;
        its best pages decide which windows are read next. Scanned pages have no text layer,
        so they cannot be found this way and are read in order.
        """
        promoted = []
        for record in self.get(slug)["files"]:
            if record.get("status") not in ("queued", "reading") or record["kind"] != "pdf":
                continue
            key = (slug, record["id"])
            if key not in self._tier0:
                if not self.blobs.exists(self._tier0_key(slug, record["id"])):
                    continue
                texts = json.loads(self.blobs.read_bytes(self._tier0_key(slug, record["id"])))
                self._tier0[key] = BM25Index(texts)
            hits = self._tier0[key].search(question, 6)
            size = record.get("window_pages") or self.settings.window_pages
            pages = sorted(row + 1 for row, _ in hits)
            windows = sorted(
                {(page - 1) // size for page in pages}
                - {
                    int(m.group(1))
                    for k in self.blobs.list(self._index_key(slug, record["id"]))
                    if (m := re.search(r"/w(\d{5})\.chunks\.jsonl$", k))
                }
            )
            if windows:
                self._priority.setdefault(key, set()).update(windows)
                promoted.append({"file_id": record["id"], "pages": pages, "windows": windows})
        return promoted

    def wait_for_windows(self, slug: str, promoted: list[dict], seconds: float) -> bool:
        """Wait up to `seconds` for promoted windows to be committed. True if they all were."""
        deadline = time.monotonic() + seconds
        while True:
            missing = [
                (item["file_id"], window)
                for item in promoted
                for window in item["windows"]
                if not self.blobs.exists(
                    self._window_index_key(slug, item["file_id"], window, "chunks.jsonl")
                )
            ]
            if not missing:
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.2)

    def chapter_numbers(self, question: str) -> set[int]:
        return chapter_numbers(question)

    # --- index ---------------------------------------------------------------------------

    def _documents(
        self,
        slug: str,
        record: dict,
        unit_name: str | None,
        units: list[dict],
        paths: dict[int, str] | None = None,
    ) -> list[Document]:
        """One Document per unit, so a citation resolves to a page, slide or sheet. With an
        outline, the title also says where the page sits: "book.pdf (Page 37) › Ch 3 › 3.2"."""
        documents = []
        paths = paths or {}
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
                    title=(f"{record['name']} ({unit['label']})" if labelled else record["name"])
                    + (f" › {paths[unit['number']]}" if unit["number"] in paths else ""),
                    url=url,
                    text=unit["text"],
                )
            )
        return documents

    def _register(
        self, slug: str, group: str, chunks_key: str, chunks: list[Chunk], embeddings: np.ndarray
    ) -> None:
        """Put one window's index into the vector and keyword stores."""
        namespace = self._namespace(slug)
        ids = [chunk.id for chunk in chunks]
        self.vectors.add(namespace, group, ids, embeddings if chunks else embeddings[:0])
        self.lexical.add(namespace, group, ids, [chunk.text for chunk in chunks])
        self._chunks[chunks_key] = chunks

    def _file_chunks(self, slug: str, record: dict) -> list[Chunk]:
        """A file's committed chunks, making sure the stores hold them for this embedder."""
        file_id = record["id"]
        index_key = self._index_key(slug, file_id)
        keys = [k for k in self.blobs.list(index_key) if k.endswith("chunks.jsonl")]
        if not keys and record.get("status", "ready") == "ready":
            # Indexed with a different embedding model (or before windows): index it again.
            return self._reindex(slug, record)
        namespace = self._namespace(slug)
        chunks: list[Chunk] = []
        for key in keys:
            match = re.search(r"/([ws]\d{5})\.chunks\.jsonl$", key)
            group = f"{file_id}#{match.group(1)}" if match else file_id
            cached = self._chunks.get(key)
            if (
                cached is not None
                and self.vectors.has(namespace, group)
                and self.lexical.has(namespace, group)
            ):
                chunks.extend(cached)
                continue
            lines = self.blobs.read_bytes(key).decode("utf-8").splitlines()
            window_chunks = [Chunk(**json.loads(line)) for line in lines]
            npy = key[: -len("chunks.jsonl")] + ("npy" if match else "embeddings.npy")
            embeddings = np.load(io.BytesIO(self.blobs.read_bytes(npy)))
            self._register(slug, group, key, window_chunks, embeddings)
            chunks.extend(window_chunks)
        return chunks

    def _reindex(self, slug: str, record: dict) -> list[Chunk]:
        file_id = record["id"]
        legacy = self.blobs.exists(self._legacy_parsed_key(slug, file_id))
        if legacy:
            unit_name, units = self.units(slug, file_id)
            windows = [(0, unit_name, units)]
        else:
            windows = []
            for key in self.blobs.list(self._parsed_prefix(slug, file_id)):
                match = re.search(r"/w(\d{5})\.json$", key)
                if match:
                    parsed = json.loads(self.blobs.read_bytes(key))
                    windows.append((int(match.group(1)), parsed["unit_name"], parsed["units"]))
        chunks: list[Chunk] = []
        for window, unit_name, units in windows:
            window_chunks = chunk_documents(
                self._documents(slug, record, unit_name, units),
                self.settings.upload_chunk_size,
                self.settings.upload_chunk_overlap,
                structured=True,
            )
            self._write_window_index(slug, file_id, window, window_chunks)
            chunks.extend(window_chunks)
        return chunks

    def retriever(self, slug: str) -> Retriever:
        with self._lock:
            meta = self.get(slug)
            cached = self._retrievers.get(slug)
            if cached and cached[0] == meta["updated"]:
                return cached[1]
        # Loading indexes happens outside the lock: a big upload's metadata writes must
        # not wait for it, and two loads of the same window are harmless.
        chunks: list[Chunk] = []
        for record in meta["files"]:
            if record.get("status", "ready") == "failed":
                continue
            chunks.extend(self._file_chunks(slug, record))
        if not chunks:
            reading = any(r.get("status") in ("queued", "reading") for r in meta["files"])
            raise CollectionError(
                f"Collection '{meta['name']}' is still reading its first pages. "
                "Ask again in a moment."
                if reading
                else f"Collection '{meta['name']}' has no searchable text yet. Upload a document."
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
        with self._lock:
            self._retrievers[slug] = (meta["updated"], retriever)
        return retriever

    # --- the Galaxy view (plan v2 phase 4, a demo and recording mode) --------------------

    def map(self, slug: str) -> dict:
        """Every passage of the collection placed in 3D, and the projection that placed them.

        Vectors are read from the blob store (the windows' .npy files), so this works the
        same whatever the vector store is. Cached until the collection changes."""
        from hyper_rag.projection import fit

        meta = self.get(slug)
        cached = self._maps.get(slug)
        if cached and cached[0] == meta["updated"]:
            return cached[1]
        ids, titles, files, matrices = [], [], [], []
        for record in meta["files"]:
            for key in self.blobs.list(self._index_key(slug, record["id"])):
                if not key.endswith("chunks.jsonl"):
                    continue
                lines = self.blobs.read_bytes(key).decode("utf-8").splitlines()
                if not lines:
                    continue
                stem = key[: -len("chunks.jsonl")]
                npy = stem + ("npy" if self.blobs.exists(stem + "npy") else "embeddings.npy")
                matrices.append(np.load(io.BytesIO(self.blobs.read_bytes(npy))))
                for line in lines:
                    chunk = json.loads(line)
                    ids.append(chunk["id"])
                    titles.append(chunk["title"])
                    files.append(record["id"])
        if not ids:
            raise CollectionError("This collection has no passages to map yet.")
        matrix = np.vstack(matrices).astype(np.float32)
        projection = fit(matrix)
        xyz = np.round(projection.place(matrix), 4)
        result = {
            "points": [
                {"id": cid, "file_id": fid, "title": title, "xyz": point.tolist()}
                for cid, fid, title, point in zip(ids, files, titles, xyz, strict=True)
            ],
            "files": [{"id": r["id"], "name": r["name"]} for r in meta["files"]],
            "explained": projection.explained,
            "projection": projection,
        }
        self._maps[slug] = (meta["updated"], result)
        return result

    def place_question(self, slug: str, question: str) -> list[float] | None:
        try:
            projection = self.map(slug)["projection"]
        except CollectionError:
            return None
        vector = self.embedder.embed_query(question)
        return np.round(projection.place(vector)[0], 4).tolist()

    # --- click-through citations ---------------------------------------------------------

    def source(self, slug: str, chunk_id: str) -> dict:
        """Everything the UI needs to show where a cited passage came from."""
        match = re.fullmatch(r"([0-9a-f]{12})/(\d+)#([sc]?)(\d+)", chunk_id)
        if not match:
            raise CollectionNotFound(f"No passage '{chunk_id}'")
        file_id, unit_number = match.group(1), int(match.group(2))
        record = self.file_record(slug, file_id)
        unit_name, unit = self.unit(slug, file_id, unit_number)
        chunks = self._file_chunks(slug, record)
        chunk = next((c for c in chunks if c.id == chunk_id), None)
        if unit is None or chunk is None:
            raise CollectionNotFound(f"No passage '{chunk_id}'")
        if match.group(3):
            # A summary: show it whole, next to the page its section starts on.
            body = chunk.text.split("\n", 1)[-1]
            lines = [[{"text": sentence, "hit": True}] for sentence in split_sentences(body)]
            unit = {**unit, "label": chunk.title.split(" › ", 1)[-1]}
        else:
            lines = mark_lines(unit["text"], chunk.text)
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
            "lines": lines,
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

        with PDFIUM_LOCK:  # pdfium is not thread-safe; ingestion may be using it
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


MAX_REPORT_WARNINGS = 50
TIER0_CHARS = 3000  # per page, for the just-in-time keyword index


def _empty_report(kind: str, unit_name: str | None) -> dict:
    return {
        "kind": kind,
        "unit_name": unit_name or "section",
        "units": 0,
        "characters": 0,
        "tables": 0,
        "images": 0,
        "images_with_text": 0,
        "ocr_units": 0,
        "empty_units": 0,
        "warnings": [],
    }


def _count_window(
    record: dict, units: list[Unit], warnings: list[str], chunks: int, unit_name: str | None
) -> dict:
    """Add one committed window to a record's running totals (the parse report grows as
    the file is read, so the Files tab is honest about a half-read book)."""
    report = dict(record["report"])
    report["units"] += len(units)
    report["characters"] += sum(len(u.text) for u in units)
    report["tables"] += sum(u.tables for u in units)
    report["images"] += sum(u.images for u in units)
    report["images_with_text"] += sum(u.images_with_text for u in units)
    report["ocr_units"] += sum(u.ocr for u in units)
    report["empty_units"] += sum(not u.text.strip() for u in units)
    report["warnings"] = (report["warnings"] + warnings)[:MAX_REPORT_WARNINGS]
    if unit_name:
        report["unit_name"] = unit_name
    return {
        **record,
        "report": report,
        "pages_done": record["pages_done"] + len(units),
        "windows_done": record["windows_done"] + 1,
        "chunks": record["chunks"] + chunks,
    }


# Worker processes build their own OCR engine once and keep it.
_PROCESS_OCR: dict[str, Ocr] = {}


def parse_window_in_process(
    path: str, pages: list[dict], ocr_name: str, boilerplate: list[str]
) -> tuple[list[Unit], list[str], float]:
    """Parse one window of a PDF in a worker process (settings.ingest_processes)."""
    started = time.perf_counter()
    if ocr_name not in _PROCESS_OCR:
        _PROCESS_OCR[ocr_name] = build_ocr(ocr_name)
    units, warnings = parse_pdf_pages(
        Path(path), [PageInfo(**page) for page in pages], _PROCESS_OCR[ocr_name], boilerplate
    )
    return units, warnings, elapsed_ms(started)


def _release_memory() -> None:
    """Free what a window left behind before reading the next one.

    pdfminer builds reference cycles that Python's collector reaches only now and then, so
    without this a 1.3 GB book peaked at 730 MB instead of about 150 (docs/DECISIONS.md 30).
    malloc_trim hands the freed memory back to the system (glibc only).
    """
    import contextlib
    import ctypes
    import gc

    gc.collect()
    with contextlib.suppress(OSError, AttributeError):
        ctypes.CDLL("libc.so.6").malloc_trim(0)


def _from_cache(cache: PageCache, pages: list[PageInfo]) -> tuple[dict[int, Unit], list[PageInfo]]:
    """Split a window into pages already parsed before (any file, any edition) and the rest."""
    cached, missing = {}, []
    for page in pages:
        hit = cache.get(page.hash, page.route) if page.route != "skip" else None
        if hit is not None:
            cached[page.number] = Unit(
                **{**hit, "number": page.number, "label": f"Page {page.number}"}
            )
        else:
            missing.append(page)
    return cached, missing


def _to_cache(
    cache: PageCache, pages: list[PageInfo], units: list[Unit], warnings: list[str]
) -> None:
    failed = {int(n) for n in re.findall(r"Page (\d+) could not be read", " ".join(warnings))}
    for page, unit in zip(pages, units, strict=True):
        if page.route != "skip" and page.number not in failed:
            cache.put(page.hash, page.route, unit.to_dict())


def _merge(pages: list[PageInfo], cached: dict[int, Unit], parsed: list[Unit]) -> list[Unit]:
    by_number = {unit.number: unit for unit in parsed} | cached
    return [by_number[page.number] for page in pages]


def _first_headings(units: list[dict], limit: int = 6) -> list[str]:
    headings = []
    for unit in units:
        for line in unit["text"].splitlines():
            if line.startswith("#") and len(headings) < limit:
                headings.append(line.lstrip("#").strip()[:60])
    return headings
