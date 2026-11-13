"""The retrieval pipeline: dense + BM25 -> reciprocal rank fusion -> rerank."""

from typing import Literal

from hyper_rag.config import Settings
from hyper_rag.retrieval.bm25 import BM25Index
from hyper_rag.retrieval.dense import DenseIndex
from hyper_rag.retrieval.embedders import Embedder
from hyper_rag.retrieval.fusion import reciprocal_rank_fusion
from hyper_rag.retrieval.rerank import Reranker
from hyper_rag.types import Chunk, ScoredChunk

# The three retrieval configurations compared in the ablation.
Mode = Literal["vector", "hybrid", "hybrid_rerank"]
MODES: tuple[Mode, ...] = ("vector", "hybrid", "hybrid_rerank")


class Retriever:
    def __init__(
        self,
        chunks: list[Chunk],
        dense: DenseIndex,
        bm25: BM25Index,
        embedder: Embedder,
        reranker: Reranker,
        settings: Settings,
    ):
        self.chunks = chunks
        self.dense = dense
        self.bm25 = bm25
        self.embedder = embedder
        self.reranker = reranker
        self.settings = settings

    def retrieve(
        self, query: str, mode: Mode = "hybrid_rerank", top_k: int | None = None
    ) -> list[ScoredChunk]:
        top_k = top_k or self.settings.top_k
        pool = self.settings.candidates_per_retriever

        dense_hits = self.dense.search(self.embedder.embed_query(query), pool)
        if mode == "vector":
            return [ScoredChunk(self.chunks[row], score) for row, score in dense_hits[:top_k]]

        bm25_hits = self.bm25.search(query, pool)
        fused = reciprocal_rank_fusion(
            [[row for row, _ in dense_hits], [row for row, _ in bm25_hits]],
            k=self.settings.rrf_k,
        )
        if mode == "hybrid":
            return [ScoredChunk(self.chunks[row], score) for row, score in fused[:top_k]]

        # hybrid_rerank: the cross-encoder rescores only the fused shortlist.
        shortlist = [self.chunks[row] for row, _ in fused[: self.settings.rerank_pool]]
        scores = self.reranker.score(query, [chunk.text for chunk in shortlist])
        # sorted() is stable, so equal scores keep their fused order.
        ranked = sorted(zip(shortlist, scores, strict=True), key=lambda pair: -pair[1])
        return [ScoredChunk(chunk, score) for chunk, score in ranked[:top_k]]
