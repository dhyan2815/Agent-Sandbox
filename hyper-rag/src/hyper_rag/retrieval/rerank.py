"""Rerankers: rescore a short candidate list by reading query and passage together."""

from typing import Protocol

from hyper_rag.config import Settings
from hyper_rag.text import coverage


class Reranker(Protocol):
    def score(self, query: str, passages: list[str]) -> list[float]:
        """One relevance score per passage; higher is better."""
        ...


class LexicalReranker:
    """Offline stand-in: fraction of the query's content words found in the passage."""

    def score(self, query: str, passages: list[str]) -> list[float]:
        return [coverage(query, passage) for passage in passages]


class FastEmbedReranker:
    """A cross-encoder on CPU through ONNX Runtime.

    A bi-encoder embeds query and passage separately, so it can only compare summaries.
    A cross-encoder reads the pair together and can tell "refund takes 5 days" from
    "capture within 5 days". It is too slow to run over the whole corpus, which is why it
    only rescores the fused shortlist.
    """

    def __init__(self, model_name: str):
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        self._model = TextCrossEncoder(model_name)

    def score(self, query: str, passages: list[str]) -> list[float]:
        return [float(s) for s in self._model.rerank(query, passages)]


def build_reranker(settings: Settings) -> Reranker:
    if settings.reranker == "lexical":
        return LexicalReranker()
    return FastEmbedReranker(settings.reranker_model)
