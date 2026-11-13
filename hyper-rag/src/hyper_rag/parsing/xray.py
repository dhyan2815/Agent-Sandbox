"""The X-ray pass: look at every page of a PDF in milliseconds before doing any real work.

For each page it records how much text the text layer holds, how much of the page large
images cover, whether there are ruled lines (a table hint) or two columns, a content hash,
and the first and last line. From that each page gets a route (plan v2, A2):

    fast-text  text layer, no ruled lines, one column   pypdfium2 text objects, about 1 ms
    layout     ruled lines or two columns                the careful pdfplumber parser
    images     text layer plus large images              the careful parser, which OCRs them
    ocr        (almost) no text layer                    render the page and OCR it
    skip       blank, or an exact copy of an earlier page nothing

The pass also finds running headers and footers (lines that repeat at the top or bottom
of most pages, "Page 12 of 900" included) so they can be stripped, and reads the outline.
Nothing is rendered and no image is decoded, which is what keeps it fast on a 1 GB scan.
"""

import hashlib
import math
import re
import threading
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from hyper_rag.parsing.model import ParseError

# pdfium is not thread-safe: every call into it, from any thread, holds this lock.
# Parsing in worker processes (settings.ingest_processes) does not contend for it.
PDFIUM_LOCK = threading.RLock()

SCANNED_PAGE_CHARS = 25  # fewer characters than this: the page is a picture of a page
MIN_IMAGE_SIDE = 40  # points; smaller images are icons, rules and bullets
IMAGE_SHARE = 0.01  # images covering 1% of the page (about 70 x 70 pt on A4) get OCR
RULED_PATHS = 4  # this many vector paths suggest table rules
BOILERPLATE_SHARE = 0.5  # a line on at least half the pages is a running header/footer
BOILERPLATE_MIN_PAGES = 3
PAGE_NUMBER_WORDS = 4  # "Page 12 of 900" has two words; a sentence with a number has more

# Seconds per page by route, for the estimate shown before work starts. Measured on the
# 2-vCPU container this was built in (docs/DECISIONS.md 30); a guide, not a promise.
SECONDS_PER_PAGE = {"fast-text": 0.004, "layout": 0.25, "images": 0.6, "ocr": 2.0, "skip": 0.0}
ROUTES = tuple(SECONDS_PER_PAGE)


@dataclass
class PageInfo:
    number: int
    route: str
    chars: int = 0
    image_share: float = 0.0
    paths: int = 0
    columns: bool = False
    hash: str = ""
    reason: str = ""  # why a page was skipped
    margin_lines: list[str] = field(default_factory=list)  # text in the top/bottom 10%

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class XRay:
    pages: list[PageInfo]
    outline: list[dict] = field(default_factory=list)  # {"level", "title", "page"}
    boilerplate: list[str] = field(default_factory=list)  # normalised header/footer lines

    def counts(self) -> dict[str, int]:
        counted = Counter(page.route for page in self.pages)
        return {route: counted.get(route, 0) for route in ROUTES}

    def estimate_seconds(self) -> float:
        return round(sum(SECONDS_PER_PAGE[page.route] for page in self.pages), 1)

    def summary(self) -> dict:
        return {
            "pages": len(self.pages),
            "routes": self.counts(),
            "estimate_seconds": self.estimate_seconds(),
            "boilerplate_lines": len(self.boilerplate),
            "outline_entries": len(self.outline),
        }


def normalise_line(line: str) -> str:
    """A header or footer with its numbers blanked, so "Page 3 of 90" matches "Page 4 of 90"."""
    return re.sub(r"\d+", "#", " ".join(line.split()).lower())


MARGIN = 0.1  # running headers and footers live in the top and bottom tenth of a page


def _two_columns(textpage, width: float, height: float, chars: int) -> bool:
    """Text on both halves of the page and almost none in a strip down the middle."""
    if chars < 400:
        return False
    left = len(textpage.get_text_bounded(0, 0, width * 0.47, height).strip())
    right = len(textpage.get_text_bounded(width * 0.53, 0, width, height).strip())
    middle = len(textpage.get_text_bounded(width * 0.49, 0, width * 0.51, height).strip())
    return min(left, right) > 0.25 * chars and middle < 0.02 * chars


def _page_info(page, number: int) -> tuple[PageInfo, str, str]:
    """Measure one page. Returns its info (route and hash still to decide), its text layer
    and a digest of its images' raw bytes."""
    import pypdfium2.raw as pdfium_c

    width, height = page.get_size()
    textpage = page.get_textpage()
    text = textpage.get_text_range()
    chars = len(text.strip())
    digest = hashlib.sha1()
    image_area = 0.0
    paths = 0
    margin_lines = []
    for obj in page.get_objects(max_depth=4):
        if obj.type == pdfium_c.FPDF_PAGEOBJ_TEXT:
            # Found by position, not by order: the text layer is in drawing order, and a
            # footer is often drawn before the body.
            _, bottom, _, top = obj.get_bounds()
            if top >= height * (1 - MARGIN) or bottom <= height * MARGIN:
                line = " ".join(_object_text(obj, textpage).split())
                if line and len(line) <= 80:
                    margin_lines.append(line)
        elif obj.type == pdfium_c.FPDF_PAGEOBJ_PATH:
            paths += 1
        elif obj.type == pdfium_c.FPDF_PAGEOBJ_IMAGE:
            left, bottom, right, top = obj.get_bounds()
            if right - left >= MIN_IMAGE_SIDE and top - bottom >= MIN_IMAGE_SIDE:
                image_area += (right - left) * (top - bottom)
            # The raw (still compressed) bytes identify the image without decoding it.
            try:
                digest.update(bytes(obj.get_data(decode_simple=False)))
            except Exception:  # an image pdfium cannot hand over still counts by size
                digest.update(f"{left:.0f},{bottom:.0f},{right:.0f},{top:.0f}".encode())
    info = PageInfo(
        number=number,
        route="fast-text",
        chars=chars,
        image_share=round(min(image_area / max(width * height, 1.0), 1.0), 3),
        paths=paths,
        columns=_two_columns(textpage, width, height, chars),
    )
    info.margin_lines = sorted(set(margin_lines))
    textpage.close()
    return info, text, digest.hexdigest()


def content_hash(text: str, images: str, boilerplate: set[str]) -> str:
    """What a page says and shows, without its running header and footer: two pages with
    the same hash are copies even if their page numbers differ."""
    lines = [
        " ".join(line.split())
        for line in text.splitlines()
        if line.strip() and normalise_line(line) not in boilerplate
    ]
    return hashlib.sha1(("\n".join(lines) + "\x00" + images).encode("utf-8")).hexdigest()[:16]


def _route(info: PageInfo, seen: set[str]) -> None:
    if info.chars < SCANNED_PAGE_CHARS:
        if info.image_share == 0 and info.paths == 0:
            info.route, info.reason = "skip", "blank"
        else:
            info.route = "ocr"
    elif info.hash in seen:
        info.route, info.reason = "skip", "copy of an earlier page"
    elif info.image_share >= IMAGE_SHARE:
        info.route = "images"
    elif info.paths >= RULED_PATHS or info.columns:
        info.route = "layout"
    seen.add(info.hash)


def _boilerplate(pages: list[PageInfo]) -> list[str]:
    """Running headers and footers, as normalised lines.

    Two kinds count: a margin line that repeats word for word on most pages (a running
    title), and a short margin line whose number follows the page number on most pages
    ("Page 12 of 900", "- 12 -"). A margin line that merely has the same shape on every
    page, such as "Plate 7" above a figure or "Fact 7: ...", is content and stays.
    """
    with_text = [page for page in pages if page.chars >= SCANNED_PAGE_CHARS]
    if len(with_text) < BOILERPLATE_MIN_PAGES:
        return []
    needed = max(BOILERPLATE_MIN_PAGES, math.ceil(BOILERPLATE_SHARE * len(with_text)))
    exact: Counter[str] = Counter()
    offsets: dict[str, list[int]] = {}
    for page in with_text:
        for line in set(page.margin_lines):
            exact[line] += 1
            numbers = re.findall(r"\d+", line)
            if numbers and len(re.findall(r"[^\W\d_]+", line)) <= PAGE_NUMBER_WORDS:
                offsets.setdefault(normalise_line(line), []).append(page.number - int(numbers[0]))
    found = {normalise_line(line) for line, count in exact.items() if count >= needed}
    for pattern, seen in offsets.items():
        if len(seen) >= needed and Counter(seen).most_common(1)[0][1] >= 0.8 * len(seen):
            found.add(pattern)  # the number moves with the page: page numbering
    return sorted(found)


def xray_pdf(path: Path, batch: int = 32) -> XRay:
    """X-ray every page. The document is reopened every `batch` pages: pdfium keeps what it
    has loaded (image streams included) until the document is closed, and holding a whole
    1 GB scan in memory is exactly what this pass exists to avoid."""
    import pypdfium2

    def open_pdf():
        try:
            return pypdfium2.PdfDocument(str(path))
        except Exception as error:  # encrypted, corrupt, not a PDF
            raise ParseError(f"Could not open the PDF ({error})") from error

    measured = []
    with PDFIUM_LOCK:
        pdf = open_pdf()
        try:
            total = len(pdf)
            outline = []
            try:
                for item in pdf.get_toc():
                    if item.page_index is not None:
                        outline.append(
                            {"level": item.level, "title": item.title, "page": item.page_index + 1}
                        )
            except Exception:  # a broken outline is not worth failing the file for
                outline = []
        finally:
            pdf.close()
    for start in range(0, total, batch):
        with PDFIUM_LOCK:  # released between batches, so previews are not kept waiting
            pdf = open_pdf()
            try:
                for index in range(start, min(start + batch, total)):
                    page = pdf[index]
                    try:
                        measured.append(_page_info(page, index + 1))
                    except Exception:  # one unreadable page: let the careful parser try it
                        measured.append((PageInfo(number=index + 1, route="layout"), "", "?"))
                    finally:
                        page.close()
            finally:
                pdf.close()
    pages = [info for info, _, _ in measured]
    boilerplate = _boilerplate(pages)
    seen: set[str] = set()
    for info, text, images in measured:
        info.hash = content_hash(text, images, set(boilerplate))
        if images == "?":
            continue  # unreadable in the X-ray: already routed to the careful parser
        _route(info, seen)
    return XRay(pages=pages, outline=outline, boilerplate=boilerplate)


def _object_text(obj, textpage) -> str:
    """The exact text of one text object (a run of glyphs drawn together)."""
    import ctypes

    import pypdfium2.raw as pdfium_c

    size = pdfium_c.FPDFTextObj_GetText(obj.raw, textpage.raw, None, 0)
    if size <= 2:
        return ""
    buffer = (ctypes.c_ushort * (size // 2))()
    pdfium_c.FPDFTextObj_GetText(obj.raw, textpage.raw, buffer, size)
    return bytes(buffer).decode("utf-16-le", "replace").rstrip("\x00")


def fast_text(page, boilerplate: set[str]) -> str:
    """Markdown from a page's text objects: lines in reading order, larger type as headings.

    Only used for pages the X-ray found simple (one column, no ruled lines), where the
    order of lines top to bottom is the reading order.
    """
    import pypdfium2.raw as pdfium_c

    textpage = page.get_textpage()
    _, page_height = page.get_size()
    pieces = []  # (top, bottom, left, right, size, text)
    for obj in page.get_objects(filter=(pdfium_c.FPDF_PAGEOBJ_TEXT,), max_depth=4):
        text = _object_text(obj, textpage)
        if not text.strip():
            continue
        left, bottom, right, top = obj.get_bounds()
        matrix = obj.get_matrix()
        scale = math.hypot(matrix.c, matrix.d) or 1.0
        pieces.append((top, bottom, left, right, obj.get_font_size() * scale, text))
    textpage.close()
    if not pieces:
        return ""

    # Group pieces into lines: same baseline within a third of the type size.
    pieces.sort(key=lambda p: (-p[1], p[2]))
    lines: list[list[tuple]] = []
    for piece in pieces:
        if lines and abs(lines[-1][0][1] - piece[1]) <= max(piece[4], 1.0) / 3:
            lines[-1].append(piece)
        else:
            lines.append([piece])

    weights = Counter()
    for piece in pieces:
        weights[round(piece[4], 1)] += len(piece[5])
    body = weights.most_common(1)[0][0]

    blocks: list[str] = []
    previous_bottom = None
    open_paragraph = False
    for line in lines:
        line.sort(key=lambda p: p[2])
        text = ""
        for i, piece in enumerate(line):
            gap = piece[2] - line[i - 1][3] if i else 0
            joiner = " " if i and gap > 0.15 * piece[4] and not text.endswith(" ") else ""
            text += joiner + piece[5].replace("\r", " ").replace("\n", " ")
        text = " ".join(text.split())
        top = max(p[0] for p in line)
        bottom = min(p[1] for p in line)
        size = max(p[4] for p in line)
        in_margin = top >= page_height * (1 - MARGIN) or bottom <= page_height * MARGIN
        if not text or (in_margin and normalise_line(text) in boilerplate):
            continue
        height = max(top - bottom, 1.0)
        gap = previous_bottom is not None and previous_bottom - top > 0.7 * height
        previous_bottom = bottom
        if size >= 1.2 * body and len(text) <= 120:
            blocks.append(f"## {text}")
            open_paragraph = False
        elif open_paragraph and not gap:
            if blocks[-1].endswith("-") and text[0].islower():
                blocks[-1] = blocks[-1][:-1] + text  # a word hyphenated across lines
            else:
                blocks[-1] += f" {text}"
        else:
            blocks.append(text)
            open_paragraph = True
    return "\n\n".join(blocks)


def strip_boilerplate(text: str, boilerplate: set[str]) -> str:
    """Remove running headers and footers from the first and last lines of a page's text."""
    if not boilerplate:
        return text
    lines = text.split("\n")
    for index in (0, 1, -2, -1):
        if -len(lines) <= index < len(lines):
            candidate = lines[index].lstrip("#").strip()
            if candidate and normalise_line(candidate) in boilerplate:
                lines[index] = ""
    return "\n".join(lines).strip()
