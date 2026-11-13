import pytest

from conftest import StubOcr
from hyper_rag.chunking import chunk_document
from hyper_rag.parsing import ParseError, build_ocr, parse_file
from hyper_rag.parsing.model import table_to_markdown
from hyper_rag.types import Document
from make_files import (
    make_csv,
    make_docx,
    make_html,
    make_markdown,
    make_pdf,
    make_png,
    make_pptx,
    make_xlsx,
)

OCR = StubOcr()


def test_pdf_keeps_headings_tables_and_reads_images(tmp_path):
    parsed = parse_file(make_pdf(tmp_path / "guide.pdf"), OCR)
    first, second, third = parsed.units

    assert [unit.label for unit in parsed.units] == ["Page 1", "Page 2", "Page 3"]
    assert "## Scheduling" in first.text
    # Wrapped lines are joined back into one paragraph.
    assert "arrives at 8 am and needs access to the roof" in first.text

    assert second.tables == 1 and "| Inverter | 10 | Manufacturer |" in second.text
    # The table is not repeated as loose words outside the table.
    assert second.text.count("Mounting frame") == 1
    assert second.images == 1 and second.images_with_text == 1
    assert "Text in image (OCR):\nTEXT FROM IMAGE" in second.text

    # Page 3 is only a picture of text: the whole page goes through OCR.
    assert third.ocr and third.text == "TEXT FROM IMAGE"
    assert parsed.report()["ocr_units"] == 1 and parsed.report()["tables"] == 1


def test_docx_sections_lists_tables_and_inline_images(tmp_path):
    parsed = parse_file(make_docx(tmp_path / "handbook.docx"), OCR)
    assert [unit.label for unit in parsed.units] == [
        "Maintenance handbook",
        "Cleaning",
        "Service visits",
    ]
    cleaning, service = parsed.units[1], parsed.units[2]
    assert "- Never use a pressure washer.\n- Clean before 9 am" in cleaning.text
    assert "| Cable inspection | Yearly |" in service.text and service.tables == 1
    assert service.images_with_text == 1 and "TEXT FROM IMAGE" in service.text


def test_pptx_slides_tables_notes_and_pictures(tmp_path):
    parsed = parse_file(make_pptx(tmp_path / "pricing.pptx"), OCR)
    first, second = parsed.units
    assert first.label == "Slide 1" and first.text.count("Pricing overview") == 1
    assert "Speaker notes: Mention the subsidy is paid within 30 days." in first.text
    assert "| 5 kW | 94000 |" in second.text and second.images_with_text == 1


def test_xlsx_one_table_per_non_empty_sheet(tmp_path):
    parsed = parse_file(make_xlsx(tmp_path / "output.xlsx"), OCR)
    assert [unit.label for unit in parsed.units] == ["Sheet Output", "Sheet Notes"]
    # 2480.0 in the workbook reads as 2480.
    assert "| January | 310 | 2480 |" in parsed.units[0].text


def test_text_formats(tmp_path):
    csv = parse_file(make_csv(tmp_path / "branches.csv"), OCR)
    assert "| Surat | Imran Shaikh | 0261-555-0188 |" in csv.units[0].text

    html = parse_file(make_html(tmp_path / "returns.html"), OCR)
    assert html.units[0].text.startswith("# Returns policy") and "Home" not in html.units[0].text

    markdown = parse_file(make_markdown(tmp_path / "app.md"), OCR)
    assert "## Alerts" in markdown.units[0].text

    latin = tmp_path / "old.txt"
    latin.write_bytes("Caf\xe9 tariff is 6 rupees".encode("cp1252"))
    parsed = parse_file(latin, OCR)
    assert "Café" in parsed.units[0].text and parsed.warnings


def test_image_file_is_read_by_the_real_ocr_models(tmp_path):
    # The one test that loads RapidOCR: its models ship in the wheel, so no network.
    parsed = parse_file(make_png(tmp_path / "invoice.png"), build_ocr("rapidocr"))
    text = parsed.units[0].text
    assert "INV-2041" in text and "18450" in text and parsed.units[0].ocr


def test_image_without_ocr_says_so(tmp_path):
    parsed = parse_file(make_png(tmp_path / "invoice.png"), build_ocr("none"))
    assert parsed.units[0].text == "" and "switched off" in parsed.warnings[0]


def test_unsupported_and_broken_files_raise_clear_errors(tmp_path):
    with pytest.raises(ParseError, match="Save the file as .docx"):
        parse_file(tmp_path / "old.doc", OCR)
    with pytest.raises(ParseError, match="not supported"):
        parse_file(tmp_path / "movie.mp4", OCR)
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"this is not a pdf")
    with pytest.raises(ParseError, match="Could not open the PDF"):
        parse_file(broken, OCR)


def test_table_to_markdown_drops_empty_rows_and_columns_and_escapes_pipes():
    rows = [["Name", None, "Note"], [None, None, None], ["a|b", None, "two\nlines"]]
    assert table_to_markdown(rows) == "| Name | Note |\n|---|---|\n| a\\|b | two lines |"


def test_long_table_is_split_by_rows_with_the_header_repeated(tmp_path):
    parsed = parse_file(make_xlsx(tmp_path / "big.xlsx", rows=120), OCR)
    document = Document(id="f/1", title="big.xlsx", url="", text=parsed.units[0].text)
    chunks = chunk_document(document, size=600, overlap=100, structured=True)

    assert len(chunks) > 3
    for chunk in chunks:
        lines = chunk.text.splitlines()
        assert (
            lines[1].startswith("| Month | Units generated (kWh)") and lines[2] == "|---|---|---|"
        )
        assert len(chunk.text) <= 600 + len("big.xlsx\n")
    # Every row lands in exactly one chunk.
    body = "\n".join(chunk.text for chunk in chunks)
    assert body.count("| Period 100 |") == 1


def test_pack_chunking_is_unchanged_by_default():
    document = Document(id="d", title="T", url="", text="x" * 3000)
    assert [len(c.text) for c in chunk_document(document, 1200, 150)] == [1202, 1202, 902]


def test_two_column_pdf_is_read_column_by_column(tmp_path):
    from reportlab.pdfgen import canvas

    path = tmp_path / "columns.pdf"
    page = canvas.Canvas(str(path), pagesize=(595, 842))
    page.setFont("Helvetica", 16)
    page.drawString(60, 790, "A full-width title that spans both of the columns below")
    page.setFont("Helvetica", 9)
    for row in range(30):
        y = 750 - row * 12
        page.drawString(60, y, f"left column line {row} talks about solar panels here")
        page.drawString(
            310, y, f"right column line {row} talks about billing and net metering there"
        )
    page.save()

    text = parse_file(path, OCR).units[0].text
    assert text.startswith("## A full-width title that spans both of the columns below")
    # All of the left column comes before any of the right column, with word spaces intact.
    assert text.index("left column line 29 talks about") < text.index("right column line 0 talks")
    assert "panels here right column" not in text
