"""Answer to artifact (deck card D6): take a cited answer out of the app.

    markdown   the question, the answer and its sources as one Markdown document. Needs no
               model. Notion, Obsidian and most editors turn pasted Markdown into formatted
               pages, so this is also the Notion route.
    linkedin   an outline for a LinkedIn post, written by the model from the answer only.
               It costs one model request, and it is a draft: it is the answer reshaped,
               not checked again, so read it against the sources before posting.

The inputs are a saved run (what the server kept when the question was answered), never
text sent by the page, so an export can only contain what the system actually said.
"""

import re

from hyper_rag.llm import LLM
from hyper_rag.llm.base import complete_with_usage
from hyper_rag.prompts import post_outline_prompt
from hyper_rag.text import strip_citations

FORMATS = ("markdown", "linkedin")
QUOTE_CHARS = 400


def _filename(question: str, extension: str) -> str:
    kept: list[str] = []
    for word in re.findall(r"[a-z0-9]+", question.lower()):
        if len("-".join([*kept, word])) > 48:
            break  # whole words only: "installation-ta.md" reads like a bug
        kept.append(word)
    return f"{'-'.join(kept) or 'answer'}.{extension}"


def _quote(text: str) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    if len(flat) > QUOTE_CHARS:
        flat = flat[:QUOTE_CHARS].rsplit(" ", 1)[0] + "…"
    return flat


def to_markdown(answer: dict) -> str:
    """The answer as Markdown. A refusal is exported as a refusal, not as an answer."""
    lines = [f"# {answer['question']}", ""]
    if answer.get("refused"):
        lines += ["_No answer: the documents do not support one._", ""]
        return "\n".join(lines)
    lines += [answer["answer"].strip(), ""]
    if answer.get("citations"):
        lines += ["## Sources", ""]
        for citation in answer["citations"]:
            title = citation["title"]
            # Links inside a collection are paths on the server, useless outside it.
            url = citation.get("url", "")
            label = f"[{title}]({url})" if url.startswith("http") else title
            lines.append(f"{citation['number']}. {label}")
            lines.append(f"   > {_quote(citation['text'])}")
        lines.append("")
    return "\n".join(lines)


def to_linkedin(answer: dict, llm: LLM) -> tuple[str, int]:
    """A post outline from the answer. Returns (text, model calls). Refusals have none."""
    if answer.get("refused"):
        raise ValueError("There is no answer to turn into a post: the question was declined.")
    reply, _ = complete_with_usage(llm, post_outline_prompt(answer["question"], answer["answer"]))
    text = strip_citations(reply).strip()
    if not text:
        raise ValueError("The model returned nothing. Try again.")
    return text, 1


def export_answer(answer: dict, fmt: str, llm: LLM | None = None) -> dict:
    """{"format", "filename", "text", "llm_calls"} for one saved answer."""
    if fmt == "markdown":
        return {
            "format": fmt,
            "filename": _filename(answer["question"], "md"),
            "text": to_markdown(answer),
            "llm_calls": 0,
        }
    if fmt == "linkedin":
        if llm is None:
            raise ValueError("The LinkedIn outline needs a model.")
        text, calls = to_linkedin(answer, llm)
        return {
            "format": fmt,
            "filename": _filename(answer["question"], "txt"),
            "text": text,
            "llm_calls": calls,
        }
    raise ValueError(f"Unknown format '{fmt}'. Choose one of: {', '.join(FORMATS)}.")
