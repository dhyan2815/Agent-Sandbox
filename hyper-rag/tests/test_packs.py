from hyper_rag.packs import list_packs, load_golden, load_pack


def test_sample_pack_is_discovered(settings):
    assert "sample" in list_packs(settings.packs_dir)


def test_sample_pack_yields_documents(settings, tmp_path):
    pack = load_pack(settings.packs_dir, "sample")
    documents = list(pack.fetch_documents(tmp_path))
    assert len(documents) == 8
    assert {"payments", "refunds", "webhooks"} <= {d.id for d in documents}
    assert all(d.title and d.text for d in documents)


def test_golden_sources_exist_in_corpus(settings, tmp_path):
    pack = load_pack(settings.packs_dir, "sample")
    doc_ids = {d.id for d in pack.fetch_documents(tmp_path)}
    golden = load_golden(pack)
    assert any(not q.answerable for q in golden), "need unanswerable questions to test refusals"
    for question in golden:
        assert {doc for need in question.relevant_sources for doc in need} <= doc_ids
        assert question.answerable == bool(question.relevant_sources)
