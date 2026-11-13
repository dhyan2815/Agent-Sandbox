"""Builds small test documents of every supported format, from code.

Nothing binary is committed: each test writes the files it needs into a temp folder.
The content is an invented company ("Northwind Solar") so no real document is copied.
"""

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WARRANTY_ROWS = [
    ["Component", "Warranty (years)", "Covered by"],
    ["Solar panel", "25", "Manufacturer"],
    ["Inverter", "10", "Manufacturer"],
    ["Mounting frame", "15", "Northwind Solar"],
    ["Battery", "8", "Manufacturer"],
]


def text_image(lines: list[str], size: tuple[int, int] = (900, 260)) -> Image.Image:
    """A white image with black text on it: what a screenshot or a scan looks like to OCR."""
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=34)
    for row, line in enumerate(lines):
        draw.text((30, 30 + row * 70), line, fill="black", font=font)
    return image


def _png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def make_pdf(path: Path) -> Path:
    """Three pages: prose with a heading, a table plus an embedded image, and a scanned page."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Image as FlowImage
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table

    styles = getSampleStyleSheet()
    table = Table(WARRANTY_ROWS)
    table.setStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)])
    sticker = io.BytesIO(_png_bytes(text_image(["Support line: 1800-555-0142"], (900, 120))))
    scan = io.BytesIO(_png_bytes(text_image(["Site survey fee is 1500 rupees", "Paid on booking"])))
    story = [
        Paragraph("Northwind Solar installation guide", styles["Title"]),
        Paragraph("Scheduling", styles["Heading1"]),
        Paragraph(
            "A standard rooftop installation takes two working days. The crew arrives at "
            "8 am and needs access to the roof and to the main distribution board.",
            styles["BodyText"],
        ),
        Paragraph(
            "Net metering approval from the electricity board usually takes three weeks "
            "after the installation is inspected.",
            styles["BodyText"],
        ),
        PageBreak(),
        Paragraph("Warranty", styles["Heading1"]),
        Paragraph("Each component carries its own warranty period.", styles["BodyText"]),
        Spacer(1, 12),
        table,
        Spacer(1, 24),
        FlowImage(sticker, width=360, height=48),
        PageBreak(),
        FlowImage(scan, width=450, height=130),
    ]
    SimpleDocTemplate(str(path), pagesize=A4).build(story)
    return path


def make_docx(path: Path) -> Path:
    from docx import Document

    document = Document()
    document.add_heading("Maintenance handbook", level=0)
    document.add_paragraph("This handbook covers routine care of a rooftop solar system.")
    document.add_heading("Cleaning", level=1)
    document.add_paragraph("Clean the panels every six weeks with soft water and a sponge.")
    document.add_paragraph("Never use a pressure washer.", style="List Bullet")
    document.add_paragraph("Clean before 9 am, while the glass is cool.", style="List Bullet")
    document.add_heading("Service visits", level=1)
    document.add_paragraph("The annual service visit costs 2400 rupees.")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text, table.rows[0].cells[1].text = "Check", "Frequency"
    for check, frequency in [("Inverter log review", "Monthly"), ("Cable inspection", "Yearly")]:
        cells = table.add_row().cells
        cells[0].text, cells[1].text = check, frequency
    picture = io.BytesIO(_png_bytes(text_image(["Emergency shutdown: red switch"], (900, 120))))
    document.add_picture(picture)
    document.save(str(path))
    return path


def make_pptx(path: Path) -> Path:
    from pptx import Presentation
    from pptx.util import Inches

    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide.shapes.title.text = "Pricing overview"
    slide.placeholders[1].text = "A 3 kW system costs 185000 rupees before subsidy."
    slide.notes_slide.notes_text_frame.text = "Mention the subsidy is paid within 30 days."

    slide = presentation.slides.add_slide(presentation.slide_layouts[5])
    slide.shapes.title.text = "Subsidy by system size"
    shape = slide.shapes.add_table(3, 2, Inches(1), Inches(1.5), Inches(6), Inches(1.5))
    rows = [("System size", "Subsidy"), ("3 kW", "78000"), ("5 kW", "94000")]
    for row, values in enumerate(rows):
        for column, value in enumerate(values):
            shape.table.cell(row, column).text = value
    picture = io.BytesIO(_png_bytes(text_image(["Payback period: 4.5 years"], (900, 120))))
    slide.shapes.add_picture(picture, Inches(1), Inches(4), width=Inches(6))
    presentation.save(str(path))
    return path


def make_xlsx(path: Path, rows: int = 4) -> Path:
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Output"
    sheet.append(["Month", "Units generated (kWh)", "Bill saved (INR)"])
    months = ["January", "February", "March", "April", "May", "June"]
    for index in range(rows):
        name = months[index] if index < len(months) else f"Period {index + 1}"
        sheet.append([name, 310 + index * 15, 2480.0 + index * 120])
    notes = workbook.create_sheet("Notes")
    notes.append(["Topic", "Detail"])
    notes.append(["Meter type", "Bidirectional net meter"])
    workbook.create_sheet("Empty")
    workbook.save(str(path))
    return path


def make_png(path: Path) -> Path:
    text_image(["Invoice INV-2041", "Total due: 18450 INR", "Due date: 14 March"]).save(path)
    return path


def make_csv(path: Path) -> Path:
    path.write_text(
        "city,branch_manager,phone\nPune,Asha Kulkarni,020-555-0101\n"
        "Surat,Imran Shaikh,0261-555-0188\n",
        encoding="utf-8",
    )
    return path


def make_html(path: Path) -> Path:
    path.write_text(
        "<html><head><title>Returns policy</title></head><body><nav>Home</nav><main>"
        "<h1>Returns policy</h1><p>Unused accessories can be returned within 14 days.</p>"
        "<h2>Refunds</h2><p>Refunds are paid to the original payment method in 5 working days.</p>"
        "</main></body></html>",
        encoding="utf-8",
    )
    return path


def make_markdown(path: Path) -> Path:
    path.write_text(
        "# Monitoring app\n\nThe Northwind app shows live output and daily totals.\n\n"
        "## Alerts\n\nAn alert is sent when output drops below 60 percent of the forecast "
        "for two days in a row.\n",
        encoding="utf-8",
    )
    return path


MAKERS = {
    "guide.pdf": make_pdf,
    "handbook.docx": make_docx,
    "pricing.pptx": make_pptx,
    "output.xlsx": make_xlsx,
    "invoice.png": make_png,
    "branches.csv": make_csv,
    "returns.html": make_html,
    "app.md": make_markdown,
}


def make_all(folder: Path) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    return [maker(folder / name) for name, maker in MAKERS.items()]


def make_book(
    path: Path,
    pages: int = 40,
    blank_every: int = 0,
    repeat_page: int = 0,
    changed: dict[int, str] | None = None,
    outline: bool = False,
) -> Path:
    """A long PDF: a running header and "Page n of N" footer on every page, a chapter
    heading every ten pages, and one fact per page that only that page states.

    blank_every adds an empty page after every n pages; repeat_page appends an exact copy
    of that page at the end. Both are what the X-ray pass should skip.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    width, height = A4
    pdf = canvas.Canvas(str(path), pagesize=A4)
    total = pages + (pages // blank_every if blank_every else 0) + (1 if repeat_page else 0)
    printed = 0

    def page(number: int) -> None:
        nonlocal printed
        printed += 1
        pdf.setFont("Helvetica", 8)
        pdf.drawString(60, height - 40, "Northwind Solar field manual - internal edition")
        pdf.drawString(width / 2 - 30, 30, f"Page {printed} of {total}")
        y = height - 90
        if outline and number % 10 == 1:
            chapter = number // 10 + 1
            pdf.bookmarkPage(f"c{chapter}")
            pdf.addOutlineEntry(f"Chapter {chapter}: Site work part {chapter}", f"c{chapter}", 0)
        if outline and number % 10 in (1, 6):
            part = 1 if number % 10 == 1 else 2
            key = f"c{number // 10 + 1}s{part}"
            pdf.bookmarkPage(key)
            pdf.addOutlineEntry(f"{number // 10 + 1}.{part} Rows {number} onward", key, 1)
        if number % 10 == 1:
            pdf.setFont("Helvetica-Bold", 18)
            pdf.drawString(60, y, f"Chapter {number // 10 + 1}: Site work part {number // 10 + 1}")
            y -= 36
        pdf.setFont("Helvetica", 10)
        fact = f"Fact {number}: the inspection code for panel row {number} is NW-{number * 7:04d}."
        lines = [
            (changed or {}).get(number, fact),
            "Crews log every inspection in the site book before leaving the roof.",
            f"Row {number} uses mounting rails cut to {100 + number} centimetres.",
        ]
        for line in lines:
            pdf.drawString(60, y, line)
            y -= 16
        pdf.showPage()

    for number in range(1, pages + 1):
        page(number)
        if blank_every and number % blank_every == 0:
            printed += 1
            pdf.showPage()  # an empty page
    if repeat_page:
        page(repeat_page)
    pdf.save()
    return path
