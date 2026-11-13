"""Plan v2 phase 5 acceptance: a long-book golden set, before and after book structure.

    python scripts/bench_book.py --out results/phase5-book.md            # offline (fake LLM)
    python scripts/bench_book.py --live --out results/phase5-book-live.md  # the configured LLM

Builds a 200-page manual (10 chapters on different topics, 2 sections each, a PDF outline,
one fact per page that only that page states), uploads it to a fresh collection and asks
20 questions: 12 about a fact on one page, 8 about a whole chapter or the whole book.

"Before" turns book structure off (no outline paths, no summaries); "after" turns it on.
Scored per question:
  fact questions:   the answer contains the fact (exact string)
  global questions: share of the chapter's topic terms found in the passages the grader
                    kept, which the answer was written from ("context"), and in the answer
and the model calls each question made, chapter summaries included.
"""

import argparse
import json
import random
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]

CHAPTERS = [
    ("Site survey", ["roof orientation", "shading", "structural load", "rafters"]),
    ("Solar panels", ["monocrystalline", "efficiency", "degradation", "bypass diodes"]),
    ("Inverters", ["string inverter", "microinverter", "MPPT", "clipping"]),
    ("Batteries", ["lithium iron phosphate", "cycles", "depth of discharge", "thermal runaway"]),
    ("Wiring", ["DC cable", "conduit", "earthing", "voltage drop"]),
    ("Net metering", ["export", "bidirectional meter", "tariff", "billing cycle"]),
    ("Safety", ["fall protection", "isolation", "arc flash", "lockout"]),
    ("Maintenance", ["cleaning", "inspection", "thermal imaging", "hot spots"]),
    ("Monitoring", ["data logger", "alerts", "yield", "irradiance"]),
    ("Warranty", ["product warranty", "performance guarantee", "claims", "serial number"]),
]
PAGES_PER_CHAPTER = 20


def code(page: int) -> str:
    return f"KX-{(page * 7919) % 100000:05d}"


def make_book(path: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    rng = random.Random(5)
    width, height = A4
    pdf = canvas.Canvas(str(path), pagesize=A4)
    page = 0
    for number, (topic, terms) in enumerate(CHAPTERS, start=1):
        for offset in range(PAGES_PER_CHAPTER):
            page += 1
            y = height - 80
            if offset == 0:
                pdf.bookmarkPage(f"c{number}")
                pdf.addOutlineEntry(f"Chapter {number}: {topic}", f"c{number}", 0)
                pdf.setFont("Helvetica-Bold", 18)
                pdf.drawString(60, y, f"Chapter {number}: {topic}")
                y -= 34
            if offset in (0, PAGES_PER_CHAPTER // 2):
                part = 1 if offset == 0 else 2
                pdf.bookmarkPage(f"c{number}s{part}")
                title = f"{number}.{part} {topic}: {'basics' if part == 1 else 'in practice'}"
                pdf.addOutlineEntry(title, f"c{number}s{part}", 1)
            pdf.setFont("Helvetica", 10)
            lines = [
                f"The reference code for page {page} is {code(page)}.",
                f"This page of the {topic.lower()} chapter deals with {rng.choice(terms)}.",
                f"Installers check the {rng.choice(terms)} before they sign off the job.",
                f"A common mistake is to ignore {rng.choice(terms)} on older houses.",
                f"The {topic.lower()} work is recorded in the site book with photos.",
                f"Customers often ask how {rng.choice(terms)} affects their bill.",
            ]
            for line in lines:
                pdf.drawString(60, y, line)
                y -= 16
            pdf.setFont("Helvetica", 8)
            pdf.drawString(width / 2 - 20, 30, f"Page {page}")
            pdf.showPage()
    pdf.save()


def golden() -> list[dict]:
    rng = random.Random(11)
    pages = sorted(rng.sample(range(1, len(CHAPTERS) * PAGES_PER_CHAPTER + 1), 12))
    facts = [
        {"kind": "fact", "question": f"What is the reference code for page {p}?", "fact": code(p)}
        for p in pages
    ]

    def terms(*numbers: int) -> list[str]:
        return [term for n in numbers for term in CHAPTERS[n - 1][1]]

    whole = [
        {"question": "What is chapter 4 about?", "terms": terms(4)},
        {"question": "What does chapter 7 cover?", "terms": terms(7)},
        {"question": "Summarise chapter 9.", "terms": terms(9)},
        {"question": "What is chapter 1 about?", "terms": terms(1)},
        {"question": "Summarise chapter 10.", "terms": terms(10)},
        {"question": "Compare chapters 2 and 3.", "terms": terms(2, 3)},
        {"question": "Which chapter covers net metering, and what does it say?", "terms": terms(6)},
        {
            "question": "What is this book about overall?",
            "terms": [CHAPTERS[n][1][0] for n in range(10)],
        },
    ]
    return facts + [{"kind": "global", **item} for item in whole]


def coverage(terms: list[str], text: str) -> float:
    text = text.lower()
    return round(sum(term.lower() in text for term in terms) / len(terms), 3)


def run(book: Path, structure: bool, live: bool) -> list[dict]:
    from fastapi.testclient import TestClient

    from hyper_rag import api
    from hyper_rag.config import load_settings
    from hyper_rag.uploads import CollectionStore

    data = Path(tempfile.mkdtemp(prefix="hyper-rag-book-"))
    settings = load_settings(offline=not live).model_copy(
        update={"data_dir": data, "book_structure": structure, "ocr": "none"}
    )
    store = CollectionStore(settings)
    api.get_settings, api.get_store = (lambda: settings), (lambda: store)
    api.get_llms.cache_clear()
    store.create("Manual")
    copy = data / "manual.pdf"
    copy.write_bytes(book.read_bytes())
    store.add_path("manual", "manual.pdf", copy)
    client = TestClient(api.app)
    rows = []
    for item in golden():
        started = time.monotonic()
        reply = client.post("/collections/manual/ask", json={"question": item["question"]})
        if reply.status_code != 200:
            rows.append({**item, "error": reply.text[:200]})
            continue
        body = reply.json()
        run_log = client.get(f"/collections/manual/runs/{body['run_id']}").json()
        summaries = sum(e["t"] == "a.summarize" for e in run_log["events"])
        passages = [store.source("manual", c["chunk_id"]) for c in body["citations"]]
        texts = {chunk.id: chunk.text for chunk in store.retriever("manual").chunks}
        grades = [e for e in run_log["events"] if e["t"] == "a.grade"]
        kept = grades[-1]["kept"] if grades else []
        context = " ".join(texts.get(chunk_id, "") for chunk_id in kept)
        row = {
            "kind": item["kind"],
            "question": item["question"],
            "answer": body["answer"],
            "refused": body["refused"],
            "calls": body["llm_calls"] + summaries,
            "seconds": round(time.monotonic() - started, 1),
            "cited": [p["unit_label"] for p in passages],
            "kept": kept,
        }
        if item["kind"] == "fact":
            row["score"] = float(item["fact"] in body["answer"])
        else:
            row["context"] = coverage(item["terms"], context)
            row["score"] = coverage(item["terms"], body["answer"])
        rows.append(row)
    return rows


def summarise(rows: list[dict], kind: str, key: str) -> float:
    values = [r.get(key, 0) for r in rows if r["kind"] == kind]
    return round(sum(values) / len(values), 3) if values else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="use the configured LLM, not the fake")
    parser.add_argument("--out", type=Path, default=HERE / "results" / "phase5-book.md")
    args = parser.parse_args()
    sys.path.insert(0, str(HERE / "src"))

    book = Path(tempfile.mkdtemp()) / "manual.pdf"
    make_book(book)
    results = {"before": run(book, False, args.live), "after": run(book, True, args.live)}
    model = "the configured model (live)" if args.live else "the offline rule-based stand-in"
    lines = [
        f"# Phase 5: a long-book golden set, before and after book structure "
        f"({time.strftime('%Y-%m-%d')})",
        "",
        f"A 200-page manual (10 chapters, 2 sections each, a PDF outline), 20 questions, "
        f"answered by {model}. Before: no outline paths, no summaries. After: outline paths, "
        "extractive section summaries, chapter summaries written on demand, summaries searched "
        "first for questions about a whole.",
        "",
        "| | Fact questions: fact in answer | Whole-book questions: topic terms in the passages "
        "kept for the answer | ... in the answer | Model calls per question (mean) |",
        "|---|---|---|---|---|",
    ]
    for label, rows in results.items():
        calls = round(sum(r.get("calls", 0) for r in rows) / len(rows), 2)
        fact = summarise(rows, "fact", "score")
        context = summarise(rows, "global", "context")
        answer = summarise(rows, "global", "score")
        lines.append(f"| {label} | {fact} | {context} | {answer} | {calls} |")
    lines += [
        "",
        "## Whole-book questions",
        "",
        "| Question | Before: context / answer / calls | After: context / answer / calls |",
        "|---|---|---|",
    ]
    before = {r["question"]: r for r in results["before"]}
    for row in results["after"]:
        if row["kind"] != "global":
            continue
        old = before[row["question"]]
        lines.append(
            f"| {row['question']} | {old.get('context')} / {old.get('score')} / {old.get('calls')}"
            f" | {row.get('context')} / {row.get('score')} / {row.get('calls')} |"
        )
    lines += [
        "",
        "## What this does not show",
        "",
        "- The book is synthetic: chapters on distinct topics make the gain easy to see. "
        "A real book's chapters overlap more.",
        "- The 'answer' score counts topic terms, a proxy for a good summary, not a judge.",
        "- The first whole-book question pays for the chapter summaries it needs; later "
        "ones reuse them, so the mean calls fall as the collection is used.",
        "",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines))
    (args.out.with_suffix(".json")).write_text(json.dumps(results, indent=1))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
