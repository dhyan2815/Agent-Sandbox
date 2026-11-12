"""Standalone images (screenshots, photos of documents, scans): everything comes from OCR."""

from pathlib import Path

from PIL import Image

from hyper_rag.parsing.model import ParsedFile, ParseError, Unit
from hyper_rag.parsing.ocr import Ocr


def parse_image(path: Path, ocr: Ocr) -> ParsedFile:
    parsed = ParsedFile(kind="image", unit_name="image")
    try:
        with Image.open(path) as image:
            image.load()
            text = ocr.read(image)
    except Exception as error:
        raise ParseError(f"Could not open the image ({error})") from error
    unit = Unit(number=1, label="", text=text.strip(), images=1, ocr=True)
    unit.images_with_text = 1 if unit.text else 0
    parsed.units.append(unit)
    if ocr.name == "none":
        parsed.warnings.append("OCR is switched off, so nothing was read from this image.")
    elif not unit.text:
        parsed.warnings.append("No text was found in this image.")
    return parsed
