"""Plan v2 phase 1: big files read in windows, in the background, resumably."""

import json
import threading

import pytest
from fastapi.testclient import TestClient

from hyper_rag import api
from hyper_rag.background import IngestWorker, UploadSessions
from hyper_rag.parsing.xray import xray_pdf
from hyper_rag.stores.jobs import SqliteJobStore
from hyper_rag.uploads import CollectionError, CollectionStore
from make_files import make_book


class Killed(BaseException):
    """Stands in for kill -9: not an Exception, so nothing on the way up handles it."""


@pytest.fixture
def small_windows(settings):
    return settings.model_copy(update={"window_pages": 8, "ocr": "none"})


@pytest.fixture
def books(small_windows, tmp_path):
    from conftest import StubOcr

    store = CollectionStore(small_windows, ocr=StubOcr())
    store.create("Manual")
    return store


def test_xray_routes_strips_running_lines_and_skips_blank_and_copied_pages(tmp_path):
    path = make_book(tmp_path / "book.pdf", pages=20, blank_every=10, repeat_page=3)
    xray = xray_pdf(path)
    assert len(xray.pages) == 23
    counts = xray.counts()
    assert counts["skip"] == 3 and counts["fast-text"] == 20
    reasons = sorted(p.reason for p in xray.pages if p.route == "skip")
    assert reasons == ["blank", "blank", "copy of an earlier page"]
    assert "page # of #" in xray.boilerplate
    assert any("field manual" in line for line in xray.boilerplate)
    assert xray.summary()["estimate_seconds"] >= 0


def test_a_book_is_read_in_windows_without_its_running_lines(books, tmp_path):
    path = make_book(tmp_path / "book.pdf", pages=40)
    events = []
    record = books.stage_file("manual", "book.pdf", path)
    done = books.ingest_file("manual", record["id"], on_event=events.append)
    assert done["status"] == "ready" and done["pages_done"] == 40
    assert done["windows_total"] == 5 and done["windows_done"] == 5
    assert [e["t"] for e in events].count("ingest.commit") == 5
    assert events[0]["t"] == "ingest.triage" and events[-1]["t"] == "ingest.done"
    _, units = books.units("manual", record["id"])
    assert len(units) == 40
    text = "\n".join(u["text"] for u in units)
    assert "Page 3 of 40" not in text and "internal edition" not in text
    assert "## Chapter 2: Site work part 2" in units[10]["text"]
    # A citation reads one window, and finds its page.
    hits = books.retriever("manual").retrieve("inspection code for panel row 37")
    top = hits[0].chunk
    assert top.id.startswith(f"{record['id']}/37#")
    assert books.source("manual", top.id)["unit_label"] == "Page 37"
    grid = books.pages("manual", record["id"])
    assert len(grid["pages"]) == 40 and all(p["done"] for p in grid["pages"])


def test_search_works_on_the_pages_read_so_far(books, tmp_path):
    path = make_book(tmp_path / "book.pdf", pages=40)
    record = books.stage_file("manual", "book.pdf", path)
    seen = {}

    def after_first_window(event):
        if event["t"] == "ingest.commit" and event["window"] == 0:
            seen["coverage"] = books.coverage("manual")
            hits = books.retriever("manual").retrieve("inspection code for panel row 5", top_k=20)
            seen["pages"] = {int(h.chunk.doc_id.split("/")[1]) for h in hits}

    books.ingest_file("manual", record["id"], on_event=after_first_window)
    assert seen["pages"] and max(seen["pages"]) <= 8  # only window 0 was searchable
    assert seen["coverage"][0]["pages_done"] == 8 and seen["coverage"][0]["pages_total"] == 40
    assert books.coverage("manual") == []  # finished


def test_a_crash_resumes_after_the_last_committed_window(books, small_windows, tmp_path):
    path = make_book(tmp_path / "book.pdf", pages=40)
    record = books.stage_file("manual", "book.pdf", path)
    parsed_pages = []
    original = books._commit_window

    def crash_on_third(slug, rec, window, units, *args):
        parsed_pages.extend(u.number for u in units)
        if window == 2:
            raise Killed()
        return original(slug, rec, window, units, *args)

    books._commit_window = crash_on_third
    with pytest.raises(Killed):
        books.ingest_file("manual", record["id"])
    assert books.file_record("manual", record["id"])["status"] == "reading"

    # A new process: new store objects, empty search stores, the same blobs.
    from conftest import StubOcr

    restarted = CollectionStore(small_windows, ocr=StubOcr())
    resumed_pages = []
    original_restarted = restarted._commit_window

    def count(slug, rec, window, units, *args):
        resumed_pages.extend(u.number for u in units)
        return original_restarted(slug, rec, window, units, *args)

    restarted._commit_window = count
    jobs = SqliteJobStore(small_windows.data_dir / "jobs.sqlite3")
    worker = IngestWorker(restarted, jobs)
    assert worker.resume() == 1
    worker.wait()
    done = restarted.file_record("manual", record["id"])
    assert done["status"] == "ready" and done["pages_done"] == 40
    assert min(resumed_pages) == 17  # windows 0 and 1 (pages 1-16) were not read again
    assert sorted(set(parsed_pages[:16]) | set(resumed_pages)) == list(range(1, 41))
    chunks = restarted.retriever("manual").chunks
    summaries = [c for c in chunks if "#s" in c.id]
    assert len(chunks) - len(summaries) == done["chunks"]
    assert len(summaries) == done["sections"] == 4  # one per chapter of the book


def test_questions_do_not_wait_for_a_big_file(books, tmp_path):
    path = make_book(tmp_path / "book.pdf", pages=24)
    small = books.add_file("manual", "notes.md", b"# Notes\n\nThe depot opens at seven.")
    record = books.stage_file("manual", "book.pdf", path)
    reading, release = threading.Event(), threading.Event()
    original = books._commit_window

    def slow(slug, rec, window, *args):
        if window == 1:
            reading.set()
            release.wait(10)  # the book is stuck in the middle of a window
        return original(slug, rec, window, *args)

    books._commit_window = slow
    thread = threading.Thread(target=books.ingest_file, args=("manual", record["id"]))
    thread.start()
    assert reading.wait(10)
    # While the book is being read: search works, and so do other uploads.
    hits = books.retriever("manual").retrieve("When does the depot open?")
    assert hits[0].chunk.doc_id.startswith(small["id"])
    books.create("Other")
    assert books.add_file("other", "a.md", b"# A\n\nAlpha bravo charlie.")["status"] == "ready"
    release.set()
    thread.join(10)
    assert books.file_record("manual", record["id"])["status"] == "ready"


def test_page_budget_replaces_the_page_cap(books, small_windows, tmp_path):
    books.settings = small_windows.model_copy(update={"max_collection_pages": 12})
    path = make_book(tmp_path / "book.pdf", pages=20)
    record = books.add_path("manual", "book.pdf", path)
    assert record["pages_total"] == 12
    assert "page budget is 12" in record["report"]["warnings"][0]


def test_replacing_a_file_keeps_the_old_one_until_the_new_one_is_ready(books, tmp_path):
    first = books.add_file("manual", "guide.md", b"# Guide\n\nVersion one says blue.")
    staged = books.stage_file("manual", "guide.md", _write(tmp_path, "# Guide\n\nTwo says red."))
    names = [r["name"] for r in books.get("manual")["files"]]
    assert names == ["guide.md", "guide.md"]  # both listed while the new one is read
    books.ingest_file("manual", staged["id"])
    files = books.get("manual")["files"]
    assert [r["id"] for r in files] == [staged["id"]] and files[0]["replaced"]
    assert first["id"] != staged["id"]


def test_a_failed_background_read_is_listed_with_its_reason(books, tmp_path):
    bad = tmp_path / "broken.pdf"
    bad.write_bytes(b"%PDF-1.4 this is not really a pdf")
    record = books.stage_file("manual", "broken.pdf", bad)
    failed = books.ingest_file("manual", record["id"])
    assert failed["status"] == "failed" and "Could not open the PDF" in failed["error"]
    with pytest.raises(CollectionError):
        books.add_file("manual", "broken2.pdf", b"%PDF-1.4 still not a pdf")
    assert [r["id"] for r in books.get("manual")["files"]] == [record["id"]]


def test_windows_parsed_in_worker_processes_match_inline(small_windows, tmp_path):
    from conftest import StubOcr

    path = make_book(tmp_path / "book.pdf", pages=24)
    results = []
    for processes in (0, 2):
        settings = small_windows.model_copy(
            update={"ingest_processes": processes, "data_dir": tmp_path / f"data{processes}"}
        )
        store = CollectionStore(settings, ocr=StubOcr())
        store.create("Manual")
        record = store.add_path("manual", "book.pdf", _copy(path, tmp_path / f"b{processes}.pdf"))
        results.append([c.text for c in store.retriever("manual").chunks])
        assert record["pages_done"] == 24
    assert results[0] == results[1]


# --- the resumable upload API ---------------------------------------------------------


@pytest.fixture
def client(small_windows, books):
    settings = small_windows.model_copy(update={"upload_part_mb": 0.01})  # 10 KB parts
    books.settings = settings
    originals = api.get_settings, api.get_store
    api.get_settings, api.get_store = (lambda: settings), (lambda: books)
    for cached in (api.get_jobs, api.get_worker, api.get_uploads):
        cached.cache_clear()
    yield TestClient(api.app)
    api.get_worker().wait()
    api.get_settings, api.get_store = originals
    for cached in (api.get_jobs, api.get_worker, api.get_uploads):
        cached.cache_clear()


def test_resumable_upload_survives_a_dropped_part_then_reads_in_the_background(client, tmp_path):
    data = make_book(tmp_path / "book.pdf", pages=16).read_bytes()
    started = client.post(
        "/collections/manual/uploads", json={"name": "book.pdf", "size": len(data)}
    )
    assert started.status_code == 201
    upload, part = started.json()["id"], started.json()["part_size"]
    url = f"/collections/manual/uploads/{upload}"

    first = client.put(url, params={"offset": 0}, content=data[:part])
    assert first.status_code == 200, first.text
    assert first.json()["received"] == part
    # The connection drops; the client resends from a stale offset and is told where to go on.
    stale = client.put(url, params={"offset": 0}, content=data[:part])
    assert stale.status_code == 409 and stale.json()["received"] == part
    assert client.get(url).json()["received"] == part
    offset = part
    while offset < len(data):
        reply = client.put(url, params={"offset": offset}, content=data[offset : offset + part])
        assert reply.status_code == 200, reply.text
        offset = reply.json()["received"]
    too_big = client.put(url, params={"offset": offset}, content=b"x" * (part + 1))
    assert too_big.status_code == 413

    done = client.post(f"{url}/complete")
    assert done.status_code == 202 and done.json()["status"] == "queued"
    api.get_worker().wait()
    record = client.get("/collections/manual").json()["files"][0]
    assert record["status"] == "ready" and record["pages_done"] == 16

    events = client.get(f"/collections/manual/files/{record['id']}/events")
    messages = [
        json.loads(line[6:]) for line in events.text.splitlines() if line.startswith("data: ")
    ]
    assert messages[-1] == {"type": "end", "status": "ready"}
    grid = client.get(f"/collections/manual/files/{record['id']}/pages").json()
    assert {p["route"] for p in grid["pages"]} == {"fast-text"}


def test_upload_refuses_unknown_types_and_oversize_before_any_bytes(client):
    bad = client.post("/collections/manual/uploads", json={"name": "a.exe", "size": 10})
    assert bad.status_code == 400
    huge = client.post("/collections/manual/uploads", json={"name": "a.pdf", "size": 10**13})
    assert huge.status_code == 400 and "limit" in huge.json()["detail"]
    missing = client.get("/collections/manual/uploads/" + "0" * 32)
    assert missing.status_code == 404


def test_answers_say_what_was_still_being_read(client, books, tmp_path):
    books.add_file("manual", "notes.md", b"# Notes\n\nThe depot opens at seven in the morning.")
    staged = books.stage_file("manual", "book.pdf", make_book(tmp_path / "b.pdf", pages=8))
    body = client.post("/collections/manual/ask", json={"question": "When does the depot open?"})
    reading = body.json()["reading"]
    assert reading == [
        {
            "file_id": staged["id"],
            "name": "book.pdf",
            "status": "queued",
            "pages_done": 0,
            "pages_total": None,
        }
    ]


def _write(tmp_path, text: str):
    path = tmp_path / f"t{abs(hash(text))}.md"
    path.write_text(text)
    return path


def _copy(source, target):
    target.write_bytes(source.read_bytes())
    return target


def test_upload_sessions_are_scoped_to_their_collection(books, tmp_path):
    sessions = UploadSessions(books, tmp_path / "up")
    books.create("Other")
    upload = sessions.create("manual", "a.md", 5)
    with pytest.raises(CollectionError):
        sessions.status("other", upload["id"])


def test_numbered_titles_at_the_top_of_pages_are_kept(tmp_path):
    """ "Plate 7" over a figure has the same shape on every page, but it is content: only
    lines repeated word for word, or short ones numbered like the pages, are stripped."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    from hyper_rag.parsing import parse_file
    from hyper_rag.parsing.ocr import build_ocr

    path = tmp_path / "plates.pdf"
    pdf = canvas.Canvas(str(path), pagesize=A4)
    for number in range(1, 7):
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(50, A4[1] - 60, f"Plate {number * 3}")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(
            50, A4[1] - 80, f"Fact {number}: plate {number * 3} was taken at S-{number}."
        )
        pdf.drawString(50, 400, "Body text in the middle of the page for the reader.")
        pdf.drawString(280, 30, f"- {number} -")
        pdf.showPage()
    pdf.save()
    units = parse_file(path, build_ocr("none")).units
    assert "Plate 9" in units[2].text and "Fact 3: plate 9" in units[2].text
    assert "- 3 -" not in units[2].text  # the page number is a footer
