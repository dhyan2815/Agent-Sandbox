import pytest

from conftest import StubOcr
from hyper_rag.agent import Agent
from hyper_rag.llm import FakeLLM
from hyper_rag.uploads import CollectionError, CollectionNotFound, CollectionStore, mark_lines
from make_files import make_pdf, make_xlsx


def ask(store, slug, question, history=None):
    agent = Agent(store.retriever(slug), FakeLLM(), store.description(slug))
    return agent.ask(question, history)


def test_create_list_delete(store):
    meta = store.create("  Q3   Contracts ")
    assert meta["slug"] == "q3-contracts" and meta["name"] == "Q3 Contracts"
    assert [m["slug"] for m in store.all()] == ["q3-contracts"]
    with pytest.raises(CollectionError, match="already exists"):
        store.create("q3 contracts")
    store.delete("q3-contracts")
    assert store.all() == []
    with pytest.raises(CollectionNotFound):
        store.get("q3-contracts")
    with pytest.raises(CollectionNotFound):
        store.get("../etc")  # not a slug: never reaches the file system


def test_upload_records_a_parse_report(store, tmp_path):
    store.create("Solar")
    pdf = make_pdf(tmp_path / "guide.pdf")
    record = store.add_file("solar", "guide.pdf", pdf.read_bytes())

    assert record["kind"] == "pdf" and record["chunks"] >= 3
    assert record["report"]["units"] == 3 and record["report"]["tables"] == 1
    assert record["report"]["ocr_units"] == 1 and record["report"]["images_with_text"] == 1
    assert "Scheduling" in record["headings"]
    assert store.file_path("solar", record["id"]).read_bytes() == pdf.read_bytes()
    assert "guide.pdf" in store.description("solar") and "Warranty" in store.description("solar")


def test_duplicate_replace_and_remove(store, tmp_path):
    store.create("Solar")
    small = make_xlsx(tmp_path / "output.xlsx", rows=4).read_bytes()
    first = store.add_file("solar", "output.xlsx", small)
    assert store.add_file("solar", "copy.xlsx", small)["duplicate"] is True

    bigger = make_xlsx(tmp_path / "output2.xlsx", rows=6).read_bytes()
    second = store.add_file("solar", "output.xlsx", bigger)  # same name, new content
    assert second["replaced"] is True
    assert [f["id"] for f in store.get("solar")["files"]] == [second["id"]]
    hits = store.retriever("solar").retrieve("How many units were generated in June?")
    assert "| June | 385 |" in hits[0].chunk.text
    assert not (store.path("solar") / "files" / f"{first['id']}.xlsx").exists()

    store.remove_file("solar", second["id"])
    with pytest.raises(CollectionError, match="no searchable text"):
        store.retriever("solar")


def test_rejects_unsupported_empty_and_oversize_uploads(store):
    store.create("Solar")
    with pytest.raises(CollectionError, match="Save the file as .docx"):
        store.add_file("solar", "old.doc", b"data")
    with pytest.raises(CollectionError, match="is empty"):
        store.add_file("solar", "notes.txt", b"")
    with pytest.raises(CollectionError, match="upload limit"):
        store.add_file("solar", "big.txt", b"x" * (25 * 1024 * 1024 + 1))
    with pytest.raises(CollectionError, match="Could not open the PDF"):
        store.add_file("solar", "broken.pdf", b"not a pdf")
    assert store.get("solar")["files"] == []
    assert list((store.path("solar") / "files").iterdir()) == []  # nothing left behind


def test_upload_name_cannot_escape_the_collection_folder(store):
    store.create("Solar")
    record = store.add_file("solar", "../../evil.txt", b"The tariff is 6 rupees per unit.")
    assert record["name"] == "evil.txt"
    assert store.file_path("solar", record["id"]).parent == store.path("solar") / "files"


@pytest.mark.parametrize(
    ("question", "expected", "source"),
    [
        ("How long does a standard rooftop installation take?", "two working days", "guide.pdf"),
        ("What is the warranty of the inverter?", "| Inverter | 10 |", "guide.pdf (Page 2)"),
        ("How much does the annual service visit cost?", "2400 rupees", "handbook.docx"),
        ("What is the subsidy for a 5 kW system?", "| 5 kW | 94000 |", "pricing.pptx (Slide 2)"),
        ("How many units were generated in March?", "| March | 340 |", "output.xlsx (Sheet Ou"),
        ("Who is the branch manager in Surat?", "Imran Shaikh", "branches.csv"),
        ("How are refunds paid?", "original payment method", "returns.html"),
        ("When is an alert sent by the app?", "60 percent", "app.md"),
    ],
)
def test_every_format_is_retrievable(solar, question, expected, source):
    # Checked at the retriever: the rule-based fake LLM cannot read a table row, and
    # this test is about what the upload pipeline put in the index.
    hits = solar.retriever("solar-docs").retrieve(question, top_k=3)
    matching = [hit.chunk for hit in hits if expected in hit.chunk.text]
    assert matching, [hit.chunk.title for hit in hits]
    assert matching[0].title.startswith(source)


def test_answers_cite_the_uploaded_file(solar):
    answer = ask(solar, "solar-docs", "How much does the annual service visit cost?")
    assert not answer.refused and "2400 rupees" in answer.text
    number, chunk = answer.citations[0]
    assert chunk.title == "handbook.docx > Service visits"
    assert chunk.url.startswith("/collections/solar-docs/files/")


def test_declines_what_the_documents_do_not_say(solar):
    assert ask(solar, "solar-docs", "Which football club won the league in 1998?").refused


def test_follow_up_question_uses_the_conversation(solar):
    history = [("What does the annual service visit cost?", "It costs 2400 rupees [1].")]
    answer = ask(solar, "solar-docs", "How much is it?", history)
    assert answer.trace[0].startswith("condense: 'How much is it? What does the annual")
    assert "2400 rupees" in answer.text
    # Without the conversation the same words have no subject to retrieve on.
    assert ask(solar, "solar-docs", "How much is it?").refused


def test_agent_reports_its_steps_as_they_happen(solar):
    agent = Agent(solar.retriever("solar-docs"), FakeLLM(), solar.description("solar-docs"))
    events = list(agent.ask_events("How much does the annual service visit cost?"))
    kinds = [kind for kind, _ in events]
    assert kinds[-1] == "answer" and kinds.count("answer") == 1
    steps = [payload.split(":")[0] for kind, payload in events if kind == "step"]
    assert steps == ["route", "retrieve", "grade", "generate", "check"]
    assert events[-1][1].trace == [payload for kind, payload in events if kind == "step"]


def test_citation_opens_its_page_with_the_passage_marked(solar):
    hits = solar.retriever("solar-docs").retrieve("What is the warranty of the inverter?")
    chunk = next(hit.chunk for hit in hits if "| Inverter | 10 |" in hit.chunk.text)
    source = solar.source("solar-docs", chunk.id)

    assert source["file_name"] == "guide.pdf" and source["unit_label"] == "Page 2"
    assert source["file_url"].endswith("#page=2") and source["preview_url"].endswith("/preview/2")
    marked = [span["text"] for line in source["lines"] for span in line if span["hit"]]
    assert "| Inverter | 10 | Manufacturer |" in marked

    image, media_type = solar.preview("solar-docs", source["file_id"], 2)
    assert media_type == "image/png" and image.startswith(b"\x89PNG")
    with pytest.raises(CollectionNotFound):
        solar.source("solar-docs", "not-a-chunk")
    with pytest.raises(CollectionNotFound):
        solar.preview("solar-docs", source["file_id"], 99)


def test_mark_lines_flags_only_sentences_inside_the_passage():
    unit = "# Title\n\nFirst point here. Second point here.\n\nUnrelated closing line."
    lines = mark_lines(unit, "Title\nSecond point   here.")
    flags = [(span["text"], span["hit"]) for line in lines for span in line]
    assert flags == [
        ("# Title", True),
        ("First point here.", False),
        ("Second point here.", True),
        ("Unrelated closing line.", False),
    ]


def test_index_is_rebuilt_for_a_different_embedder(solar, settings):
    class OtherEmbedder(type(solar.embedder)):
        name = "hashing-other"

    other = CollectionStore(settings, ocr=StubOcr(), embedder=OtherEmbedder())
    assert len(other.retriever("solar-docs").chunks) == len(solar.retriever("solar-docs").chunks)
    assert (other.path("solar-docs") / "index-hashing-other").is_dir()


def test_collections_can_skip_the_router(solar):
    retriever, description = solar.retriever("solar-docs"), solar.description("solar-docs")
    question = "How much does the annual service visit cost?"
    routed = Agent(retriever, FakeLLM(), description).ask(question)
    direct = Agent(retriever, FakeLLM(), description, route=False).ask(question)
    assert routed.trace[0] == "route: retrieve" and direct.trace[0].startswith("retrieve:")
    assert direct.text == routed.text and direct.llm_calls == routed.llm_calls - 1


def test_zip_bomb_is_refused_before_parsing(store, monkeypatch):
    import io
    import zipfile

    from hyper_rag import parsing

    monkeypatch.setattr(parsing, "MAX_UNZIPPED_MB", 1)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", b"0" * (3 * 1024 * 1024))  # compresses to ~3 KB
    store.create("Bombs")
    with pytest.raises(CollectionError, match="expands to more than"):
        store.add_file("bombs", "bomb.docx", buffer.getvalue())
    with pytest.raises(CollectionError, match="not a valid"):
        store.add_file("bombs", "fake.xlsx", b"not a zip")
    assert store.get("bombs")["files"] == []


def test_failed_indexing_leaves_no_orphan_files(store, monkeypatch):
    store.create("Orphans")

    def boom(*args, **kwargs):
        raise RuntimeError("embedder down")

    monkeypatch.setattr(store, "_build_index", boom)
    with pytest.raises(RuntimeError):
        store.add_file("orphans", "notes.txt", b"Some searchable text about solar panels.")
    assert list((store.path("orphans") / "files").iterdir()) == []
    assert list((store.path("orphans") / "parsed").iterdir()) == []
