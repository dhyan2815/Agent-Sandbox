"""Single-shot RAG: retrieve once, generate once. The non-agentic baseline in the ablation."""

from hyper_rag.agent.answer import Answer, build_answer, build_refusal
from hyper_rag.llm import LLM
from hyper_rag.prompts import INSUFFICIENT, generate_prompt
from hyper_rag.retrieval.retriever import Mode, Retriever
from hyper_rag.text import normalise_answer


def single_shot_answer(question: str, retriever: Retriever, llm: LLM, mode: Mode) -> Answer:
    passages = [hit.chunk for hit in retriever.retrieve(question, mode=mode)]
    trace = [f"retrieve[{mode}]: {len(passages)} passages"]
    # Same generation prompt as the agent, so the ablation isolates retrieval and control
    # flow rather than prompt wording.
    reply = normalise_answer(llm.complete(generate_prompt(question, passages)))
    if INSUFFICIENT in reply:
        return build_refusal(question, "generator found no answer", passages, trace, 1)
    return build_answer(question, reply, passages, [*trace, "generate: answered"], 1)
