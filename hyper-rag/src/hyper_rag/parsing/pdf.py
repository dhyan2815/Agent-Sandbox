"""PDF parsing with pdfplumber: text in reading order, tables, embedded images, scans."""

import statistics
from pathlib import Path

import pdfplumber

from hyper_rag.parsing.model import (
    ParsedFile,
    ParseError,
    Unit,
    image_text_block,
    table_to_markdown,
)
from hyper_rag.parsing.ocr import Ocr

# A page with fewer characters of real text than this is treated as a scan and read by OCR.
SCANNED_PAGE_CHARS = 25
# Embedded images smaller than this (in points; 72 per inch) are icons, rules and bullets.
MIN_IMAGE_SIDE = 40
MAX_IMAGES_PER_PAGE = 8
OCR_RESOLUTION = 200  # dots per inch when rendering a page or an image region for OCR
# pdfplumber's default gap for "these two letters are separate words" is 3 points, which
# is wider than a space in 9-point type: small print came out with its words run together.
# A tolerance relative to the font size works at every size.
WORDS = {"x_tolerance_ratio": 0.15}
MIN_WORDS_FOR_COLUMNS = 60
GUTTER = 6  # points of white space that count as a column gap


def _lines_to_markdown(lines: list[dict], body_size: float) -> str:
    """Join text lines into paragraphs, and mark lines in clearly larger type as headings.

    A PDF stores lines, not paragraphs: a paragraph is recovered as consecutive lines
    with no large vertical gap between them.
    """
    blocks: list[str] = []
    previous_bottom = None
    open_paragraph = False
    for line in lines:
        text = line["text"].strip()
        if not text:
            continue
        sizes = [char["size"] for char in line.get("chars", []) if char.get("size")]
        size = statistics.median(sizes) if sizes else body_size
        height = max(line["bottom"] - line["top"], 1.0)
        gap = previous_bottom is not None and line["top"] - previous_bottom > 0.7 * height
        previous_bottom = line["bottom"]
        if size >= 1.2 * body_size and len(text) <= 120:
            blocks.append(f"## {text}")
            open_paragraph = False
        elif open_paragraph and not gap:
            if blocks[-1].endswith("-") and text[0].islower():
                # A word hyphenated across a line break ("evalu-" / "ation"). Rejoining
                # also glues the rare real hyphen ("llama-" / "index"), a fair trade:
                # half-words match nothing in keyword search.
                blocks[-1] = blocks[-1][:-1] + text
            else:
                blocks[-1] += f" {text}"
        else:
            blocks.append(text)
            open_paragraph = True
    return "\n\n".join(blocks)


def _reading_order(box: tuple, page) -> list[tuple]:
    """Split a region of a page into boxes to read one after another.

    A two-column page read straight across gives lines made of half a sentence from each
    column. This looks for a vertical strip of white space near the middle of the region.
    If there is one, the region becomes: any full-width rows (a title, an abstract), then
    the left column, then the right column, repeated down the page.
    """
    x0, top, x1, bottom = box
    words = page.crop(box).extract_words(**WORDS)
    if len(words) < MIN_WORDS_FOR_COLUMNS:
        return [box]
    width = x1 - x0

    def crossing(x: float) -> list[dict]:
        return [w for w in words if w["x0"] < x + GUTTER / 2 and w["x1"] > x - GUTTER / 2]

    candidates = [x0 + width * share / 100 for share in range(35, 66)]
    gutter = min(candidates, key=lambda x: len(crossing(x)))
    spanning = crossing(gutter)
    left = sum(w["x1"] <= gutter for w in words)
    right = sum(w["x0"] >= gutter for w in words)
    # Two columns only if almost nothing crosses the strip and both sides carry real text.
    if len(spanning) > 0.06 * len(words) or min(left, right) < 0.2 * len(words):
        return [box]

    # Rows that do cross the strip are full-width; everything between them is two columns.
    boxes: list[tuple] = []
    cursor = top
    rows: list[list[float]] = []
    for word in sorted(spanning, key=lambda w: w["top"]):
        if rows and word["top"] <= rows[-1][1] + 2:
            rows[-1][1] = max(rows[-1][1], word["bottom"])
        else:
            rows.append([word["top"], word["bottom"]])

    def columns(upper: float, lower: float) -> None:
        if lower - upper > 2:
            boxes.extend([(x0, upper, gutter, lower), (gutter, upper, x1, lower)])

    for row_top, row_bottom in rows:
        row_top, row_bottom = max(row_top - 1, cursor), min(row_bottom + 1, bottom)
        columns(cursor, row_top)
        if row_bottom - row_top > 2:
            boxes.append((x0, row_top, x1, row_bottom))
        cursor = max(cursor, row_bottom)
    columns(cursor, bottom)
    return boxes


def _is_real_table(rows: list[list]) -> bool:
    # pdfplumber also reports boxes and rules as one-cell "tables".
    filled = [row for row in rows if any((cell or "").strip() for cell in row)]
    return len(filled) >= 2 and max(len(row) for row in filled) >= 2


def _parse_page(page, number: int, ocr: Ocr) -> Unit:
    x0, top, x1, bottom = page.bbox
    sizes = [char["size"] for char in page.chars if char.get("size")]
    body_size = statistics.median(sizes) if sizes else 10.0

    tables = [table for table in page.find_tables() if _is_real_table(table.extract())]
    tables.sort(key=lambda table: table.bbox[1])

    # Walk down the page: the text above each table, then the table, then what is left.
    # Extracting the text of the whole page instead would repeat every table as loose words.
    parts: list[str] = []
    cursor = top

    def band(upper: float, lower: float) -> None:
        if lower - upper > 2:
            for box in _reading_order((x0, upper, x1, lower), page):
                lines = page.crop(box).extract_text_lines(**WORDS)
                text = _lines_to_markdown(lines, body_size)
                if text:
                    parts.append(text)

    for table in tables:
        table_top = max(table.bbox[1], top)
        table_bottom = min(table.bbox[3], bottom)
        band(cursor, table_top)
        parts.append(table_to_markdown(table.extract()))
        cursor = max(cursor, table_bottom)
    band(cursor, bottom)

    unit = Unit(number=number, label=f"Page {number}", text="", tables=len(tables))
    typed_characters = sum(len(part) for part in parts)

    if typed_characters < SCANNED_PAGE_CHARS and ocr.name != "none":
        # No text layer worth the name: this page is a picture of a page.
        text = ocr.read(page.to_image(resolution=OCR_RESOLUTION).original)
        if text.strip():
            unit.text, unit.ocr = text.strip(), True
            return unit

    images = [
        image
        for image in page.images
        if image["x1"] - image["x0"] >= MIN_IMAGE_SIDE
        and image["bottom"] - image["top"] >= MIN_IMAGE_SIDE
    ]
    unit.images = len(images)
    for image in images[:MAX_IMAGES_PER_PAGE]:
        box = (
            max(image["x0"], x0),
            max(image["top"], top),
            min(image["x1"], x1),
            min(image["bottom"], bottom),
        )
        if box[2] - box[0] < MIN_IMAGE_SIDE or box[3] - box[1] < MIN_IMAGE_SIDE:
            continue
        block = image_text_block(
            ocr.read(page.crop(box).to_image(resolution=OCR_RESOLUTION).original)
        )
        if block:
            unit.images_with_text += 1
            parts.append(block)
    unit.text = "\n\n".join(part for part in parts if part).strip()
    return unit


def parse_pdf(path: Path, ocr: Ocr, max_units: int) -> ParsedFile:
    parsed = ParsedFile(kind="pdf", unit_name="page")
    try:
        pdf = pdfplumber.open(path)
    except Exception as error:  # pdfminer raises many types for encrypted/corrupt files
        raise ParseError(f"Could not open the PDF ({type(error).__name__}: {error})") from error
    with pdf:
        total = len(pdf.pages)
        if total > max_units:
            parsed.warnings.append(f"Only the first {max_units} of {total} pages were read.")
        for number, page in enumerate(pdf.pages[:max_units], start=1):
            try:
                parsed.units.append(_parse_page(page, number, ocr))
            except Exception as error:  # one broken page should not lose the document
                parsed.warnings.append(f"Page {number} could not be read ({error}).")
                parsed.units.append(Unit(number=number, label=f"Page {number}", text=""))
            page.flush_cache()  # pdfplumber keeps every parsed page in memory otherwise
    return parsed
