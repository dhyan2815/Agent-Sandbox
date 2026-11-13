"""A rule-based stand-in for an LLM, so tests and the CI eval run with no key and no network.

It is extractive and deterministic: it answers by copying the passage sentence that best
matches the question, and judges relevance and support by word overlap. That is nowhere
near a real model, but it exercises every branch of the agent (retry, decline, self-check)
and makes the offline eval numbers reproducible to the digit.
"""

import json
import re

from hyper_rag.prompts import INSUFFICIENT, Prompt
from hyper_rag.text import STOPWORDS, coverage, split_sentences, strip_citations, tokenize

# Fraction of the question's content words a passage/sentence must contain to count as a match.
RELEVANT_THRESHOLD = 0.5
ANSWER_THRESHOLD = 0.6
SUPPORTED_THRESHOLD = 0.8


class FakeLLM:
    name = "fake:rule-based"

    def complete(self, prompt: Prompt) -> str:
        handler = getattr(self, f"_{prompt.task}")
        return handler(**prompt.inputs)

    def _route(self, question: str) -> str:
        return json.dumps({"route": "retrieve"})

    def _grade(self, question: str, passages: list) -> str:
        relevant = [
            number
            for number, passage in enumerate(passages, start=1)
            if coverage(question, passage.text) >= RELEVANT_THRESHOLD
        ]
        return json.dumps({"relevant": relevant})

    def _rewrite(self, question: str, tried: list[str]) -> str:
        # A keyword version of the question: drops the stopwords a dense retriever may latch onto.
        return " ".join(t for t in tokenize(question) if t not in STOPWORDS)

    def _generate(self, question: str, passages: list) -> str:
        best_score, best_sentence, best_number = 0.0, "", 0
        for number, passage in enumerate(passages, start=1):
            for sentence in split_sentences(passage.text):
                score = coverage(question, sentence)
                if score > best_score:
                    best_score, best_sentence, best_number = score, sentence, number
        if best_score < ANSWER_THRESHOLD:
            return INSUFFICIENT
        return f"{best_sentence} [{best_number}]"

    def _check(self, answer: str, passages: list) -> str:
        sources = " ".join(p.text for p in passages)
        for sentence in split_sentences(strip_citations(answer)):
            if coverage(sentence, sources) < SUPPORTED_THRESHOLD:
                return json.dumps({"grounded": False, "unsupported": sentence})
        return json.dumps({"grounded": True})

    def _judge(self, reference: str, answer: str) -> str:
        score = coverage(reference, answer)
        verdict = "correct" if score >= 0.6 else "partial" if score >= 0.3 else "incorrect"
        return json.dumps({"verdict": verdict})

    def _condense(self, history: list, question: str) -> str:
        # Carry the previous question along, so the follow-up keeps its subject.
        return f"{question} {history[-1][0]}" if history else question

    def _summarize(self, title: str, sections: list) -> str:
        # Extractive: the first sentence of each section's notes, after the chapter title.
        firsts = [split_sentences(text)[0] for text in sections if text and split_sentences(text)]
        return f"{title}. " + " ".join(firsts[:5])

    def _claims(self, text: str, max: int) -> str:
        # Every sentence of some length is a claim.
        sentences = [s for s in split_sentences(text) if len(s.split()) >= 4]
        return json.dumps({"claims": sentences[:max]})

    def _verify(self, items: list) -> str:
        verdicts = []
        for number, (claim, passages) in enumerate(items, start=1):
            best_score, best_index = 0.0, 0
            for index, passage in enumerate(passages, start=1):
                score = coverage(claim, passage.text)
                if score > best_score:
                    best_score, best_index = score, index
            verdict = "not_found"
            if best_score >= 0.5:
                # Mostly the same words but a figure that the passage does not contain.
                figures = set(re.findall(r"\d+(?:[.,]\d+)?", claim))
                passage_text = passages[best_index - 1].text
                missing = figures - set(re.findall(r"\d+(?:[.,]\d+)?", passage_text))
                if missing:
                    verdict = "contradicted"
                elif best_score >= SUPPORTED_THRESHOLD:
                    verdict = "supported"
            entry = {"claim": number, "verdict": verdict}
            if verdict != "not_found":
                entry["passage"] = best_index
            verdicts.append(entry)
        return json.dumps({"verdicts": verdicts})

    def _synthesize(self, passage) -> str:
        # The longest sentence of the passage body, turned into a question about itself.
        body = passage.text.split("\n", 1)[-1]
        sentences = [s for s in split_sentences(body) if not s.startswith("|")]
        if not sentences:
            return json.dumps({})
        sentence = max(sentences, key=len)
        words = sentence.rstrip(".!?").split()
        # The "fact" is the last few words: short and literal, as the prompt demands.
        return json.dumps(
            {
                "question": f"{' '.join(words)}?",
                "answer": sentence,
                "fact": " ".join(words[-3:]),
            }
        )
