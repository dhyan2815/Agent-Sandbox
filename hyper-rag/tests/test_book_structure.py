"""Plan v2 phase 5: book structure (outline paths, summaries) and just-in-time reading."""

import threading
import time

import pytest
from fastapi.testclient import TestClient

from hyper_rag import api
from hyper_rag.llm.fake import FakeLLM
from hyper_rag.structure import chapter_numbers, is_global, page_paths, sections
from hyper_rag.uploads import CollectionStore
from make_files import make_book


@pytest.fixture
def books(settings):
    from conftest import StubOcr

    store = CollectionStore(settings.model_copy(update={"window_pages": 8}), ocr=StubOcr())
    store.create("Manual")
    return store


def test_questions_about_a_whole_are_recognised():
    for question in (
        "Summarise the book",
        "What is chapter 3 about?",
        "Compare chapters 2 and 5",
        "Which chapter covers billing?",
        "What is the main argument?",
    ):
        assert is_global(question), question
    for question in ("What is the inspection code for row 7?", "How long is the warranty?"):
        assert not is_global(question), question
    assert chapter_numbers("Compare chapters 2 and 5") == {2, 5}
    assert chapter_numbers("What is chapter 3 about?") == {3}


def test_outline_paths_and_section_ranges():
    entries = [
        {"level": 0, "title": "One", "page": 1},
        {"level": 1, "title": "1.1", "page": 1},
        {"level": 1, "title": "1.2", "page": 4},
        {"level": 0, "title": "Two", "page": 7},
    ]
    paths = page_paths(entries, 9)
    assert paths[3] == "One › 1.1" and paths[5] == "One › 1.2" and paths[8] == "Two"
    found = {(s.title, s.start, s.end, s.path) for s in sections(entries, 9)}
    assert ("One", 1, 6, "One") in found and ("1.2", 4, 6, "One › 1.2") in found
    assert ("Two", 7, 9, "Two") in found


def test_a_book_with_an_outline_gets_paths_and_section_summaries(books, tmp_path):
    record = books.add_path("manual", "book.pdf", make_book(tmp_path / "b.pdf", 40, outline=True))
    assert record["sections"] == 12  # 4 chapters and 8 sections
    chunks = books.retriever("manual").chunks
    page_37 = next(c for c in chunks if c.id.startswith(f"{record['id']}/37#"))
    assert "Chapter 4: Site work part 4 › 4.2 Rows 36 onward" in page_37.title
    summary = next(c for c in chunks if c.id == f"{record['id']}/11#s3")
    assert "summary, pages 11–20" in summary.title
    body = summary.text.split("\n", 1)[1]
    assert body.count(".") == 3  # three sentences, all from the chapter's own pages
    assert all(11 <= int(n) <= 20 for n in __import__("re").findall(r"Row (\d+)", body))
    source = books.source("manual", summary.id)
    assert source["unit_number"] == 11 and all(line[0]["hit"] for line in source["lines"])


def test_chapter_summaries_are_written_once_and_found_by_number(books, tmp_path):
    books.add_path("manual", "book.pdf", make_book(tmp_path / "b.pdf", 40, outline=True))
    events = []
    assert books.ensure_chapter_summaries("manual", FakeLLM(), {2}, events.append) == 1
    assert [e["t"] for e in events] == ["a.summarize"] and events[0]["chapter"] == 2
    assert books.ensure_chapter_summaries("manual", FakeLLM(), {2}) == 0  # kept
    assert books.ensure_chapter_summaries("manual", FakeLLM()) == 3  # the other three

    from hyper_rag.structure import SummaryFirst

    retriever = SummaryFirst(books.retriever("manual"), {3})
    hits = retriever.retrieve("What is chapter 3 about?")
    assert hits[0].chunk.id.endswith("#c2") and "chapter summary" in hits[0].chunk.title


def test_short_documents_get_no_summaries(books, tmp_path):
    record = books.add_path("manual", "short.pdf", make_book(tmp_path / "s.pdf", 12, outline=True))
    assert "sections" not in record
    assert not [c for c in books.retriever("manual").chunks if "#s" in c.id]


def test_a_question_moves_the_pages_it_needs_to_the_front(books, tmp_path):
    record = books.stage_file("manual", "book.pdf", make_book(tmp_path / "b.pdf", 64))
    committed = []
    started = threading.Event()
    original = books._commit_window

    def slow(slug, rec, window, *args):
        committed.append(window)
        started.set()
        time.sleep(0.15)
        return original(slug, rec, window, *args)

    books._commit_window = slow
    thread = threading.Thread(target=books.ingest_file, args=("manual", record["id"]))
    thread.start()
    assert started.wait(10)
    # Page 60's fact is in window 7 (pages 57-64), the last one.
    promoted = books.promote("manual", "inspection code for panel row 60 NW-0420")
    assert promoted and 7 in promoted[0]["windows"] and 59 in promoted[0]["pages"] or promoted
    assert books.wait_for_windows("manual", promoted, 10)
    thread.join(20)
    assert committed.index(7) < committed.index(3)  # read before the windows in between
    hits = books.retriever("manual").retrieve("inspection code for panel row 60")
    assert hits[0].chunk.id.startswith(f"{record['id']}/60#")


def test_the_api_prepares_whole_book_questions(settings, books, tmp_path):
    books.add_path("manual", "book.pdf", make_book(tmp_path / "b.pdf", 40, outline=True))
    originals = api.get_settings, api.get_store
    api.get_settings, api.get_store = (lambda: books.settings), (lambda: books)
    api.get_llms.cache_clear()
    try:
        client = TestClient(api.app)
        body = client.post("/collections/manual/ask", json={"question": "What is chapter 2 about?"})
        assert body.status_code == 200, body.text
        run = client.get(f"/collections/manual/runs/{body.json()['run_id']}").json()
        names = [e["t"] for e in run["events"]]
        assert names[:2] == ["a.summarize", "q.global"] and "r.summaries" in names
        assert any(c["chunk_id"].endswith("#c1") for c in body.json()["citations"])
    finally:
        api.get_settings, api.get_store = originals
        api.get_llms.cache_clear()
