# Phase 2: retrieval with Qdrant against numpy + rank_bm25

Qdrant: `http://127.0.0.1:6333`. Same chunks, same embeddings (fastembed), same reranker; only the dense and keyword search change. Rule: no metric may drop by more than one question's worth.

## payments (2389 chunks, 32 questions)

| Mode | Store | recall@5 | MRR | nDCG@10 | facts@5 |
|---|---|---|---|---|---|
| vector | numpy + rank_bm25 | 0.984 | 0.88 | 0.91 | 0.96 |
| vector | Qdrant | 0.984 | 0.88 | 0.91 | 0.96 |
| hybrid | numpy + rank_bm25 | 0.984 | 0.892 | 0.914 | 0.96 |
| hybrid | Qdrant | 0.969 | 0.901 | 0.921 | 0.96 |
| hybrid_rerank | numpy + rank_bm25 | 0.984 | 0.912 | 0.929 | 0.92 |
| hybrid_rerank | Qdrant | 0.984 | 0.938 | 0.947 | 0.96 |

## papers (654 chunks, 15 questions)

| Mode | Store | recall@5 | MRR | nDCG@10 | facts@5 |
|---|---|---|---|---|---|
| vector | numpy + rank_bm25 | 0.933 | 0.94 | 0.947 | 0.786 |
| vector | Qdrant | 0.933 | 0.94 | 0.947 | 0.786 |
| hybrid | numpy + rank_bm25 | 0.967 | 0.95 | 0.948 | 0.929 |
| hybrid | Qdrant | 0.967 | 0.933 | 0.925 | 1.0 |
| hybrid_rerank | numpy + rank_bm25 | 1.0 | 1.0 | 1.0 | 0.929 |
| hybrid_rerank | Qdrant | 1.0 | 1.0 | 1.0 | 0.929 |

Result: passed.
