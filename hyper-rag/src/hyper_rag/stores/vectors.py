"""Vector storage: chunk embeddings per collection, searchable by cosine similarity.

A namespace is one collection under one embedding model (vectors from different models
are not comparable). Inside it, vectors are added in groups (one window of a file's pages,
named "<file id>#w00003") and removed a whole file at a time.

Today's implementation keeps the matrices in memory and scans them exactly, the same
search the packs use (`DenseIndex`). The hosted one (plan v2, A7) is a Qdrant collection
with int8 quantization, which keeps vectors on disk and survives restarts.
"""

import threading
from typing import Protocol

import numpy as np

from hyper_rag.retrieval.dense import DenseIndex


class VectorStore(Protocol):
    def has(self, namespace: str, file_id: str) -> bool:
        """Whether this file's vectors are already stored, so loading them can be skipped."""
        ...

    def add(self, namespace: str, file_id: str, chunk_ids: list[str], vectors: np.ndarray) -> None:
        """Store one file's vectors (row i belongs to chunk_ids[i]), replacing earlier ones."""
        ...

    def remove(self, namespace: str, file_id: str) -> None:
        """Remove the file's groups: `file_id` itself and every "file_id#..." group."""
        ...

    def drop(self, namespace: str) -> None: ...

    def search(self, namespace: str, query_vector: np.ndarray, k: int) -> list[tuple[str, float]]:
        """The k most similar chunks as (chunk id, cosine similarity), best first."""
        ...


class NumpyVectorStore:
    name = "numpy"

    def __init__(self) -> None:
        self._files: dict[str, dict[str, tuple[list[str], np.ndarray]]] = {}
        # The stacked matrix of a namespace, rebuilt on the first search after a change.
        self._stacked: dict[str, tuple[list[str], DenseIndex]] = {}
        self._lock = threading.Lock()

    def has(self, namespace: str, file_id: str) -> bool:
        with self._lock:
            return file_id in self._files.get(namespace, {})

    def add(self, namespace: str, file_id: str, chunk_ids: list[str], vectors: np.ndarray) -> None:
        if len(chunk_ids) != len(vectors):
            raise ValueError(f"{len(chunk_ids)} chunk ids for {len(vectors)} vectors")
        with self._lock:
            files = self._files.setdefault(namespace, {})
            files.pop(file_id, None)  # re-adding moves the file to the end, like an upload
            files[file_id] = (list(chunk_ids), vectors)
            self._stacked.pop(namespace, None)

    def remove(self, namespace: str, file_id: str) -> None:
        with self._lock:
            files = self._files.get(namespace, {})
            for group in [g for g in files if _belongs(g, file_id)]:
                del files[group]
            self._stacked.pop(namespace, None)

    def drop(self, namespace: str) -> None:
        with self._lock:
            self._files.pop(namespace, None)
            self._stacked.pop(namespace, None)

    def _index(self, namespace: str) -> tuple[list[str], DenseIndex | None]:
        with self._lock:
            if namespace not in self._stacked:
                files = [f for f in self._files.get(namespace, {}).values() if f[0]]
                if not files:
                    return [], None
                ids = [chunk_id for file_ids, _ in files for chunk_id in file_ids]
                self._stacked[namespace] = (ids, DenseIndex(np.vstack([m for _, m in files])))
            return self._stacked[namespace]

    def search(self, namespace: str, query_vector: np.ndarray, k: int) -> list[tuple[str, float]]:
        ids, index = self._index(namespace)
        if index is None:
            return []
        return [(ids[row], score) for row, score in index.search(query_vector, k)]


def _belongs(group: str, file_id: str) -> bool:
    """A file's vectors are stored in groups: the file id, or "<file id>#<window>"."""
    return group == file_id or group.startswith(file_id + "#")
