"""Score each retrieval mode on a pack's golden set. Needs no LLM."""

from hyper_rag.evaluation.retrieval_metrics import mean, ndcg_at_k, recall_at_k, reciprocal_rank
from hyper_rag.packs import GoldenQuestion
from hyper_rag.retrieval.retriever import MODES, Retriever

# Retrieve 10 so recall@10 can be reported next to the top-5 the generator actually sees.
EVAL_DEPTH = 10


def evaluate_retrieval(retriever: Retriever, golden: list[GoldenQuestion]) -> list[dict]:
    """One row of averaged metrics per retrieval mode, over the answerable questions."""
    answerable = [q for q in golden if q.answerable]
    rows = []
    for mode in MODES:
        per_question = []
        for question in answerable:
            hits = retriever.retrieve(question.question, mode=mode, top_k=EVAL_DEPTH)
            docs = [hit.chunk.doc_id for hit in hits]
            gold = question.relevant_sources
            per_question.append(
                {
                    "recall@5": recall_at_k(docs, gold, 5),
                    "recall@10": recall_at_k(docs, gold, 10),
                    "mrr": reciprocal_rank(docs, gold),
                    "ndcg@10": ndcg_at_k(docs, gold, 10),
                }
            )
        row = {"mode": mode, "questions": len(answerable)}
        for metric in ("recall@5", "recall@10", "mrr", "ndcg@10"):
            row[metric] = round(mean([scores[metric] for scores in per_question]), 3)
        rows.append(row)
    return rows
