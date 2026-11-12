# Plan: upload any document and ask questions about it

Added 2026-11-12. The first build (see PLAN.md) answers questions over four scripted
domain packs. This adds what the project was meant to be for its user: upload your own
files, including ones with tables and images, and ask questions about them.

## What was decided with the user

| Question | Answer |
|---|---|
| File types | PDF; Word, PowerPoint, Excel; standalone images; text, Markdown, HTML, CSV |
| Images and charts | Local OCR only (no vision model, nothing leaves the machine) |
| Organisation | Named collections; files can be added and removed later |
| Extras | Click-through citations, parse report, chat with follow-ups, auto-evaluation |

## Shape

```
upload -> parse (per format) -> units (page / slide / sheet / section)
       -> chunk (table-aware) -> embed -> per-file index inside the collection
question (+ chat history) -> condense to a standalone question -> existing agent
       -> answer with citations -> each citation opens its page with the passage marked
```

```
src/hyper_rag/
  parsing/            one module per format family, all return the same ParsedFile
    model.py          Unit (page/slide/sheet text as markdown), ParsedFile, ParseReport
    ocr.py            OCR interface; RapidOCR (ONNX, models shipped in the wheel)
    pdf.py            pdfplumber: text, tables, embedded images; OCR for scanned pages
    office.py         python-docx, python-pptx, openpyxl
    textual.py        txt, md, html, csv
    image.py          png, jpg, webp, bmp, tiff through OCR
  collections.py      create / add file / remove file / load retriever / source view
  evaluation/synthetic.py   write a golden set from a collection's own passages
data/collections/<slug>/    git-ignored: originals, parsed units, per-file indexes
```

Nothing in the retrieval pipeline, the agent graph or the metrics changes. A collection
gives the engine the same things a pack does: documents, a description, a golden set.

## Steps

1. Parsers and the parse report, with tests that build their own fixture files.
2. Table-aware chunking: a long table is split by rows and each piece repeats the header.
3. Collections: storage, per-file index, add and remove without re-embedding the rest.
4. Agent: follow-up questions rewritten against the chat history; step-by-step streaming.
5. Auto-evaluation: generate questions from sampled passages, run the existing harness.
6. API: collections, upload, ask (plain and streamed), source view, page preview, eval.
7. CLI: `hyper-rag collection create | add | list | report | ask | eval | remove`.
8. Web UI: collections sidebar, drag-and-drop upload, chat, source panel, eval panel.
9. Use it: a real mixed collection through the live models; record what happened.
10. README and DECISIONS updates.

## Known limits, stated up front

- OCR reads text in images. A chart or photo with no text contributes nothing.
- Legacy `.doc`, `.ppt`, `.xls` are not supported; save as the modern format first.
- Word files have no fixed pages, so their citations point to a section, not a page.
- Auto-generated questions are written from the passages they are scored against, so
  they are easier than questions a person would ask. They measure "is the system
  working on this collection", not absolute quality.
- The API has no login. It is meant to run on your own machine.
