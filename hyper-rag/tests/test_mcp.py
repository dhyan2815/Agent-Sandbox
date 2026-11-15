"""MCP server (deck card D1): the five tools, over the local engine and over HTTP."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from hyper_rag import api
from hyper_rag.mcp_server import LocalBackend, RemoteBackend, build_server
from make_files import make_pdf

QUESTION = "How long does a standard rooftop installation take?"


def call(server, name, **arguments):
    """Call a tool the way an MCP client does. Returns its structured result."""
    _, structured = asyncio.run(server.call_tool(name, arguments))
    return structured.get("result", structured)


@pytest.fixture
def local(store, settings, tmp_path):
    store.create("Solar")
    store.add_file("solar", "guide.pdf", make_pdf(tmp_path / "guide.pdf").read_bytes())
    return build_server(LocalBackend(settings, store))


def test_the_server_offers_five_tools_and_marks_them_read_only(local):
    tools = asyncio.run(local.list_tools())
    assert {t.name for t in tools} == {
        "list_collections",
        "search",
        "ask",
        "get_source",
        "check_claims",
    }
    assert all(t.annotations.readOnlyHint for t in tools)


def test_list_search_ask_and_open_a_source(local):
    [solar] = call(local, "list_collections")
    assert solar["slug"] == "solar" and solar["files"] == ["guide.pdf"] and solar["passages"] > 0

    hits = call(local, "search", collection="solar", query=QUESTION, top_k=3)
    assert 1 <= len(hits) <= 3 and "two working days" in hits[0]["text"]
    assert hits[0]["score"] >= hits[-1]["score"]

    answer = call(local, "ask", collection="solar", question=QUESTION)
    assert not answer["declined"] and "two working days" in answer["answer"]
    cited = answer["citations"][0]

    source = call(local, "get_source", collection="solar", chunk_id=cited["chunk_id"])
    assert source["file"] == "guide.pdf" and "**" in source["text"]  # the cited line is marked


def test_a_question_the_documents_cannot_answer_is_declined(local):
    answer = call(
        local, "ask", collection="solar", question="What is the capital city of Mongolia?"
    )
    assert answer["declined"] is True and answer["citations"] == []


def test_check_claims_tool_and_its_input_limits(local):
    text = "A standard rooftop installation takes two working days. The crew arrives at 8 am."
    report = call(local, "check_claims", collection="solar", text=text)
    assert report["summary"]["supported"] == 2
    with pytest.raises(Exception, match="between 20 and 4000"):
        call(local, "check_claims", collection="solar", text="too short")


def test_errors_reach_the_model_as_messages_and_top_k_is_capped(local):
    with pytest.raises(Exception, match="No collection"):
        call(local, "search", collection="missing", query="x")
    with pytest.raises(Exception, match="No collection"):
        call(local, "search", collection="../../etc", query="x")
    hits = call(local, "search", collection="solar", query="warranty", top_k=999)
    assert len(hits) <= 10


# --- the same tools against a deployed app's HTTP API -----------------------------------


@pytest.fixture
def served(settings, store, tmp_path, monkeypatch):
    protected = settings.model_copy(update={"password": "open sesame"})
    monkeypatch.setattr(api, "get_settings", lambda: protected)
    monkeypatch.setattr(api, "get_store", lambda: store)
    for cached in (api.get_llms, api.get_jobs, api.get_quota):
        cached.cache_clear()
    store.create("Solar")
    store.add_file("solar", "guide.pdf", make_pdf(tmp_path / "guide.pdf").read_bytes())
    yield lambda: TestClient(api.app, base_url="https://hyper.example")
    for cached in (api.get_llms, api.get_jobs, api.get_quota):
        cached.cache_clear()


def test_remote_backend_logs_in_and_uses_every_tool(served):
    remote = build_server(RemoteBackend("https://hyper.example", "open sesame", client=served()))
    [solar] = call(remote, "list_collections")
    assert solar["slug"] == "solar"
    hits = call(remote, "search", collection="solar", query=QUESTION, top_k=2)
    assert "two working days" in hits[0]["text"]
    answer = call(remote, "ask", collection="solar", question=QUESTION)
    assert not answer["declined"]
    source = call(
        remote, "get_source", collection="solar", chunk_id=answer["citations"][0]["chunk_id"]
    )
    assert source["file"] == "guide.pdf"
    report = call(
        remote, "check_claims", collection="solar", text="The crew arrives at 8 am on the day."
    )
    assert "claims" in report


def test_remote_backend_reports_a_wrong_password_clearly(served):
    remote = build_server(RemoteBackend("https://hyper.example", "wrong", client=served()))
    with pytest.raises(Exception, match="refused the password"):
        call(remote, "list_collections")


def test_without_a_password_the_login_wall_is_reported_not_hidden(served):
    remote = build_server(RemoteBackend("https://hyper.example", "", client=served()))
    with pytest.raises(Exception, match="401"):
        call(remote, "list_collections")


def test_search_endpoint_uses_no_model_budget(served, settings, monkeypatch):
    limited = settings.model_copy(update={"password": "", "model_requests_per_hour": 1})
    monkeypatch.setattr(api, "get_settings", lambda: limited)
    api.get_quota.cache_clear()
    client = served()
    for _ in range(3):
        assert client.get("/collections/solar/search", params={"q": "warranty"}).status_code == 200
    assert client.get("/collections/solar/search", params={"q": ""}).status_code == 422
