"""The agent: a LangGraph state machine around retrieval and generation.

    route -> retrieve -> grade -> generate -> check -> done
       |                  |  ^        |         |
       |                  v  |        |         |
       |               rewrite        |         |
       v                  |           v         v
    decline <-------------+-----------+---------+

Each node is a small function from state to a partial state update. Every decision
the agent makes (in scope? relevant? grounded?) is a separate, cheap LLM call with a
JSON reply, so each one can be inspected in the trace and evaluated on its own.
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from hyper_rag.agent.answer import Answer, build_answer, build_refusal
from hyper_rag.llm import LLM, parse_json
from hyper_rag.prompts import (
    INSUFFICIENT,
    check_prompt,
    generate_prompt,
    grade_prompt,
    rewrite_prompt,
    route_prompt,
)
from hyper_rag.retrieval.retriever import Mode, Retriever
from hyper_rag.text import normalise_answer
from hyper_rag.types import Chunk


class AgentState(TypedDict, total=False):
    question: str
    query: str  # the current search query: the question at first, then rewrites
    tried: list[str]  # every query searched so far
    candidates: list[Chunk]  # what retrieval returned for the current query
    passages: list[Chunk]  # the candidates the grader kept; these are what gets cited
    draft: str  # the generator's reply
    decline_reason: str  # set by whichever node decides to stop
    trace: list[str]
    llm_calls: int


class Agent:
    def __init__(
        self,
        retriever: Retriever,
        llm: LLM,
        pack_description: str,
        max_rewrites: int = 2,
        mode: Mode = "hybrid_rerank",
        control_llm: LLM | None = None,
    ):
        self.retriever = retriever
        self.llm = llm  # writes the answer
        # Makes the decisions (route, grade, rewrite, check). Defaults to the same model.
        self.control = control_llm or llm
        self.pack_description = pack_description
        self.max_rewrites = max_rewrites
        self.mode = mode
        self.graph = self._build_graph()

    # --- nodes ------------------------------------------------------------------

    def _route(self, state: AgentState) -> dict:
        reply = parse_json(
            self.control.complete(route_prompt(state["question"], self.pack_description))
        )
        # Anything other than an explicit "decline" goes to retrieval: a wrong
        # "retrieve" costs one search, a wrong "decline" loses an answerable question.
        route = "decline" if reply.get("route") == "decline" else "retrieve"
        update = {
            "trace": [*state["trace"], f"route: {route}"],
            "llm_calls": state["llm_calls"] + 1,
        }
        if route == "decline":
            update["decline_reason"] = "question is outside this collection"
        return update

    def _retrieve(self, state: AgentState) -> dict:
        hits = self.retriever.retrieve(state["query"], mode=self.mode)
        return {
            "candidates": [hit.chunk for hit in hits],
            "tried": [*state["tried"], state["query"]],
            "trace": [*state["trace"], f"retrieve: {len(hits)} passages for '{state['query']}'"],
        }

    def _grade(self, state: AgentState) -> dict:
        candidates = state["candidates"]
        # Passages are graded against the original question, not the rewritten query:
        # a rewrite can drift, and the question is what must be answered.
        reply = parse_json(self.control.complete(grade_prompt(state["question"], candidates)))
        numbers = reply.get("relevant", [])
        kept = [
            candidates[n - 1] for n in numbers if isinstance(n, int) and 1 <= n <= len(candidates)
        ]
        update = {
            "passages": kept,
            "trace": [*state["trace"], f"grade: {len(kept)} of {len(candidates)} relevant"],
            "llm_calls": state["llm_calls"] + 1,
        }
        if not kept and len(state["tried"]) > self.max_rewrites:
            update["decline_reason"] = "no relevant passages after rewriting the query"
        return update

    def _rewrite(self, state: AgentState) -> dict:
        reply = self.control.complete(rewrite_prompt(state["question"], state["tried"]))
        query = reply.strip().strip('"').splitlines()[0] if reply.strip() else state["question"]
        return {
            "query": query,
            "trace": [*state["trace"], f"rewrite: '{query}'"],
            "llm_calls": state["llm_calls"] + 1,
        }

    def _generate(self, state: AgentState) -> dict:
        draft = normalise_answer(
            self.llm.complete(generate_prompt(state["question"], state["passages"]))
        )
        update = {"draft": draft, "llm_calls": state["llm_calls"] + 1}
        if INSUFFICIENT in draft:
            update["decline_reason"] = "passages do not contain the answer"
            update["trace"] = [*state["trace"], "generate: insufficient context"]
        else:
            update["trace"] = [*state["trace"], "generate: drafted an answer"]
        return update

    def _check(self, state: AgentState) -> dict:
        reply = parse_json(self.control.complete(check_prompt(state["draft"], state["passages"])))
        # Only an explicit true passes. An unparseable reply counts as not grounded:
        # the check exists to stop unsupported answers, so it fails closed.
        grounded = reply.get("grounded") is True
        update = {
            "trace": [*state["trace"], f"check: {'grounded' if grounded else 'not grounded'}"],
            "llm_calls": state["llm_calls"] + 1,
        }
        if not grounded:
            claim = str(reply.get("unsupported", "")).strip()
            update["decline_reason"] = "draft answer was not supported by the sources" + (
                f" ({claim})" if claim else ""
            )
        return update

    # --- edges ------------------------------------------------------------------

    @staticmethod
    def _after_route(state: AgentState) -> str:
        return "decline" if state.get("decline_reason") else "retrieve"

    @staticmethod
    def _after_grade(state: AgentState) -> str:
        if state["passages"]:
            return "generate"
        return "decline" if state.get("decline_reason") else "rewrite"

    @staticmethod
    def _after_generate(state: AgentState) -> str:
        return "decline" if state.get("decline_reason") else "check"

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("route", self._route)
        graph.add_node("retrieve", self._retrieve)
        graph.add_node("grade", self._grade)
        graph.add_node("rewrite", self._rewrite)
        graph.add_node("generate", self._generate)
        graph.add_node("check", self._check)

        graph.add_edge(START, "route")
        graph.add_conditional_edges(
            "route", self._after_route, {"retrieve": "retrieve", "decline": END}
        )
        graph.add_edge("retrieve", "grade")
        graph.add_conditional_edges(
            "grade",
            self._after_grade,
            {"generate": "generate", "rewrite": "rewrite", "decline": END},
        )
        graph.add_edge("rewrite", "retrieve")
        graph.add_conditional_edges(
            "generate", self._after_generate, {"check": "check", "decline": END}
        )
        graph.add_edge("check", END)
        return graph.compile()

    # --- entry point ------------------------------------------------------------

    def ask(self, question: str) -> Answer:
        final: AgentState = self.graph.invoke(
            {"question": question, "query": question, "tried": [], "trace": [], "llm_calls": 0}
        )
        passages = final.get("passages", [])
        if final.get("decline_reason"):
            return build_refusal(
                question, final["decline_reason"], passages, final["trace"], final["llm_calls"]
            )
        return build_answer(question, final["draft"], passages, final["trace"], final["llm_calls"])
