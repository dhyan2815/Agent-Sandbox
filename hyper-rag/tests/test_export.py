"""Answer to artifact (deck card D6)."""

import pytest
from fastapi.testclient import TestClient

from hyper_rag import api, export
from hyper_rag.llm.fake import FakeLLM
from make_files import make_pdf

ANSWER = {
    "question": "How long does a standard rooftop installation take?",
    "answer": "A standard rooftop installation takes two working days. [1]",
    "refused": False,
    "citations": [
        {
            "number": 1,
            "title": "guide.pdf (Page 1) > Scheduling",
            "url": "/collections/solar/files/ab12#page=1",
            "chunk_id": "ab12/1#0",
            "doc_id": "ab12/1",
            "text": (
                "A standard rooftop installation takes two working days.\n\n"
                "The crew arrives at 8 am."
            ),
        }
    ],
}


def test_markdown_has_the_question_answer_and_quoted_sources():
    text = export.to_markdown(ANSWER)
    assert text.startswith("# How long does a standard rooftop installation take?")
    assert "takes two working days. [1]" in text
    assert "## Sources" in text and "1. guide.pdf (Page 1) > Scheduling" in text
    # The server's own path is no link anywhere else; the quote is one flat line.
    assert "/collections/" not in text
    assert "> A standard rooftop installation takes two working days. The crew arrives" in text


def test_a_web_source_becomes_a_link_and_long_quotes_are_cut():
    web = {
        **ANSWER,
        "citations": [
            {**ANSWER["citations"][0], "url": "https://example.com/a", "text": "word " * 200}
        ],
    }
    text = export.to_markdown(web)
    assert "1. [guide.pdf (Page 1) > Scheduling](https://example.com/a)" in text
    assert "…" in text and len(max(text.splitlines(), key=len)) < 450


def test_a_refusal_is_exported_as_a_refusal():
    text = export.to_markdown({"question": "Who is the CEO?", "answer": "", "refused": True})
    assert "No answer" in text and "## Sources" not in text
    with pytest.raises(ValueError, match="declined"):
        export.to_linkedin({"question": "Q", "answer": "", "refused": True}, FakeLLM())


def test_linkedin_outline_comes_from_the_answer_without_citation_numbers():
    result = export.export_answer(ANSWER, "linkedin", FakeLLM())
    assert result["llm_calls"] == 1 and result["filename"].endswith(".txt")
    assert "two working days" in result["text"] and "[1]" not in result["text"]
    assert "\n- " in result["text"]


def test_filenames_are_safe_and_formats_are_checked():
    assert export.export_answer(ANSWER, "markdown")["filename"] == (
        "how-long-does-a-standard-rooftop-installation.md"
    )
    odd = export.export_answer({**ANSWER, "question": "../../etc/passwd?!"}, "markdown")
    assert odd["filename"] == "etc-passwd.md"
    with pytest.raises(ValueError):
        export.export_answer(ANSWER, "pdf")
    with pytest.raises(ValueError):
        export.export_answer(ANSWER, "linkedin")  # no model given


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


@pytest.fixture
def asked(client, tmp_path):
    client.post("/collections", json={"name": "Solar"})
    pdf = make_pdf(tmp_path / "guide.pdf").read_bytes()
    client.post("/collections/solar/files", files={"file": ("guide.pdf", pdf, "application/pdf")})
    return client.post("/collections/solar/ask", json={"question": ANSWER["question"]}).json()


def test_api_exports_a_saved_run(client, asked):
    body = client.post(
        "/collections/solar/export", json={"run_id": asked["run_id"], "format": "markdown"}
    ).json()
    assert body["text"].startswith("# How long") and "## Sources" in body["text"]
    post = client.post(
        "/collections/solar/export", json={"run_id": asked["run_id"], "format": "linkedin"}
    ).json()
    assert post["llm_calls"] == 1 and post["text"]


def test_api_export_errors(client, asked):
    path = "/collections/solar/export"
    assert client.post(path, json={"run_id": asked["run_id"], "format": "doc"}).status_code == 422
    missing = client.post(
        path, json={"run_id": "20260101T000000000000-abcdef", "format": "markdown"}
    )
    assert missing.status_code == 404
    assert (
        client.post(
            path, json={"run_id": "../../../../etc/passwd", "format": "markdown"}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/collections/nope/export", json={"run_id": "x" * 12, "format": "markdown"}
        ).status_code
        == 404
    )
