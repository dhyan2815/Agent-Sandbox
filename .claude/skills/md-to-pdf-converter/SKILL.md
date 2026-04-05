---
name: md-to-pdf-converter
description: >
  Converts Markdown (.md) files into professional, high-fidelity PDF reports.
  Use when the user needs a PDF output from a Markdown file that preserves
  tables, bold/italic text, headers (H1–H4), bullet lists, code blocks, and
  horizontal rules. Produces clean, readable output via reportlab's Platypus
  layout engine with full Unicode support.
---

allowed-tools:
  - Read
  - Write
  - Bash

dependencies:
  - python >= 3.8
  - reportlab >= 3.6

---

## Overview

This skill converts a Markdown file to a polished PDF using **reportlab's Platypus** layout engine. Platypus handles automatic page breaks, word-wrap, inline bold/italic via XML tags, and table layout — eliminating the manual drawing problems of lower-level libraries like `fpdf`.

---

## Execution Steps

### Step 1 — Install Dependencies

Always run this first. Use `--break-system-packages` to avoid pip environment errors on modern systems:

```bash
pip install reportlab --break-system-packages -q
```

Verify it worked:
```bash
python3 -c "import reportlab; print('reportlab OK:', reportlab.Version)"
```

If this fails, try `pip3` instead of `pip`.

---

### Step 2 — Read the Markdown File

Read the input `.md` file completely before generating the converter script. Note:
- The input path (e.g. `report.md`)
- Derive the output path by replacing `.md` with `.pdf` (e.g. `report.pdf`)

---

### Step 3 — Generate and Run `convert.py`

Write the following **complete, runnable** Python script as `convert.py`, substituting:
- `INPUT_PATH` → actual path to the `.md` file
- `OUTPUT_PATH` → derived `.pdf` output path

```python
#!/usr/bin/env python3
"""
Markdown to PDF Converter
Uses reportlab Platypus for robust layout, auto page-breaks, and Unicode support.
"""

import re
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Preformatted
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

INPUT_PATH = "INPUT_PATH"   # ← Replace with actual input path
OUTPUT_PATH = "OUTPUT_PATH" # ← Replace with actual output path

# ── Styles ─────────────────────────────────────────────────────────────────
base_styles = getSampleStyleSheet()

styles = {
    "h1": ParagraphStyle(
        "H1", parent=base_styles["Normal"],
        fontSize=20, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=10, spaceBefore=16,
        borderPad=4, backColor=colors.HexColor("#e8ecf0"),
        leading=24, leftIndent=4,
    ),
    "h2": ParagraphStyle(
        "H2", parent=base_styles["Normal"],
        fontSize=15, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#16213e"),
        spaceAfter=8, spaceBefore=12,
        borderPad=3, leading=18,
        leftIndent=2,
    ),
    "h3": ParagraphStyle(
        "H3", parent=base_styles["Normal"],
        fontSize=12, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0f3460"),
        spaceAfter=6, spaceBefore=8, leading=15,
    ),
    "h4": ParagraphStyle(
        "H4", parent=base_styles["Normal"],
        fontSize=11, fontName="Helvetica-BoldOblique",
        textColor=colors.HexColor("#333333"),
        spaceAfter=4, spaceBefore=6, leading=14,
    ),
    "body": ParagraphStyle(
        "Body", parent=base_styles["Normal"],
        fontSize=10, fontName="Helvetica",
        textColor=colors.HexColor("#222222"),
        spaceAfter=6, leading=14, alignment=TA_LEFT,
    ),
    "bullet": ParagraphStyle(
        "Bullet", parent=base_styles["Normal"],
        fontSize=10, fontName="Helvetica",
        textColor=colors.HexColor("#222222"),
        spaceAfter=3, leading=13, leftIndent=18,
        bulletIndent=6,
    ),
    "code": ParagraphStyle(
        "Code", parent=base_styles["Code"],
        fontSize=8.5, fontName="Courier",
        textColor=colors.HexColor("#2d2d2d"),
        backColor=colors.HexColor("#f4f4f4"),
        spaceAfter=8, spaceBefore=4,
        leftIndent=12, rightIndent=12, leading=13,
        borderColor=colors.HexColor("#cccccc"),
        borderWidth=0.5, borderPad=6, borderRadius=2,
    ),
}

# ── Inline Markdown → ReportLab XML ────────────────────────────────────────
def inline_md(text: str) -> str:
    """Convert inline Markdown (bold, italic, inline-code) to ReportLab XML."""
    # Escape XML special chars first (but not & which may already be entities)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Bold+italic: ***text*** or ___text___
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)
    text = re.sub(r'___(.+?)___', r'<b><i>\1</i></b>', text)
    # Bold: **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    # Italic: *text* or _text_
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)
    # Inline code: `code`
    text = re.sub(r'`(.+?)`', r'<font name="Courier" size="9" color="#c0392b">\1</font>', text)
    return text

# ── Table Parser ────────────────────────────────────────────────────────────
def is_separator_row(row: str) -> bool:
    """Detect Markdown table separator rows like |---|:---:|"""
    return bool(re.match(r'^\|[\s\-:| ]+\|$', row.strip()))

def parse_md_table(lines: list[str]) -> Table | None:
    """Parse Markdown table lines into a reportlab Table flowable."""
    rows = []
    for line in lines:
        if is_separator_row(line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows.append(cells)

    if not rows:
        return None

    col_count = max(len(r) for r in rows)
    # Pad rows with unequal columns
    padded = [r + [""] * (col_count - len(r)) for r in rows]

    usable_width = A4[0] - 4 * cm  # A4 width minus margins
    col_width = usable_width / col_count

    # Convert cell text to Paragraph objects for word-wrap
    cell_style = ParagraphStyle(
        "TC", parent=base_styles["Normal"],
        fontSize=9, leading=12, fontName="Helvetica",
    )
    header_style = ParagraphStyle(
        "TH", parent=base_styles["Normal"],
        fontSize=9, leading=12, fontName="Helvetica-Bold",
    )
    formatted = []
    for i, row in enumerate(padded):
        st = header_style if i == 0 else cell_style
        formatted.append([Paragraph(inline_md(c), st) for c in row])

    t = Table(formatted, colWidths=[col_width] * col_count, repeatRows=1)
    t.setStyle(TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        # Alternating row colours
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#ffffff"), colors.HexColor("#f2f5f7")]),
        # Grid
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
        # Padding
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t

# ── Main Parser ─────────────────────────────────────────────────────────────
def parse_markdown(md_text: str) -> list:
    """Convert full Markdown text into a list of reportlab Flowable objects."""
    flowables = []
    lines = md_text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]

        # ── Fenced code block ── ` ``` ` or ` ~~~ `
        if re.match(r'^```|^~~~', line):
            code_lines = []
            i += 1
            while i < len(lines) and not re.match(r'^```|^~~~', lines[i]):
                code_lines.append(lines[i])
                i += 1
            code_text = "\n".join(code_lines)
            flowables.append(Preformatted(code_text, styles["code"]))
            flowables.append(Spacer(1, 4))
            i += 1
            continue

        # ── Markdown table (collect all contiguous table lines) ──
        if line.startswith("|") and "|" in line[1:]:
            table_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            tbl = parse_md_table(table_lines)
            if tbl:
                flowables.append(Spacer(1, 4))
                flowables.append(tbl)
                flowables.append(Spacer(1, 8))
            continue

        # ── Horizontal rule ──
        if re.match(r'^(\-{3,}|\*{3,}|_{3,})\s*$', line):
            flowables.append(HRFlowable(width="100%", thickness=0.8,
                                        color=colors.HexColor("#aaaaaa"),
                                        spaceAfter=6, spaceBefore=6))
            i += 1
            continue

        # ── Headings ──
        h_match = re.match(r'^(#{1,4})\s+(.*)', line)
        if h_match:
            level = len(h_match.group(1))
            text = inline_md(h_match.group(2).strip())
            key = f"h{level}" if level <= 4 else "h4"
            flowables.append(Paragraph(text, styles[key]))
            i += 1
            continue

        # ── Unordered list item ──
        ul_match = re.match(r'^(\s*)[-*+]\s+(.*)', line)
        if ul_match:
            indent_lvl = len(ul_match.group(1)) // 2
            bullet_text = inline_md(ul_match.group(2).strip())
            sty = ParagraphStyle(
                f"BL{indent_lvl}",
                parent=styles["bullet"],
                leftIndent=18 + indent_lvl * 14,
                bulletText="•",
            )
            flowables.append(Paragraph(bullet_text, sty))
            i += 1
            continue

        # ── Ordered list item ──
        ol_match = re.match(r'^(\s*)\d+\.\s+(.*)', line)
        if ol_match:
            indent_lvl = len(ol_match.group(1)) // 2
            item_text = inline_md(ol_match.group(2).strip())
            # Count position for numbering
            num = sum(1 for f in flowables
                      if isinstance(f, Paragraph) and
                      hasattr(f, 'style') and f.style.name.startswith("OL")) + 1
            sty = ParagraphStyle(
                f"OL{indent_lvl}",
                parent=styles["bullet"],
                leftIndent=22 + indent_lvl * 14,
                bulletIndent=8,
                bulletText=f"{num}.",
            )
            flowables.append(Paragraph(item_text, sty))
            i += 1
            continue

        # ── Blank line → small spacer ──
        if line.strip() == "":
            if flowables and not isinstance(flowables[-1], Spacer):
                flowables.append(Spacer(1, 6))
            i += 1
            continue

        # ── Regular paragraph ──
        # Accumulate consecutive non-blank, non-special lines into one paragraph
        para_lines = []
        while (i < len(lines)
               and lines[i].strip() != ""
               and not lines[i].startswith("#")
               and not lines[i].startswith("|")
               and not re.match(r'^[-*+]\s', lines[i])
               and not re.match(r'^\d+\.\s', lines[i])
               and not re.match(r'^```|^~~~', lines[i])
               and not re.match(r'^(\-{3,}|\*{3,}|_{3,})\s*$', lines[i])):
            para_lines.append(lines[i].strip())
            i += 1
        if para_lines:
            para_text = inline_md(" ".join(para_lines))
            flowables.append(Paragraph(para_text, styles["body"]))

    return flowables


# ── Build PDF ───────────────────────────────────────────────────────────────
def build_pdf(input_path: str, output_path: str) -> None:
    with open(input_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2 * cm,
        title=input_path.replace(".md", ""),
    )

    flowables = parse_markdown(md_text)

    if not flowables:
        raise ValueError("No content parsed from the Markdown file.")

    doc.build(flowables)
    print(f"✅  PDF created: {output_path}")


if __name__ == "__main__":
    try:
        build_pdf(INPUT_PATH, OUTPUT_PATH)
    except FileNotFoundError:
        print(f"❌  Input file not found: {INPUT_PATH}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌  Conversion failed: {e}", file=sys.stderr)
        sys.exit(1)
```

---

### Step 4 — Execute and Verify

```bash
python3 convert.py
```

After execution:
- Confirm the output `.pdf` exists: `ls -lh output.pdf`
- If it fails, read the full error output and fix the script before retrying.
- Common errors and fixes:

| Error | Fix |
|---|---|
| `ModuleNotFoundError: reportlab` | Re-run the pip install step |
| `FileNotFoundError` | Check `INPUT_PATH` is the correct absolute or relative path |
| `XML syntax error in Paragraph` | Unescape raw `<`, `>`, `&` in the markdown before passing to `inline_md()` — the function handles this, but double-check custom edits |
| `Table has no rows` | Check that the Markdown table has at least one non-separator row |

---

### Step 5 — Cleanup

```bash
rm convert.py
```

Only remove `convert.py` after confirming the PDF exists and is non-zero bytes.

---

## Key Design Decisions

| Feature | Approach | Why |
|---|---|---|
| Layout engine | `reportlab` Platypus | Auto page-breaks, word-wrap, no manual coordinate math |
| Tables | `Table` + `TableStyle` | Handles variable column counts, alternating rows, header styling |
| Inline formatting | `inline_md()` regex → XML tags | `Paragraph` objects support `<b>`, `<i>`, `<font>` natively |
| Code blocks | `Preformatted` | Monospace, preserves indentation, no wrapping |
| Unicode | Helvetica + UTF-8 open | Works for most Latin-extended characters |
| Output filename | Derived from input | `report.md` → `report.pdf` (never hardcoded) |

---

## Limitations

- **Non-Latin scripts** (Arabic, CJK, Devanagari): Helvetica does not include these glyphs. Register a Unicode TTF font (e.g. DejaVuSans) and substitute in the `ParagraphStyle` definitions.
- **Nested lists** beyond 2 levels may render with imprecise indentation.
- **Images** (`![alt](url)`) are not rendered — they are silently skipped.
- **HTML inside Markdown** is not supported and may cause XML parse errors — strip it before conversion.

---

## Resources

- [ReportLab User Guide (PDF)](https://www.reportlab.com/docs/reportlab-userguide.pdf)
- [Platypus Flowables Reference](https://docs.reportlab.com/reportlab/userguide/ch6_paragraphs/)
- [TableStyle Commands](https://docs.reportlab.com/reportlab/userguide/ch7_tables/)