"""Turn an uploaded file of any supported format into citable units of markdown text.

One function, `parse_file`, picks the parser from the file extension. Every parser
returns the same `ParsedFile`, so nothing after this point knows what format it was.
"""

from pathlib import Path

from hyper_rag.parsing.model import ParsedFile, ParseError, Unit
from hyper_rag.parsing.ocr import Ocr, build_ocr

__all__ = ["SUPPORTED", "Ocr", "ParseError", "ParsedFile", "Unit", "build_ocr", "parse_file"]

# Extension -> format family. Upload validation and the UI's file picker read this.
SUPPORTED: dict[str, str] = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".pptx": "pptx",
    ".xlsx": "xlsx",
    ".xlsm": "xlsx",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".bmp": "image",
    ".tif": "image",
    ".tiff": "image",
    ".txt": "text",
    ".log": "text",
    ".rst": "text",
    ".json": "text",
    ".md": "markdown",
    ".markdown": "markdown",
    ".html": "html",
    ".htm": "html",
    ".csv": "csv",
    ".tsv": "csv",
}

_LEGACY = {".doc": ".docx", ".ppt": ".pptx", ".xls": ".xlsx"}


def parse_file(path: Path, ocr: Ocr, max_units: int = 300) -> ParsedFile:
    """Parse one file. Raises ParseError if the format is unsupported or the file is unreadable."""
    suffix = path.suffix.lower()
    family = SUPPORTED.get(suffix)
    if family is None:
        if suffix in _LEGACY:
            raise ParseError(
                f"The old {suffix} format is not supported. Save the file as "
                f"{_LEGACY[suffix]} and upload that."
            )
        raise ParseError(
            f"Files of type '{suffix or 'unknown'}' are not supported. Supported: "
            + ", ".join(sorted(SUPPORTED))
        )
    # Imports are per format so that, say, asking a question never loads the PDF stack.
    if family == "pdf":
        from hyper_rag.parsing.pdf import parse_pdf

        return parse_pdf(path, ocr, max_units)
    if family in ("docx", "pptx", "xlsx"):
        from hyper_rag.parsing import office

        return getattr(office, f"parse_{family}")(path, ocr, max_units)
    if family == "image":
        from hyper_rag.parsing.image import parse_image

        return parse_image(path, ocr)
    from hyper_rag.parsing import textual

    if family == "html":
        return textual.parse_html(path)
    if family == "csv":
        return textual.parse_csv(path)
    return textual.parse_text(path, kind=family)
