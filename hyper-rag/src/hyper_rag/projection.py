"""3D positions for the Galaxy view (plan v2, phase 4): PCA over a collection's passages.

The projection is fitted once per state of the collection, with numpy (no new dependency),
and a question is placed with the same matrix multiply, so its point lands among what it
is similar to in the first three principal directions.

A projection distorts distance: two points close in 3D may not be close in 384 dimensions.
The view therefore prints the real cosine and rerank scores next to every point it
highlights; the picture is the map, the scores are the territory. UMAP, which keeps local
neighbourhoods better, is left out: umap-learn pulls in numba, and the plan made it optional.
"""

from dataclasses import dataclass

import numpy as np

FIT_SAMPLE = 5000  # rows used to fit; every row is then placed


@dataclass
class Projection:
    mean: np.ndarray  # (d,)
    components: np.ndarray  # (3, d)
    scale: float  # divides positions so the cloud fits in a unit ball
    explained: list[float]  # share of variance along each axis

    def place(self, vectors: np.ndarray) -> np.ndarray:
        return ((np.atleast_2d(vectors) - self.mean) @ self.components.T) / self.scale


def fit(matrix: np.ndarray, seed: int = 0) -> Projection:
    rows = matrix
    if len(rows) > FIT_SAMPLE:
        rng = np.random.default_rng(seed)
        rows = rows[rng.choice(len(rows), FIT_SAMPLE, replace=False)]
    mean = rows.mean(axis=0)
    centred = rows - mean
    _, singular, vt = np.linalg.svd(centred, full_matrices=False)
    components = vt[:3]
    if components.shape[0] < 3:  # fewer than 3 passages: pad with zero axes
        components = np.vstack([components, np.zeros((3 - components.shape[0], matrix.shape[1]))])
    variance = singular**2
    explained = (
        [round(float(v / variance.sum()), 3) for v in variance[:3]] if variance.sum() else []
    )
    placed = (matrix - mean) @ components.T
    scale = float(np.percentile(np.linalg.norm(placed, axis=1), 98)) or 1.0
    return Projection(mean, components, scale, explained)
