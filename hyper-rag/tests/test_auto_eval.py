from hyper_rag.evaluation.synthetic import evaluate_collection, latest_report, pick_passages


def test_pick_passages_spreads_over_files_and_is_deterministic(solar):
    chunks = solar.retriever("solar-docs").chunks
    picked = pick_passages(chunks, 6)
    assert [c.id for c in picked] == [c.id for c in pick_passages(chunks, 6)]
    assert len({c.doc_id.split("/")[0] for c in picked}) == 6


def test_auto_evaluation_writes_questions_and_scores_them(solar, settings):
    lines = []
    report = evaluate_collection(
        solar, "solar-docs", settings, questions=6, on_progress=lines.append
    )

    # The fake LLM cannot write a question from a passage that is only a table.
    assert report["questions"] >= 4 and len(report["golden"]) == report["questions"]
    assert [row["mode"] for row in report["retrieval"]] == ["vector", "hybrid", "hybrid_rerank"]
    assert [row["config"] for row in report["answers"]] == ["hybrid_rerank", "agent"]
    assert report["retrieval"][2]["recall@5"] == 1.0
    assert report["judge"] == "none" and report["answers"][0]["correctness"] == "n/a"
    assert latest_report(solar, "solar-docs") == report

    # A second run reuses the same questions and the saved answers: no new work.
    again = []
    evaluate_collection(solar, "solar-docs", settings, questions=6, on_progress=again.append)
    assert not any("question 1" in line for line in again)
    assert not any("answered" in line or "refused" in line for line in again)
