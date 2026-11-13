"""Papers pack ingestion: title and abstract from the abstract page, full text from the PDF."""

import io
import re
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

from hyper_rag.types import Document
from hyper_rag.web import PoliteFetcher


def _metadata(abs_html: str) -> tuple[str, str]:
    """(title, abstract) from the <meta> tags arXiv puts on every abstract page."""
    soup = BeautifulSoup(abs_html, "html.parser")

    def meta(name: str) -> str:
        tag = soup.find("meta", attrs={"name": name})
        return " ".join(tag["content"].split()) if tag and tag.get("content") else ""

    return meta("citation_title"), meta("citation_abstract")


def _pdf_text(pdf: bytes) -> str:
    pages = [page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages]
    text = "\n\n".join(pages)  # a page break becomes a paragraph break for the chunker
    text = re.sub(r"-\n(?=[a-z])", "", text)  # re-join words hyphenated across lines
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)  # single newlines are just line wraps
    # Drop the bibliography: reference lists match queries by title but answer nothing.
    cut = max(text.rfind("\n\nReferences"), text.rfind(" References "))
    return text[:cut] if cut > len(text) * 0.4 else text


def fetch(pack, raw_dir: Path):
    for source in pack.config.sources:
        fetcher = PoliteFetcher(raw_dir, delay_seconds=3.0)
        for arxiv_id in source["ids"]:
            abs_url = source["abs_url"] + arxiv_id
            abs_html = fetcher.get(abs_url)
            pdf = fetcher.get_bytes(source["pdf_url"] + arxiv_id, suffix=".pdf")
            if abs_html is None or pdf is None:
                continue
            title, abstract = _metadata(abs_html)
            text = f"## Abstract\n\n{abstract}\n\n## Full text\n\n{_pdf_text(pdf)}"
            yield Document(id=arxiv_id, title=title or arxiv_id, url=abs_url, text=text)
