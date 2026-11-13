"""Plain text, Markdown, HTML and CSV."""

import csv
import io
from pathlib import Path

from hyper_rag.parsing.model import ParsedFile, Unit, table_to_markdown

MAX_CSV_ROWS = 5000


def _read_text(path: Path, parsed: ParsedFile) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            return data.decode(encoding)
        except UnicodeError:
            continue
    parsed.warnings.append("Not valid UTF-8; read as Windows-1252, some characters may be wrong.")
    return data.decode("cp1252", errors="replace")


def parse_text(path: Path, kind: str = "text") -> ParsedFile:
    parsed = ParsedFile(kind=kind, unit_name="section")
    text = _read_text(path, parsed).replace("\r\n", "\n").strip()
    if text:
        parsed.units.append(Unit(number=1, label="", text=text))
    return parsed


def parse_html(path: Path) -> ParsedFile:
    from hyper_rag.web import html_to_markdown

    parsed = ParsedFile(kind="html", unit_name="section")
    title, text = html_to_markdown(_read_text(path, parsed), content_selector="main")
    if title and not text.lstrip().startswith("#"):
        text = f"# {title}\n\n{text}"
    if text.strip():
        parsed.units.append(Unit(number=1, label="", text=text.strip()))
    return parsed


def parse_csv(path: Path) -> ParsedFile:
    parsed = ParsedFile(kind="csv", unit_name="section")
    text = _read_text(path, parsed)
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel_tab if path.suffix.lower() == ".tsv" else csv.excel
    rows = []
    for row in csv.reader(io.StringIO(text), dialect):
        if len(rows) >= MAX_CSV_ROWS:
            parsed.warnings.append(f"Only the first {MAX_CSV_ROWS} rows were read.")
            break
        rows.append(row)
    markdown = table_to_markdown(rows)
    if markdown:
        parsed.units.append(Unit(number=1, label="", text=markdown, tables=1))
    return parsed
