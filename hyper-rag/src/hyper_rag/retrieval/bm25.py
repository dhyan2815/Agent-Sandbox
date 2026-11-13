"""Sparse retrieval: BM25 over word tokens."""

import numpy as np
from rank_bm25 import BM25Okapi

from hyper_rag.text import tokenize


class BM25Index:
    def __init__(self, texts: list[str]):
        self._bm25 = BM25Okapi([tokenize(t) for t in texts])

    def search(self, query: str, k: int) -> list[tuple[int, float]]:
        """Return (row, score) for the k best-matching chunks, best first."""
        scores = self._bm25.get_scores(tokenize(query))
        k = min(k, len(scores))
        top = np.argsort(-scores)[:k]
        # A score of 0 means no query term occurs in the chunk: not a match, leave it out
        # so it cannot earn rank credit during fusion.
        return [(int(i), float(scores[i])) for i in top if scores[i] > 0]
