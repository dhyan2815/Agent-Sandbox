"""Turn an uploaded file of any supported format into citable units of markdown text.

One function, `parse_file`, picks the parser from the file extension. Every parser
returns the same `ParsedFile`, so nothing after this point knows what format it was.
"""

import zipfile
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

# Office files are zip archives. A small upload can expand to gigabytes ("zip bomb"), so the
# declared uncompressed size is checked before any parser opens the archive.
MAX_UNZIPPED_MB = 300


def _check_archive(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            total = sum(info.file_size for info in archive.infolist())
    except zipfile.BadZipFile as error:
        raise ParseError(f"'{path.name}' is not a valid {path.suffix.lower()} file.") from error
    if total > MAX_UNZIPPED_MB * 1024 * 1024:
        raise ParseError(
            f"'{path.name}' expands to more than {MAX_UNZIPPED_MB} MB and was not opened."
        )


_LEGACY = {".doc": ".docx", ".ppt": ".pptx", ".xls": ".xlsx"}


def parse_file(path: Path, ocr: Ocr, max_units: int | None = None) -> ParsedFile:
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

        _check_archive(path)

        # Slides and sheets have no page budget of their own; 10,000 only stops a runaway file.
        return getattr(office, f"parse_{family}")(path, ocr, max_units or 10_000)
    if family == "image":
        from hyper_rag.parsing.image import parse_image

        return parse_image(path, ocr)
    from hyper_rag.parsing import textual

    if family == "html":
        return textual.parse_html(path)
    if family == "csv":
        return textual.parse_csv(path)
    return textual.parse_text(path, kind=family)
