"""Answer-quality evaluation and the ablation across system configurations.

Four configurations answer every golden question:

    vector          single-shot RAG over dense retrieval only
    hybrid          single-shot RAG over dense + BM25 fused with RRF
    hybrid_rerank   single-shot RAG over the fused list reranked by a cross-encoder
    agent           the LangGraph agent on top of hybrid_rerank

Results are written one JSON line per question as soon as it is scored. A run that
dies on a rate limit keeps everything it finished; running the same command again
skips those questions and continues.
"""

import json
from collections.abc import Callable
from pathlib import Path

from hyper_rag.agent import Agent, Answer, single_shot_answer
from hyper_rag.config import Settings
from hyper_rag.evaluation.retrieval_metrics import mean
from hyper_rag.llm import LLM, parse_json
from hyper_rag.packs import GoldenQuestion
from hyper_rag.prompts import check_prompt, judge_prompt
from hyper_rag.retrieval.retriever import MODES, Retriever
from hyper_rag.text import contains_fact

CONFIGS = (*MODES, "agent")

VERDICT_SCORES = {"correct": 1.0, "partial": 0.5, "incorrect": 0.0}


def score_answer(question: GoldenQuestion, answer: Answer, judge: LLM | None) -> dict:
    """Score one answer. Fields that do not apply to this question are left out.

    With judge=None only the deterministic metrics are computed (citations, key facts,
    refusals); the two judged metrics, groundedness and correctness, are skipped.
    """
    row: dict = {
        "id": question.id,
        "answerable": question.answerable,
        "refused": answer.refused,
        "llm_calls": answer.llm_calls,
        "answer": answer.text,
        "passages": [chunk.id for chunk in answer.passages],
        "trace": answer.trace,
    }
    if answer.refused:
        if question.answerable and judge is not None:
            row["correctness"] = 0.0  # declining an answerable question is a wrong answer
        return row

    # --- the system gave an answer -------------------------------------------------
    # Groundedness: is every claim supported by the passages the answer cites? Judging
    # against the cited passages (rather than everything retrieved) also catches a
    # correct claim attributed to the wrong source, and keeps the judge prompt small.
    # An answer with no citations is checked against all the passages it was given.
    if judge is not None:
        evidence = [chunk for _, chunk in answer.citations] or answer.passages
        verdict = parse_json(judge.complete(check_prompt(answer.text, evidence)))
        row["grounded"] = 1.0 if verdict.get("grounded") is True else 0.0

    # Citations (deterministic, no LLM).
    row["has_citation"] = 1.0 if answer.cited else 0.0
    row["invalid_citations"] = len(answer.invalid_citations)

    if question.answerable:
        gold_docs = {doc for need in question.relevant_sources for doc in need}
        if answer.cited:
            # Citation precision: share of cited passages that come from a gold document.
            cited_docs = [chunk.doc_id for _, chunk in answer.citations]
            row["citation_precision"] = sum(d in gold_docs for d in cited_docs) / len(cited_docs)
        # Correctness against the reference answer, by the judge model...
        if judge is not None:
            prompt = judge_prompt(question.question, question.reference_answer, answer.text)
            reply = parse_json(judge.complete(prompt))
            row["correctness"] = VERDICT_SCORES.get(str(reply.get("verdict")), 0.0)
        # ...and by exact string match on key facts, as a check on the judge itself.
        if question.key_facts:
            found = all(contains_fact(answer.text, fact) for fact in question.key_facts)
            row["key_facts"] = 1.0 if found else 0.0
    return row


def summarise(config: str, rows: list[dict]) -> dict:
    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    answered = [r for r in rows if not r["refused"]]

    def average(items: list[dict], field: str) -> float | str:
        values = [r[field] for r in items if field in r]
        return round(mean(values), 3) if values else "n/a"

    return {
        "config": config,
        "questions": len(rows),
        # Over answerable questions; a refusal scores 0.
        "correctness": average(answerable, "correctness"),
        "key_facts": average(answerable, "key_facts"),
        # Over every answer the system gave.
        "grounded": average(answered, "grounded"),
        "cited": average(answered, "has_citation"),
        "citation_precision": average(answerable, "citation_precision"),
        # Refusal behaviour: unanswerable questions should be declined, answerable ones not.
        "refused_unanswerable": average([{"v": float(r["refused"])} for r in unanswerable], "v"),
        "refused_answerable": average([{"v": float(r["refused"])} for r in answerable], "v"),
        "llm_calls": average(rows, "llm_calls"),
    }


def _load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def run_answer_eval(
    description: str,
    golden: list[GoldenQuestion],
    retriever: Retriever,
    generator: LLM,
    control: LLM,
    judge: LLM | None,
    settings: Settings,
    run_dir: Path,
    configs: tuple[str, ...] = CONFIGS,
    on_progress: Callable[[str], None] = print,
    route: bool = True,
) -> list[dict]:
    """Answer and score every golden question under each configuration. Resumable.

    `description` is what the agent's router is told the corpus is about: a pack's
    description, or the generated one of an uploaded collection.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    agent = Agent(
        retriever,
        generator,
        description,
        max_rewrites=settings.max_rewrites,
        control_llm=control,
        route=route,
    )
    summaries = []
    for config in configs:
        path = run_dir / f"{config}.jsonl"
        rows = _load_rows(path)
        done = {row["id"] for row in rows}
        with path.open("a", encoding="utf-8") as handle:
            for question in golden:
                if question.id in done:
                    continue
                if config == "agent":
                    answer = agent.ask(question.question)
                else:
                    answer = single_shot_answer(question.question, retriever, generator, config)
                row = score_answer(question, answer, judge)
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.flush()
                rows.append(row)
                on_progress(
                    f"  {config} {question.id}: {'refused' if answer.refused else 'answered'}"
                )
        summaries.append(summarise(config, rows))
    (run_dir / "summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    return summaries
