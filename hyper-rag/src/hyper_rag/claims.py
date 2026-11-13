"""Claim checker (deck card D4): paste a draft, see which claims your documents support.

    text --split--> claims --retrieve (local)--> top passages per claim --verify--> verdicts

Costs two kinds of model call and no more: one to split the text into claims, and one per
batch of four claims to judge them. Retrieval is the same hybrid search the chat uses and
runs on the machine. The verdicts are the model's reading of the passages, and the page
always shows the passage next to each verdict, so it can be read and overruled.

The check fails closed in the same way the agent's self-check does: a claim only counts as
supported or contradicted if the model names a passage that exists. Anything else, such as a
missing verdict or a made-up passage number, is "not_found", which means "your documents do
not settle this", never "this is true".
"""

from dataclasses import dataclass, field

from hyper_rag.llm import LLM, parse_json
from hyper_rag.llm.base import complete_with_usage
from hyper_rag.prompts import claims_prompt, verify_claims_prompt
from hyper_rag.text import split_sentences
from hyper_rag.types import Chunk

VERDICTS = ("supported", "contradicted", "not_found")
MAX_CLAIMS = 10
PASSAGES_PER_CLAIM = 3
CLAIMS_PER_CALL = 4  # keeps one verify call near 3,000 tokens: Groq's free minute allows 8,000


@dataclass
class CheckedClaim:
    text: str
    verdict: str
    evidence: Chunk | None = None  # the passage that decides a supported or contradicted claim
    closest: Chunk | None = None  # the best match for a not_found claim, to look at yourself

    def to_dict(self) -> dict:
        def passage(chunk: Chunk | None) -> dict | None:
            if chunk is None:
                return None
            return {
                "title": chunk.title,
                "url": chunk.url,
                "chunk_id": chunk.id,
                "doc_id": chunk.doc_id,
                "text": chunk.text,
            }

        return {
            "claim": self.text,
            "verdict": self.verdict,
            "evidence": passage(self.evidence),
            "closest": passage(self.closest),
        }


@dataclass
class ClaimReport:
    claims: list[CheckedClaim] = field(default_factory=list)
    llm_calls: int = 0
    truncated: bool = False  # the text had more claims than MAX_CLAIMS

    def summary(self) -> dict:
        return {v: sum(c.verdict == v for c in self.claims) for v in VERDICTS}

    def to_dict(self) -> dict:
        return {
            "claims": [c.to_dict() for c in self.claims],
            "summary": self.summary(),
            "llm_calls": self.llm_calls,
            "truncated": self.truncated,
        }


def split_claims(llm: LLM, text: str, limit: int = MAX_CLAIMS) -> tuple[list[str], int, bool]:
    """The claims in `text`. Falls back to its sentences if the model's reply is unusable.

    Returns (claims, model calls made, whether the list was cut at `limit`).
    """
    # Ask for one more than the limit: a model told "at most 10" never shows that an eleventh
    # claim existed, and the page must say when part of a text was left unchecked.
    reply = parse_json(complete_with_usage(llm, claims_prompt(text, limit + 1))[0])
    raw = reply.get("claims")
    claims = [c.strip() for c in raw if isinstance(c, str) and c.strip()] if raw else []
    if not claims:
        claims = [s for s in split_sentences(text) if len(s.split()) >= 4]
    seen: set[str] = set()
    unique = [c for c in claims if not (c.lower() in seen or seen.add(c.lower()))]
    return unique[:limit], 1, len(unique) > limit


def _verdict_of(entry: object, passages: list[Chunk]) -> tuple[str, Chunk | None]:
    """One verdict, accepted only if it is well formed and names a passage that exists."""
    if not isinstance(entry, dict):
        return "not_found", None
    verdict = entry.get("verdict")
    if verdict not in VERDICTS or verdict == "not_found":
        return "not_found", None
    number = entry.get("passage")
    if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= len(passages):
        return "not_found", None  # a verdict with nothing to point at does not count
    return verdict, passages[number - 1]


def check_claims(retriever, llm: LLM, text: str, max_claims: int = MAX_CLAIMS) -> ClaimReport:
    """Check every claim in `text` against the collection behind `retriever`."""
    report = ClaimReport()
    claims, calls, report.truncated = split_claims(llm, text, max_claims)
    report.llm_calls += calls
    found = [
        (claim, [hit.chunk for hit in retriever.retrieve(claim, top_k=PASSAGES_PER_CLAIM)])
        for claim in claims
    ]
    for start in range(0, len(found), CLAIMS_PER_CALL):
        batch = found[start : start + CLAIMS_PER_CALL]
        askable = [(claim, passages) for claim, passages in batch if passages]
        verdicts = []
        if askable:
            reply = parse_json(complete_with_usage(llm, verify_claims_prompt(askable))[0])
            report.llm_calls += 1
            verdicts = reply.get("verdicts") if isinstance(reply.get("verdicts"), list) else []
        by_number = {v.get("claim"): v for v in verdicts if isinstance(v, dict) and "claim" in v}
        position = 0
        for claim, passages in batch:
            if not passages:  # an empty collection or no hits: nothing to check against
                report.claims.append(CheckedClaim(claim, "not_found"))
                continue
            position += 1
            verdict, evidence = _verdict_of(by_number.get(position), passages)
            report.claims.append(
                CheckedClaim(
                    claim,
                    verdict,
                    evidence=evidence,
                    closest=passages[0] if verdict == "not_found" else None,
                )
            )
    return report
