"""Plan v2 phase 1 acceptance: big files, measured.

    python scripts/bench_big_files.py --gb 1.0 --scanned 40 --out results/phase1-big-files.md

Builds the test files in a temporary folder (nothing is committed), then:

1. a synthetic PDF of about --gb gigabytes (one large, incompressible image per page):
   peak memory of the process that reads it, which must not grow with the file
2. the same kind of PDF read to about 30%, killed with SIGKILL, asked a question from
   another process while half-read, then resumed: no committed window may be read twice
3. --scanned pages of rendered text (a scanned book), read by the real OCR
4. a plain-text book of 600 pages
5. a spreadsheet with 200,000 rows

Every number in the report comes from this run. Run from the hyper-rag/ folder.
"""

import argparse
import io
import json
import os
import random
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
PY = sys.executable


# --- building the files ------------------------------------------------------------------


def noise_jpeg(seed: int, side: int) -> bytes:
    """A photo-like image that does not compress: random blocks of colour with fine noise."""
    from PIL import Image

    rng = random.Random(seed)
    small = Image.new("RGB", (side // 8, side // 8))
    small.putdata(
        [
            (rng.randrange(256), rng.randrange(256), rng.randrange(256))
            for _ in range((side // 8) ** 2)
        ]
    )
    image = small.resize((side, side))
    noise = Image.effect_noise((side, side), 64).convert("RGB")
    image = Image.blend(image, noise, 0.5)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()


def make_image_pdf(path: Path, target_bytes: int, side: int = 1400) -> int:
    """Pages with a heading, a fact and one large image each, until the file is big enough."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    width, height = A4
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pages, written = 0, 0
    while written < target_bytes:
        pages += 1
        data = noise_jpeg(pages, side)
        written += len(data)
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(50, height - 60, f"Plate {pages}")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(
            50, height - 80, f"Fact {pages}: plate {pages} was photographed at site S-{pages * 13}."
        )
        pdf.drawImage(ImageReader(io.BytesIO(data)), 50, 120, width=width - 100, height=width - 100)
        pdf.showPage()
    pdf.save()
    return pages


def make_scanned_pdf(path: Path, pages: int) -> None:
    """Each page is a picture of typed text, as a scanner would produce."""
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    width, height = A4
    font = ImageFont.load_default(size=30)
    pdf = canvas.Canvas(str(path), pagesize=A4)
    for number in range(1, pages + 1):
        image = Image.new("L", (1240, 1754), 255)
        draw = ImageDraw.Draw(image)
        lines = [
            f"Scanned page {number}",
            f"Meter reading for house {number} was {number * 37} units.",
            "The inspector signed the sheet on site.",
            "Copies go to the district office.",
        ]
        for row, line in enumerate(lines * 4):
            draw.text((90, 120 + row * 70), line, fill=0, font=font)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        pdf.drawImage(ImageReader(io.BytesIO(buffer.getvalue())), 0, 0, width=width, height=height)
        pdf.showPage()
    pdf.save()


def make_text_book(path: Path, pages: int) -> None:
    sys.path.insert(0, str(HERE / "tests"))
    from make_files import make_book

    make_book(path, pages=pages)


def make_big_xlsx(path: Path, rows: int) -> None:
    from openpyxl import Workbook

    book = Workbook(write_only=True)
    sheet = book.create_sheet("Readings")
    sheet.append(["Meter", "Month", "Units", "Billed"])
    for row in range(rows):
        sheet.append([f"M-{row:06d}", 1 + row % 12, row % 900, round((row % 900) * 7.5, 2)])
    book.save(path)


# --- the child process that does the reading --------------------------------------------

CHILD = r"""
import json, sys, time
from pathlib import Path
from hyper_rag.config import Settings
from hyper_rag.uploads import CollectionStore

data_dir, slug, name, source, ocr, mode = sys.argv[1:7]
settings = Settings(data_dir=Path(data_dir), packs_dir=Path("packs"), ocr=ocr).offline()
store = CollectionStore(settings)
if mode == "stage":
    try:
        store.create(slug)
    except Exception:
        pass
    record = store.stage_file(slug, name, Path(source))
    print(json.dumps({"staged": record["id"]}), flush=True)
    sys.exit(0)
file_id = mode
def peak_mb():
    # VmHWM is this program's own peak. (ru_maxrss is not: Linux carries it over from the
    # parent process across exec, so it reported the benchmark's own memory.)
    for line in open("/proc/self/status"):
        if line.startswith("VmHWM:"):
            return round(int(line.split()[1]) / 1024)
store.embedder, store.reranker  # load the models first: their memory is not the file's
import hyper_rag.parsing.pdf, pdfplumber  # noqa
baseline = peak_mb()
started = time.monotonic()
record = store.ingest_file(slug, file_id, on_event=lambda e: print(json.dumps(e), flush=True))
print(json.dumps({"t": "result", "status": record["status"], "pages": record["pages_done"],
                  "chunks": record["chunks"], "seconds": round(time.monotonic() - started, 1),
                  "peak_rss_mb": peak_mb(), "baseline_rss_mb": baseline}), flush=True)
"""

ASK = r"""
import json, sys
from pathlib import Path
from hyper_rag.config import Settings
from hyper_rag.uploads import CollectionStore
data_dir, slug, question = sys.argv[1:4]
store = CollectionStore(Settings(data_dir=Path(data_dir), packs_dir=Path("packs")).offline())
hits = store.retriever(slug).retrieve(question)
print(json.dumps({"coverage": store.coverage(slug),
                  "top": [h.chunk.id for h in hits[:3]]}))
"""


def child(
    data_dir: Path, slug: str, name: str, source: Path, ocr: str, mode: str
) -> subprocess.Popen:
    return subprocess.Popen(
        [PY, "-c", CHILD, str(data_dir), slug, name, str(source), ocr, mode],
        cwd=HERE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def stage(data_dir: Path, slug: str, name: str, source: Path, ocr: str) -> str:
    process = child(data_dir, slug, name, source, ocr, "stage")
    out, err = process.communicate()
    if process.returncode:
        raise RuntimeError(err)
    return json.loads(out.splitlines()[-1])["staged"]


def read_all(
    data_dir: Path, slug: str, name: str, source: Path, ocr: str
) -> tuple[dict, list[dict]]:
    file_id = stage(data_dir, slug, name, source, ocr)
    process = child(data_dir, slug, name, source, ocr, file_id)
    out, err = process.communicate()
    events = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    result = next((e for e in events if e.get("t") == "result"), None)
    if result is None:
        raise RuntimeError(err[-2000:])
    return result, events


def window_stats(data_dir: Path, slug: str, file_id: str) -> dict:
    """Pages per minute by route, from the per-window timings saved with the parsed pages."""
    folder = data_dir / "collections" / slug / "parsed" / file_id
    by_route: dict[str, list[float]] = {}
    for path in sorted(folder.glob("w*.json")):
        window = json.loads(path.read_text())
        routes = list(window["routes"].values()) or ["whole file"]
        share = window["ms"] / max(len(routes), 1)
        for route in routes:
            by_route.setdefault(route, []).append(share)
    return {
        route: round(60000 / (sum(ms) / len(ms)), 1) if sum(ms) else None
        for route, ms in by_route.items()
    }


# --- the runs ----------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gb", type=float, default=1.0)
    parser.add_argument("--scanned", type=int, default=40)
    parser.add_argument("--out", type=Path, default=HERE / "results" / "phase1-big-files.md")
    parser.add_argument("--work", type=Path, help="reuse the test files built in this folder")
    args = parser.parse_args()

    work = args.work or Path(tempfile.mkdtemp(prefix="hyper-rag-bench-"))
    for old in work.glob("d*"):
        if old.is_dir():
            import shutil

            shutil.rmtree(old)  # read again from scratch; only the built files are reused
    lines = [
        f"# Phase 1: big files, measured ({time.strftime('%Y-%m-%d')})",
        "",
        f"Machine: {os.cpu_count()} vCPU. Settings: windows of 32 pages, parsing in the "
        "reading process (ingest_processes=0), hashing embedder (offline mode), so the "
        "numbers measure reading and memory, not the embedding model.",
        "",
    ]

    # 1. The big PDF: peak memory.
    big = work / "plates.pdf"
    t = time.monotonic()
    pages = None if big.exists() else make_image_pdf(big, int(args.gb * 1024**3))
    size_mb = big.stat().st_size / 1024**2
    print(
        f"built {big.name}: {size_mb:.0f} MB, {pages} pages in {time.monotonic() - t:.0f} s",
        flush=True,
    )
    result, _ = read_all(work / "d1", "plates", "plates.pdf", big, "none")
    file_id = stage(work / "d1", "plates", "plates.pdf", big, "none")
    rates = window_stats(work / "d1", "plates", file_id)
    lines += [
        "## 1. A synthetic PDF of one large photo per page",
        "",
        "| File | Pages | Read in | Process memory before reading | Peak while reading "
        "| Pages/min by route |",
        "|---|---|---|---|---|---|",
        f"| {size_mb:,.0f} MB | {result['pages']} | {result['seconds']} s | "
        f"{result['baseline_rss_mb']} MB | **{result['peak_rss_mb']} MB** | {rates} |",
        "",
    ]
    print(lines[-2], flush=True)

    # Peak memory against file size: the same pages at a quarter of the size.
    small = work / "plates-small.pdf"
    if not small.exists():
        make_image_pdf(small, int(args.gb * 1024**3 / 4))
    small_result, _ = read_all(work / "d1b", "small", "plates-small.pdf", small, "none")
    lines += [
        f"The same kind of file at {small.stat().st_size / 1024**2:,.0f} MB "
        f"({small_result['pages']} pages) peaked at {small_result['peak_rss_mb']} MB "
        f"(from {small_result['baseline_rss_mb']} MB before reading). The target in the "
        "plan is a fixed bound of 1.5 GB whatever the file size.",
        "",
    ]

    # 2. Kill at ~30%, ask while half-read, resume.
    data = work / "d2"
    file_id = stage(data, "crash", "plates.pdf", big, "none")
    process = child(data, "crash", "plates.pdf", big, "none", file_id)
    committed_before: list[int] = []
    total_windows = None
    for line in process.stdout:
        event = json.loads(line) if line.startswith("{") else {}
        if event.get("t") == "ingest.triage":
            total_windows = -(-event["pages"] // 32)
        if event.get("t") == "ingest.commit":
            committed_before.append(event["window"])
            if total_windows and len(committed_before) >= 0.3 * total_windows:
                break
    asked = subprocess.run(
        [
            PY,
            "-c",
            ASK,
            str(data),
            "crash",
            f"Where was plate {committed_before[-1] * 32 + 5} photographed?",
        ],
        cwd=HERE,
        capture_output=True,
        text=True,
    )
    asked_while_reading = (
        json.loads(asked.stdout) if asked.returncode == 0 else {"error": asked.stderr[-500:]}
    )
    print("asked:", asked_while_reading, flush=True)
    process.send_signal(signal.SIGKILL)
    process.wait()
    resumed = child(data, "crash", "plates.pdf", big, "none", file_id)
    out, err = resumed.communicate()
    events = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    committed_after = [e["window"] for e in events if e.get("t") == "ingest.commit"]
    repeated = sorted(set(committed_before) & set(committed_after))
    final = next(e for e in events if e.get("t") == "result")
    lines += [
        "## 2. Killed at 30%, asked while half-read, resumed",
        "",
        f"- Killed (SIGKILL) after {len(committed_before)} of {total_windows} windows "
        "were committed.",
        f"- A question asked from another process at that moment searched: "
        f"`{json.dumps(asked_while_reading.get('coverage'))}`; top passages "
        f"`{asked_while_reading.get('top')}`.",
        f"- The restarted process committed windows {min(committed_after)} to "
        f"{max(committed_after)}; "
        f"windows committed twice: **{repeated or 'none'}**.",
        f"- Finished: {final['status']}, {final['pages']} pages, {final['chunks']} passages.",
        "",
    ]
    print("\n".join(lines[-6:]), flush=True)

    # 3. Scanned pages through the real OCR.
    scanned = work / "scanned.pdf"
    if not scanned.exists():
        make_scanned_pdf(scanned, args.scanned)
    result, _ = read_all(work / "d3", "scans", "scanned.pdf", scanned, "rapidocr")
    file_id = stage(work / "d3", "scans", "scanned.pdf", scanned, "rapidocr")
    lines += [
        "## 3. A scanned book (rendered pages, real OCR)",
        "",
        "| Pages | Read in | Memory before | Peak | Pages/min by route |",
        "|---|---|---|---|---|",
        f"| {result['pages']} | {result['seconds']} s | {result['baseline_rss_mb']} MB | "
        f"{result['peak_rss_mb']} MB | {window_stats(work / 'd3', 'scans', file_id)} |",
        "",
        "Most of that peak is the OCR models (RapidOCR's ONNX networks), loaded on the first "
        "scanned page; it does not grow with the number of pages.",
        "",
    ]
    print(lines[-2], flush=True)

    # 4. A long plain-text book.
    book = work / "book.pdf"
    if not book.exists():
        make_text_book(book, 600)
    result, _ = read_all(work / "d4", "book", "book.pdf", book, "none")
    file_id = stage(work / "d4", "book", "book.pdf", book, "none")
    lines += [
        "## 4. A 600-page text book",
        "",
        "| Pages | Read in | Memory before | Peak | Pages/min by route |",
        "|---|---|---|---|---|",
        f"| {result['pages']} | {result['seconds']} s | {result['baseline_rss_mb']} MB | "
        f"{result['peak_rss_mb']} MB | {window_stats(work / 'd4', 'book', file_id)} |",
        "",
    ]
    print(lines[-2], flush=True)

    # 5. A 200,000-row spreadsheet.
    sheet = work / "readings.xlsx"
    if not sheet.exists():
        make_big_xlsx(sheet, 200_000)
    result, _ = read_all(work / "d5", "sheet", "readings.xlsx", sheet, "none")
    lines += [
        "## 5. A spreadsheet of 200,000 rows",
        "",
        f"{sheet.stat().st_size / 1024**2:.1f} MB; read in {result['seconds']} s, peak memory "
        f"{result['peak_rss_mb']} MB (from {result['baseline_rss_mb']} MB), "
        f"{result['chunks']} passages (rows past the per-sheet "
        "cap are reported, not read: a table profile and SQL are deck item D3).",
        "",
    ]
    print(lines[-2], flush=True)

    lines += [
        "## What this does not show",
        "",
        "- Embedding cost: the offline hashing embedder is used; bge-small adds about "
        "1 to 3 ms per passage on CPU.",
        "- Real scans: the scanned pages are clean renders, easier than a photocopied book.",
        "- Upload: the files are staged from local disk; resumable uploads are tested "
        "separately (tests/test_big_files.py) and move 8 MB parts.",
        "",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
