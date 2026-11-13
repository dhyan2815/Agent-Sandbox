"""Plan v2 phase 2: hosted stores (Qdrant, S3/R2), the job store replica, the page cache.

Qdrant runs in the client's in-process mode and S3 is moto's server, so nothing here needs
a network or an account. The same code talks to Qdrant Cloud and Cloudflare R2.
"""

import socket

import numpy as np
import pytest

from hyper_rag.retrieval.dense import DenseIndex
from hyper_rag.stores.jobs import ReplicatedJobStore
from hyper_rag.stores.lexical import BM25LexicalStore
from hyper_rag.stores.qdrant import QdrantLexicalStore, QdrantVectorStore
from hyper_rag.uploads import CollectionStore
from make_files import make_book, make_pdf


@pytest.fixture
def qdrant():
    from qdrant_client import QdrantClient

    return QdrantClient(location=":memory:")


@pytest.fixture(scope="module")
def s3_endpoint():
    from moto.server import ThreadedMotoServer

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = ThreadedMotoServer(ip_address="127.0.0.1", port=port)
    server.start()
    yield f"http://127.0.0.1:{port}"
    server.stop()


@pytest.fixture
def s3(s3_endpoint, monkeypatch, request):
    import boto3

    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    client = boto3.client("s3", endpoint_url=s3_endpoint, region_name="us-east-1")
    bucket = request.node.name.replace("_", "-")[:50].lower()
    client.create_bucket(Bucket=bucket)
    return client, bucket


def _blobs(s3, tmp_path, cache="cache"):
    from hyper_rag.stores.s3 import S3BlobStore

    client, bucket = s3
    return S3BlobStore(bucket, cache_dir=tmp_path / cache, prefix="team", client=client)


def _unit(rows):
    rows = np.asarray(rows, dtype=np.float32)
    return rows / np.linalg.norm(rows, axis=1, keepdims=True)


def test_qdrant_vectors_rank_like_the_exact_scan(qdrant):
    rng = np.random.default_rng(7)
    vectors = _unit(rng.normal(size=(60, 16)))
    ids = [f"f{i // 20}/1#{i}" for i in range(60)]
    store = QdrantVectorStore(":memory:", client=qdrant)
    for group in range(3):
        rows = slice(group * 20, group * 20 + 20)
        store.add("ns", f"f{group}#w00000", ids[rows], vectors[rows])
    query = _unit(rng.normal(size=(1, 16)))[0]
    exact = [ids[row] for row, _ in DenseIndex(vectors).search(query, 10)]
    assert [cid for cid, _ in store.search("ns", query, 10)] == exact
    assert store.has("ns", "f1#w00000") and not store.has("ns", "f9#w00000")
    store.remove("ns", "f1")
    assert not {cid for cid, _ in store.search("ns", query, 60)} & set(ids[20:40])
    store.drop("ns")
    assert store.search("ns", query, 5) == []


def test_qdrant_keywords_find_what_bm25_finds(qdrant):
    texts = [
        "refunds take five working days to reach the customer",
        "capture the payment within seven days of authorisation",
        "webhooks are signed with an HMAC of the raw body",
        "a refund can be partial or full",
        "payouts settle daily to the linked bank account",
    ]
    ids = [f"f/1#{i}" for i in range(5)]
    store = QdrantLexicalStore(":memory:", client=qdrant)
    store.add("ns", "f#w00000", ids, texts)
    reference = BM25LexicalStore()
    reference.add("ns", "f#w00000", ids, texts)
    for query in ("refund", "webhook signed body", "settle bank"):
        found = [cid for cid, _ in store.search("ns", query, 5)]
        expected = [cid for cid, _ in reference.search("ns", query, 5)]
        assert found[0] == expected[0] and set(found) == set(expected), query
    assert store.search("ns", "sourdough", 5) == []
    # Re-adding a group replaces it rather than duplicating it.
    store.add("ns", "f#w00000", ids[:1], texts[:1])
    assert [cid for cid, _ in store.search("ns", "refunds customer webhook", 5)] == ids[:1]


def test_s3_blob_store_round_trip(s3, tmp_path):
    blobs = _blobs(s3, tmp_path)
    blobs.write_bytes("c/a/one.txt", b"1")
    source = tmp_path / "big.bin"
    source.write_bytes(b"x" * 3000)
    blobs.write_file("c/a/sub/two.bin", source, move=True)
    assert not source.exists()  # moved into the local cache, not copied
    assert blobs.read_bytes("c/a/one.txt") == b"1" and blobs.exists("c/a/sub/two.bin")
    assert blobs.list("c") == ["c/a/one.txt", "c/a/sub/two.bin"]
    fresh = _blobs(s3, tmp_path, cache="other-cache")  # a new machine: nothing cached
    assert fresh.local_path("c/a/sub/two.bin").read_bytes() == b"x" * 3000
    blobs.delete_prefix("c/a/sub")
    assert blobs.list("c") == ["c/a/one.txt"]
    with pytest.raises(KeyError):
        blobs.read_bytes("c/missing")
    with pytest.raises(ValueError):
        blobs.write_bytes("../escape", b"")


def test_a_collection_on_qdrant_and_s3_survives_a_wiped_disk(settings, s3, qdrant, tmp_path):
    from conftest import StubOcr
    from hyper_rag.stores.qdrant import QdrantLexicalStore, QdrantVectorStore

    def store(data_dir):
        local = settings.model_copy(update={"data_dir": data_dir})
        return CollectionStore(
            local,
            ocr=StubOcr(),
            blobs=_blobs(s3, tmp_path, cache=f"{data_dir.name}-cache"),
            vectors=QdrantVectorStore(":memory:", client=qdrant),
            lexical=QdrantLexicalStore(":memory:", client=qdrant),
        )

    first = store(tmp_path / "machine-1")
    first.create("Solar")
    record = first.add_file("solar", "guide.pdf", make_pdf(tmp_path / "guide.pdf").read_bytes())
    question = "How long does a standard rooftop installation take?"
    before = [h.chunk.id for h in first.retriever("solar").retrieve(question)]

    # The host restarts with an empty disk: files come back from S3, vectors were in Qdrant.
    second = store(tmp_path / "machine-2")
    assert [c["slug"] for c in second.all()] == ["solar"]
    assert [h.chunk.id for h in second.retriever("solar").retrieve(question)] == before
    source = second.source("solar", before[0])
    assert source["file_name"] == "guide.pdf"
    image, kind = second.preview("solar", record["id"], 1)
    assert kind == "image/png" and image.startswith(b"\x89PNG")
    second.delete("solar")
    assert second.all() == [] and first.blobs.list("collections") == []


def test_job_store_is_restored_from_its_replica(s3, tmp_path):
    blobs = _blobs(s3, tmp_path)
    jobs = ReplicatedJobStore(tmp_path / "a" / "jobs.sqlite3", blobs, every=0)
    job = jobs.start("eval", "solar")
    jobs.log(job["id"], "line one")
    jobs.finish(job["id"], {"score": 1})
    jobs.close()
    restored = ReplicatedJobStore(tmp_path / "wiped" / "jobs.sqlite3", blobs)
    latest = restored.latest("eval", "solar")
    assert latest["state"] == "done" and latest["result"] == {"score": 1}


def test_a_new_edition_only_reads_its_changed_pages(settings, tmp_path, monkeypatch):
    import hyper_rag.uploads as uploads
    from conftest import StubOcr

    store = CollectionStore(settings.model_copy(update={"window_pages": 8}), ocr=StubOcr())
    store.create("Manual")
    parsed: list[int] = []
    real = uploads.parse_pdf_pages

    def counting(path, pages, *args):
        parsed.extend(page.number for page in pages)
        return real(path, pages, *args)

    monkeypatch.setattr(uploads, "parse_pdf_pages", counting)
    store.add_path("manual", "manual.pdf", make_book(tmp_path / "v1.pdf", pages=40))
    assert sorted(parsed) == list(range(1, 41))

    # Version 2: the same manual with one page rewritten (2.5% of the pages).
    edition = make_book(tmp_path / "v2.pdf", pages=40, changed={23: "Fact 23 was revised."})
    parsed.clear()
    store.add_path("manual", "manual.pdf", edition)
    assert parsed == [23]
    record = store.get("manual")["files"][0]
    assert record["replaced"] and record["pages_done"] == 40
    hits = store.retriever("manual").retrieve("Fact 23 was revised")
    assert hits[0].chunk.id.startswith(f"{record['id']}/23#")


def test_unchanged_passages_are_not_embedded_again(settings):
    from conftest import StubOcr

    store = CollectionStore(settings, ocr=StubOcr())
    store.create("Notes")
    store.add_file("notes", "a.md", b"# Depot\n\nThe depot opens at seven.")
    calls = []
    real = store.embedder.embed_documents
    store.embedder.embed_documents = lambda texts: calls.append(len(texts)) or real(texts)
    store.create("Other")
    store.add_file("other", "a.md", b"# Depot\n\nThe depot opens at seven.\n")
    assert calls == []  # the same passages, in another collection: embedded once
