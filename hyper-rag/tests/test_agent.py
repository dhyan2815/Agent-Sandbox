import json

import pytest

from hyper_rag.agent import Agent, single_shot_answer
from hyper_rag.index import ingest_pack, load_retriever
from hyper_rag.llm import build_llm
from hyper_rag.llm.fake import FakeLLM
from hyper_rag.packs import load_pack
from hyper_rag.prompts import REFUSAL_MESSAGE


@pytest.fixture
def pack(settings):
    return load_pack(settings.packs_dir, "sample")


@pytest.fixture
def retriever(settings, pack):
    ingest_pack(pack, settings)
    return load_retriever(pack, settings)


@pytest.fixture
def agent(settings, pack, retriever):
    return Agent(retriever, build_llm(settings), pack.config.description, settings.max_rewrites)


def test_answers_with_a_citation_to_the_right_document(agent):
    answer = agent.ask("How long does a normal refund take to reach the customer?")
    assert not answer.refused
    assert "5 to 7 business days" in answer.text
    assert answer.citations and answer.citations[0][1].doc_id == "refunds"
    assert answer.invalid_citations == []
    assert answer.trace[0] == "route: retrieve" and answer.trace[-1] == "check: grounded"
    assert answer.llm_calls == 4  # route, grade, generate, check


def test_rewrites_then_declines_when_nothing_relevant_is_found(agent, settings):
    answer = agent.ask("How do I bake sourdough bread at home?")
    assert answer.refused and answer.text == REFUSAL_MESSAGE
    assert sum(step.startswith("rewrite") for step in answer.trace) == settings.max_rewrites
    assert sum(step.startswith("retrieve") for step in answer.trace) == settings.max_rewrites + 1
    assert answer.trace[-1].startswith("decline: no relevant passages")


class ScriptedLLM(FakeLLM):
    """The fake provider, with chosen tasks overridden to force a specific branch."""

    def __init__(self, **replies: str):
        self.replies = replies

    def complete(self, prompt):
        return self.replies.get(prompt.task) or super().complete(prompt)


def test_router_can_decline_without_retrieving(pack, retriever):
    llm = ScriptedLLM(route=json.dumps({"route": "decline"}))
    answer = Agent(retriever, llm, pack.config.description).ask("What's the weather today?")
    assert answer.refused and answer.llm_calls == 1
    assert not any(step.startswith("retrieve") for step in answer.trace)


def test_self_check_blocks_an_unsupported_draft(pack, retriever):
    llm = ScriptedLLM(generate="Refunds arrive within 30 seconds, guaranteed. [1]")
    answer = Agent(retriever, llm, pack.config.description).ask("How long does a refund take?")
    assert answer.refused
    assert "not supported by the sources" in answer.trace[-1]


def test_unparseable_check_reply_fails_closed(pack, retriever):
    llm = ScriptedLLM(check="I think it is probably fine")
    assert (
        Agent(retriever, llm, pack.config.description).ask("How long does a refund take?").refused
    )


def test_out_of_range_citations_are_flagged(pack, retriever):
    llm = ScriptedLLM(
        generate="A refund takes 5 to 7 business days. [9]", check='{"grounded": true}'
    )
    answer = Agent(retriever, llm, pack.config.description).ask("How long does a refund take?")
    assert answer.cited == [] and answer.invalid_citations == [9]


def test_single_shot_baseline_answers_and_refuses(settings, retriever):
    llm = build_llm(settings)
    good = single_shot_answer(
        "Which header carries the webhook signature?", retriever, llm, "hybrid"
    )
    assert "X-Lumen-Signature" in good.text and good.llm_calls == 1
    assert single_shot_answer("How do I bake sourdough bread?", retriever, llm, "hybrid").refused
