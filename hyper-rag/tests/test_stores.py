"""The storage interfaces' local implementations (plan v2, phase 0)."""

import numpy as np
import pytest

from hyper_rag.retrieval.bm25 import BM25Index
from hyper_rag.retrieval.dense import DenseIndex
from hyper_rag.stores.blob import LocalBlobStore
from hyper_rag.stores.jobs import INTERRUPTED, SqliteJobStore
from hyper_rag.stores.lexical import BM25LexicalStore
from hyper_rag.stores.vectors import NumpyVectorStore
from hyper_rag.uploads import CollectionStore
from make_files import make_pdf


def test_blobs_round_trip_list_and_delete(tmp_path):
    blobs = LocalBlobStore(tmp_path)
    blobs.write_bytes("c/a/one.txt", b"1")
    blobs.write_bytes("c/a/sub/two.txt", b"2")
    blobs.write_bytes("c/b.txt", b"3")
    assert blobs.read_bytes("c/a/one.txt") == b"1" and blobs.exists("c/b.txt")
    assert blobs.list("c/a") == ["c/a/one.txt", "c/a/sub/two.txt"]
    assert blobs.local_path("c/b.txt").read_bytes() == b"3"
    blobs.write_bytes("c/b.txt", b"new")  # replace
    assert blobs.read_bytes("c/b.txt") == b"new" and not list(tmp_path.rglob("*.tmp"))
    blobs.delete_prefix("c/a")
    blobs.delete("c/missing.txt")  # not an error
    assert blobs.list("c") == ["c/b.txt"]
    with pytest.raises(KeyError):
        blobs.read_bytes("c/a/one.txt")


@pytest.mark.parametrize("key", ["", "/etc/passwd", "a/../../b", "a//b", "a/./b", "a\\b"])
def test_blob_keys_cannot_leave_the_root(tmp_path, key):
    with pytest.raises(ValueError):
        LocalBlobStore(tmp_path).write_bytes(key, b"x")


def _unit(vectors):
    vectors = np.asarray(vectors, dtype=np.float32)
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def test_vector_store_matches_the_dense_index_and_tracks_files():
    a, b = _unit([[1, 0, 0], [0.9, 0.1, 0]]), _unit([[0, 1, 0], [0, 0, 1]])
    store = NumpyVectorStore()
    store.add("ns", "fa", ["a0", "a1"], a)
    store.add("ns", "fb", ["b0", "b1"], b)
    query = _unit([[0.2, 1, 0.1]])[0]
    expected = DenseIndex(np.vstack([a, b])).search(query, 4)
    ids = ["a0", "a1", "b0", "b1"]
    assert store.search("ns", query, 4) == [(ids[row], score) for row, score in expected]

    store.remove("ns", "fb")
    assert {cid for cid, _ in store.search("ns", query, 4)} == {"a0", "a1"}
    assert store.has("ns", "fa") and not store.has("ns", "fb")
    assert store.search("other", query, 4) == []  # namespaces are separate
    store.drop("ns")
    assert store.search("ns", query, 4) == []
    with pytest.raises(ValueError):
        store.add("ns", "fc", ["only-one"], a)


def test_lexical_store_matches_bm25_over_all_files():
    texts_a = ["refunds take five days", "capture within seven days"]
    texts_b = ["webhooks are signed", "refunds of refunds", "payouts settle daily"]
    store = BM25LexicalStore()
    store.add("ns", "fa", ["a0", "a1"], texts_a)
    store.add("ns", "fb", ["b0", "b1", "b2"], texts_b)
    ids = ["a0", "a1", "b0", "b1", "b2"]
    # IDF is computed over both files, exactly as one BM25 index over all chunks would.
    expected = BM25Index(texts_a + texts_b).search("refunds days", 4)
    assert store.search("ns", "refunds days", 4) == [(ids[r], s) for r, s in expected]
    store.remove("ns", "fa")
    assert [cid for cid, _ in store.search("ns", "refunds", 4)] == ["b1"]


def test_jobs_run_once_per_scope_and_keep_their_log(tmp_path):
    jobs = SqliteJobStore(tmp_path / "jobs.sqlite3")
    job = jobs.start("eval", "solar")
    assert job["state"] == "running" and jobs.start("eval", "solar") is None
    assert jobs.start("eval", "other") is not None  # another scope is independent
    jobs.log(job["id"], "question 1 of 3")
    jobs.log(job["id"], "question 2 of 3")
    jobs.finish(job["id"], {"score": 0.9})
    latest = jobs.latest("eval", "solar")
    assert latest["state"] == "done" and latest["result"] == {"score": 0.9}
    assert latest["log"] == ["question 1 of 3", "question 2 of 3"]
    assert jobs.start("eval", "solar") is not None  # finished, so a new one may start
    jobs.forget("eval", "solar")
    assert jobs.latest("eval", "solar") is None


def test_a_restart_marks_running_jobs_as_interrupted(tmp_path):
    path = tmp_path / "jobs.sqlite3"
    first = SqliteJobStore(path)
    job = first.start("eval", "solar")
    first.close()
    reopened = SqliteJobStore(path).get(job["id"])
    assert reopened["state"] == "failed" and reopened["error"] == INTERRUPTED


def test_collection_survives_a_restart_from_blobs_alone(settings, store, tmp_path):
    """A new process has empty vector and keyword stores and must refill them from blobs."""
    store.create("Solar")
    store.add_file("solar", "guide.pdf", make_pdf(tmp_path / "guide.pdf").read_bytes())
    question = "How long does a standard rooftop installation take?"
    before = [h.chunk.id for h in store.retriever("solar").retrieve(question)]

    fresh = CollectionStore(settings, ocr=store.ocr)
    assert not fresh.vectors.has(f"solar:{fresh.embedder.name}", "x")
    assert [h.chunk.id for h in fresh.retriever("solar").retrieve(question)] == before


def test_removing_a_file_removes_it_from_search(store, tmp_path):
    from make_files import make_html

    store.create("Solar")
    pdf = store.add_file("solar", "guide.pdf", make_pdf(tmp_path / "guide.pdf").read_bytes())
    html = store.add_file("solar", "returns.html", make_html(tmp_path / "r.html").read_bytes())
    files_of = lambda hits: {h.chunk.doc_id.split("/")[0] for h in hits}  # noqa: E731
    assert files_of(store.retriever("solar").retrieve("refund returns", top_k=20)) == {
        pdf["id"],
        html["id"],
    }
    store.remove_file("solar", html["id"])
    assert files_of(store.retriever("solar").retrieve("refund returns", top_k=20)) == {pdf["id"]}
    store.delete("solar")
    assert store.vectors.search(f"solar:{store.embedder.name}", np.ones(1), 5) == []
