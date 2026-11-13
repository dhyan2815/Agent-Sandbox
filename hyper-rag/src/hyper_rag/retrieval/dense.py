"""Dense retrieval: exact cosine similarity over a matrix of chunk embeddings."""

import numpy as np


class DenseIndex:
    def __init__(self, embeddings: np.ndarray):
        # Rows are L2-normalised, so a dot product is the cosine similarity.
        self.embeddings = embeddings

    def search(self, query_vector: np.ndarray, k: int) -> list[tuple[int, float]]:
        """Return (row, score) for the k most similar chunks, best first.

        This is a full scan: one matrix-vector product. For the corpus sizes here (a few
        thousand chunks x 384 dimensions) that takes well under a millisecond, and unlike
        an approximate index it cannot miss a neighbour.
        """
        scores = self.embeddings @ query_vector
        k = min(k, len(scores))
        top = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in top]
