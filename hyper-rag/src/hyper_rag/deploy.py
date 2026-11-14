"""Running on a host (plan v2 phase 6): warm-up, a quota guard, and a settings check.

Three small pieces, none of which touch retrieval or answers:

    Warmup         loads the embedding and reranking models in the background at start-up,
                   so /health can say "warming" and the page can show a waking-up screen
                   instead of a first question that hangs for a minute.
    QuotaGuard     a sliding-window limit on requests that spend model quota (questions,
                   claim checks, LLM exports), per client, so one runaway tab or script
                   cannot use up the day's free allowance.
    check_settings the same questions `hyper-rag doctor` and the start-up log ask: is this
                   configuration safe and complete for a host?
"""

import logging
import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Literal

from hyper_rag.config import Settings

log = logging.getLogger("hyper_rag.deploy")


class Warmup:
    """Runs `load` once on a background thread and reports where it got to."""

    def __init__(self) -> None:
        self.state: Literal["idle", "warming", "ready", "failed"] = "idle"
        self.error = ""
        self.seconds = 0.0
        self._thread: threading.Thread | None = None

    def start(self, load) -> None:
        if self._thread is not None:
            return
        self.state = "warming"

        def run() -> None:
            started = time.monotonic()
            try:
                load()
                self.state = "ready"
            except Exception as error:  # a failed warm-up must not stop the app from serving
                self.state, self.error = "failed", f"{type(error).__name__}: {error}"
                log.warning("warm-up failed: %s", self.error)
            self.seconds = round(time.monotonic() - started, 1)

        self._thread = threading.Thread(target=run, name="warmup", daemon=True)
        self._thread.start()

    def wait(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    def to_dict(self) -> dict:
        return {"state": self.state, "seconds": self.seconds, "error": self.error}


class QuotaGuard:
    """At most `limit` requests per `window` seconds for each client. limit 0 = no limit."""

    def __init__(self, limit: int, window: float = 3600.0):
        self.limit = limit
        self.window = window
        self._seen: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _trim(self, client: str, now: float) -> deque[float]:
        seen = self._seen[client]
        while seen and seen[0] <= now - self.window:
            seen.popleft()
        return seen

    def take(self, client: str) -> float:
        """Count one request. Returns 0 if allowed, else the seconds until one is free."""
        if self.limit <= 0:
            return 0.0
        now = time.monotonic()
        with self._lock:
            seen = self._trim(client, now)
            if len(seen) >= self.limit:
                return max(1.0, seen[0] + self.window - now)
            seen.append(now)
            return 0.0

    def left(self, client: str) -> int | None:
        if self.limit <= 0:
            return None
        with self._lock:
            return max(0, self.limit - len(self._trim(client, time.monotonic())))


@dataclass(frozen=True)
class Problem:
    level: Literal["error", "warning"]
    message: str


def on_hosted_disk() -> bool:
    """True where the local disk is wiped on restart (a Hugging Face Space sets SPACE_ID)."""
    return bool(os.environ.get("SPACE_ID"))


def check_settings(settings: Settings, hosted: bool | None = None) -> list[Problem]:
    """What is wrong or risky about this configuration. Errors stop a deploy; warnings do not."""
    hosted = on_hosted_disk() if hosted is None else hosted
    problems: list[Problem] = []

    def error(message: str) -> None:
        problems.append(Problem("error", message))

    def warn(message: str) -> None:
        problems.append(Problem("warning", message))

    if settings.llm_provider == "groq" and not settings.groq_api_key:
        error("llm_provider is groq but GROQ_API_KEY is not set.")
    if settings.llm_provider == "gemini" and not settings.gemini_api_key:
        error("llm_provider is gemini but GEMINI_API_KEY is not set.")
    if settings.llm_provider == "fake":
        warn("llm_provider is fake: answers come from the rule-based stand-in.")
    if settings.embedder == "hashing" and settings.llm_provider != "fake":
        warn("embedder is hashing: search is word overlap only. Set embedder: fastembed.")

    if settings.blob_store == "s3":
        if not settings.s3_bucket:
            error("blob_store is s3 but HYPER_RAG_S3_BUCKET is not set.")
        if not (os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY")):
            error("blob_store is s3 but AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY are not set.")
    if settings.blob_store == "hf":
        if not settings.hf_bucket:
            error("blob_store is hf but HYPER_RAG_HF_BUCKET is not set.")
        if not os.environ.get("HF_TOKEN"):
            error("blob_store is hf but HF_TOKEN is not set.")
    if "qdrant" in (settings.vector_store, settings.lexical_store):
        if not settings.qdrant_url:
            error("A Qdrant store is selected but HYPER_RAG_QDRANT_URL is not set.")
        elif settings.qdrant_url != ":memory:" and not settings.qdrant_api_key:
            warn("QDRANT_API_KEY is not set: fine for a local server, not for Qdrant Cloud.")
        if settings.qdrant_url == ":memory:":
            warn("Qdrant runs in memory: vectors are lost on every restart.")
    if settings.vector_store != settings.lexical_store and "qdrant" in (
        settings.vector_store,
        settings.lexical_store,
    ):
        warn("Only one of vector_store and lexical_store is qdrant. Use qdrant for both.")

    if hosted:
        if settings.blob_store == "local":
            warn(
                "The host's disk is wiped on restart and blob_store is local: uploaded files "
                "and indexes will be lost. Use blob_store: hf (a Hugging Face bucket)."
            )
        if not settings.password:
            error("HYPER_RAG_PASSWORD is not set: anyone with the URL can read your documents.")
    elif not settings.password:
        warn("No password set (HYPER_RAG_PASSWORD): fine on your own machine, not on a host.")

    if not (settings.ui_dir / "index.html").is_file():
        warn(f"No built web app in {settings.ui_dir}: the classic page will be served.")
    if settings.model_requests_per_hour == 0 and settings.llm_provider != "fake":
        warn("model_requests_per_hour is 0: nothing limits how fast the free quota is spent.")
    return problems


def readiness(settings: Settings, store) -> dict:
    """Cheap probes of the stores behind the app, for GET /ready. Never raises."""
    checks: dict[str, str] = {}

    def probe(name: str, call) -> None:
        try:
            call()
            checks[name] = "ok"
        except Exception as error:
            checks[name] = f"{type(error).__name__}: {error}"[:200]

    probe("blobs", lambda: store.blobs.list("collections"))
    if settings.vector_store == "qdrant":
        probe("vectors", lambda: store.vectors.search("__probe__", _ONE, 1))
    return {"ready": all(v == "ok" for v in checks.values()), "checks": checks}


try:  # numpy is a hard dependency; imported here so the probe vector is built once
    import numpy as _np

    _ONE = _np.ones(1, dtype=_np.float32)
except ImportError:  # pragma: no cover
    _ONE = None
