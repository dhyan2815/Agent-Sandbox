"""What every parser returns, whatever the file format."""

import re
from dataclasses import asdict, dataclass, field


@dataclass
class Unit:
    """One citable part of a file: a PDF page, a slide, a sheet, or a document section.

    The text is markdown: '#' headings, pipe tables, blank lines between paragraphs.
    That is the one shape the chunker understands, so tables and headings survive
    from every format.
    """

    number: int  # 1-based position in the file
    label: str  # "Page 3", "Slide 2", "Sheet Sales"; "" when the file is a single unit
    text: str
    tables: int = 0
    images: int = 0  # images found in this unit
    images_with_text: int = 0  # of those, how many OCR read text from
    ocr: bool = False  # the whole unit was read by OCR (scanned page, image file)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ParsedFile:
    kind: str  # pdf | docx | pptx | xlsx | image | text | markdown | html | csv
    unit_name: str  # what a unit is called for this format: page | slide | sheet | section
    units: list[Unit] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def report(self) -> dict:
        """The numbers shown to the user after an upload: what was actually extracted."""
        return {
            "kind": self.kind,
            "unit_name": self.unit_name,
            "units": len(self.units),
            "characters": sum(len(unit.text) for unit in self.units),
            "tables": sum(unit.tables for unit in self.units),
            "images": sum(unit.images for unit in self.units),
            "images_with_text": sum(unit.images_with_text for unit in self.units),
            "ocr_units": sum(unit.ocr for unit in self.units),
            "empty_units": sum(not unit.text.strip() for unit in self.units),
            "warnings": self.warnings,
        }


class ParseError(Exception):
    """The file could not be read at all (unsupported, encrypted, corrupt)."""


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)  # spreadsheets store 18450 as 18450.0
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text.replace("|", "\\|")


def table_to_markdown(rows: list[list]) -> str:
    """Render rows as a markdown pipe table. The first non-empty row is the header.

    Empty rows and columns are dropped, so a sheet with a few stray cells far to the
    right does not become a hundred blank columns.
    """
    cleaned = [[_cell(value) for value in row] for row in rows]
    cleaned = [row for row in cleaned if any(row)]
    if not cleaned:
        return ""
    width = max(len(row) for row in cleaned)
    cleaned = [row + [""] * (width - len(row)) for row in cleaned]
    keep = [i for i in range(width) if any(row[i] for row in cleaned)]
    cleaned = [[row[i] for i in keep] for row in cleaned]
    lines = ["| " + " | ".join(cleaned[0]) + " |", "|" + "|".join("---" for _ in keep) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in cleaned[1:]]
    return "\n".join(lines)


def image_text_block(text: str) -> str:
    """How text read from an embedded image appears in a unit: one labelled paragraph."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "Text in image (OCR):\n" + "\n".join(lines) if lines else ""
