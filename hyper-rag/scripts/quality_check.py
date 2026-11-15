"""Real-model quality check for the claim checker and the LinkedIn outline export.

    python scripts/quality_check.py --out results/quality-check.md            # Groq (real)
    python scripts/quality_check.py --offline --out /tmp/q.md                 # stand-in, plumbing

The collection is the eight test fixtures (tests/make_files.py: an invented solar company,
one file per format, including a scanned page read by OCR). Two measurements:

1. Claim verdicts. 30 claims in results/quality/claims.jsonl, 10 per verdict, written and
   labelled by the author of this script from the fixtures' text (not by an independent
   person). Claims go straight to judge_claims, so the split step cannot change them.
   Reported: accuracy, the confusion matrix, and the rate that matters most for a checker,
   claims that are not supported but were called supported.
2. Outlines. The agent answers 8 questions (results/quality/questions.jsonl); each answer
   is exported as a LinkedIn outline. Reported: figures in the outline that are not in the
   answer it came from (a deterministic test for invented numbers), and the claim checker's
   verdicts on the outline's points against the collection.
"""

import argparse
import json
import re
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tests"))

VERDICTS = ("supported", "contradicted", "not_found")
FIGURE = re.compile(r"\d+(?:[.,]\d+)*")


def figures(text: str) -> set[str]:
    return {f.replace(",", "") for f in FIGURE.findall(text)}


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    from hyper_rag.agent import Agent
    from hyper_rag.claims import judge_claims
    from hyper_rag.config import load_settings
    from hyper_rag.export import export_answer
    from hyper_rag.llm import build_llm
    from hyper_rag.structure import PassagesOnly
    from hyper_rag.uploads import CollectionStore
    from make_files import make_all

    workdir = Path(tempfile.mkdtemp(prefix="hyper-rag-quality-"))
    settings = load_settings(offline=args.offline).model_copy(update={"data_dir": workdir / "data"})
    store = CollectionStore(settings)
    store.create("Solar")
    for path in make_all(workdir / "files"):
        store.add_file("solar", path.name, path.read_bytes())
    retriever = PassagesOnly(store.retriever("solar"))
    generator, control = build_llm(settings, "generator"), build_llm(settings, "control")

    # 1. Claim verdicts
    labelled = load(HERE / "results/quality/claims.jsonl")
    started = time.monotonic()
    checked, calls = judge_claims(retriever, control, [row["claim"] for row in labelled])
    rows = [
        {"claim": row["claim"], "label": row["label"], "verdict": c.verdict}
        for row, c in zip(labelled, checked, strict=True)
    ]
    confusion = Counter((r["label"], r["verdict"]) for r in rows)
    correct = sum(r["label"] == r["verdict"] for r in rows)
    not_supported = [r for r in rows if r["label"] != "supported"]
    false_supported = sum(r["verdict"] == "supported" for r in not_supported)
    claim_seconds = round(time.monotonic() - started, 1)

    # 2. Outlines
    agent = Agent(
        retriever=retriever,
        llm=generator,
        pack_description=store.description("solar"),
        max_rewrites=settings.max_rewrites,
        control_llm=control,
        route=False,
    )
    outlines = []
    for row in load(HERE / "results/quality/questions.jsonl"):
        answer = agent.ask(row["question"]).to_dict()
        if answer["refused"]:
            outlines.append({"question": row["question"], "refused": True})
            continue
        text = export_answer(answer, "linkedin", generator)["text"]
        points = [line[2:].strip() for line in text.splitlines() if line.startswith("- ")]
        point_checks, _ = judge_claims(retriever, control, points) if points else ([], 0)
        outlines.append(
            {
                "question": row["question"],
                "refused": False,
                "answer": answer["answer"],
                "outline": text,
                "invented_figures": sorted(figures(text) - figures(answer["answer"])),
                "points": [{"point": p.text, "verdict": p.verdict} for p in point_checks],
            }
        )

    report = {
        "date": time.strftime("%Y-%m-%d"),
        "offline": args.offline,
        "generator": generator.name,
        "control": control.name,
        "claims": {
            "rows": rows,
            "accuracy": round(correct / len(rows), 3),
            "correct": correct,
            "total": len(rows),
            "false_supported": false_supported,
            "not_supported_total": len(not_supported),
            "llm_calls": calls,
            "seconds": claim_seconds,
            "confusion": {f"{a}->{b}": n for (a, b), n in sorted(confusion.items())},
        },
        "outlines": outlines,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.with_suffix(".json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    args.out.write_text(render(report))
    print(render(report))


def render(report: dict) -> str:
    c = report["claims"]
    lines = [
        "# Quality check: claim checker and LinkedIn outlines",
        "",
        f"Run {report['date']}. Generator `{report['generator']}`, decisions `{report['control']}`."
        + (
            " **Offline stand-in: these numbers measure plumbing, not quality.**"
            if report["offline"]
            else ""
        ),
        "Command: `python scripts/quality_check.py --out results/quality-check.md`.",
        "",
        "## Claim verdicts",
        "",
        f"30 claims, 10 per verdict, labelled by the script's author from the fixtures' text. "
        f"{c['llm_calls']} model calls, {c['seconds']} s.",
        "",
        f"- Accuracy: **{c['correct']} of {c['total']}** ({c['accuracy']:.0%})",
        f"- Called supported when not supported: **{c['false_supported']} of "
        f"{c['not_supported_total']}** (the error that matters most for a checker)",
        "",
        "| Label \\ verdict | supported | contradicted | not_found |",
        "|---|---|---|---|",
    ]
    counts = Counter((r["label"], r["verdict"]) for r in c["rows"])
    for label in VERDICTS:
        lines.append(f"| {label} | " + " | ".join(str(counts[(label, v)]) for v in VERDICTS) + " |")
    wrong = [r for r in c["rows"] if r["label"] != r["verdict"]]
    if wrong:
        lines += ["", "Misjudged claims:", ""]
        lines += [f"- {r['claim']} (label {r['label']}, verdict {r['verdict']})" for r in wrong]
    lines += ["", "## LinkedIn outlines", ""]
    done = [o for o in report["outlines"] if not o["refused"]]
    invented = sum(bool(o["invented_figures"]) for o in done)
    points = [p for o in done for p in o["points"]]
    tally = Counter(p["verdict"] for p in points)
    lines += [
        f"{len(done)} of {len(report['outlines'])} questions answered and exported.",
        "",
        f"- Outlines with a figure not in their answer: **{invented} of {len(done)}**",
        f"- Outline points checked against the collection: {len(points)}; supported "
        f"{tally['supported']}, contradicted {tally['contradicted']}, "
        f"not found {tally['not_found']}",
        "",
    ]
    for o in report["outlines"]:
        if o["refused"]:
            lines.append(f"- {o['question']}: declined, nothing to export")
            continue
        flags = (
            f" invented figures: {', '.join(o['invented_figures'])}"
            if o["invented_figures"]
            else ""
        )
        verdicts = ", ".join(p["verdict"] for p in o["points"]) or "no points"
        lines.append(f"- {o['question']}: {verdicts}.{flags}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
