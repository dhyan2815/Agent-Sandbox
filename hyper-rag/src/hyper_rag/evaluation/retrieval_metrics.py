"""Retrieval metrics, computed at document level.

A golden question lists its information needs. Each need is a group of documents, any
one of which contains that piece of the answer. Most questions have one need; a
question that combines two facts from different pages has two.

    "relevant_sources": [["refunds/normal", "refunds/faqs"], ["settlements"]]
                          need 1: either page will do      need 2

A retrieved chunk satisfies a need if it comes from one of that need's documents.
Document-level labels survive changes to chunk size (chunk ids would not), at the
price of being lenient: a chunk from the right page that misses the exact sentence
still counts.
"""

import math

Needs = list[list[str]]


def recall_at_k(retrieved_docs: list[str], needs: Needs, k: int) -> float:
    """Fraction of the needs satisfied by at least one of the top k chunks."""
    if not needs:
        return 0.0
    top = set(retrieved_docs[:k])
    return sum(1 for need in needs if top & set(need)) / len(needs)


def reciprocal_rank(retrieved_docs: list[str], needs: Needs) -> float:
    """1 / rank of the first chunk that satisfies any need, 0 if there is none."""
    wanted = {doc for need in needs for doc in need}
    for rank, doc in enumerate(retrieved_docs, start=1):
        if doc in wanted:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved_docs: list[str], needs: Needs, k: int) -> float:
    """Normalised discounted cumulative gain with binary relevance.

    Only the first chunk that satisfies each need earns gain. Otherwise three chunks
    from the same page would score higher than one chunk for each of three needs.
    """
    if not needs:
        return 0.0
    open_needs = [set(need) for need in needs]
    dcg = 0.0
    for rank, doc in enumerate(retrieved_docs[:k], start=1):
        for need in open_needs:
            if doc in need:
                open_needs.remove(need)
                dcg += 1.0 / math.log2(rank + 1)
                break
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, min(len(needs), k) + 1))
    return dcg / ideal


def facts_in_top_k(retrieved_texts: list[str], key_facts: list[str], k: int) -> float:
    """1.0 if every key fact of the answer appears somewhere in the top k chunks, else 0.0.

    This is the passage-level counterpart to recall: it asks whether the generator was
    actually shown the answer, not just a chunk from the right page.
    """
    shown = " ".join(retrieved_texts[:k]).lower()
    return 1.0 if all(fact.lower() in shown for fact in key_facts) else 0.0


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
