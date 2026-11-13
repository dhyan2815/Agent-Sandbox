import json
import time

import pytest
from fastapi.testclient import TestClient

from hyper_rag import api
from make_files import make_html, make_pdf


@pytest.fixture
def client(settings, store):
    originals = api.get_settings, api.get_store
    api.get_settings, api.get_store = (lambda: settings), (lambda: store)
    api.get_llms.cache_clear()
    api.get_jobs.cache_clear()
    yield TestClient(api.app)
    api.get_settings, api.get_store = originals
    api.get_llms.cache_clear()
    api.get_jobs.cache_clear()


@pytest.fixture
def uploaded(client, tmp_path):
    """A collection 'solar' with the three-page test PDF in it. Returns the file record."""
    assert client.post("/collections", json={"name": "Solar"}).status_code == 201
    pdf = make_pdf(tmp_path / "guide.pdf").read_bytes()
    response = client.post(
        "/collections/solar/files", files={"file": ("guide.pdf", pdf, "application/pdf")}
    )
    assert response.status_code == 201
    return response.json()


def test_create_upload_and_read_the_parse_report(client, uploaded):
    assert uploaded["report"]["units"] == 3 and uploaded["report"]["tables"] == 1
    listed = client.get("/collections").json()["collections"]
    assert [c["slug"] for c in listed] == ["solar"]
    files = client.get("/collections/solar").json()["files"]
    assert files[0]["name"] == "guide.pdf" and files[0]["chunks"] == uploaded["chunks"]


def test_ask_with_follow_up_and_open_the_citation(client, uploaded):
    question = "How long does a standard rooftop installation take?"
    first = client.post("/collections/solar/ask", json={"question": question}).json()
    assert "two working days" in first["answer"] and not first["refused"]

    follow_up = client.post(
        "/collections/solar/ask",
        json={
            "question": "How long is that?",
            "history": [{"question": question, "answer": first["answer"]}],
        },
    ).json()
    assert follow_up["trace"][0].startswith("condense:") and not follow_up["refused"]

    citation = first["citations"][0]
    source = client.get("/collections/solar/source", params={"chunk_id": citation["chunk_id"]})
    assert source.json()["unit_label"] == "Page 1"
    assert any(span["hit"] for line in source.json()["lines"] for span in line)
    page = client.get(source.json()["preview_url"])
    assert page.headers["content-type"] == "image/png" and page.content.startswith(b"\x89PNG")


def test_streamed_answer_sends_steps_then_the_answer(client, uploaded):
    with client.stream(
        "POST",
        "/collections/solar/ask/stream",
        json={"question": "How long does a standard rooftop installation take?"},
    ) as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        events = [
            json.loads(line[6:]) for line in response.iter_lines() if line.startswith("data: ")
        ]
    steps = [e for e in events if e["type"] == "step"]
    typed = [e["t"] for e in events if e["type"] == "event"]
    assert {e["type"] for e in events[:-1]} == {"step", "event"}
    assert steps[0]["text"].startswith("retrieve: ")  # uploads skip the router
    assert typed[:6] == ["a.retrieve", "q.embed", "r.dense", "r.bm25", "r.fuse", "r.rerank"]
    assert typed[6:] == ["a.grade", "a.generate", "a.check"]
    assert events[-1]["type"] == "answer" and "two working days" in events[-1]["answer"]

    # The run was saved with every event, so it can be replayed.
    run = client.get(f"/collections/solar/runs/{events[-1]['run_id']}").json()
    assert [e["t"] for e in run["events"]] == typed
    assert run["answer"]["answer"] == events[-1]["answer"]
    listed = client.get("/collections/solar/runs").json()["runs"]
    assert listed[0]["id"] == run["id"] and listed[0]["events"] == len(typed)


def test_originals_pdf_inline_html_only_as_download(client, uploaded, tmp_path):
    pdf = client.get(f"/collections/solar/files/{uploaded['id']}")
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.headers["content-disposition"].startswith("inline")

    html = make_html(tmp_path / "returns.html").read_bytes()
    record = client.post(
        "/collections/solar/files", files={"file": ("returns.html", html, "text/html")}
    ).json()
    served = client.get(f"/collections/solar/files/{record['id']}")
    assert served.headers["content-disposition"].startswith("attachment")
    assert served.headers["x-content-type-options"] == "nosniff"


def test_errors_are_reported_with_the_right_status(client, uploaded):
    assert client.post("/collections", json={"name": "Solar"}).status_code == 400  # exists
    assert client.get("/collections/nope").status_code == 404
    assert client.post("/collections/nope/ask", json={"question": "anything?"}).status_code == 404
    bad = client.post("/collections/solar/files", files={"file": ("a.exe", b"MZ", "x/y")})
    assert bad.status_code == 400 and "not supported" in bad.json()["detail"]
    assert client.get("/collections/solar/source", params={"chunk_id": "x"}).status_code == 404

    client.post("/collections", json={"name": "Empty"})
    empty = client.post("/collections/empty/ask", json={"question": "anything?"})
    assert empty.status_code == 400 and "Upload a document" in empty.json()["detail"]
    assert client.post("/collections/empty/eval", json={}).status_code == 400


def test_remove_file_and_delete_collection(client, uploaded):
    assert client.delete(f"/collections/solar/files/{uploaded['id']}").status_code == 204
    assert client.get("/collections/solar").json()["files"] == []
    assert client.delete("/collections/solar").status_code == 204
    assert client.get("/collections").json()["collections"] == []


def test_evaluation_runs_in_the_background_and_reports(client, uploaded):
    assert client.get("/collections/solar/eval").json()["state"] == "idle"
    assert client.post("/collections/solar/eval", json={"questions": 3}).status_code == 202
    for _ in range(100):
        status = client.get("/collections/solar/eval").json()
        if status["state"] != "running":
            break
        time.sleep(0.05)
    assert status["state"] == "done", status
    assert status["report"]["retrieval"][0]["mode"] == "vector"
    assert [row["config"] for row in status["report"]["answers"]] == ["hybrid_rerank", "agent"]
    assert any("test questions" in line for line in status["log"])


def test_config_lists_what_can_be_uploaded(client):
    body = client.get("/config").json()
    assert body["offline"] is True and ".pdf" in body["extensions"] and body["max_upload_mb"] == 25
