# Phase 1: big files, measured (2026-11-13)

Machine: 4 vCPU. Settings: windows of 32 pages, parsing in the reading process (ingest_processes=0), hashing embedder (offline mode), so the numbers measure reading and memory, not the embedding model.

## 1. A synthetic PDF of one large photo per page

| File | Pages | Read in | Process memory before reading | Peak while reading | Pages/min by route |
|---|---|---|---|---|---|
| 1,282 MB | 768 | 56.5 s | 62 MB | **175 MB** | {'images': 879.8} |

The same kind of file at 320 MB (192 pages) peaked at 167 MB (from 63 MB before reading). The target in the plan is a fixed bound of 1.5 GB whatever the file size.

## 2. Killed at 30%, asked while half-read, resumed

- Killed (SIGKILL) after 8 of 24 windows were committed.
- A question asked from another process at that moment searched: `[{"file_id": "bdac743fa24a", "name": "plates.pdf", "status": "reading", "pages_done": 256, "pages_total": 768}]`; top passages `['bdac743fa24a/229#0', 'bdac743fa24a/1#0', 'bdac743fa24a/3#0']`.
- The restarted process committed windows 8 to 23; windows committed twice: **none**.
- Finished: ready, 768 pages, 768 passages.

## 3. A scanned book (rendered pages, real OCR)

| Pages | Read in | Memory before | Peak | Pages/min by route |
|---|---|---|---|---|
| 40 | 58.1 s | 63 MB | 741 MB | {'ocr': 41.4} |

Most of that peak is the OCR models (RapidOCR's ONNX networks), loaded on the first scanned page; it does not grow with the number of pages.

## 4. A 600-page text book

| Pages | Read in | Memory before | Peak | Pages/min by route |
|---|---|---|---|---|
| 600 | 0.8 s | 62 MB | 75 MB | {'fast-text': 165213.4} |

## 5. A spreadsheet of 200,000 rows

4.1 MB; read in 1.9 s, peak memory 96 MB (from 63 MB), 138 passages (rows past the per-sheet cap are reported, not read: a table profile and SQL are deck item D3).

## What this does not show

- Embedding cost: the offline hashing embedder is used; bge-small adds about 1 to 3 ms per passage on CPU.
- Real scans: the scanned pages are clean renders, easier than a photocopied book.
- Upload: the files are staged from local disk; resumable uploads are tested separately (tests/test_big_files.py) and move 8 MB parts.
