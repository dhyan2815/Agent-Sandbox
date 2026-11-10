"""Small text helpers used by BM25 and by the offline stand-ins (fake LLM, lexical reranker)."""

import re

_TOKEN = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)*")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_CITATION = re.compile(r"\[(\d+)\]")

STOPWORDS = frozenset(
    """a an and are as at be by can do does for from how i if in is it its of on or that the
    this to was what when where which who why will with you your my me we our there their
    they them than then so not no into about should would could has have had any all each
    per up out get after before much many long take takes use used using""".split()
)


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens. snake_case identifiers stay whole so API names match exactly."""
    return _TOKEN.findall(text.lower())


def _stem(word: str) -> str:
    # Deliberately crude: enough for "refunds" to match "refund" in the offline stand-ins.
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def content_words(text: str) -> set[str]:
    """Stemmed tokens without stopwords: a rough 'what is this about' signature."""
    return {_stem(t) for t in tokenize(text) if t not in STOPWORDS}


def coverage(needle: str, haystack: str) -> float:
    """Fraction of the needle's content words that also appear in the haystack (0..1)."""
    wanted = content_words(needle)
    if not wanted:
        return 0.0
    return len(wanted & content_words(haystack)) / len(wanted)


def split_sentences(text: str) -> list[str]:
    # A line break also ends a sentence: headings and list items carry no full stop.
    return [
        sentence.strip()
        for line in text.splitlines()
        for sentence in _SENTENCE_END.split(line)
        if sentence.strip()
    ]


def cited_numbers(answer: str) -> list[int]:
    """Citation markers in order of first appearance: 'x [2] y [1][2]' -> [2, 1]."""
    seen: list[int] = []
    for match in _CITATION.finditer(answer):
        number = int(match.group(1))
        if number not in seen:
            seen.append(number)
    return seen


def strip_citations(answer: str) -> str:
    return re.sub(r"\s*\[\d+\]", "", answer).strip()
