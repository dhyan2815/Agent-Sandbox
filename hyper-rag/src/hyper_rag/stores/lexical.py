"""Lexical storage: keyword (BM25) search per collection.

Same shape as the vector store: namespaces, whole files added and removed. BM25's term
statistics (IDF) depend on the whole collection, so today's implementation rebuilds the
index on the first search after a change. The hosted one (plan v2, A7) is Qdrant sparse
vectors or SQLite FTS5, which update in place.
"""

import threading
from typing import Protocol

from hyper_rag.retrieval.bm25 import BM25Index


class LexicalStore(Protocol):
    def has(self, namespace: str, file_id: str) -> bool: ...

    def add(self, namespace: str, file_id: str, chunk_ids: list[str], texts: list[str]) -> None: ...

    def remove(self, namespace: str, file_id: str) -> None: ...

    def drop(self, namespace: str) -> None: ...

    def search(self, namespace: str, query: str, k: int) -> list[tuple[str, float]]:
        """The k best keyword matches as (chunk id, BM25 score), best first; no zero scores."""
        ...


class BM25LexicalStore:
    name = "bm25"

    def __init__(self) -> None:
        self._files: dict[str, dict[str, tuple[list[str], list[str]]]] = {}
        self._built: dict[str, tuple[list[str], BM25Index]] = {}
        self._lock = threading.Lock()

    def has(self, namespace: str, file_id: str) -> bool:
        with self._lock:
            return file_id in self._files.get(namespace, {})

    def add(self, namespace: str, file_id: str, chunk_ids: list[str], texts: list[str]) -> None:
        if len(chunk_ids) != len(texts):
            raise ValueError(f"{len(chunk_ids)} chunk ids for {len(texts)} texts")
        with self._lock:
            files = self._files.setdefault(namespace, {})
            files.pop(file_id, None)
            files[file_id] = (list(chunk_ids), list(texts))
            self._built.pop(namespace, None)

    def remove(self, namespace: str, file_id: str) -> None:
        with self._lock:
            self._files.get(namespace, {}).pop(file_id, None)
            self._built.pop(namespace, None)

    def drop(self, namespace: str) -> None:
        with self._lock:
            self._files.pop(namespace, None)
            self._built.pop(namespace, None)

    def _index(self, namespace: str) -> tuple[list[str], BM25Index | None]:
        with self._lock:
            if namespace not in self._built:
                files = [f for f in self._files.get(namespace, {}).values() if f[0]]
                if not files:
                    return [], None
                ids = [chunk_id for file_ids, _ in files for chunk_id in file_ids]
                texts = [text for _, file_texts in files for text in file_texts]
                self._built[namespace] = (ids, BM25Index(texts))
            return self._built[namespace]

    def search(self, namespace: str, query: str, k: int) -> list[tuple[str, float]]:
        ids, index = self._index(namespace)
        if index is None:
            return []
        return [(ids[row], score) for row, score in index.search(query, k)]
