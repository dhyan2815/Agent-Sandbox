"""Every prompt the system sends, in one place.

Prompts are kept short on purpose: free tiers cap tokens per minute, and the agent
makes several calls per question.
"""

from dataclasses import dataclass, field

from hyper_rag.types import Chunk

# The generator writes this exact token when the passages do not contain the answer.
# A fixed token is easier to detect reliably than a free-text apology.
INSUFFICIENT = "INSUFFICIENT_CONTEXT"

REFUSAL_MESSAGE = "I can't answer that from the available sources."


@dataclass(frozen=True)
class Prompt:
    task: str  # route | grade | rewrite | generate | check | judge | condense | synthesize
    #           | summarize | claims | verify
    system: str
    user: str
    max_tokens: int = 400
    # The structured values the prompt was rendered from. Real providers ignore this;
    # the fake provider reads it so it does not have to parse prompt text.
    inputs: dict = field(default_factory=dict, compare=False)


def format_passages(passages: list[Chunk]) -> str:
    """Numbered passages. The numbers are what the answer cites as [1], [2], ..."""
    return "\n\n".join(f"[{i}] {c.title}\n{c.text}" for i, c in enumerate(passages, start=1))


def route_prompt(question: str, pack_description: str) -> Prompt:
    # The router only filters out questions that are obviously about something else.
    # It must not guess whether the answer exists: that is what retrieval and grading
    # are for. An earlier, stricter wording ("could plausibly be answered from the
    # collection") made a small model decline 7 of 16 answerable farming questions.
    system = (
        "You route questions for a documentation assistant. Reply with JSON only. "
        'Reply {"route": "retrieve"} if the question is about any subject the document '
        "collection below deals with, even loosely, and even if you doubt the answer is in "
        'it: a search will check that. Reply {"route": "decline"} only if the question '
        "is plainly about something else, such as small talk or an unrelated field."
    )
    user = f"Collection: {pack_description}\n\nQuestion: {question}"
    return Prompt("route", system, user, max_tokens=200, inputs={"question": question})


def grade_prompt(question: str, passages: list[Chunk]) -> Prompt:
    # One call grades all passages. Grading them one by one would multiply the
    # number of requests by top_k, which free-tier rate limits cannot absorb.
    system = (
        "You grade retrieved passages. A passage is relevant if it contains information "
        'that helps answer the question. Reply with JSON only: {"relevant": [numbers]} '
        "listing the relevant passage numbers. Use an empty list if none are relevant."
    )
    user = f"Question: {question}\n\nPassages:\n{format_passages(passages)}"
    return Prompt(
        "grade", system, user, max_tokens=300, inputs={"question": question, "passages": passages}
    )


def rewrite_prompt(question: str, tried: list[str]) -> Prompt:
    system = (
        "The search queries below did not find relevant passages. Write one new search "
        "query for the same question: use different wording, expand abbreviations, and "
        "name the specific feature or term. Reply with the query only."
    )
    user = f"Question: {question}\n\nQueries already tried:\n" + "\n".join(f"- {q}" for q in tried)
    return Prompt(
        "rewrite", system, user, max_tokens=200, inputs={"question": question, "tried": tried}
    )


def generate_prompt(question: str, passages: list[Chunk]) -> Prompt:
    system = (
        "Answer the question using only the numbered passages. "
        "After each claim, cite the passage it comes from as [n]. "
        "Be concise: a few sentences, or short steps if the question asks how to do something. "
        "Do not use outside knowledge. If the passages do not contain the answer, reply with "
        f"exactly {INSUFFICIENT} and nothing else."
    )
    user = f"Passages:\n{format_passages(passages)}\n\nQuestion: {question}"
    return Prompt(
        "generate",
        system,
        user,
        max_tokens=700,
        inputs={"question": question, "passages": passages},
    )


def check_prompt(answer: str, passages: list[Chunk]) -> Prompt:
    """Groundedness check. The agent runs it on its own draft; the eval reuses it with the judge."""
    system = (
        "You verify an answer against source passages. The answer is grounded only if every "
        "factual claim in it is directly supported by the passages. Reply with JSON only: "
        '{"grounded": true} or {"grounded": false, "unsupported": "<the unsupported claim>"}.'
    )
    # The answer goes in a clearly marked block with the question repeated after it. With
    # a bare "Answer: ..." line at the end of long passages, a small model sometimes
    # replied that there was no answer to verify.
    user = (
        f"Passages:\n{format_passages(passages)}\n\n"
        f"Answer to verify:\n<answer>\n{answer}\n</answer>\n\n"
        "Is every factual claim in the answer supported by the passages?"
    )
    return Prompt(
        "check", system, user, max_tokens=120, inputs={"answer": answer, "passages": passages}
    )


def judge_prompt(question: str, reference: str, answer: str) -> Prompt:
    """Answer correctness against the golden reference answer (eval only)."""
    system = (
        'You grade an answer against a reference answer. "correct": it states the same key '
        'facts as the reference. "partial": some key facts are right but others are missing '
        'or wrong. "incorrect": it contradicts the reference or misses the point. Extra '
        'correct detail is fine. Reply with JSON only: {"verdict": "correct"}, '
        '{"verdict": "partial"} or {"verdict": "incorrect"}.'
    )
    user = f"Question: {question}\n\nReference answer: {reference}\n\nAnswer to grade: {answer}"
    return Prompt(
        "judge", system, user, max_tokens=40, inputs={"reference": reference, "answer": answer}
    )


def condense_prompt(history: list[tuple[str, str]], question: str) -> Prompt:
    """Turn a follow-up ("and for the bigger one?") into a question that stands on its own.

    Retrieval sees only the question, so a follow-up has to carry its own subject.
    Only the last few turns are sent, with answers cut short: the earlier questions
    carry most of what a pronoun can refer to.
    """
    system = (
        "Rewrite the follow-up question as one standalone question, using the conversation "
        "to fill in what it refers to. If it already stands on its own, repeat it unchanged. "
        "Do not answer it. Reply with the question only."
    )
    turns = "\n".join(f"User: {q}\nAssistant: {a[:300]}" for q, a in history[-3:])
    user = f"Conversation:\n{turns}\n\nFollow-up question: {question}"
    return Prompt(
        "condense", system, user, max_tokens=200, inputs={"history": history, "question": question}
    )


def synthesize_prompt(passage: Chunk) -> Prompt:
    """Write one test question from a passage (auto-evaluation of uploaded collections)."""
    system = (
        "You write test questions for a document search system. From the passage, write one "
        "specific question that the passage answers, as a person who has not seen the "
        'passage would ask it: name the subject, never say "the passage" or "the document". '
        "Reply with JSON only: "
        '{"question": "...", "answer": "<one or two sentences>", "fact": "..."}. '
        "The fact is the one number, name or term (at most four words, copied exactly from "
        "the passage, never a whole sentence or a table row) that any correct answer must "
        "contain."
    )
    return Prompt(
        "synthesize",
        system,
        f"Passage:\n{passage.text}",
        max_tokens=400,
        inputs={"passage": passage},
    )


def chapter_summary_prompt(title: str, sections: list[str]) -> Prompt:
    """One chapter's summary, written from its sections' extractive summaries (plan v2, A8).

    The input is a few sentences per section, never the chapter's raw text, so one call
    per chapter stays small on a free tier.
    """
    system = (
        "You summarise one chapter of a document for a reader who has not read it. Use only "
        "the notes given. Write 3 to 5 plain sentences: what the chapter is about and its "
        "main points. No preamble, no lists, no citations."
    )
    notes = "\n".join(f"- {text}" for text in sections if text)
    user = f"Chapter: {title}\n\nNotes from its sections:\n{notes}"
    return Prompt(
        "summarize", system, user, max_tokens=300, inputs={"title": title, "sections": sections}
    )


def claims_prompt(text: str, max_claims: int) -> Prompt:
    """Split a draft into separate checkable claims (claim checker, deck card D4)."""
    system = (
        "You split a text into its separate factual claims, so that each can be checked "
        "against documents. A claim is one statement that is true or false: a number, a date, "
        "a name, a property, a cause. Rewrite each so it stands on its own (replace pronouns "
        "with what they refer to). Skip opinions, greetings and questions. "
        f'Reply with JSON only: {{"claims": ["...", "..."]}} with at most {max_claims} claims.'
    )
    return Prompt(
        "claims", system, f"Text:\n{text}", max_tokens=600, inputs={"text": text, "max": max_claims}
    )


def verify_claims_prompt(items: list[tuple[str, list[Chunk]]]) -> Prompt:
    """Verdicts for a few claims at once, each against its own numbered passages."""
    system = (
        "You check claims against source passages. For each claim give one verdict: "
        '"supported" (a passage states it), "contradicted" (a passage states something that '
        'conflicts with it, such as a different number, date or name) or "not_found" (the '
        "passages say nothing about it). Judge only from the passages, never from outside "
        "knowledge, and do not guess: if the passages are silent, the verdict is not_found. "
        "For supported and contradicted, give the number of the passage that decides it. Reply "
        'with JSON only: {"verdicts": [{"claim": 1, "verdict": "supported", "passage": 2}, ...]}.'
    )
    blocks = []
    for number, (claim, passages) in enumerate(items, start=1):
        shown = "\n".join(f"  [{i}] {c.text[:600]}" for i, c in enumerate(passages, start=1))
        blocks.append(f"Claim {number}: {claim}\nPassages for claim {number}:\n{shown}")
    return Prompt(
        "verify",
        system,
        "\n\n".join(blocks),
        max_tokens=60 + 40 * len(items),
        inputs={"items": items},
    )
