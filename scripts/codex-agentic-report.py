#!/usr/bin/env python3
"""Generate a compact markdown report from the experiment docs folder."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable


TITLE_RE = re.compile(r"^\s*>?\s*#\s+(?P<title>.+)$", re.MULTILINE)
DATE_RE = re.compile(r"^\s*>?\s*\*\*Date:\*\*\s*(?P<date>.+)$", re.MULTILINE)
DAY_RE = re.compile(r"^\s*>?\s*\*\*Day:\*\*\s*(?P<day>.+)$", re.MULTILINE)
SESSION_RE = re.compile(r"^\s*>?\s*\*\*Session:\*\*\s*(?P<session>.+)$", re.MULTILINE)


@dataclass(frozen=True)
class ExperimentDoc:
    path: Path
    title: str
    date: str
    day: str
    session: str


def parse_experiment_doc(path: Path) -> ExperimentDoc:
    content = path.read_text(encoding="utf-8")
    title_match = TITLE_RE.search(content)
    date_match = DATE_RE.search(content)
    day_match = DAY_RE.search(content)
    session_match = SESSION_RE.search(content)

    title = title_match.group("title").strip() if title_match else path.stem
    date = date_match.group("date").strip() if date_match else "Unknown"
    day = day_match.group("day").strip() if day_match else "Unknown"
    session = session_match.group("session").strip() if session_match else ""

    return ExperimentDoc(path=path, title=title, date=date, day=day, session=session)


def iter_experiment_docs(root: Path) -> Iterable[ExperimentDoc]:
    for path in sorted(root.glob("*.md")):
        if path.is_file():
            yield parse_experiment_doc(path)


def build_report(docs: list[ExperimentDoc], root: Path) -> str:
    lines = [
        "# Codex Agentic Workflow Report",
        "",
        f"Source folder: `{root.as_posix()}`",
        "",
        "## Experiment Docs",
        "",
        "| File | Title | Date | Day | Session |",
        "|------|-------|------|-----|---------|",
    ]

    for doc in docs:
        lines.append(
            f"| `{doc.path.name}` | {doc.title} | {doc.date} | {doc.day} | {doc.session} |"
        )

    lines.extend(
        [
            "",
            "## Observations",
            "",
            f"- Found {len(docs)} experiment document(s) in the folder.",
            "- Documents follow a consistent header pattern with title, date, and day metadata.",
            "- The output is suitable for quick planning, indexing, or a final summary pass.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a markdown report from docs/experiments."
    )
    parser.add_argument(
        "--root",
        default="docs/experiments",
        help="Path to the experiment documentation folder.",
    )
    parser.add_argument(
        "--output",
        help="Optional path to write the report. Prints to stdout when omitted.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        raise SystemExit(f"Experiment folder not found: {root}")

    docs = list(iter_experiment_docs(root))
    report = build_report(docs, root)

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.write_text(report + "\n", encoding="utf-8")
    else:
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
