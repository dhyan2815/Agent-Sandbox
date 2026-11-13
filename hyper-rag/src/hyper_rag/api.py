"""HTTP API and the web page.

    GET  /                                   the web UI
    POST /ask                                ask a built-in domain pack
    GET/POST   /collections                  list / create a collection of uploads
    POST       /collections/{c}/files        upload a document (parsed and indexed on arrival)
    POST       /collections/{c}/ask          answer with citations
    POST       /collections/{c}/ask/stream   the same, streamed step by step (server-sent events)
    GET        /collections/{c}/source       the page a citation points to, passage marked
    POST/GET   /collections/{c}/eval         start / read the auto-evaluation

Run with:  uvicorn hyper_rag.api:app
Set HYPER_RAG_OFFLINE=1 to serve with the fake LLM and hashing embedder (no key, no network).

There is no login: this is meant to run on your own machine. Do not expose it to a network
you do not trust; anyone who can reach it can read and delete the uploaded documents.
"""

import json
import os
import threading
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from hyper_rag.agent import Agent
from hyper_rag.config import Settings, load_settings
from hyper_rag.llm import LLM, LLMError, build_llm
from hyper_rag.packs import list_packs
from hyper_rag.parsing import SUPPORTED
from hyper_rag.service import build_agent
from hyper_rag.uploads import CollectionError, CollectionNotFound, CollectionStore

app = FastAPI(title="Hyper-RAG", version="0.2.0")


class Turn(BaseModel):
    question: str = Field(max_length=500)
    answer: str = Field(max_length=4000)


class AskRequest(BaseModel):
    pack: str = Field(examples=["payments"])
    question: str = Field(min_length=3, max_length=500)


class CollectionAskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    # Earlier turns of the conversation, oldest first. Only the last three are used.
    history: list[Turn] = Field(default_factory=list, max_length=20)


class Citation(BaseModel):
    number: int
    title: str
    url: str
    chunk_id: str
    doc_id: str
    text: str


class AskResponse(BaseModel):
    question: str
    answer: str
    refused: bool
    citations: list[Citation]
    trace: list[str]
    llm_calls: int


class NewCollection(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    description: str = Field(default="", max_length=500)


class EvalRequest(BaseModel):
    questions: int = Field(default=8, ge=2, le=30)
    judge: bool = False  # also run the LLM-judged metrics (uses the judge model's quota)
    agent: bool = True  # also answer with the full agent (about four LLM calls per question)
    regenerate: bool = False  # write new test questions even if a set exists


@lru_cache
def get_settings() -> Settings:
    return load_settings(offline=os.environ.get("HYPER_RAG_OFFLINE") == "1")


@lru_cache
def get_agent(pack: str) -> Agent:
    # Building an agent loads the index and the embedding model, so keep one per pack.
    return build_agent(pack, get_settings())


@lru_cache
def get_store() -> CollectionStore:
    return CollectionStore(get_settings())


@lru_cache
def get_llms() -> tuple[LLM, LLM]:
    settings = get_settings()
    return build_llm(settings, "generator"), build_llm(settings, "control")


def collection_agent(slug: str) -> Agent:
    # Cheap to build per request: the store caches the retriever until the files change.
    store = get_store()
    generator, control = get_llms()
    return Agent(
        retriever=store.retriever(slug),
        llm=generator,
        pack_description=store.description(slug),
        max_rewrites=get_settings().max_rewrites,
        control_llm=control,
        route=False,  # see Agent.__init__: the description of an upload is only a guess
    )


def _http_error(error: Exception) -> HTTPException:
    if isinstance(error, CollectionNotFound | FileNotFoundError):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, CollectionError):
        return HTTPException(status_code=400, detail=str(error))
    if isinstance(error, LLMError):  # provider down, rate limited or no key
        return HTTPException(status_code=503, detail=str(error))
    raise error


# --- page, health, configuration ---------------------------------------------------------


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/config")
def config() -> dict:
    """What the UI needs to know about this server."""
    settings = get_settings()
    offline = settings.llm_provider == "fake"
    return {
        "offline": offline,
        "generator": "rule-based stand-in (offline mode)" if offline else settings.llm_model,
        "ocr": settings.ocr,
        "max_upload_mb": settings.max_upload_mb,
        "extensions": sorted(SUPPORTED),
    }


# --- built-in domain packs ---------------------------------------------------------------


@app.get("/packs")
def packs() -> dict:
    return {"packs": list_packs(get_settings().packs_dir)}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> dict:
    try:
        return get_agent(request.pack).ask(request.question).to_dict()
    except (FileNotFoundError, LLMError) as error:  # unknown or un-ingested pack; provider
        raise _http_error(error) from error


# --- collections -------------------------------------------------------------------------


@app.get("/collections")
def collections() -> dict:
    return {"collections": get_store().all()}


@app.post("/collections", status_code=201)
def create_collection(request: NewCollection) -> dict:
    try:
        return get_store().create(request.name, request.description)
    except CollectionError as error:
        raise _http_error(error) from error


@app.get("/collections/{slug}")
def get_collection(slug: str) -> dict:
    try:
        return get_store().get(slug)
    except CollectionError as error:
        raise _http_error(error) from error


@app.delete("/collections/{slug}", status_code=204)
def delete_collection(slug: str) -> None:
    try:
        get_store().delete(slug)
    except CollectionError as error:
        raise _http_error(error) from error
    _eval_jobs.pop(slug, None)


# --- files -------------------------------------------------------------------------------


@app.post("/collections/{slug}/files", status_code=201)
def upload_file(slug: str, file: UploadFile) -> dict:
    """Upload one document. The reply is its record, including the parse report."""
    limit = get_settings().max_upload_mb * 1024 * 1024
    data = file.file.read(limit + 1)  # one byte past the limit is enough to know it is too big
    try:
        return get_store().add_file(slug, file.filename or "upload", data)
    except CollectionError as error:
        raise _http_error(error) from error


@app.delete("/collections/{slug}/files/{file_id}", status_code=204)
def delete_file(slug: str, file_id: str) -> None:
    try:
        get_store().remove_file(slug, file_id)
    except CollectionError as error:
        raise _http_error(error) from error


@app.get("/collections/{slug}/files/{file_id}")
def download_file(slug: str, file_id: str) -> FileResponse:
    try:
        record = get_store().file_record(slug, file_id)
        path = get_store().file_path(slug, file_id)
    except CollectionError as error:
        raise _http_error(error) from error
    # Only PDFs and images open in the browser. Everything else is sent as a download:
    # an uploaded HTML file must never be rendered as a page of this site.
    inline = record["kind"] in ("pdf", "image")
    return FileResponse(
        path,
        filename=record["name"],
        media_type="application/pdf" if record["kind"] == "pdf" else None,
        content_disposition_type="inline" if inline else "attachment",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@app.get("/collections/{slug}/files/{file_id}/preview/{unit}")
def preview(slug: str, file_id: str, unit: int) -> Response:
    try:
        data, media_type = get_store().preview(slug, file_id, unit)
    except CollectionError as error:
        raise _http_error(error) from error
    return Response(data, media_type=media_type, headers={"Cache-Control": "max-age=3600"})


@app.get("/collections/{slug}/source")
def source(slug: str, chunk_id: str) -> dict:
    """Where a cited passage came from: its page text with the cited sentences flagged."""
    try:
        return get_store().source(slug, chunk_id)
    except CollectionError as error:
        raise _http_error(error) from error


# --- asking ------------------------------------------------------------------------------


def _history(request: CollectionAskRequest) -> list[tuple[str, str]]:
    return [(turn.question, turn.answer) for turn in request.history]


@app.post("/collections/{slug}/ask", response_model=AskResponse)
def ask_collection(slug: str, request: CollectionAskRequest) -> dict:
    try:
        return collection_agent(slug).ask(request.question, _history(request)).to_dict()
    except (CollectionError, LLMError) as error:
        raise _http_error(error) from error


@app.post("/collections/{slug}/ask/stream")
def ask_collection_stream(slug: str, request: CollectionAskRequest) -> StreamingResponse:
    """Server-sent events: {"type": "step", "text": ...} per agent step, then one
    {"type": "answer", ...} (or {"type": "error", "detail": ...})."""
    try:
        agent = collection_agent(slug)
    except (CollectionError, LLMError) as error:
        raise _http_error(error) from error

    def events() -> Iterator[str]:
        try:
            for kind, payload in agent.ask_events(request.question, _history(request)):
                body = (
                    {"type": "step", "text": payload}
                    if kind == "step"
                    else {"type": "answer", **payload.to_dict()}
                )
                yield f"data: {json.dumps(body, ensure_ascii=False)}\n\n"
        except LLMError as error:
            yield f"data: {json.dumps({'type': 'error', 'detail': str(error)})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- auto-evaluation ---------------------------------------------------------------------

# One evaluation per collection at a time, run on a background thread because it takes
# minutes on a free tier. State is in memory: a restart forgets a running job, but the
# rows it finished are on disk and the next run resumes from them.
_eval_jobs: dict[str, dict] = {}
_eval_lock = threading.Lock()


def _run_eval(slug: str, request: EvalRequest) -> None:
    from hyper_rag.evaluation.synthetic import evaluate_collection

    job = _eval_jobs[slug]
    try:
        job["report"] = evaluate_collection(
            get_store(),
            slug,
            get_settings(),
            questions=request.questions,
            configs=("hybrid_rerank", "agent") if request.agent else ("hybrid_rerank",),
            use_judge=request.judge,
            regenerate=request.regenerate,
            on_progress=lambda line: job["log"].append(line.strip()),
        )
        job["state"] = "done"
    except Exception as error:  # report every failure to the UI instead of dying silently
        job["state"] = "failed"
        job["error"] = str(error)


@app.post("/collections/{slug}/eval", status_code=202)
def start_eval(slug: str, request: EvalRequest) -> dict:
    try:
        get_store().retriever(slug)  # fails now, with a clear message, if there is nothing to test
    except CollectionError as error:
        raise _http_error(error) from error
    with _eval_lock:
        if _eval_jobs.get(slug, {}).get("state") == "running":
            raise HTTPException(status_code=409, detail="An evaluation is already running.")
        _eval_jobs[slug] = {"state": "running", "log": [], "report": None, "error": None}
    threading.Thread(target=_run_eval, args=(slug, request), daemon=True).start()
    return {"state": "running"}


@app.get("/collections/{slug}/eval")
def read_eval(slug: str) -> dict:
    from hyper_rag.evaluation.synthetic import latest_report

    try:
        get_store().get(slug)
        saved = latest_report(get_store(), slug)
    except CollectionError as error:
        raise _http_error(error) from error
    job = _eval_jobs.get(slug)
    if job is None:
        return {"state": "idle", "log": [], "report": saved, "error": None}
    return {**job, "report": job["report"] or saved}
