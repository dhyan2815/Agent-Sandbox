"""Claim checker (deck card D4)."""

import json

import pytest
from fastapi.testclient import TestClient

from hyper_rag import api, claims
from hyper_rag.llm.fake import FakeLLM
from hyper_rag.prompts import Prompt
from hyper_rag.structure import PassagesOnly
from make_files import make_pdf

DRAFT = (
    "A standard rooftop installation takes two working days. "
    "A standard rooftop installation takes 5 working days. "
    "The company was founded in 1998 by two brothers in Pune."
)


@pytest.fixture
def collection(store, tmp_path):
    store.create("Solar")
    store.add_file("solar", "guide.pdf", make_pdf(tmp_path / "guide.pdf").read_bytes())
    return PassagesOnly(store.retriever("solar"))


def test_each_claim_is_supported_contradicted_or_not_found(collection):
    report = claims.check_claims(collection, FakeLLM(), DRAFT)
    verdicts = [c.verdict for c in report.claims]
    assert verdicts == ["supported", "contradicted", "not_found"]
    assert report.summary() == {"supported": 1, "contradicted": 1, "not_found": 1}
    supported, contradicted, missing = report.claims
    assert "two working days" in supported.evidence.text
    assert contradicted.evidence is not None
    assert missing.evidence is None and missing.closest is not None  # something to look at
    assert report.llm_calls == 2  # one to split, one verdict batch


def test_many_claims_are_judged_in_batches_and_capped(collection):
    text = " ".join(f"Component number {i} carries a warranty of {i} years." for i in range(1, 15))
    report = claims.check_claims(collection, FakeLLM(), text, max_claims=10)
    assert len(report.claims) == 10 and report.truncated
    assert report.llm_calls == 1 + 3  # split, then 4 + 4 + 2 claims


class Scripted:
    """An LLM that replies with fixed JSON, to test how bad replies are handled."""

    name = "scripted"

    def __init__(self, claims_reply, verify_reply):
        self.replies = {"claims": claims_reply, "verify": verify_reply}

    def complete(self, prompt: Prompt) -> str:
        return self.replies[prompt.task]


def test_a_verdict_without_a_real_passage_is_not_found(collection):
    claims_reply = json.dumps({"claims": ["A", "B", "C", "D"]})
    verify_reply = json.dumps(
        {
            "verdicts": [
                {"claim": 1, "verdict": "supported", "passage": 99},  # no such passage
                {"claim": 2, "verdict": "supported"},  # nothing to point at
                {"claim": 3, "verdict": "true", "passage": 1},  # not a verdict
                {"claim": 4, "verdict": "contradicted", "passage": 1},  # the only valid one
            ]
        }
    )
    report = claims.check_claims(collection, Scripted(claims_reply, verify_reply), "x" * 30)
    assert [c.verdict for c in report.claims] == [
        "not_found",
        "not_found",
        "not_found",
        "contradicted",
    ]


def test_unreadable_replies_fail_closed(collection):
    report = claims.check_claims(collection, Scripted("not json", "also not json"), DRAFT)
    # The split fell back to the text's sentences; the verdicts fell back to not_found.
    assert len(report.claims) == 3 and {c.verdict for c in report.claims} == {"not_found"}


@pytest.fixture
def client(settings, store):
    originals = api.get_settings, api.get_store
    api.get_settings, api.get_store = (lambda: settings), (lambda: store)
    for cached in (api.get_llms, api.get_jobs, api.get_quota):
        cached.cache_clear()
    yield TestClient(api.app)
    api.get_settings, api.get_store = originals
    for cached in (api.get_llms, api.get_jobs, api.get_quota):
        cached.cache_clear()


def test_api_checks_a_text_against_a_collection(client, tmp_path):
    client.post("/collections", json={"name": "Solar"})
    pdf = make_pdf(tmp_path / "guide.pdf").read_bytes()
    client.post("/collections/solar/files", files={"file": ("guide.pdf", pdf, "application/pdf")})
    body = client.post("/collections/solar/check", json={"text": DRAFT}).json()
    assert body["summary"] == {"supported": 1, "contradicted": 1, "not_found": 1}
    first = body["claims"][0]
    assert first["verdict"] == "supported" and first["evidence"]["chunk_id"].startswith(
        first["evidence"]["doc_id"]
    )


def test_api_rejects_short_text_and_empty_collections(client):
    client.post("/collections", json={"name": "Empty"})
    assert client.post("/collections/empty/check", json={"text": "too short"}).status_code == 422
    assert client.post("/collections/empty/check", json={"text": DRAFT}).status_code == 400
    assert client.post("/collections/nope/check", json={"text": DRAFT}).status_code == 404
