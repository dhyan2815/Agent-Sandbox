"""Split documents into overlapping passages along their heading structure."""

import re

from hyper_rag.types import Chunk, Document

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def _sections(text: str) -> list[tuple[str, str]]:
    """Split markdown into (heading, body) sections. Text before the first heading gets ''."""
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in text.splitlines():
        match = _HEADING.match(line)
        if match:
            sections.append((match.group(2).strip(), []))
        else:
            sections[-1][1].append(line)
    return [(heading, "\n".join(lines).strip()) for heading, lines in sections]


def _is_table(paragraph: str) -> bool:
    lines = paragraph.split("\n")
    return len(lines) >= 3 and lines[0].startswith("|") and lines[1].startswith("|---")


def _split_structured(paragraph: str, size: int) -> list[str]:
    """Split an oversize paragraph at line boundaries instead of at a character count.

    A table is split between rows, and every piece starts with the header row again:
    a row of numbers is meaningless without its column names, both to the retriever
    and to the model that has to read it.
    """
    lines = paragraph.split("\n")
    header = lines[:2] if _is_table(paragraph) else []
    prefix = "\n".join(header)
    pieces: list[str] = []
    current: list[str] = []
    for line in lines[len(header) :]:
        while len(line) > size:  # a single line longer than a chunk: nothing left but a cut
            if current:
                pieces.append("\n".join([*header, *current]))
                current = []
            pieces.append(line[:size])
            line = line[size:]
        if current and len(prefix) + 1 + sum(len(c) + 1 for c in current) + len(line) > size:
            pieces.append("\n".join([*header, *current]))
            current = []
        current.append(line)
    if current:
        pieces.append("\n".join([*header, *current]))
    return pieces


def _pack_paragraphs(body: str, size: int, overlap: int, structured: bool = False) -> list[str]:
    """Greedily fill pieces up to `size` characters without cutting inside a paragraph.

    Each new piece starts with the tail of the previous one (`overlap` characters), so a
    fact that straddles a boundary is still whole in at least one piece.
    """
    pieces: list[str] = []
    current = ""
    for paragraph in re.split(r"\n\s*\n", body):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if structured and len(paragraph) > size:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(_split_structured(paragraph, size))
            continue
        # A single paragraph longer than the limit (a big table, a code block) is cut hard.
        while len(paragraph) > size:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(paragraph[:size])
            paragraph = paragraph[size - overlap :]
        if current and len(current) + len(paragraph) + 2 > size:
            pieces.append(current)
            current = current[-overlap:] if overlap else ""
        current = f"{current}\n\n{paragraph}" if current else paragraph
    if current.strip():
        pieces.append(current)
    return pieces


def chunk_document(
    document: Document, size: int, overlap: int, structured: bool = False
) -> list[Chunk]:
    """Split one document into chunks.

    `structured=True` splits oversize paragraphs along their lines and keeps table
    headers (see _split_structured). Uploaded documents use it. The domain packs keep
    the original hard cut, so the chunks behind the published eval numbers do not change.
    """
    chunks: list[Chunk] = []
    for heading, body in _sections(document.text):
        if not body:
            continue
        for piece in _pack_paragraphs(body, size, overlap, structured):
            # Prefix every chunk with its document title and section heading. A passage
            # such as "It expires after 5 minutes" is unfindable on its own; with
            # "UPI payments > Collect flow" in front, both BM25 and the embedding see
            # what "it" refers to.
            header = (
                document.title
                if not heading or heading == document.title
                else (f"{document.title} > {heading}")
            )
            chunks.append(
                Chunk(
                    id=f"{document.id}#{len(chunks)}",
                    doc_id=document.id,
                    title=header,
                    url=document.url,
                    text=f"{header}\n{piece.strip()}",
                )
            )
    return chunks


def chunk_documents(
    documents: list[Document], size: int, overlap: int, structured: bool = False
) -> list[Chunk]:
    return [
        chunk
        for document in documents
        for chunk in chunk_document(document, size, overlap, structured)
    ]
