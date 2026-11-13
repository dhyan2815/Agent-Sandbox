"""Word, PowerPoint and Excel files (the modern .docx / .pptx / .xlsx formats)."""

import io
from datetime import date, datetime, time
from pathlib import Path

from PIL import Image

from hyper_rag.parsing.model import (
    ParsedFile,
    ParseError,
    Unit,
    image_text_block,
    table_to_markdown,
)
from hyper_rag.parsing.ocr import Ocr

# Rows read per sheet. A sheet beyond this is almost always a data export, where a
# question-answering index is the wrong tool; the parse report says it was cut.
MAX_SHEET_ROWS = 5000
MAX_IMAGES_PER_FILE = 40


def _ocr_blob(blob: bytes, ocr: Ocr) -> str:
    try:
        return image_text_block(ocr.read(Image.open(io.BytesIO(blob))))
    except Exception:  # vector formats (EMF/WMF) and broken images: nothing to read
        return ""


# --- Word ---------------------------------------------------------------------------


def parse_docx(path: Path, ocr: Ocr, max_units: int) -> ParsedFile:
    from docx import Document as open_docx
    from docx.table import Table

    parsed = ParsedFile(kind="docx", unit_name="section")
    try:
        document = open_docx(str(path))
    except Exception as error:
        raise ParseError(f"Could not open the Word file ({error})") from error

    # Word has no fixed pages (they depend on the printer and fonts), so the citable
    # unit is a top-level section: everything under one "Heading 1" or "Title".
    sections: list[Unit] = [Unit(number=1, label="", text="")]
    parts: list[str] = []
    images_read = 0

    def close_section() -> None:
        sections[-1].text = "\n\n".join(part for part in parts if part).strip()
        parts.clear()

    for block in document.iter_inner_content():
        current = sections[-1]
        if isinstance(block, Table):
            rows = [[cell.text for cell in row.cells] for row in block.rows]
            markdown = table_to_markdown(rows)
            if markdown:
                parts.append(markdown)
                current.tables += 1
            continue

        text = block.text.strip()
        style = (block.style.name or "") if block.style is not None else ""
        if text and (style == "Title" or style == "Heading 1"):
            if parts or current.text:
                close_section()
                sections.append(Unit(number=len(sections) + 1, label=text[:80], text=""))
            else:
                current.label = text[:80]
            parts.append(f"# {text}")
        elif text and style.startswith("Heading"):
            level = int(style.split()[-1]) if style.split()[-1].isdigit() else 2
            parts.append(f"{'#' * min(level, 6)} {text}")
        elif text and style.startswith("List"):
            # Consecutive list items stay one paragraph, so a list is not split mid-way.
            if parts and parts[-1].startswith("- "):
                parts[-1] += f"\n- {text}"
            else:
                parts.append(f"- {text}")
        elif text:
            parts.append(text)

        for relation_id in block._p.xpath(".//a:blip/@r:embed"):
            sections[-1].images += 1
            part = document.part.related_parts.get(relation_id)
            if part is None or images_read >= MAX_IMAGES_PER_FILE:
                continue
            images_read += 1
            image_text = _ocr_blob(part.blob, ocr)
            if image_text:
                sections[-1].images_with_text += 1
                parts.append(image_text)
    close_section()

    parsed.units = [unit for unit in sections if unit.text][:max_units]
    for number, unit in enumerate(parsed.units, start=1):
        unit.number = number
    return parsed


# --- PowerPoint ---------------------------------------------------------------------


def _slide_parts(shapes, unit: Unit, ocr: Ocr, title_id: int | None) -> list[str]:
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    parts: list[str] = []
    for shape in shapes:
        if shape.shape_id == title_id:
            continue  # the title is already the slide's heading
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            parts.extend(_slide_parts(shape.shapes, unit, ocr, title_id))
        elif getattr(shape, "has_table", False) and shape.has_table:
            rows = [[cell.text for cell in row.cells] for row in shape.table.rows]
            markdown = table_to_markdown(rows)
            if markdown:
                parts.append(markdown)
                unit.tables += 1
        elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            unit.images += 1
            try:
                blob = shape.image.blob
            except Exception:  # linked (not embedded) pictures have no data in the file
                continue
            image_text = _ocr_blob(blob, ocr)
            if image_text:
                unit.images_with_text += 1
                parts.append(image_text)
        elif shape.has_text_frame:
            lines = [
                ("- " if paragraph.level else "") + paragraph.text.strip()
                for paragraph in shape.text_frame.paragraphs
                if paragraph.text.strip()
            ]
            if lines:
                parts.append("\n".join(lines))
    return parts


def parse_pptx(path: Path, ocr: Ocr, max_units: int) -> ParsedFile:
    from pptx import Presentation

    parsed = ParsedFile(kind="pptx", unit_name="slide")
    try:
        presentation = Presentation(str(path))
    except Exception as error:
        raise ParseError(f"Could not open the PowerPoint file ({error})") from error

    slides = list(presentation.slides)
    if len(slides) > max_units:
        parsed.warnings.append(f"Only the first {max_units} of {len(slides)} slides were read.")
    for number, slide in enumerate(slides[:max_units], start=1):
        unit = Unit(number=number, label=f"Slide {number}", text="")
        title_shape = slide.shapes.title
        parts = []
        if title_shape is not None and title_shape.text_frame.text.strip():
            parts.append(f"## {' '.join(title_shape.text_frame.text.split())}")
        title_id = title_shape.shape_id if title_shape is not None else None
        parts.extend(_slide_parts(slide.shapes, unit, ocr, title_id))
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                parts.append(f"Speaker notes: {notes}")
        unit.text = "\n\n".join(parts).strip()
        parsed.units.append(unit)
    return parsed


# --- Excel --------------------------------------------------------------------------


def _plain(value):
    """Dates as ISO text; everything else is formatted by table_to_markdown."""
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == time(0) else value.isoformat(" ")
    if isinstance(value, date | time):
        return value.isoformat()
    return value


def parse_xlsx(path: Path, ocr: Ocr, max_units: int) -> ParsedFile:
    from openpyxl import load_workbook

    parsed = ParsedFile(kind="xlsx", unit_name="sheet")
    try:
        # data_only: read the value Excel last calculated for a formula, not the formula.
        workbook = load_workbook(str(path), read_only=True, data_only=True)
    except Exception as error:
        raise ParseError(f"Could not open the Excel file ({error})") from error
    try:
        for sheet in workbook.worksheets:
            if len(parsed.units) >= max_units:
                parsed.warnings.append(f"Only the first {max_units} sheets were read.")
                break
            rows = []
            for row in sheet.iter_rows(values_only=True):
                if len(rows) >= MAX_SHEET_ROWS:
                    parsed.warnings.append(
                        f"Sheet '{sheet.title}': only the first {MAX_SHEET_ROWS} rows were read."
                    )
                    break
                rows.append([_plain(value) for value in row])
            markdown = table_to_markdown(rows)
            if not markdown:
                continue  # an empty sheet is not a citable unit
            parsed.units.append(
                Unit(
                    number=len(parsed.units) + 1,
                    label=f"Sheet {sheet.title}",
                    text=markdown,
                    tables=1,
                )
            )
    finally:
        workbook.close()
    return parsed
