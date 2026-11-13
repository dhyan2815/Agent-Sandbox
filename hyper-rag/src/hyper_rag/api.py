"""HTTP API and the web page.

    GET  /                                   the web UI (the React app if built, else /classic)
    POST /ask                                ask a built-in domain pack
    GET/POST   /collections                  list / create a collection of uploads
    POST       /collections/{c}/files        upload a small document (read before the reply)
    POST       /collections/{c}/uploads      start a resumable upload (big files; see background.py)
    PUT/GET    /collections/{c}/uploads/{id} send a part at ?offset= / ask how much arrived
    POST       /collections/{c}/uploads/{id}/complete   finish it; reading runs in the background
    GET        /collections/{c}/files/{id}/events      reading progress (server-sent events)
    GET        /collections/{c}/files/{id}/pages       per-page route and progress (page grid)
    POST       /collections/{c}/ask          answer with citations
    POST       /collections/{c}/ask/stream   the same, streamed: typed events, steps, the answer
    GET        /collections/{c}/runs         saved event logs of recent answers (for replay)
    GET        /collections/{c}/runs/{id}    one saved run: every event and the answer
    GET        /collections/{c}/source       the page a citation points to, passage marked
    POST/GET   /collections/{c}/eval         start / read the auto-evaluation
    GET/POST   /login, POST /logout          single-user login (only when a password is set)

Run with:  uvicorn hyper_rag.api:app
Set HYPER_RAG_OFFLINE=1 to serve with the fake LLM and hashing embedder (no key, no network).

Login is off unless HYPER_RAG_PASSWORD is set. Without it, anyone who can reach the app can
read and delete the uploaded documents, which is fine on your own machine and nowhere else.
"""

import asyncio
import json
import os
import shutil
import threading
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, RedirectResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from hyper_rag import auth
from hyper_rag.agent import Agent, Answer
from hyper_rag.background import IngestWorker, OffsetMismatch, UploadSessions
from hyper_rag.config import Settings, load_settings
from hyper_rag.llm import LLM, LLMError, build_llm
from hyper_rag.packs import list_packs
from hyper_rag.parsing import SUPPORTED
from hyper_rag.service import build_agent
from hyper_rag.stores import JobStore, build_job_store
from hyper_rag.uploads import CollectionError, CollectionNotFound, CollectionStore


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Files a previous run left half-read are picked up again, from their last window.
    await run_in_threadpool(lambda: get_worker().resume())
    yield
    get_worker().shutdown()


app = FastAPI(title="Hyper-RAG", version="0.3.0", lifespan=lifespan)


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
    run_id: str | None = None  # collections only: the saved events, at /runs/{run_id}
    # Files still being read when the question was asked: the answer only searched what
    # had been read so far (pages_done of pages_total).
    reading: list[dict] = Field(default_factory=list)


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
def get_jobs() -> JobStore:
    return build_job_store(get_settings())


@lru_cache
def get_worker() -> IngestWorker:
    return IngestWorker(get_store(), get_jobs(), get_settings().ingest_workers)


@lru_cache
def get_uploads() -> UploadSessions:
    return UploadSessions(get_store(), get_settings().data_dir / "incoming" / "resumable")


class NewUpload(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    size: int = Field(gt=0)


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


# --- login -------------------------------------------------------------------------------


@app.middleware("http")
async def login_required(request: Request, call_next):
    refusal = auth.require_login(request, get_settings().password)
    return refusal if refusal is not None else await call_next(request)


@app.get("/login", include_in_schema=False)
def login_form(request: Request) -> Response:
    settings = get_settings()
    if not settings.password or auth.valid_token(
        settings.password, request.cookies.get(auth.COOKIE)
    ):
        return RedirectResponse("/", status_code=303)
    return auth.login_page()


@app.post("/login", include_in_schema=False)
def login(request: Request, password: str = Form(default="", max_length=200)) -> Response:
    settings = get_settings()
    return auth.login(request, settings.password, password, settings.session_days)


@app.post("/logout", include_in_schema=False)
def logout() -> Response:
    return auth.logout()


# --- page, health, configuration ---------------------------------------------------------


CLASSIC_PAGE = Path(__file__).parent / "static" / "index.html"


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """The React app when it has been built (web/dist), otherwise the classic page.

    The build is made by `npm run build` in web/, by the Dockerfile and by CI; it is not
    committed. Without it, a plain `pip install` still serves a complete UI.
    """
    built = get_settings().ui_dir / "index.html"
    return FileResponse(built if built.is_file() else CLASSIC_PAGE)


@app.get("/classic", include_in_schema=False)
def classic() -> FileResponse:
    """Today's single-file page, kept until the React app has replaced it everywhere."""
    return FileResponse(CLASSIC_PAGE)


@app.get("/assets/{name}", include_in_schema=False)
def asset(name: str) -> FileResponse:
    """The React app's bundled scripts and styles. Their names carry a content hash."""
    folder = (get_settings().ui_dir / "assets").resolve()
    path = (folder / name).resolve()
    if path.parent != folder or not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=31536000, immutable"})


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
        "login": bool(settings.password),
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
    get_jobs().forget("eval", slug)
    # The evaluation's working files live in a local folder whatever the blob store is.
    shutil.rmtree(get_store().path(slug), ignore_errors=True)


# --- files -------------------------------------------------------------------------------


@app.post("/collections/{slug}/files", status_code=201)
def upload_file(slug: str, file: UploadFile) -> dict:
    """Upload one small document. The reply is its record, including the parse report.

    The upload is copied to disk in blocks, never held in memory whole; a file over the
    direct-upload limit is refused before it is read. Big files use /uploads instead.
    """
    store = get_store()
    limit = get_settings().max_upload_mb * 1024 * 1024
    name = file.filename or "upload"
    try:
        store.get(slug)
        too_big = CollectionError(
            f"'{Path(name).name}' is larger than the {get_settings().max_upload_mb} MB "
            "direct upload limit. Larger files are sent in parts (resumable upload)."
        )
        if file.size is not None and file.size > limit:
            raise too_big
        path = store.incoming_path()
        with path.open("wb") as handle:
            copied = 0
            while block := file.file.read(1024 * 1024):
                copied += len(block)
                if copied > limit:
                    break
                handle.write(block)
        if copied > limit:
            path.unlink(missing_ok=True)
            raise too_big
        return store.add_path(slug, name, path)
    except CollectionError as error:
        raise _http_error(error) from error


@app.post("/collections/{slug}/uploads", status_code=201)
def start_upload(slug: str, request: NewUpload) -> dict:
    try:
        return get_uploads().create(slug, request.name, request.size)
    except CollectionError as error:
        raise _http_error(error) from error


@app.get("/collections/{slug}/uploads/{upload_id}")
def upload_status(slug: str, upload_id: str) -> dict:
    try:
        return get_uploads().status(slug, upload_id)
    except CollectionError as error:
        raise _http_error(error) from error


@app.put("/collections/{slug}/uploads/{upload_id}")
async def upload_part(
    slug: str, upload_id: str, request: Request, offset: int = Query(ge=0)
) -> Response:
    """Append the next part. 409 with the expected offset if it does not follow on."""
    limit = get_uploads().part_size
    declared = request.headers.get("content-length")
    if declared is not None and int(declared) > limit:
        raise HTTPException(status_code=413, detail="This part is larger than allowed.")
    body = await request.body()  # one part, at most upload_part_mb
    try:
        status = await run_in_threadpool(get_uploads().append, slug, upload_id, offset, [body])
    except OffsetMismatch as error:
        return Response(
            json.dumps({"detail": str(error), "received": error.received}),
            status_code=409,
            media_type="application/json",
        )
    except CollectionError as error:
        raise _http_error(error) from error
    return Response(json.dumps(status), media_type="application/json")


@app.post("/collections/{slug}/uploads/{upload_id}/complete", status_code=202)
def complete_upload(slug: str, upload_id: str) -> dict:
    """The file is stored and listed as "queued"; reading it runs in the background."""
    try:
        record = get_uploads().complete(slug, upload_id)
    except CollectionError as error:
        raise _http_error(error) from error
    if not record.get("duplicate"):
        get_worker().submit(slug, record["id"])
    return record


@app.get("/collections/{slug}/files/{file_id}/pages")
def file_pages(slug: str, file_id: str) -> dict:
    try:
        return get_store().pages(slug, file_id)
    except CollectionError as error:
        raise _http_error(error) from error


@app.get("/collections/{slug}/files/{file_id}/events")
async def file_events(slug: str, file_id: str) -> StreamingResponse:
    """Server-sent events while a file is read: its record each time it changes, until
    it is ready or failed. {"type": "progress", ...record} then {"type": "end", ...}."""
    store = get_store()
    try:
        store.file_record(slug, file_id)
    except CollectionError as error:
        raise _http_error(error) from error

    async def events() -> AsyncIterator[str]:
        last = None
        while True:
            try:
                record = await run_in_threadpool(store.file_record, slug, file_id)
            except CollectionError:
                yield f"data: {json.dumps({'type': 'end', 'status': 'removed'})}\n\n"
                return
            seen = (record.get("status"), record.get("pages_done"), record.get("windows_done"))
            if seen != last:
                last = seen
                yield f"data: {json.dumps({'type': 'progress', **record})}\n\n"
            if record.get("status") in ("ready", "failed"):
                yield f"data: {json.dumps({'type': 'end', 'status': record['status']})}\n\n"
                return
            await asyncio.sleep(0.5)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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


def _answer_events(
    slug: str, agent: Agent, request: CollectionAskRequest
) -> Iterator[tuple[str, str | dict]]:
    """Run the agent and save its run. Yields ("event", dict), ("step", str), and last
    ("answer", the answer's dict with its run_id)."""
    events: list[dict] = []
    reading = get_store().coverage(slug)
    if reading:
        # Honest about a half-read collection: only the pages read so far were searched.
        coverage = {"t": "q.coverage", "reading": reading}
        events.append(coverage)
        yield "event", coverage
    for kind, payload in agent.ask_events(request.question, _history(request)):
        if kind == "event":
            events.append(payload)
            yield kind, payload
        elif kind == "step":
            yield kind, payload
        else:
            assert isinstance(payload, Answer)
            body = payload.to_dict()
            body["reading"] = reading
            body["run_id"] = get_store().save_run(slug, {"answer": body, "events": events})
            yield "answer", body


@app.post("/collections/{slug}/ask", response_model=AskResponse)
def ask_collection(slug: str, request: CollectionAskRequest) -> dict:
    try:
        agent = collection_agent(slug)
        for kind, payload in _answer_events(slug, agent, request):
            if kind == "answer":
                return payload
    except (CollectionError, LLMError) as error:
        raise _http_error(error) from error
    raise RuntimeError("the agent finished without an answer")  # unreachable


@app.post("/collections/{slug}/ask/stream")
def ask_collection_stream(slug: str, request: CollectionAskRequest) -> StreamingResponse:
    """Server-sent events, one JSON object each:

    {"type": "event", "t": "r.rerank", ...}   typed engine events (hyper_rag.events)
    {"type": "step", "text": ...}             one trace line per agent step
    {"type": "answer", ..., "run_id": ...}    last; the run is saved under run_id
    {"type": "error", "detail": ...}          instead of the answer, if a call failed
    """
    try:
        agent = collection_agent(slug)
    except (CollectionError, LLMError) as error:
        raise _http_error(error) from error

    def events() -> Iterator[str]:
        try:
            for kind, payload in _answer_events(slug, agent, request):
                if kind == "event":
                    body = {"type": "event", **payload}
                elif kind == "step":
                    body = {"type": "step", "text": payload}
                else:
                    body = {"type": "answer", **payload}
                yield f"data: {json.dumps(body, ensure_ascii=False)}\n\n"
        except (LLMError, CollectionError) as error:
            yield f"data: {json.dumps({'type': 'error', 'detail': str(error)})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/collections/{slug}/runs")
def list_runs(slug: str) -> dict:
    try:
        return {"runs": get_store().runs(slug)}
    except CollectionError as error:
        raise _http_error(error) from error


@app.get("/collections/{slug}/runs/{run_id}")
def read_run(slug: str, run_id: str) -> dict:
    try:
        return get_store().run(slug, run_id)
    except CollectionError as error:
        raise _http_error(error) from error


# --- auto-evaluation ---------------------------------------------------------------------

# One evaluation per collection at a time, run on a background thread because it takes
# minutes on a free tier. The job and its log are in the job store, so a restart reports
# the interrupted job instead of forgetting it; the rows it finished are on disk and the
# next run resumes from them.


def _run_eval(slug: str, job_id: str, request: EvalRequest) -> None:
    from hyper_rag.evaluation.synthetic import evaluate_collection

    jobs = get_jobs()
    try:
        report = evaluate_collection(
            get_store(),
            slug,
            get_settings(),
            questions=request.questions,
            configs=("hybrid_rerank", "agent") if request.agent else ("hybrid_rerank",),
            use_judge=request.judge,
            regenerate=request.regenerate,
            on_progress=lambda line: jobs.log(job_id, line.strip()),
        )
        jobs.finish(job_id, report)
    except Exception as error:  # report every failure to the UI instead of dying silently
        jobs.fail(job_id, str(error))


@app.post("/collections/{slug}/eval", status_code=202)
def start_eval(slug: str, request: EvalRequest) -> dict:
    try:
        get_store().retriever(slug)  # fails now, with a clear message, if there is nothing to test
    except CollectionError as error:
        raise _http_error(error) from error
    job = get_jobs().start("eval", slug)
    if job is None:
        raise HTTPException(status_code=409, detail="An evaluation is already running.")
    threading.Thread(target=_run_eval, args=(slug, job["id"], request), daemon=True).start()
    return {"state": "running"}


@app.get("/collections/{slug}/eval")
def read_eval(slug: str) -> dict:
    from hyper_rag.evaluation.synthetic import latest_report

    try:
        get_store().get(slug)
        saved = latest_report(get_store(), slug)
    except CollectionError as error:
        raise _http_error(error) from error
    job = get_jobs().latest("eval", slug)
    if job is None:
        return {"state": "idle", "log": [], "report": saved, "error": None}
    return {
        "state": job["state"],
        "log": job["log"],
        "report": job["result"] or saved,
        "error": job["error"],
    }
