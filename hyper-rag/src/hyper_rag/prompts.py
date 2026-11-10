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
    task: str  # route | grade | rewrite | generate | check | judge
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
    system = (
        "You route questions for a documentation assistant. "
        'Reply with JSON only: {"route": "retrieve"} if the question could plausibly be '
        'answered from the document collection described below, or {"route": "decline"} '
        "if it is clearly unrelated to it (small talk, other topics)."
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
    user = f"Passages:\n{format_passages(passages)}\n\nAnswer: {answer}"
    return Prompt(
        "check", system, user, max_tokens=300, inputs={"answer": answer, "passages": passages}
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
        "judge", system, user, max_tokens=300, inputs={"reference": reference, "answer": answer}
    )
