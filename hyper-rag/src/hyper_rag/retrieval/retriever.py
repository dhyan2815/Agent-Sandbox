"""The retrieval pipeline: dense + BM25 -> reciprocal rank fusion -> rerank."""

import time
from collections.abc import Callable
from typing import Literal, Protocol

import numpy as np

from hyper_rag.config import Settings
from hyper_rag.events import EventSink, elapsed_ms, emit, ranked
from hyper_rag.retrieval.embedders import Embedder
from hyper_rag.retrieval.fusion import reciprocal_rank_fusion
from hyper_rag.retrieval.rerank import Reranker
from hyper_rag.types import Chunk, ScoredChunk

# The three retrieval configurations compared in the ablation.
Mode = Literal["vector", "hybrid", "hybrid_rerank"]
MODES: tuple[Mode, ...] = ("vector", "hybrid", "hybrid_rerank")


class VectorIndex(Protocol):
    """Dense search over the retriever's chunks. A row is a position in `chunks`."""

    def search(self, query_vector: np.ndarray, k: int) -> list[tuple[int, float]]: ...


class LexicalIndex(Protocol):
    """Keyword search over the retriever's chunks. A row is a position in `chunks`."""

    def search(self, query: str, k: int) -> list[tuple[int, float]]: ...


class Retriever:
    def __init__(
        self,
        chunks: list[Chunk],
        dense: VectorIndex,
        bm25: LexicalIndex,
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

    def _ids(self, rows: list[int]) -> list[str]:
        return [self.chunks[row].id for row in rows]

    def retrieve(
        self,
        query: str,
        mode: Mode = "hybrid_rerank",
        top_k: int | None = None,
        on_event: EventSink | None = None,
        allow: Callable[[Chunk], bool] | None = None,
    ) -> list[ScoredChunk]:
        """Search for `query`. With `on_event`, each stage reports its ranked hits and time:
        q.embed, r.dense, then for hybrid modes r.bm25 and r.fuse, then r.rerank. With
        `allow`, chunks it rejects are dropped from both searches before anything else."""
        top_k = top_k or self.settings.top_k
        pool = self.settings.candidates_per_retriever
        # Over-fetch a little when filtering, so the pool is still full afterwards.
        fetch = pool * 2 if allow else pool

        started = time.perf_counter()
        query_vector = self.embedder.embed_query(query)
        emit(on_event, "q.embed", ms=elapsed_ms(started))

        started = time.perf_counter()
        dense_hits = self.dense.search(query_vector, fetch)
        if allow:
            dense_hits = [h for h in dense_hits if allow(self.chunks[h[0]])][:pool]
        if on_event:
            rows, scores = [r for r, _ in dense_hits], [s for _, s in dense_hits]
            emit(on_event, "r.dense", hits=ranked(self._ids(rows), scores), ms=elapsed_ms(started))
        if mode == "vector":
            return [ScoredChunk(self.chunks[row], score) for row, score in dense_hits[:top_k]]

        started = time.perf_counter()
        bm25_hits = self.bm25.search(query, fetch)
        if allow:
            bm25_hits = [h for h in bm25_hits if allow(self.chunks[h[0]])][:pool]
        if on_event:
            rows, scores = [r for r, _ in bm25_hits], [s for _, s in bm25_hits]
            emit(on_event, "r.bm25", hits=ranked(self._ids(rows), scores), ms=elapsed_ms(started))

        started = time.perf_counter()
        fused = reciprocal_rank_fusion(
            [[row for row, _ in dense_hits], [row for row, _ in bm25_hits]],
            k=self.settings.rrf_k,
        )
        if on_event:
            shown = fused[: self.settings.rerank_pool]
            rows, scores = [r for r, _ in shown], [s for _, s in shown]
            emit(on_event, "r.fuse", hits=ranked(self._ids(rows), scores), ms=elapsed_ms(started))
        if mode == "hybrid":
            return [ScoredChunk(self.chunks[row], score) for row, score in fused[:top_k]]

        # hybrid_rerank: the cross-encoder rescores only the fused shortlist.
        started = time.perf_counter()
        shortlist = [self.chunks[row] for row, _ in fused[: self.settings.rerank_pool]]
        scores = self.reranker.score(query, [chunk.text for chunk in shortlist])
        # sorted() is stable, so equal scores keep their fused order.
        ranked_pairs = sorted(zip(shortlist, scores, strict=True), key=lambda pair: -pair[1])
        kept = ranked_pairs[:top_k]
        if on_event:
            emit(
                on_event,
                "r.rerank",
                hits=ranked([c.id for c, _ in kept], [s for _, s in kept]),
                top_score=round(float(kept[0][1]), 4) if kept else None,
                ms=elapsed_ms(started),
            )
        return [ScoredChunk(chunk, score) for chunk, score in kept]
