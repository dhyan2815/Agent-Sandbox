"""The result type shared by the agent and the single-shot baseline."""

from dataclasses import dataclass, field

from hyper_rag.prompts import REFUSAL_MESSAGE
from hyper_rag.text import cited_numbers
from hyper_rag.types import Chunk


@dataclass
class Answer:
    question: str
    text: str
    refused: bool
    passages: list[Chunk]  # the numbered passages the generator saw; [n] cites passages[n-1]
    cited: list[int] = field(default_factory=list)  # valid citation numbers, in order of use
    invalid_citations: list[int] = field(default_factory=list)  # numbers with no such passage
    trace: list[str] = field(default_factory=list)  # one line per step, for debugging and demos
    llm_calls: int = 0

    @property
    def citations(self) -> list[tuple[int, Chunk]]:
        return [(number, self.passages[number - 1]) for number in self.cited]

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.text,
            "refused": self.refused,
            "citations": [
                {
                    "number": n,
                    "title": c.title,
                    "url": c.url,
                    "chunk_id": c.id,
                    "doc_id": c.doc_id,
                    "text": c.text,
                }
                for n, c in self.citations
            ],
            "trace": self.trace,
            "llm_calls": self.llm_calls,
        }


def build_answer(
    question: str, text: str, passages: list[Chunk], trace: list[str], llm_calls: int
) -> Answer:
    numbers = cited_numbers(text)
    return Answer(
        question=question,
        text=text,
        refused=False,
        passages=passages,
        cited=[n for n in numbers if 1 <= n <= len(passages)],
        invalid_citations=[n for n in numbers if not 1 <= n <= len(passages)],
        trace=trace,
        llm_calls=llm_calls,
    )


def build_refusal(
    question: str, reason: str, passages: list[Chunk], trace: list[str], llm_calls: int
) -> Answer:
    return Answer(
        question=question,
        text=REFUSAL_MESSAGE,
        refused=True,
        passages=passages,
        trace=[*trace, f"decline: {reason}"],
        llm_calls=llm_calls,
    )
