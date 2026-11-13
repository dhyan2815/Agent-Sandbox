"""Qdrant as the vector and keyword store (plan v2, A7): survives restarts, grows without RAM.

Each namespace (a collection under one embedding model) becomes two Qdrant collections:

    <prefix><namespace>-dense    the chunk embeddings, cosine, int8 scalar quantization kept
                                 in RAM with the full vectors on disk
    <prefix><namespace>-bm25     sparse term vectors with Qdrant's IDF modifier: BM25 scored
                                 on the server, updated in place (no rebuild per upload)

A point is one chunk: its id is derived from the chunk id, and its payload names the
chunk, its group (one window of one file) and its file, so a file is removed with a filter.

The keyword scores are BM25 with a fixed average document length (Qdrant keeps the IDF,
not the lengths), so they differ from rank_bm25's. Fusion uses ranks only, and the
regression check in docs/DECISIONS.md 32 compares the two on the packs.

Works against Qdrant Cloud (url + QDRANT_API_KEY), a local server, or the client's
in-process mode (url ":memory:"), which the tests use.
"""

import re
import threading
import uuid
import zlib
from collections import Counter

import numpy as np

from hyper_rag.text import tokenize

K1, B, AVERAGE_LENGTH = 1.2, 0.75, 180.0  # BM25 constants; chunks average about 180 words
_NAMESPACE_IDS = uuid.UUID("6f1d2c4e-9b1a-4e0c-8f3a-2d7b5e9c1a40")


def _point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(_NAMESPACE_IDS, chunk_id))


def _term_id(term: str) -> int:
    return zlib.crc32(term.encode("utf-8"))  # stable across processes, unlike hash()


def sparse_document(text: str) -> tuple[list[int], list[float]]:
    """BM25's term-frequency part per term; Qdrant multiplies in the IDF at query time."""
    tokens = tokenize(text)
    counts = Counter(_term_id(token) for token in tokens)
    norm = K1 * (1 - B + B * len(tokens) / AVERAGE_LENGTH)
    indices = sorted(counts)
    return indices, [counts[i] * (K1 + 1) / (counts[i] + norm) for i in indices]


def sparse_query(text: str) -> tuple[list[int], list[float]]:
    indices = sorted({_term_id(token) for token in tokenize(text)})
    return indices, [1.0] * len(indices)


class _Qdrant:
    """What the two stores share: the client, collection naming and group bookkeeping."""

    kind = ""

    def __init__(self, url: str, api_key: str = "", prefix: str = "hyper-rag-", client=None):
        from qdrant_client import QdrantClient

        if client is not None:
            self.client = client
        elif url == ":memory:":
            self.client = QdrantClient(location=":memory:")
        else:
            self.client = QdrantClient(url=url, api_key=api_key or None, timeout=60)
        self.prefix = prefix
        self._lock = threading.Lock()
        self._known: dict[str, bool] = {}

    def _name(self, namespace: str) -> str:
        safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", namespace).strip("-")
        return f"{self.prefix}{safe}-{self.kind}"

    def _exists(self, namespace: str) -> bool:
        name = self._name(namespace)
        if not self._known.get(name):
            self._known[name] = self.client.collection_exists(name)
        return self._known[name]

    def has(self, namespace: str, file_id: str) -> bool:
        from qdrant_client import models

        if not self._exists(namespace):
            return False
        hits = self.client.count(
            self._name(namespace),
            count_filter=models.Filter(
                must=[models.FieldCondition(key="group", match=models.MatchValue(value=file_id))]
            ),
            exact=True,
        )
        return hits.count > 0

    def remove(self, namespace: str, file_id: str) -> None:
        """Remove the file's groups: `file_id` itself and every "file_id#..." group."""
        from qdrant_client import models

        if not self._exists(namespace):
            return
        self.client.delete(
            self._name(namespace),
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="file_id", match=models.MatchValue(value=file_id.split("#")[0])
                        )
                    ]
                )
            ),
            wait=True,
        )

    def drop(self, namespace: str) -> None:
        name = self._name(namespace)
        if self.client.collection_exists(name):
            self.client.delete_collection(name)
        self._known.pop(name, None)

    def _payloads(self, group: str, chunk_ids: list[str]) -> list[dict]:
        file_id = group.split("#")[0]
        return [{"chunk_id": cid, "group": group, "file_id": file_id} for cid in chunk_ids]

    def _replace(self, namespace: str, group: str, points: list) -> None:
        from qdrant_client import models

        name = self._name(namespace)
        # Re-adding a group replaces it: delete its old points first.
        self.client.delete(
            name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="group", match=models.MatchValue(value=group))]
                )
            ),
            wait=True,
        )
        for start in range(0, len(points), 256):
            self.client.upsert(name, points=points[start : start + 256], wait=True)

    def _indexes(self, name: str) -> None:
        from qdrant_client import models

        for field in ("group", "file_id"):
            self.client.create_payload_index(name, field, models.PayloadSchemaType.KEYWORD)


class QdrantVectorStore(_Qdrant):
    name = "qdrant"
    kind = "dense"

    def _ensure(self, namespace: str, dimension: int) -> None:
        from qdrant_client import models

        with self._lock:
            if self._exists(namespace):
                return
            name = self._name(namespace)
            self.client.create_collection(
                name,
                vectors_config=models.VectorParams(
                    size=dimension, distance=models.Distance.COSINE, on_disk=True
                ),
                quantization_config=models.ScalarQuantization(
                    scalar=models.ScalarQuantizationConfig(
                        type=models.ScalarType.INT8, quantile=0.99, always_ram=True
                    )
                ),
            )
            self._indexes(name)
            self._known[name] = True

    def add(self, namespace: str, file_id: str, chunk_ids: list[str], vectors: np.ndarray) -> None:
        from qdrant_client import models

        if len(chunk_ids) != len(vectors):
            raise ValueError(f"{len(chunk_ids)} chunk ids for {len(vectors)} vectors")
        if not chunk_ids:
            return
        self._ensure(namespace, int(vectors.shape[1]))
        points = [
            models.PointStruct(id=_point_id(cid), vector=vector.tolist(), payload=payload)
            for cid, vector, payload in zip(
                chunk_ids, vectors, self._payloads(file_id, chunk_ids), strict=True
            )
        ]
        self._replace(namespace, file_id, points)

    def search(self, namespace: str, query_vector: np.ndarray, k: int) -> list[tuple[str, float]]:
        from qdrant_client import models

        if not self._exists(namespace):
            return []
        hits = self.client.query_points(
            self._name(namespace),
            query=query_vector.tolist(),
            limit=k,
            with_payload=["chunk_id"],
            # Rescore the int8 shortlist with the full vectors: quantization speeds the
            # search up without changing which chunks come out on top.
            search_params=models.SearchParams(
                quantization=models.QuantizationSearchParams(rescore=True, oversampling=2.0)
            ),
        ).points
        return [(hit.payload["chunk_id"], float(hit.score)) for hit in hits]


class QdrantLexicalStore(_Qdrant):
    name = "qdrant-bm25"
    kind = "bm25"

    def _ensure(self, namespace: str) -> None:
        from qdrant_client import models

        with self._lock:
            if self._exists(namespace):
                return
            name = self._name(namespace)
            self.client.create_collection(
                name,
                vectors_config={},
                sparse_vectors_config={
                    "bm25": models.SparseVectorParams(modifier=models.Modifier.IDF)
                },
            )
            self._indexes(name)
            self._known[name] = True

    def add(self, namespace: str, file_id: str, chunk_ids: list[str], texts: list[str]) -> None:
        from qdrant_client import models

        if len(chunk_ids) != len(texts):
            raise ValueError(f"{len(chunk_ids)} chunk ids for {len(texts)} texts")
        if not chunk_ids:
            return
        self._ensure(namespace)
        points = []
        for cid, text, payload in zip(
            chunk_ids, texts, self._payloads(file_id, chunk_ids), strict=True
        ):
            indices, values = sparse_document(text)
            points.append(
                models.PointStruct(
                    id=_point_id(cid),
                    vector={"bm25": models.SparseVector(indices=indices, values=values)},
                    payload=payload,
                )
            )
        self._replace(namespace, file_id, points)

    def search(self, namespace: str, query: str, k: int) -> list[tuple[str, float]]:
        from qdrant_client import models

        indices, values = sparse_query(query)
        if not indices or not self._exists(namespace):
            return []
        hits = self.client.query_points(
            self._name(namespace),
            query=models.SparseVector(indices=indices, values=values),
            using="bm25",
            limit=k,
            with_payload=["chunk_id"],
        ).points
        return [(hit.payload["chunk_id"], float(hit.score)) for hit in hits if hit.score > 0]
