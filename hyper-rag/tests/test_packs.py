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


def test_every_pack_has_a_valid_config_and_golden_set(settings):
    names = list_packs(settings.packs_dir)
    assert {"sample", "payments", "farming", "papers", "codebase"} <= set(names)
    for name in names:
        pack = load_pack(settings.packs_dir, name)
        golden = load_golden(pack)
        assert pack.config.description and (pack.path / "ingest.py").exists()
        assert len({q.id for q in golden}) == len(golden) >= 15
        assert any(not q.answerable for q in golden)
        assert all(q.reference_answer and q.relevant_sources for q in golden if q.answerable)


def test_codebase_pack_gives_each_function_its_own_section(settings, tmp_path):
    pack = load_pack(settings.packs_dir, "codebase")
    documents = {d.id: d for d in pack.fetch_documents(tmp_path)}
    fusion = documents["src/hyper_rag/retrieval/fusion.py"]
    assert "## function reciprocal_rank_fusion" in fusion.text
    assert "## Module overview" in fusion.text
