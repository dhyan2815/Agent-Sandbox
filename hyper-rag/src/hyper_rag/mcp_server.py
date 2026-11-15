"""Hyper-RAG as an MCP server (deck card D1): ask your documents from Claude Code, Gemini CLI
or n8n.

    hyper-rag mcp                                  your collections on this machine
    hyper-rag mcp --remote https://you-hyper-rag.hf.space    a deployed Hyper-RAG

Five tools, over stdio:

    list_collections   what there is to ask
    search             the best passages for a query, with scores. No model call, so free.
    ask                a cited answer, from the same agent the web page uses
    get_source         the page a citation points to, with the cited sentences marked
    check_claims       each claim in a text: supported, contradicted or not found

Local mode reads the same data folder and settings as the web app. Remote mode talks to a
deployed app's HTTP API and logs in with the password in HYPER_RAG_REMOTE_PASSWORD (an
environment variable, so it never lands in shell history or a process list).

`search`, `get_source` and `list_collections` only read. `ask` and `check_claims` spend model
requests, which on a host count toward its hourly limit.
"""

import os
from typing import Any, Protocol

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from hyper_rag import claims
from hyper_rag.agent import Agent
from hyper_rag.config import Settings
from hyper_rag.llm import LLMError, build_llm
from hyper_rag.structure import PassagesOnly
from hyper_rag.uploads import CollectionError, CollectionStore

PASSAGE_CHARS = 1200  # a tool result goes into a model's context: keep passages short
MAX_TOP_K = 10


class Backend(Protocol):
    def list_collections(self) -> list[dict]: ...
    def search(self, collection: str, query: str, top_k: int) -> list[dict]: ...
    def ask(self, collection: str, question: str) -> dict: ...
    def get_source(self, collection: str, chunk_id: str) -> dict: ...
    def check_claims(self, collection: str, text: str) -> dict: ...


def _short(text: str) -> str:
    return text if len(text) <= PASSAGE_CHARS else text[:PASSAGE_CHARS].rsplit(" ", 1)[0] + " …"


def _passage(chunk, score: float | None = None) -> dict:
    found = {"chunk_id": chunk.id, "title": chunk.title, "text": _short(chunk.text)}
    if score is not None:
        found["score"] = round(float(score), 4)
    return found


def _answer(body: dict) -> dict:
    """What `ask` returns, from either backend's answer dict."""
    out = {
        "answer": body["answer"],
        "declined": body["refused"],
        "citations": [
            {
                "number": c["number"],
                "title": c["title"],
                "chunk_id": c["chunk_id"],
                "text": _short(c["text"]),
            }
            for c in body["citations"]
        ],
    }
    if body.get("reading"):
        out["note"] = "Some files are still being read, so only part of them was searched."
    return out


def _lines(source: dict) -> str:
    """A source page as text, the cited sentences wrapped in ** **."""
    rows = []
    for line in source["lines"]:
        rows.append(" ".join(f"**{s['text']}**" if s["hit"] else s["text"] for s in line))
    return "\n".join(rows)


class LocalBackend:
    """Collections on this machine, answered by the same engine as the web app."""

    def __init__(self, settings: Settings, store: CollectionStore | None = None):
        self.settings = settings
        self.store = store or CollectionStore(settings)
        self._llms = None

    def _agent(self, slug: str) -> Agent:
        if self._llms is None:
            self._llms = build_llm(self.settings, "generator"), build_llm(self.settings, "control")
        generator, control = self._llms
        return Agent(
            retriever=PassagesOnly(self.store.retriever(slug)),
            llm=generator,
            pack_description=self.store.description(slug),
            max_rewrites=self.settings.max_rewrites,
            control_llm=control,
            route=False,
        )

    def list_collections(self) -> list[dict]:
        return [
            {
                "slug": c["slug"],
                "name": c["name"],
                "files": [f["name"] for f in c["files"]],
                "passages": sum(f.get("chunks", 0) for f in c["files"]),
            }
            for c in self.store.all()
        ]

    def search(self, collection: str, query: str, top_k: int) -> list[dict]:
        hits = PassagesOnly(self.store.retriever(collection)).retrieve(query, top_k=top_k)
        return [_passage(h.chunk, h.score) for h in hits]

    def ask(self, collection: str, question: str) -> dict:
        body = self._agent(collection).ask(question).to_dict()
        body["reading"] = self.store.coverage(collection)
        return body

    def get_source(self, collection: str, chunk_id: str) -> dict:
        return self.store.source(collection, chunk_id)

    def check_claims(self, collection: str, text: str) -> dict:
        retriever = PassagesOnly(self.store.retriever(collection))
        if self._llms is None:
            self._llms = build_llm(self.settings, "generator"), build_llm(self.settings, "control")
        return claims.check_claims(retriever, self._llms[1], text).to_dict()


class RemoteBackend:
    """A deployed Hyper-RAG, over its HTTP API."""

    def __init__(
        self, url: str, password: str = "", client: httpx.Client | None = None, timeout: float = 120
    ):
        self.http = client or httpx.Client(base_url=url.rstrip("/"), timeout=timeout)
        self.password = password
        self._logged_in = False

    def _login(self) -> None:
        if self._logged_in or not self.password:
            return
        response = self.http.post(
            "/login", data={"password": self.password}, follow_redirects=False
        )
        if response.status_code == 401:
            raise ValueError(
                "The remote Hyper-RAG refused the password in HYPER_RAG_REMOTE_PASSWORD."
            )
        if response.status_code == 429:
            raise ValueError("The remote Hyper-RAG has blocked logins for now. Try again later.")
        self._logged_in = True

    def _call(self, method: str, path: str, **kwargs):
        self._login()
        response = self.http.request(method, path, follow_redirects=False, **kwargs)
        if response.status_code == 401:
            self._logged_in = False  # the session ended: log in once more
            self._login()
            response = self.http.request(method, path, follow_redirects=False, **kwargs)
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise ValueError(f"The remote Hyper-RAG said {response.status_code}: {detail}")
        return response.json()

    def list_collections(self) -> list[dict]:
        found = self._call("GET", "/collections")["collections"]
        return [
            {
                "slug": c["slug"],
                "name": c["name"],
                "files": [f["name"] for f in c["files"]],
                "passages": sum(f.get("chunks", 0) for f in c["files"]),
            }
            for c in found
        ]

    def search(self, collection: str, query: str, top_k: int) -> list[dict]:
        return self._call(
            "GET", f"/collections/{collection}/search", params={"q": query, "k": top_k}
        )["passages"]

    def ask(self, collection: str, question: str) -> dict:
        return self._call("POST", f"/collections/{collection}/ask", json={"question": question})

    def get_source(self, collection: str, chunk_id: str) -> dict:
        return self._call("GET", f"/collections/{collection}/source", params={"chunk_id": chunk_id})

    def check_claims(self, collection: str, text: str) -> dict:
        return self._call("POST", f"/collections/{collection}/check", json={"text": text})


def build_server(backend: Backend) -> FastMCP:
    server = FastMCP(
        "hyper-rag",
        instructions=(
            "Answers questions from the user's own uploaded documents, with citations. Call "
            "list_collections first to see what exists. Prefer search when you only need "
            "passages; use ask for a written answer. Quote and cite what comes back; if an "
            "answer is declined, the documents do not support one, so say so."
        ),
    )
    # Return types are spelled dict[str, Any]: a bare dict gives the client text only, while
    # a parameterised one also carries the result as structured content.
    read_only = ToolAnnotations(readOnlyHint=True, openWorldHint=False)

    def guarded(call):
        """Turn the engine's expected failures into messages the model can read."""
        try:
            return call()
        except (CollectionError, LLMError, ValueError, httpx.HTTPError) as error:
            raise ValueError(str(error)) from error

    @server.tool(annotations=read_only)
    def list_collections() -> list[dict[str, Any]]:
        """List the document collections: slug, name, file names and how many passages."""
        return guarded(backend.list_collections)

    @server.tool(annotations=read_only)
    def search(collection: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Find the best passages for a query in a collection. Returns chunk_id, title, text
        and a relevance score, best first. Uses no model, so it is the cheap way to look."""
        k = max(1, min(top_k, MAX_TOP_K))
        return guarded(lambda: backend.search(collection, query, k))

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
    def ask(collection: str, question: str) -> dict[str, Any]:
        """Ask a question of a collection. Returns the answer, whether it was declined, and
        the cited passages. A declined answer means the documents do not contain one."""
        return _answer(guarded(lambda: backend.ask(collection, question)))

    @server.tool(annotations=read_only)
    def get_source(collection: str, chunk_id: str) -> dict[str, Any]:
        """Open the page a citation points to. The cited sentences are wrapped in ** **."""
        source = guarded(lambda: backend.get_source(collection, chunk_id))
        return {
            "file": source["file_name"],
            "location": source["unit_label"] or "whole file",
            "read_by_ocr": source["read_by_ocr"],
            "text": _lines(source),
        }

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
    def check_claims(collection: str, text: str) -> dict[str, Any]:
        """Check each factual claim in a text against a collection. Every claim comes back
        supported, contradicted or not_found (the documents do not settle it), with the
        deciding passage. Text must be 20 to 4000 characters."""
        if not 20 <= len(text) <= 4000:
            raise ValueError("The text must be between 20 and 4000 characters.")
        return guarded(lambda: backend.check_claims(collection, text))

    return server


def run(settings: Settings, remote: str = "") -> None:
    """Serve over stdio until the client disconnects."""
    if remote:
        backend: Backend = RemoteBackend(remote, os.environ.get("HYPER_RAG_REMOTE_PASSWORD", ""))
    else:
        backend = LocalBackend(settings)
    build_server(backend).run("stdio")
