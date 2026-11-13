import pytest
from fastapi.testclient import TestClient

from hyper_rag import api
from hyper_rag.index import ingest_pack
from hyper_rag.packs import load_pack


@pytest.fixture
def client(settings):
    ingest_pack(load_pack(settings.packs_dir, "sample"), settings)
    api.get_agent.cache_clear()
    api.app.dependency_overrides = {}
    original = api.get_settings
    api.get_settings = lambda: settings
    yield TestClient(api.app)
    api.get_settings = original
    api.get_agent.cache_clear()


def test_ask_returns_answer_with_citations(client):
    response = client.post(
        "/ask", json={"pack": "sample", "question": "Which header carries the webhook signature?"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "X-Lumen-Signature" in body["answer"] and not body["refused"]
    assert body["citations"][0]["url"].endswith("webhooks.md")


def test_ask_declines_unanswerable_question(client):
    response = client.post(
        "/ask", json={"pack": "sample", "question": "How do I bake sourdough bread?"}
    )
    assert response.json()["refused"] is True and response.json()["citations"] == []


def test_unknown_pack_is_404_and_bad_input_is_422(client):
    assert (
        client.post("/ask", json={"pack": "nope", "question": "anything at all"}).status_code == 404
    )
    assert client.post("/ask", json={"pack": "sample", "question": ""}).status_code == 422


def test_lists_packs(client):
    assert "sample" in client.get("/packs").json()["packs"]


def test_serves_the_web_page(client):
    response = client.get("/")
    assert response.status_code == 200 and "Hyper-RAG" in response.text
