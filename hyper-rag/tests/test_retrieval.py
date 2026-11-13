import pytest

from hyper_rag.chunking import chunk_document
from hyper_rag.evaluation.retrieval_eval import evaluate_retrieval
from hyper_rag.evaluation.retrieval_metrics import ndcg_at_k, recall_at_k, reciprocal_rank
from hyper_rag.index import ingest_pack, load_retriever
from hyper_rag.packs import load_golden, load_pack
from hyper_rag.retrieval.fusion import reciprocal_rank_fusion
from hyper_rag.types import Document


@pytest.fixture
def sample_retriever(settings):
    pack = load_pack(settings.packs_dir, "sample")
    ingest_pack(pack, settings)
    return load_retriever(pack, settings)


def test_chunks_respect_size_and_carry_their_heading():
    text = "# Guide\n\nIntro.\n\n## Setup\n\n" + "\n\n".join(
        f"Step {i} " + "x" * 80 for i in range(10)
    )
    chunks = chunk_document(Document("guide", "Guide", "", text), size=300, overlap=40)
    setup = [c for c in chunks if "Setup" in c.title]
    assert len(setup) > 1
    assert all(c.text.startswith("Guide > Setup\n") for c in setup)
    assert all(len(c.text) <= 300 + len("Guide > Setup\n") for c in chunks)
    assert [c.id for c in chunks] == [f"guide#{i}" for i in range(len(chunks))]


def test_rrf_rewards_agreement_between_rankings():
    # Item 2 is second in both lists; items 1 and 3 are first in one list and absent in the other.
    fused = reciprocal_rank_fusion([[1, 2], [3, 2]], k=60)
    assert fused[0][0] == 2
    assert fused[0][1] == pytest.approx(2 / 62)


def test_metrics_on_a_known_ranking():
    retrieved = ["a", "b", "b", "c"]
    needs = [["b", "x"], ["z"]]  # need 1: b or x; need 2: z (never retrieved)
    assert recall_at_k(retrieved, needs, 1) == 0.0
    assert recall_at_k(retrieved, needs, 4) == 0.5
    assert reciprocal_rank(retrieved, needs) == 0.5
    # One need met at rank 2 (the second "b" earns nothing); ideal is both at ranks 1 and 2.
    assert ndcg_at_k(retrieved, needs, 4) == pytest.approx(0.6309 / 1.6309, abs=1e-3)
    # Alternatives inside one need do not inflate recall.
    assert recall_at_k(["b", "x"], [["b", "x"]], 2) == 1.0


def test_every_mode_finds_the_refunds_page(sample_retriever):
    for mode in ("vector", "hybrid", "hybrid_rerank"):
        hits = sample_retriever.retrieve("How long does a refund take?", mode=mode)
        assert "refunds" in [hit.chunk.doc_id for hit in hits[:3]], mode


def test_retrieval_eval_on_sample_pack(sample_retriever, settings):
    golden = load_golden(load_pack(settings.packs_dir, "sample"))
    rows = evaluate_retrieval(sample_retriever, golden)
    assert [row["mode"] for row in rows] == ["vector", "hybrid", "hybrid_rerank"]
    assert all(row["questions"] == 14 for row in rows)
    # The sample corpus is easy; the full pipeline should find nearly everything.
    assert rows[-1]["recall@5"] >= 0.9
