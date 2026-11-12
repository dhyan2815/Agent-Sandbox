"""Optical character recognition, local and on CPU.

RapidOCR runs PaddleOCR's small detection and recognition models through ONNX Runtime,
the same runtime the embedding model already uses. The models ship inside the wheel,
so there is no system binary to install (Tesseract needs one, which is the usual way
OCR setups break on Windows) and nothing is downloaded at run time.
"""

from typing import Protocol

from PIL import Image

# Lines the recogniser is less sure of than this are dropped: on photos and charts the
# detector finds "text" in textures, and those guesses pollute the index.
MIN_CONFIDENCE = 0.5
# Larger images are scaled down before OCR; beyond this, time grows and accuracy does not.
MAX_SIDE = 2600


class Ocr(Protocol):
    name: str

    def read(self, image: Image.Image) -> str:
        """Return the text found in the image, one line per detected text line."""
        ...


class NoOcr:
    name = "none"

    def read(self, image: Image.Image) -> str:
        return ""


class RapidOcr:
    name = "rapidocr"

    def __init__(self) -> None:
        self._engine = None

    def read(self, image: Image.Image) -> str:
        import numpy as np

        if self._engine is None:  # loading the three models takes a few seconds: do it once
            from rapidocr import RapidOCR

            # The library logs every model path at INFO on each start.
            self._engine = RapidOCR(params={"Global.log_level": "error"})
        image = image.convert("RGB")
        if max(image.size) > MAX_SIDE:
            image.thumbnail((MAX_SIDE, MAX_SIDE))
        if min(image.size) < 16:
            return ""
        result = self._engine(np.array(image))
        if result is None or not result.txts:
            return ""
        scores = result.scores or [1.0] * len(result.txts)
        lines = [
            text.strip()
            for text, score in zip(result.txts, scores, strict=False)
            if score >= MIN_CONFIDENCE and text.strip()
        ]
        return "\n".join(lines)


def build_ocr(engine: str) -> Ocr:
    if engine == "none":
        return NoOcr()
    if engine == "rapidocr":
        return RapidOcr()
    raise ValueError(f"Unknown OCR engine '{engine}'")
