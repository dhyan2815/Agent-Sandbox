"""Typed events: what the engine did, with timings and the objects involved.

Every event is a flat JSON object with a "t" field naming it, for example

    {"t": "r.rerank", "hits": [{"id": "ab12/3#0", "rank": 1, "score": 7.9}], "ms": 120}

Names are grouped by prefix: "q." the question, "r." retrieval, "a." agent decisions,
"llm." provider budget. The full list is in docs/PLAN-v2-scale-visuals-features.md (B0).

Producers take an optional `on_event` callable and call it synchronously. Passing None
(the default) costs nothing, so `Agent.ask` and the retriever behave exactly as before
for callers that do not listen. Events are data for a UI and for saved replays, so they
never carry secrets or prompts: only queries, chunk ids, counts, scores and timings. A sink
should only record (append to a list, put on a queue); it runs inside the question.
"""

import time
from collections.abc import Callable, Sequence

Event = dict
EventSink = Callable[[Event], None]


def emit(sink: EventSink | None, name: str, **fields) -> None:
    if sink is not None:
        sink({"t": name, **fields})


def elapsed_ms(started: float) -> float:
    """Milliseconds since a time.perf_counter() reading, rounded for display."""
    return round((time.perf_counter() - started) * 1000, 1)


def ranked(ids: Sequence[str], scores: Sequence[float]) -> list[dict]:
    """A ranked hit list in event form: rank 1 is the best."""
    return [
        {"id": chunk_id, "rank": rank, "score": round(float(score), 4)}
        for rank, (chunk_id, score) in enumerate(zip(ids, scores, strict=True), start=1)
    ]
