"""Book structure (plan v2, A8): where a page sits in the book, and summaries of its parts.

Top-k retrieval finds passages; it cannot say what chapter 7 is about or how a book's
argument develops. RAPTOR answers that with a tree of LLM summaries over the whole book,
which a free tier cannot pay for. This is the cheaper version the plan settled on:

1. Every page gets its outline path (the PDF's bookmarks, or its own headings when it has
   none), and the path goes into the titles of its passages.
2. Section summaries are extractive and free: the sentences nearest the section's centroid
   in the local embedding space. No LLM call.
3. Chapter summaries cost one LLM call each, written from the section summaries (not the
   raw text), and only when a question first needs them; then they are kept.
4. Summaries are indexed next to the passages. Questions about the whole book or a whole
   chapter search them first.
"""

import re
from dataclasses import asdict, dataclass

import numpy as np

from hyper_rag.text import split_sentences

# "Summarise the book", "what is chapter 3 about", "compare chapters 2 and 5", "overall",
# "main argument": questions about a whole, not a fact.
_GLOBAL = re.compile(
    r"\b(summar(y|ise|ize|ies)|overview|overall|in general|main (idea|point|argument|theme)s?"
    r"|what (is|are) (this|the) (book|document|report|manual)|"
    r"(chapter|part|section)s? \w+( and \w+)? (about|cover|covers|discuss|discusses)"
    r"|compare (the )?(chapter|part|section)s?|which (chapter|part|section)s?|"
    r"how does (the|this) (book|argument|document) (develop|progress|end))\b",
    re.IGNORECASE,
)
_CHAPTER_NUMBER = re.compile(r"\b(?:chapter|part)s?\s+(\d+)(?:\s*(?:and|,|&)\s*(\d+))?", re.I)
SUMMARY_SENTENCES = 3
MAX_SENTENCES_EMBEDDED = 120  # per section: a long chapter is sampled, not read whole


def is_global(question: str) -> bool:
    return bool(_GLOBAL.search(question))


def chapter_numbers(question: str) -> set[int]:
    numbers = set()
    for match in _CHAPTER_NUMBER.finditer(question):
        numbers.update(int(n) for n in match.groups() if n)
    return numbers


@dataclass
class Section:
    level: int  # 0 = chapter, 1 = section
    title: str
    start: int  # first page
    end: int  # last page
    path: str  # "Chapter 3 › Methods"
    text: str = ""  # its summary

    def to_dict(self) -> dict:
        return asdict(self)


def outline_entries(outline: list[dict], units: list[dict]) -> list[dict]:
    """The PDF's outline, or, without one, the page-level "##" headings found in the text
    (each heading starts a chapter)."""
    if outline:
        return [
            {"level": min(e["level"], 1), "title": e["title"].strip(), "page": e["page"]}
            for e in outline
            if e.get("title", "").strip()
        ]
    entries = []
    for unit in units:
        for line in unit["text"].splitlines():
            if line.startswith("## "):
                entries.append({"level": 0, "title": line[3:].strip(), "page": unit["number"]})
                break  # one heading per page is enough to locate a chapter
    return entries


def sections(entries: list[dict], last_page: int) -> list[Section]:
    """Page ranges for every outline entry: until the next entry at the same or a higher level."""
    found = []
    for i, entry in enumerate(entries):
        end = last_page
        for later in entries[i + 1 :]:
            if later["level"] <= entry["level"]:
                end = max(later["page"] - 1, entry["page"])
                break
        parent = next(
            (e["title"] for e in reversed(entries[:i]) if e["level"] < entry["level"]), None
        )
        path = f"{parent} › {entry['title']}" if parent and entry["level"] > 0 else entry["title"]
        found.append(Section(entry["level"], entry["title"], entry["page"], end, path))
    return found


def page_paths(entries: list[dict], pages: int) -> dict[int, str]:
    """Each page's outline path, e.g. {37: "Chapter 3 › 3.2 Methods"}."""
    paths, current = {}, {0: None, 1: None}
    ordered = sorted(entries, key=lambda e: (e["page"], e["level"]))
    position = 0
    for page in range(1, pages + 1):
        while position < len(ordered) and ordered[position]["page"] <= page:
            entry = ordered[position]
            current[entry["level"]] = entry["title"]
            if entry["level"] == 0:
                current[1] = None
            position += 1
        parts = [t for t in (current[0], current[1]) if t]
        if parts:
            paths[page] = " › ".join(parts)
    return paths


def body_sentences(units: list[dict]) -> list[str]:
    sentences = []
    for unit in units:
        for line in unit["text"].splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "|", "Text in image")):
                continue
            sentences += [s for s in split_sentences(line) if len(s.split()) >= 5]
    return sentences


def extractive_summary(
    embedder, sentences: list[str], k: int = SUMMARY_SENTENCES, common: set[str] = frozenset()
) -> str:
    """k sentences that represent the section: near its centroid, but not near each other
    (maximal marginal relevance), in their original order.

    `common` holds sentence shapes (numbers blanked) that appear across many sections of the
    book, such as "The reference code for page 12 is ...". Those are the most "central"
    sentences of every section and say nothing about any of them, so they are left out.
    """
    from hyper_rag.parsing.xray import normalise_line

    candidates = [s for s in dict.fromkeys(sentences) if normalise_line(s) not in common]
    if len(candidates) < k:
        candidates = list(dict.fromkeys(sentences))
    if not candidates:
        return ""
    if len(candidates) > MAX_SENTENCES_EMBEDDED:
        step = len(candidates) / MAX_SENTENCES_EMBEDDED
        candidates = [candidates[int(i * step)] for i in range(MAX_SENTENCES_EMBEDDED)]
    vectors = np.asarray(embedder.embed_documents(candidates), dtype=np.float32)
    centroid = vectors.mean(axis=0)
    centroid /= np.linalg.norm(centroid) or 1.0
    relevance = vectors @ centroid
    chosen: list[int] = []
    while len(chosen) < min(k, len(candidates)):
        redundancy = (vectors @ vectors[chosen].T).max(axis=1) if chosen else 0.0
        score = 0.6 * relevance - 0.4 * redundancy
        if chosen:
            score[chosen] = -np.inf
        chosen.append(int(np.argmax(score)))
    return " ".join(candidates[i] for i in sorted(chosen))


def common_shapes(groups: list[list[str]], share: float = 0.3) -> set[str]:
    """Sentence shapes found in more than `share` of the groups (sections)."""
    from collections import Counter

    from hyper_rag.parsing.xray import normalise_line

    if len(groups) < 3:
        return set()
    counted = Counter(shape for group in groups for shape in {normalise_line(s) for s in group})
    return {shape for shape, count in counted.items() if count > share * len(groups)}


_SUMMARY_ID = re.compile(r"#[sc]\d+$")


def is_summary(chunk_id: str) -> bool:
    return bool(_SUMMARY_ID.search(chunk_id))


class SummaryFirst:
    """A retriever for questions about a whole: chapter summaries named in the question
    first, then the summaries the search ranks highest, then the usual passages."""

    def __init__(self, base, chapters: set[int] | None = None):
        self.base = base
        self.chunks = base.chunks
        self.embedder = base.embedder
        self.reranker = base.reranker
        self.settings = base.settings
        self.chapters = chapters or set()

    def retrieve(self, query, mode="hybrid_rerank", top_k=None, on_event=None):
        from hyper_rag.events import emit, ranked_chunks
        from hyper_rag.types import ScoredChunk

        top_k = top_k or self.settings.top_k
        pool = self.base.retrieve(query, mode=mode, top_k=max(top_k * 4, 20), on_event=on_event)
        named = [
            ScoredChunk(chunk, 1.0)
            for number in sorted(self.chapters)
            for chunk in self.chunks
            if chunk.id.endswith(f"#c{number - 1}")
        ]
        summaries = [hit for hit in pool if is_summary(hit.chunk.id)]
        chosen, seen = [], set()
        for hit in [*named, *summaries, *pool]:
            if hit.chunk.id not in seen:
                seen.add(hit.chunk.id)
                chosen.append(hit)
        chosen = chosen[:top_k]
        emit(on_event, "r.summaries", hits=ranked_chunks(chosen), named=sorted(self.chapters))
        return chosen


class PassagesOnly:
    """A retriever for ordinary questions: summaries are left out, so a section summary
    that repeats a sentence pattern cannot outrank the page that states the fact."""

    def __init__(self, base):
        self.base = base
        self.chunks = base.chunks
        self.embedder = base.embedder
        self.reranker = base.reranker
        self.settings = base.settings

    def retrieve(self, query, mode="hybrid_rerank", top_k=None, on_event=None):
        return self.base.retrieve(
            query, mode=mode, top_k=top_k, on_event=on_event, allow=lambda c: not is_summary(c.id)
        )
