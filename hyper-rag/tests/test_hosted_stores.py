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


def test_the_running_app_answers_after_a_restart_on_an_empty_disk(settings, s3, qdrant, tmp_path):
    """Phase 6 acceptance: restart the host (empty disk, same R2 and Qdrant), ask a question."""
    from fastapi.testclient import TestClient

    from conftest import StubOcr
    from hyper_rag import api
    from hyper_rag.stores.qdrant import QdrantLexicalStore, QdrantVectorStore

    def machine(name):
        local = settings.model_copy(update={"data_dir": tmp_path / name})
        return local, CollectionStore(
            local,
            ocr=StubOcr(),
            blobs=_blobs(s3, tmp_path, cache=f"{name}-cache"),
            vectors=QdrantVectorStore(":memory:", client=qdrant),
            lexical=QdrantLexicalStore(":memory:", client=qdrant),
        )

    _, before = machine("before")
    before.create("Solar")
    before.add_file("solar", "guide.pdf", make_pdf(tmp_path / "guide.pdf").read_bytes())

    local, after = machine("after")  # a fresh container: nothing on its disk
    originals = api.get_settings, api.get_store
    api.get_settings, api.get_store = (lambda: local), (lambda: after)
    for cached in (api.get_llms, api.get_jobs, api.get_quota, api.get_warmup, api.get_worker):
        cached.cache_clear()
    try:
        with TestClient(api.app) as client:  # runs start-up: warm-up and resuming jobs
            api.get_warmup().wait(5)
            assert client.get("/health").json() == {"status": "ok", "warm": "ready"}
            assert client.get("/ready").json()["ready"] is True
            assert [c["slug"] for c in client.get("/collections").json()["collections"]] == [
                "solar"
            ]
            answer = client.post(
                "/collections/solar/ask",
                json={"question": "How long does a standard rooftop installation take?"},
            ).json()
            assert not answer["refused"] and answer["citations"]
    finally:
        api.get_settings, api.get_store = originals
        for cached in (api.get_llms, api.get_jobs, api.get_quota, api.get_warmup, api.get_worker):
            cached.cache_clear()


class FakeBucketApi:
    """The five Hub calls HfBucketBlobStore makes, over a dict. Listing matches by string
    prefix, as the real Hub does (checked against a real bucket, docs/DECISIONS.md 44)."""

    def __init__(self):
        self.files: dict[str, bytes] = {}

    def batch_bucket_files(self, bucket, add=None, delete=None):
        from pathlib import Path

        for source, path in add or []:
            self.files[path] = source if isinstance(source, bytes) else Path(source).read_bytes()
        for path in delete or []:
            self.files.pop(path, None)

    def download_bucket_files(self, bucket, files, raise_on_missing_files=False):
        from huggingface_hub.errors import EntryNotFoundError

        for path, target in files:
            if path not in self.files:
                raise EntryNotFoundError(path)
            target.write_bytes(self.files[path])

    def get_bucket_paths_info(self, bucket, paths):
        return [path for path in paths if path in self.files]

    def list_bucket_tree(self, bucket, prefix=None, recursive=None):
        from types import SimpleNamespace

        return [
            SimpleNamespace(type="file", path=path)
            for path in sorted(self.files)
            if path.startswith(prefix.rstrip("/"))
        ]


def _hf_blobs(api, tmp_path, cache="cache"):
    from hyper_rag.stores.hf import HfBucketBlobStore

    return HfBucketBlobStore("me/bucket", cache_dir=tmp_path / cache, prefix="team", api=api)


def test_hf_bucket_blob_store_round_trip(tmp_path):
    api = FakeBucketApi()
    blobs = _hf_blobs(api, tmp_path)
    blobs.write_bytes("c/a/one.txt", b"1")
    blobs.write_bytes("c/ab/near.txt", b"n")  # shares a string prefix with c/a
    source = tmp_path / "big.bin"
    source.write_bytes(b"x" * 3000)
    blobs.write_file("c/a/sub/two.bin", source, move=True)
    assert not source.exists()  # moved into the local cache, not copied
    assert blobs.read_bytes("c/a/one.txt") == b"1" and blobs.exists("c/a/sub/two.bin")
    assert blobs.list("c/a") == ["c/a/one.txt", "c/a/sub/two.bin"]
    blobs.flush()
    assert set(api.files) == {"team/c/a/one.txt", "team/c/ab/near.txt", "team/c/a/sub/two.bin"}
    fresh = _hf_blobs(api, tmp_path, cache="other-cache")  # a new machine: nothing cached
    assert fresh.local_path("c/a/sub/two.bin").read_bytes() == b"x" * 3000
    blobs.delete_prefix("c/a")
    assert blobs.list("c") == ["c/ab/near.txt"] and not blobs.exists("c/a/one.txt")
    assert set(api.files) == {"team/c/ab/near.txt"}
    with pytest.raises(KeyError):
        blobs.read_bytes("c/missing")
    with pytest.raises(KeyError):
        blobs.local_path("c/missing")
    with pytest.raises(ValueError):
        blobs.write_bytes("../escape", b"")


def test_a_collection_in_one_hf_bucket_survives_a_wiped_disk(settings, tmp_path):
    """No Qdrant and no S3: the default in-memory indexes are rebuilt from the bucket."""
    from conftest import StubOcr

    api = FakeBucketApi()

    def store(data_dir):
        local = settings.model_copy(update={"data_dir": data_dir})
        blobs = _hf_blobs(api, tmp_path, cache=f"{data_dir.name}-cache")
        return CollectionStore(local, ocr=StubOcr(), blobs=blobs)

    first = store(tmp_path / "machine-1")
    first.create("Solar")
    record = first.add_file("solar", "guide.pdf", make_pdf(tmp_path / "guide.pdf").read_bytes())
    question = "How long does a standard rooftop installation take?"
    before = [h.chunk.id for h in first.retriever("solar").retrieve(question)]

    first.blobs.flush()  # what a clean shutdown does
    second = store(tmp_path / "machine-2")  # the host restarted with an empty disk
    assert [c["slug"] for c in second.all()] == ["solar"]
    assert [h.chunk.id for h in second.retriever("solar").retrieve(question)] == before
    image, kind = second.preview("solar", record["id"], 1)
    assert kind == "image/png" and image.startswith(b"\x89PNG")
    second.delete("solar")
    assert second.all() == [] and not [k for k in api.files if "/collections/" in k]


def test_hf_bucket_writes_are_batched_in_order_and_kept_when_the_hub_fails(tmp_path, monkeypatch):
    from hyper_rag.stores import hf

    monkeypatch.setattr(hf, "WRITE_DELAY", 3600.0)  # only the size limit and flush() send
    monkeypatch.setattr(hf, "WRITE_BATCH", 3)
    api = FakeBucketApi()
    batches, send = [], api.batch_bucket_files

    def record(bucket, add=None, delete=None):
        batches.append([path for _, path in add or []])
        return send(bucket, add=add, delete=delete)

    api.batch_bucket_files = record
    blobs = _hf_blobs(api, tmp_path)
    blobs.write_bytes("p/1", b"a")
    blobs.write_bytes("p/2", b"b")
    assert batches == [] and blobs.read_bytes("p/1") == b"a" and blobs.exists("p/2")
    with pytest.raises(KeyError):
        blobs.read_bytes("p/never")  # answered from the key list: no round trip
    blobs.write_bytes("p/checkpoint", b"c")  # the third write fills the batch
    assert batches == [["team/p/1", "team/p/2", "team/p/checkpoint"]]

    def down(bucket, add=None, delete=None):
        raise ConnectionError("hub is down")

    api.batch_bucket_files = down
    blobs.write_bytes("p/3", b"d")
    with pytest.raises(ConnectionError):
        blobs.flush()
    api.batch_bucket_files = record
    blobs.write_bytes("p/4", b"e")
    blobs.flush()
    assert batches[-1] == ["team/p/3", "team/p/4"] and api.files["team/p/3"] == b"d"
