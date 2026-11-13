"""Reciprocal rank fusion (Cormack, Clarke & Buettcher, 2009)."""


def reciprocal_rank_fusion(rankings: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    """Merge several ranked lists of item ids into one.

    Each list gives an item 1 / (k + rank) points; points are summed across lists.
    Only ranks are used, never raw scores. That matters here because cosine similarity
    (0..1) and BM25 (unbounded) are on different scales, and any attempt to normalise
    them needs tuning per corpus. k=60 damps the gap between rank 1 and rank 2 so one
    retriever's top hit cannot outvote an item both retrievers placed reasonably high.
    """
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    # Sort by score; break ties by id so the output is deterministic.
    return sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
