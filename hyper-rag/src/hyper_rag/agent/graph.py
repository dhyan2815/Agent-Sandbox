"""The agent: a LangGraph state machine around retrieval and generation.

    (condense) -> route -> retrieve -> grade -> generate -> check -> done
                    |                  |  ^        |         |
                    |                  v  |        |         |
                    |               rewrite        |         |
                    v                  |           v         v
                 decline <-------------+-----------+---------+

"condense" only does anything in a conversation: it rewrites a follow-up question into
one that stands on its own before anything else sees it.

Each node is a small function from state to a partial state update. Every decision
the agent makes (in scope? relevant? grounded?) is a separate, cheap LLM call with a
JSON reply, so each one can be inspected in the trace and evaluated on its own.
"""

import time
from collections.abc import Iterator
from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from hyper_rag.agent.answer import Answer, build_answer, build_refusal
from hyper_rag.events import EventSink, elapsed_ms, emit
from hyper_rag.llm import LLM, complete_with_usage, parse_json
from hyper_rag.llm.http import QUOTA_FIELDS
from hyper_rag.prompts import (
    INSUFFICIENT,
    Prompt,
    check_prompt,
    condense_prompt,
    generate_prompt,
    grade_prompt,
    rewrite_prompt,
    route_prompt,
)
from hyper_rag.retrieval.retriever import Mode, Retriever
from hyper_rag.text import normalise_answer
from hyper_rag.types import Chunk


class AgentState(TypedDict, total=False):
    question: str  # what must be answered; for a follow-up, its standalone rewrite
    history: list[tuple[str, str]]  # earlier (question, answer) turns of the conversation
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
        route: bool = True,
    ):
        self.retriever = retriever
        self.llm = llm  # writes the answer
        # Makes the decisions (route, grade, rewrite, check). Defaults to the same model.
        self.control = control_llm or llm
        self.pack_description = pack_description
        self.max_rewrites = max_rewrites
        self.mode = mode
        # The router judges scope from a description of the corpus. A pack's description
        # is written by hand. An uploaded collection's is guessed from file names and
        # headings, and a router working from that guess declined a question whose
        # answer sat on a scanned page it could not know about. Collections therefore
        # skip routing: retrieval and grading decide, at the cost of more calls on
        # questions that really are out of scope.
        self.route = route
        self.graph = self._build_graph()

    # --- events -----------------------------------------------------------------

    @staticmethod
    def _sink(config: RunnableConfig | None) -> EventSink | None:
        # The sink travels in the run's config, not on self: a pack's agent is shared
        # by every request to that pack, so it must not hold one request's listener.
        return ((config or {}).get("configurable") or {}).get("on_event")

    @staticmethod
    def _call(llm: LLM, prompt: Prompt, sink: EventSink | None) -> tuple[str, dict]:
        """One model call, timed. Returns the reply and the fields every a.* event carries."""
        started = time.perf_counter()
        reply, usage = complete_with_usage(llm, prompt)
        fields = {"ms": elapsed_ms(started), "model": usage.get("model", llm.name)}
        for key in ("tokens_in", "tokens_out", "cached"):
            if usage.get(key) is not None:
                fields[key] = usage[key]
        limits = {key: usage[key] for key in QUOTA_FIELDS if key in usage}
        if limits:
            emit(sink, "llm.quota", model=fields["model"], **limits)
        return reply, fields

    # --- nodes ------------------------------------------------------------------

    def _condense(self, state: AgentState, config: RunnableConfig) -> dict:
        if not state.get("history"):
            return {}
        sink = self._sink(config)
        reply, call = self._call(
            self.control, condense_prompt(state["history"], state["question"]), sink
        )
        lines = reply.strip().strip('"').splitlines()
        standalone = lines[0].strip() if lines and lines[0].strip() else state["question"]
        emit(sink, "q.condense", standalone=standalone, **call)
        return {
            "question": standalone,
            "query": standalone,
            "trace": [*state["trace"], f"condense: '{standalone}'"],
            "llm_calls": state["llm_calls"] + 1,
        }

    def _route(self, state: AgentState, config: RunnableConfig) -> dict:
        sink = self._sink(config)
        raw, call = self._call(
            self.control, route_prompt(state["question"], self.pack_description), sink
        )
        reply = parse_json(raw)
        # Anything other than an explicit "decline" goes to retrieval: a wrong
        # "retrieve" costs one search, a wrong "decline" loses an answerable question.
        route = "decline" if reply.get("route") == "decline" else "retrieve"
        emit(sink, "a.route", route=route, **call)
        update = {
            "trace": [*state["trace"], f"route: {route}"],
            "llm_calls": state["llm_calls"] + 1,
        }
        if route == "decline":
            update["decline_reason"] = "question is outside this collection"
        return update

    def _retrieve(self, state: AgentState, config: RunnableConfig) -> dict:
        sink = self._sink(config)
        emit(sink, "a.retrieve", query=state["query"], attempt=len(state["tried"]) + 1)
        hits = self.retriever.retrieve(state["query"], mode=self.mode, on_event=sink)
        return {
            "candidates": [hit.chunk for hit in hits],
            "tried": [*state["tried"], state["query"]],
            "trace": [*state["trace"], f"retrieve: {len(hits)} passages for '{state['query']}'"],
        }

    def _grade(self, state: AgentState, config: RunnableConfig) -> dict:
        sink = self._sink(config)
        candidates = state["candidates"]
        # Passages are graded against the original question, not the rewritten query:
        # a rewrite can drift, and the question is what must be answered.
        raw, call = self._call(self.control, grade_prompt(state["question"], candidates), sink)
        numbers = parse_json(raw).get("relevant", [])
        kept = [
            candidates[n - 1] for n in numbers if isinstance(n, int) and 1 <= n <= len(candidates)
        ]
        kept_ids = {chunk.id for chunk in kept}
        emit(
            sink,
            "a.grade",
            kept=[chunk.id for chunk in kept],
            dropped=[chunk.id for chunk in candidates if chunk.id not in kept_ids],
            **call,
        )
        update = {
            "passages": kept,
            "trace": [*state["trace"], f"grade: {len(kept)} of {len(candidates)} relevant"],
            "llm_calls": state["llm_calls"] + 1,
        }
        if not kept and len(state["tried"]) > self.max_rewrites:
            update["decline_reason"] = "no relevant passages after rewriting the query"
        return update

    def _rewrite(self, state: AgentState, config: RunnableConfig) -> dict:
        sink = self._sink(config)
        reply, call = self._call(
            self.control, rewrite_prompt(state["question"], state["tried"]), sink
        )
        query = reply.strip().strip('"').splitlines()[0] if reply.strip() else state["question"]
        emit(sink, "a.rewrite", query=query, attempt=len(state["tried"]), **call)
        return {
            "query": query,
            "trace": [*state["trace"], f"rewrite: '{query}'"],
            "llm_calls": state["llm_calls"] + 1,
        }

    def _generate(self, state: AgentState, config: RunnableConfig) -> dict:
        sink = self._sink(config)
        reply, call = self._call(
            self.llm, generate_prompt(state["question"], state["passages"]), sink
        )
        draft = normalise_answer(reply)
        update = {"draft": draft, "llm_calls": state["llm_calls"] + 1}
        emit(sink, "a.generate", insufficient=INSUFFICIENT in draft, **call)
        if INSUFFICIENT in draft:
            update["decline_reason"] = "passages do not contain the answer"
            update["trace"] = [*state["trace"], "generate: insufficient context"]
        else:
            update["trace"] = [*state["trace"], "generate: drafted an answer"]
        return update

    def _check(self, state: AgentState, config: RunnableConfig) -> dict:
        sink = self._sink(config)
        raw, call = self._call(self.control, check_prompt(state["draft"], state["passages"]), sink)
        reply = parse_json(raw)
        # Only an explicit true passes. An unparseable reply counts as not grounded:
        # the check exists to stop unsupported answers, so it fails closed.
        grounded = reply.get("grounded") is True
        emit(sink, "a.check", grounded=grounded, **call)
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
        graph.add_node("condense", self._condense)
        graph.add_node("route", self._route)
        graph.add_node("retrieve", self._retrieve)
        graph.add_node("grade", self._grade)
        graph.add_node("rewrite", self._rewrite)
        graph.add_node("generate", self._generate)
        graph.add_node("check", self._check)

        graph.add_edge(START, "condense")
        graph.add_edge("condense", "route" if self.route else "retrieve")
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

    def ask_events(
        self, question: str, history: list[tuple[str, str]] | None = None
    ) -> Iterator[tuple[str, str | dict | Answer]]:
        """Run the agent, yielding as each node finishes its typed events ("event", dict,
        see hyper_rag.events) and then its trace line ("step", str), and ("answer", Answer)
        at the end. The web UI streams these; `ask` just drains them.

        The answer text itself is not streamed token by token: it is only shown once the
        groundedness check has passed, so a reader never sees a draft that is then withdrawn.
        """
        initial: AgentState = {
            "question": question,
            "query": question,
            "history": history or [],
            "tried": [],
            "trace": [],
            "llm_calls": 0,
        }
        final: AgentState = initial
        seen = 0
        # graph.stream yields a step only after its node has returned, so every event the
        # node emitted is in the list by then; hand them out in the order they happened.
        events: list[dict] = []
        config: RunnableConfig = {"configurable": {"on_event": events.append}}
        for final in self.graph.stream(initial, config=config, stream_mode="values"):
            for event in events:
                yield "event", event
            events.clear()
            for line in final["trace"][seen:]:
                yield "step", line
            seen = len(final["trace"])
        passages = final.get("passages", [])
        if final.get("decline_reason"):
            answer = build_refusal(
                question, final["decline_reason"], passages, final["trace"], final["llm_calls"]
            )
            yield "event", {"t": "a.decline", "reason": final["decline_reason"]}
            yield "step", answer.trace[-1]
        else:
            answer = build_answer(
                question, final["draft"], passages, final["trace"], final["llm_calls"]
            )
        yield "answer", answer

    def ask(self, question: str, history: list[tuple[str, str]] | None = None) -> Answer:
        for kind, payload in self.ask_events(question, history):
            if kind == "answer":
                return payload
        raise RuntimeError("the agent finished without an answer")  # unreachable
