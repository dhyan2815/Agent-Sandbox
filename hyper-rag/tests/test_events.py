"""Typed events (plan v2, B0): what the engine emits, and that listening changes nothing."""

import httpx
import pytest

from hyper_rag.agent import Agent
from hyper_rag.index import ingest_pack, load_retriever
from hyper_rag.llm import complete_with_usage
from hyper_rag.llm.cache import CachedLLM
from hyper_rag.llm.fake import FakeLLM
from hyper_rag.packs import load_pack
from hyper_rag.prompts import Prompt
from test_providers import groq_with

QUESTION = "How long does a normal refund take to reach the customer?"


@pytest.fixture
def retriever(settings):
    pack = load_pack(settings.packs_dir, "sample")
    ingest_pack(pack, settings)
    return load_retriever(pack, settings)


def test_retrieval_events_rank_what_each_stage_returned(retriever):
    events = []
    hits = retriever.retrieve(QUESTION, on_event=events.append)
    assert [e["t"] for e in events] == ["q.embed", "r.dense", "r.bm25", "r.fuse", "r.rerank"]
    by_name = {e["t"]: e for e in events}
    rerank = by_name["r.rerank"]
    # The last stage's hits are exactly what retrieve() returned, in order.
    assert [h["id"] for h in rerank["hits"]] == [hit.chunk.id for hit in hits]
    assert [h["rank"] for h in rerank["hits"]] == list(range(1, len(hits) + 1))
    assert rerank["top_score"] == rerank["hits"][0]["score"]
    # Fusion only reorders what dense and BM25 found.
    found = {h["id"] for h in by_name["r.dense"]["hits"]} | {
        h["id"] for h in by_name["r.bm25"]["hits"]
    }
    assert {h["id"] for h in by_name["r.fuse"]["hits"]} <= found
    assert all(e["ms"] >= 0 for e in events)


def test_listening_does_not_change_the_result(retriever):
    for mode in ("vector", "hybrid", "hybrid_rerank"):
        quiet = retriever.retrieve(QUESTION, mode=mode)
        heard = retriever.retrieve(QUESTION, mode=mode, on_event=lambda event: None)
        assert [h.chunk.id for h in quiet] == [h.chunk.id for h in heard]


def test_vector_mode_stops_after_dense(retriever):
    events = []
    retriever.retrieve(QUESTION, mode="vector", on_event=events.append)
    assert [e["t"] for e in events] == ["q.embed", "r.dense"]


def test_agent_events_name_the_passages_it_kept_and_dropped(retriever, settings):
    agent = Agent(retriever, FakeLLM(), "payments docs", settings.max_rewrites)
    stream = list(agent.ask_events(QUESTION))
    events = [payload for kind, payload in stream if kind == "event"]
    names = [e["t"] for e in events]
    assert names[0] == "a.route" and names[-1] == "a.check"
    grade = next(e for e in events if e["t"] == "a.grade")
    rerank = next(e for e in events if e["t"] == "r.rerank")
    assert set(grade["kept"]) | set(grade["dropped"]) == {h["id"] for h in rerank["hits"]}
    answer = stream[-1][1]
    assert {c.id for c in answer.passages} == set(grade["kept"])
    # Every model call is timed and names its model.
    calls = [e for e in events if e["t"] in ("a.route", "a.grade", "a.generate", "a.check")]
    assert all(e["model"] == "fake:rule-based" and e["ms"] >= 0 for e in calls)


def test_a_declined_question_ends_with_its_reason(retriever, settings):
    agent = Agent(retriever, FakeLLM(), "payments docs", settings.max_rewrites)
    stream = list(agent.ask_events("How do I bake sourdough bread?"))
    events = [payload for kind, payload in stream if kind == "event"]
    assert "a.rewrite" in [e["t"] for e in events]  # it tried again before giving up
    assert events[-1]["t"] == "a.decline" and events[-1]["reason"]
    assert stream[-1][1].refused


def test_a_shared_agent_keeps_concurrent_listeners_apart(retriever, settings):
    # Two runs interleaved on one agent: each run's events stay in its own stream.
    agent = Agent(retriever, FakeLLM(), "payments docs", settings.max_rewrites)
    first = agent.ask_events(QUESTION)
    second = agent.ask_events("How do I bake sourdough bread?")
    a = [next(first) for _ in range(3)]
    b = list(second)
    a += list(first)
    assert not any(e[1]["t"] == "a.decline" for e in a if e[0] == "event")
    assert any(e[1]["t"] == "a.decline" for e in b if e[0] == "event")


def test_groq_reports_tokens_and_rate_limits():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "x-ratelimit-limit-requests": "1000",
                "x-ratelimit-remaining-requests": "999",
                "x-ratelimit-limit-tokens": "8000",
                "x-ratelimit-remaining-tokens": "7907",
            },
            json={
                "choices": [{"message": {"content": "hi"}}],
                "usage": {"prompt_tokens": 73, "completion_tokens": 20},
            },
        )

    text, usage = complete_with_usage(groq_with(handler), Prompt("generate", "s", "u"))
    assert text == "hi"
    assert usage == {
        "model": "groq:test-model",
        "tokens_in": 73,
        "tokens_out": 20,
        "requests_left_today": 999,
        "requests_per_day": 1000,
        "tokens_left_this_minute": 7907,
        "tokens_per_minute": 8000,
    }


def test_agent_emits_quota_and_a_cache_hit_says_so(retriever, settings, tmp_path):
    class Metered(FakeLLM):
        name = "metered"

        def complete_with_usage(self, prompt):
            usage = {"tokens_in": 10, "tokens_out": 2, "requests_left_today": 42}
            return self.complete(prompt), usage

    llm = CachedLLM(Metered(), tmp_path / "cache")
    agent = Agent(retriever, llm, "payments docs", settings.max_rewrites)

    first = [p for kind, p in agent.ask_events(QUESTION) if kind == "event"]
    quota = [e for e in first if e["t"] == "llm.quota"]
    assert quota and quota[-1] == {"t": "llm.quota", "model": "metered", "requests_left_today": 42}
    generate = next(e for e in first if e["t"] == "a.generate")
    assert generate["tokens_in"] == 10 and "cached" not in generate

    again = [p for kind, p in agent.ask_events(QUESTION) if kind == "event"]
    assert next(e for e in again if e["t"] == "a.generate")["cached"] is True
    assert not [e for e in again if e["t"] == "llm.quota"]  # no call, so no fresh numbers
