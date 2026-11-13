"""Auto-evaluation of an uploaded collection.

A domain pack ships a golden set written by hand. Nobody writes one for the files they
just uploaded, so this module writes one: it samples passages, asks the generator model
for a question each passage answers, and runs the normal harness on the result.

What the numbers mean, and do not mean: every question was written from the passage it
is scored against, so it shares that passage's vocabulary and is easier to retrieve than
a question a person would ask. Read the scores as "is the system working on this
collection, and which configuration works best", not as absolute quality. There are no
unanswerable questions either: nothing here can prove a question is not answered
somewhere in the collection.
"""

import hashlib
import json
import random
from collections.abc import Callable
from datetime import date
from pathlib import Path

from hyper_rag.config import Settings
from hyper_rag.evaluation.answer_eval import run_answer_eval
from hyper_rag.evaluation.retrieval_eval import evaluate_retrieval
from hyper_rag.llm import LLM, build_llm, parse_json
from hyper_rag.packs import GoldenQuestion, read_golden
from hyper_rag.prompts import synthesize_prompt
from hyper_rag.text import contains_fact
from hyper_rag.types import Chunk
from hyper_rag.uploads import CollectionStore

# Passages shorter than this rarely hold a fact worth asking about (titles, captions).
MIN_PASSAGE_CHARS = 200
MAX_FACT_CHARS = 40


def pick_passages(chunks: list[Chunk], count: int, seed: int = 0) -> list[Chunk]:
    """Sample passages spread evenly over the files, deterministically for a given seed."""
    usable = [chunk for chunk in chunks if len(chunk.text) >= MIN_PASSAGE_CHARS]
    if len(usable) < count:  # a small collection: take what there is
        usable = [chunk for chunk in chunks if len(chunk.text) >= 60]
    by_file: dict[str, list[Chunk]] = {}
    for chunk in usable:
        by_file.setdefault(chunk.doc_id.split("/")[0], []).append(chunk)
    rng = random.Random(seed)
    for file_chunks in by_file.values():
        rng.shuffle(file_chunks)
    picked: list[Chunk] = []
    # Round-robin over files, so one long PDF does not supply every question.
    while len(picked) < count and any(by_file.values()):
        for file_id in sorted(by_file):
            if by_file[file_id] and len(picked) < count:
                picked.append(by_file[file_id].pop())
    return picked


def _usable_fact(fact: str, passage: str) -> bool:
    """A key fact is checked by exact match, so it has to be short and literal.

    The first live run showed why: the model copied whole sentences and pieces of table
    rows ("Solar panel | 25") as the fact, and correct answers that reworded them were
    counted as wrong. Anything longer than a few words is dropped; the question then
    simply has no exact-match check.
    """
    return (
        bool(fact)
        and len(fact) <= MAX_FACT_CHARS
        and len(fact.split()) <= 4
        and "|" not in fact
        and contains_fact(passage, fact)
    )


def generate_golden(
    chunks: list[Chunk],
    llm: LLM,
    count: int,
    seed: int = 0,
    on_progress: Callable[[str], None] = lambda line: None,
) -> list[dict]:
    """One golden row per sampled passage. Rows the model fails to write are skipped."""
    rows = []
    for chunk in pick_passages(chunks, count, seed):
        reply = parse_json(llm.complete(synthesize_prompt(chunk)))
        question = str(reply.get("question", "")).strip()
        answer = str(reply.get("answer", "")).strip()
        if not question or not answer:
            on_progress(f"  skipped a passage of {chunk.title}: no usable question")
            continue
        fact = str(reply.get("fact", "")).strip()
        rows.append(
            {
                "id": f"auto-{len(rows) + 1:02d}",
                "question": question,
                "answerable": True,
                "reference_answer": answer,
                "relevant_sources": [[chunk.doc_id]],
                # The model is asked to copy the fact from the passage. Keep it only if
                # it really is there; a paraphrased "fact" would fail correct answers.
                "key_facts": [fact] if _usable_fact(fact, chunk.text) else [],
                "source_chunk": chunk.id,
                "source_title": chunk.title,
            }
        )
        on_progress(f"  question {len(rows)}: {question}")
    return rows


def evaluate_collection(
    store: CollectionStore,
    slug: str,
    settings: Settings,
    questions: int = 8,
    configs: tuple[str, ...] = ("hybrid_rerank", "agent"),
    use_judge: bool = False,
    regenerate: bool = False,
    on_progress: Callable[[str], None] = print,
) -> dict:
    """Write (or reuse) a golden set for the collection and run the eval harness on it."""
    retriever = store.retriever(slug)
    generator = build_llm(settings, "generator")
    control = build_llm(settings, "control")
    judge = build_llm(settings, "judge") if use_judge else None
    judge_name = judge.name if judge else "none"

    # The golden set belongs to an exact set of files, a question count and a model.
    # Change any of them and it is written again; otherwise a re-run reuses it, which is
    # also what makes an interrupted run resumable.
    files = sorted(record["sha256"] for record in store.get(slug)["files"])
    identity = json.dumps([files, questions, generator.name, retriever.embedder.name])
    signature = hashlib.sha256(identity.encode()).hexdigest()[:10]
    eval_dir = store.path(slug) / "eval"
    golden_path = eval_dir / f"golden-{signature}.jsonl"
    if regenerate or not golden_path.exists():
        on_progress(f"Writing {questions} test questions from the collection's passages")
        rows = generate_golden(retriever.chunks, generator, questions, on_progress=on_progress)
        if not rows:
            raise RuntimeError("No test questions could be written from this collection.")
        eval_dir.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
        )
    golden: list[GoldenQuestion] = read_golden(golden_path)
    golden_rows = [json.loads(line) for line in golden_path.read_text("utf-8").splitlines()]

    on_progress("Scoring retrieval (no LLM calls)")
    retrieval_rows = evaluate_retrieval(retriever, golden)

    run_name = f"{generator.name}__judge-{judge_name}".replace("/", "-").replace(":", "-")
    run_dir = eval_dir / "runs" / f"{signature}-{run_name}"
    if regenerate and run_dir.exists():
        for stale in run_dir.glob("*.jsonl"):
            stale.unlink()
    on_progress(f"Answering with: {', '.join(configs)}")
    answer_rows = run_answer_eval(
        store.description(slug),
        golden,
        retriever,
        generator,
        control,
        judge,
        settings,
        run_dir,
        configs=configs,
        on_progress=on_progress,
        route=False,  # the same agent the collection is asked with
    )
    report = {
        "collection": slug,
        "date": date.today().isoformat(),
        "generator": generator.name,
        "control": control.name,
        "judge": judge_name,
        "embedder": retriever.embedder.name,
        "chunks": len(retriever.chunks),
        "questions": len(golden),
        "golden": [
            {key: row[key] for key in ("id", "question", "reference_answer", "source_title")}
            for row in golden_rows
        ],
        "retrieval": retrieval_rows,
        "answers": answer_rows,
        "note": (
            "Questions were written by the generator model from this collection's own "
            "passages, so they are easier than real questions. See evaluation/synthetic.py."
        ),
    }
    (eval_dir / "latest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def latest_report(store: CollectionStore, slug: str) -> dict | None:
    path: Path = store.path(slug) / "eval" / "latest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
