import json

import pytest

from hyper_rag.agent.answer import build_answer, build_refusal
from hyper_rag.evaluation.answer_eval import CONFIGS, run_answer_eval, score_answer, summarise
from hyper_rag.index import ingest_pack, load_retriever
from hyper_rag.llm import build_llm
from hyper_rag.llm.base import LLMError
from hyper_rag.packs import GoldenQuestion, load_golden, load_pack
from hyper_rag.types import Chunk

REFUNDS = Chunk(
    "refunds#0", "refunds", "Refunds", "", "A normal refund takes 5 to 7 business days."
)
UPI = Chunk("upi#0", "upi", "UPI", "", "A collect request expires after 5 minutes.")
QUESTION = GoldenQuestion(
    "q1", "How long does a refund take?", True, "A refund takes 5 to 7 business days.",
    [["refunds"]], ["5 to 7 business days"],
)  # fmt: skip
UNANSWERABLE = GoldenQuestion("q2", "How do I bake bread?", False, "", [], [])


@pytest.fixture
def judge(settings):
    return build_llm(settings, "judge")


def test_correct_cited_answer_scores_full_marks(judge):
    answer = build_answer(
        QUESTION.question, "A normal refund takes 5 to 7 business days. [1]", [REFUNDS, UPI], [], 1
    )
    row = score_answer(QUESTION, answer, judge)
    assert row["correctness"] == 1.0 and row["key_facts"] == 1.0
    assert row["grounded"] == 1.0 and row["citation_precision"] == 1.0


def test_citing_the_wrong_document_lowers_citation_precision(judge):
    answer = build_answer(
        QUESTION.question,
        "A normal refund takes 5 to 7 business days. [1][2]",
        [REFUNDS, UPI],
        [],
        1,
    )
    assert score_answer(QUESTION, answer, judge)["citation_precision"] == 0.5


def test_refusals_are_scored_by_whether_the_question_was_answerable(judge):
    wrong = score_answer(QUESTION, build_refusal(QUESTION.question, "x", [], [], 1), judge)
    right = score_answer(UNANSWERABLE, build_refusal(UNANSWERABLE.question, "x", [], [], 1), judge)
    assert wrong["correctness"] == 0.0 and "grounded" not in wrong
    summary = summarise("agent", [wrong, right])
    assert summary["refused_answerable"] == 1.0 and summary["refused_unanswerable"] == 1.0
    assert summary["grounded"] == "n/a"


def test_sample_pack_ablation_runs_offline_and_resumes(settings, tmp_path):
    pack = load_pack(settings.packs_dir, "sample")
    ingest_pack(pack, settings)
    retriever, golden, llm = load_retriever(pack, settings), load_golden(pack), build_llm(settings)
    run_dir = tmp_path / "run"

    class FailsAfter:
        """A generator that hits a 'rate limit' after a few calls."""

        name = "flaky"

        def __init__(self, limit):
            self.calls, self.limit = 0, limit

        def complete(self, prompt):
            self.calls += 1
            if self.calls > self.limit:
                raise LLMError("rate limit")
            return llm.complete(prompt)

    with pytest.raises(LLMError):
        run_answer_eval(pack, golden, retriever, FailsAfter(5), llm, llm, settings, run_dir)
    finished = len((run_dir / "vector.jsonl").read_text().splitlines())
    assert finished == 5

    counting = FailsAfter(10_000)
    summaries = run_answer_eval(pack, golden, retriever, counting, llm, llm, settings, run_dir)
    # The five finished questions were not asked again: 3 single-shot configs + agent drafts.
    assert counting.calls < 4 * len(golden) - 5 + 1
    assert [s["config"] for s in summaries] == list(CONFIGS)
    assert all(s["questions"] == len(golden) for s in summaries)
    agent = summaries[-1]
    assert agent["correctness"] >= 0.9 and agent["refused_unanswerable"] == 1.0
    assert json.loads((run_dir / "summary.json").read_text()) == summaries
