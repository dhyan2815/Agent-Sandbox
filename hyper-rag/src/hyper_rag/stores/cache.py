"""Caches that make repeated work free (plan v2, A6).

Pages: the parsed text of a PDF page, keyed by the page's content hash from the X-ray
(its text without running headers, plus its images' raw bytes), the route, the OCR engine
and the parser version. A new edition of a 900-page manual with 14 changed pages parses 14
pages; a resumed job never parses a page twice. Kept in the blob store, so it survives a
restart along with the files.

Embeddings: one vector per chunk text and embedding model, in a local SQLite file. A
re-read page whose chunks did not change is not embedded again. Losing this file costs
time, never correctness, so it stays on local disk.
"""

import hashlib
import json
import sqlite3
import threading
from pathlib import Path

import numpy as np

# Bump when the page parsers change what they produce, so old cached pages are not reused.
PARSER_VERSION = "2"


class PageCache:
    def __init__(self, blobs, ocr_name: str, boilerplate: list[str]):
        self.blobs = blobs
        fingerprint = hashlib.sha1(("\n".join(sorted(boilerplate))).encode()).hexdigest()[:8]
        self.salt = f"v{PARSER_VERSION}-{ocr_name}-{fingerprint}"

    def _key(self, page_hash: str, route: str) -> str:
        return f"cache/pages/{self.salt}-{route}-{page_hash}.json"

    def get(self, page_hash: str, route: str) -> dict | None:
        if not page_hash:
            return None
        try:
            return json.loads(self.blobs.read_bytes(self._key(page_hash, route)))
        except KeyError:
            return None

    def put(self, page_hash: str, route: str, unit: dict) -> None:
        if page_hash:
            body = json.dumps(unit, ensure_ascii=False).encode("utf-8")
            self.blobs.write_bytes(self._key(page_hash, route), body)


class EmbeddingCache:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS vectors (model TEXT, sha TEXT, vector BLOB, "
            "PRIMARY KEY (model, sha))"
        )
        self._lock = threading.Lock()

    @staticmethod
    def _sha(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    def embed(self, embedder, texts: list[str]) -> tuple[np.ndarray, int]:
        """Vectors for `texts`, embedding only the ones not seen before. Returns the
        matrix and how many were embedded now."""
        shas = [self._sha(text) for text in texts]
        found: dict[str, np.ndarray] = {}
        with self._lock:
            for start in range(0, len(shas), 500):
                batch = shas[start : start + 500]
                rows = self._db.execute(
                    f"SELECT sha, vector FROM vectors WHERE model = ? AND sha IN "
                    f"({','.join('?' * len(batch))})",
                    [embedder.name, *batch],
                ).fetchall()
                found.update({sha: np.frombuffer(blob, dtype=np.float32) for sha, blob in rows})
        missing = [i for i, sha in enumerate(shas) if sha not in found]
        if missing:
            fresh = embedder.embed_documents([texts[i] for i in missing]).astype(np.float32)
            with self._lock:
                self._db.executemany(
                    "INSERT OR REPLACE INTO vectors VALUES (?, ?, ?)",
                    [(embedder.name, shas[i], fresh[j].tobytes()) for j, i in enumerate(missing)],
                )
            for j, i in enumerate(missing):
                found[shas[i]] = fresh[j]
        return np.vstack([found[sha] for sha in shas]), len(missing)
