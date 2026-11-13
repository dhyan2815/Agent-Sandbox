"""Job storage: long-running work (evaluations now, ingestion jobs in plan v2 phase 1).

SQLite, because a free host has no Redis and one file is enough for one user's jobs. On a
host whose disk is wiped on restart the file is replicated to R2 (plan v2, A7); the
interface does not change.

A job that was running when the process stopped cannot still be running, so opening the
store marks such jobs failed with a message saying so. The work they finished is not
lost: the evaluation resumes from its saved rows, and ingestion will resume from its last
checkpoint.
"""

import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

INTERRUPTED = "The server restarted while this was running. Start it again: finished work is kept."

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id       TEXT PRIMARY KEY,
    kind     TEXT NOT NULL,          -- "eval", later "ingest"
    scope    TEXT NOT NULL,          -- what it works on, e.g. a collection slug
    state    TEXT NOT NULL,          -- running | done | failed
    log      TEXT NOT NULL DEFAULT '[]',
    result   TEXT,                   -- JSON, set when done
    error    TEXT,
    created  TEXT NOT NULL,
    updated  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_by_scope ON jobs (kind, scope, created);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


class JobStore(Protocol):
    def start(self, kind: str, scope: str) -> dict | None:
        """Create a running job, or return None if one of this kind and scope is running."""
        ...

    def get(self, job_id: str) -> dict | None: ...

    def latest(self, kind: str, scope: str) -> dict | None: ...

    def log(self, job_id: str, line: str) -> None: ...

    def finish(self, job_id: str, result: dict) -> None: ...

    def fail(self, job_id: str, error: str) -> None: ...

    def forget(self, kind: str, scope: str) -> None:
        """Delete every job of this kind and scope (the collection was deleted)."""
        ...


class SqliteJobStore:
    name = "sqlite"

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        # One connection shared by the API's worker threads, serialised by a lock. Jobs are
        # written a few times a second at most, so contention is not a concern.
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.executescript(_SCHEMA)
            self._db.execute(
                "UPDATE jobs SET state = 'failed', error = ?, updated = ? WHERE state = 'running'",
                (INTERRUPTED, _now()),
            )

    @staticmethod
    def _row(row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        job = dict(row)
        job["log"] = json.loads(job["log"])
        job["result"] = json.loads(job["result"]) if job["result"] else None
        return job

    def start(self, kind: str, scope: str) -> dict | None:
        job_id = uuid.uuid4().hex[:16]
        now = _now()
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                running = self._db.execute(
                    "SELECT 1 FROM jobs WHERE kind = ? AND scope = ? AND state = 'running'",
                    (kind, scope),
                ).fetchone()
                if running is None:
                    self._db.execute(
                        "INSERT INTO jobs (id, kind, scope, state, created, updated) "
                        "VALUES (?, ?, ?, 'running', ?, ?)",
                        (job_id, kind, scope, now, now),
                    )
                self._db.execute("COMMIT")
            except BaseException:
                self._db.execute("ROLLBACK")
                raise
        return None if running else self.get(job_id)

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row(row)

    def latest(self, kind: str, scope: str) -> dict | None:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM jobs WHERE kind = ? AND scope = ? ORDER BY created DESC LIMIT 1",
                (kind, scope),
            ).fetchone()
        return self._row(row)

    def log(self, job_id: str, line: str) -> None:
        with self._lock:
            self._db.execute(
                "UPDATE jobs SET log = json_insert(log, '$[#]', ?), updated = ? WHERE id = ?",
                (line, _now(), job_id),
            )

    def finish(self, job_id: str, result: dict) -> None:
        with self._lock:
            self._db.execute(
                "UPDATE jobs SET state = 'done', result = ?, updated = ? WHERE id = ?",
                (json.dumps(result, ensure_ascii=False), _now(), job_id),
            )

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            self._db.execute(
                "UPDATE jobs SET state = 'failed', error = ?, updated = ? WHERE id = ?",
                (error, _now(), job_id),
            )

    def forget(self, kind: str, scope: str) -> None:
        with self._lock:
            self._db.execute("DELETE FROM jobs WHERE kind = ? AND scope = ?", (kind, scope))

    def close(self) -> None:
        with self._lock:
            self._db.close()
