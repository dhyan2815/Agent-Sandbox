"""Text -> vector. Two implementations behind one interface."""

import hashlib
from typing import Protocol

import numpy as np

from hyper_rag.config import Settings
from hyper_rag.text import tokenize


class Embedder(Protocol):
    name: str  # part of the index folder name, so indexes from different embedders never mix

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        """One L2-normalised row per text."""
        ...

    def embed_query(self, text: str) -> np.ndarray: ...


class HashingEmbedder:
    """Offline stand-in: a bag of words hashed into a fixed number of buckets.

    No model and no download, fully deterministic. It only captures word overlap, so it
    behaves like a weak lexical retriever. Good enough to test the pipeline, not to ship.
    """

    name = "hashing-512"
    dimensions = 512

    def _embed(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dimensions, dtype=np.float32)
        for token in tokenize(text):
            # md5 rather than hash(): Python's hash() is salted per process.
            bucket = int.from_bytes(hashlib.md5(token.encode()).digest()[:4], "little")
            vector[bucket % self.dimensions] += 1.0
        norm = np.linalg.norm(vector)
        return vector / norm if norm else vector

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return np.vstack([self._embed(t) for t in texts])

    def embed_query(self, text: str) -> np.ndarray:
        return self._embed(text)


class FastEmbedEmbedder:
    """A small sentence-embedding model running on CPU through ONNX Runtime."""

    def __init__(self, model_name: str):
        from fastembed import TextEmbedding  # imported here so offline runs never load it

        self.name = model_name.replace("/", "--")
        self._model = TextEmbedding(model_name)

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return _normalise(np.array(list(self._model.passage_embed(texts)), dtype=np.float32))

    def embed_query(self, text: str) -> np.ndarray:
        # query_embed adds the model's query instruction prefix where the model defines one.
        return _normalise(np.array(list(self._model.query_embed(text)), dtype=np.float32))[0]


def _normalise(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.where(norms == 0, 1.0, norms)


def build_embedder(settings: Settings) -> Embedder:
    if settings.embedder == "hashing":
        return HashingEmbedder()
    return FastEmbedEmbedder(settings.embedding_model)
