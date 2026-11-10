"""Retrieval metrics, computed at document level.

Golden questions list the documents that contain the answer. A retrieved chunk counts
as relevant if it comes from one of those documents. Document-level labels survive
changes to chunk size (chunk ids would not), at the price of being lenient: a chunk
from the right page that misses the exact sentence still counts.
"""

import math


def recall_at_k(retrieved_docs: list[str], gold_docs: list[str], k: int) -> float:
    """Fraction of the gold documents that appear among the top k retrieved chunks."""
    if not gold_docs:
        return 0.0
    return len(set(retrieved_docs[:k]) & set(gold_docs)) / len(set(gold_docs))


def reciprocal_rank(retrieved_docs: list[str], gold_docs: list[str]) -> float:
    """1 / rank of the first relevant chunk, 0 if none was retrieved."""
    for rank, doc in enumerate(retrieved_docs, start=1):
        if doc in gold_docs:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved_docs: list[str], gold_docs: list[str], k: int) -> float:
    """Normalised discounted cumulative gain with binary relevance.

    Only the first chunk from each gold document earns gain. Otherwise three chunks
    from the same page would score higher than one chunk each from three needed pages.
    """
    if not gold_docs:
        return 0.0
    seen: set[str] = set()
    dcg = 0.0
    for rank, doc in enumerate(retrieved_docs[:k], start=1):
        if doc in gold_docs and doc not in seen:
            seen.add(doc)
            dcg += 1.0 / math.log2(rank + 1)
    ideal_hits = min(len(set(gold_docs)), k)
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / ideal


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
