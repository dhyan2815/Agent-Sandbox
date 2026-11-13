"""Background work for big files: resumable uploads and ingestion jobs (plan v2, A1 and A3).

Resumable upload, through the API (the plan's option 2; R2 direct upload is phase 2):

    POST /collections/{c}/uploads             {name, size} -> {id, part_size, received: 0}
    PUT  /collections/{c}/uploads/{id}?offset=N   the next part's bytes, appended at N
    GET  /collections/{c}/uploads/{id}        {received} after a dropped connection
    POST /collections/{c}/uploads/{id}/complete   -> the file's record, status "queued"

Parts are appended to a file on disk as they arrive, so the server never holds a whole
upload in memory. An offset that does not match what was received is refused with the
right offset, which is how a client resumes after losing its connection.

Ingestion jobs run on a small thread pool. Every staged file whose status is "queued" or
"reading" is picked up again when the app starts, and `CollectionStore.ingest_file`
resumes after the last committed window, so a crash or a redeploy costs at most the
window that was in progress.
"""

import json
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from hyper_rag.stores import JobStore
from hyper_rag.uploads import CollectionError, CollectionNotFound, CollectionStore

STALE_SECONDS = 24 * 3600  # an upload nobody has touched for a day is abandoned


class UploadError(CollectionError):
    pass


class OffsetMismatch(UploadError):
    def __init__(self, received: int):
        super().__init__(f"Expected the part at offset {received}.")
        self.received = received


class UploadSessions:
    def __init__(self, store: CollectionStore, folder: Path):
        self.store = store
        self.folder = folder
        self._lock = threading.Lock()

    @property
    def part_size(self) -> int:
        return int(self.store.settings.upload_part_mb * 1024 * 1024)

    def _paths(self, upload_id: str) -> tuple[Path, Path]:
        if not re.fullmatch(r"[0-9a-f]{32}", upload_id):
            raise CollectionNotFound(f"No upload '{upload_id}'")
        return self.folder / f"{upload_id}.json", self.folder / f"{upload_id}.part"

    def _meta(self, slug: str, upload_id: str) -> dict:
        meta_path, part_path = self._paths(upload_id)
        if not meta_path.exists():
            raise CollectionNotFound(f"No upload '{upload_id}'")
        meta = json.loads(meta_path.read_text())
        if meta["slug"] != slug:
            raise CollectionNotFound(f"No upload '{upload_id}'")
        meta["received"] = part_path.stat().st_size if part_path.exists() else 0
        return meta

    def _sweep(self) -> None:
        cutoff = time.time() - STALE_SECONDS
        for path in self.folder.glob("*.json"):
            if path.stat().st_mtime < cutoff:
                path.with_suffix(".part").unlink(missing_ok=True)
                path.unlink(missing_ok=True)

    def create(self, slug: str, name: str, size: int) -> dict:
        self.store.get(slug)
        name, _ = self.store.check_upload(slug, name, size)
        self.folder.mkdir(parents=True, exist_ok=True)
        self._sweep()
        upload_id = uuid.uuid4().hex
        meta = {"id": upload_id, "slug": slug, "name": name, "size": size, "created": time.time()}
        meta_path, part_path = self._paths(upload_id)
        meta_path.write_text(json.dumps(meta))
        part_path.touch()
        return self.status(slug, upload_id)

    def status(self, slug: str, upload_id: str) -> dict:
        meta = self._meta(slug, upload_id)
        return {
            "id": upload_id,
            "name": meta["name"],
            "size": meta["size"],
            "received": meta["received"],
            "part_size": self.part_size,
        }

    def append(self, slug: str, upload_id: str, offset: int, chunks) -> dict:
        """Append one part, read from `chunks` (an iterable of bytes) as it arrives."""
        limit = self.part_size
        with self._lock:
            meta = self._meta(slug, upload_id)
            if offset != meta["received"]:
                raise OffsetMismatch(meta["received"])
            _, part_path = self._paths(upload_id)
            written = 0
            with part_path.open("ab") as handle:
                try:
                    for chunk in chunks:
                        written += len(chunk)
                        if written > limit or offset + written > meta["size"]:
                            raise UploadError("This part is larger than allowed.")
                        handle.write(chunk)
                except BaseException:
                    handle.truncate(offset)  # a part is all or nothing
                    raise
        return self.status(slug, upload_id)

    def complete(self, slug: str, upload_id: str) -> dict:
        meta = self._meta(slug, upload_id)
        if meta["received"] != meta["size"]:
            raise UploadError(f"Received {meta['received']} of {meta['size']} bytes.")
        meta_path, part_path = self._paths(upload_id)
        try:
            record = self.store.stage_file(slug, meta["name"], part_path, move=True)
        finally:
            part_path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
        return record


class IngestWorker:
    """Runs ingestion jobs in the background and resumes unfinished ones at start-up."""

    def __init__(self, store: CollectionStore, jobs: JobStore, workers: int = 1):
        self.store = store
        self.jobs = jobs
        self._pool = ThreadPoolExecutor(max_workers=max(workers, 1), thread_name_prefix="ingest")
        self._queued: set[tuple[str, str]] = set()
        self._lock = threading.Lock()

    def submit(self, slug: str, file_id: str) -> bool:
        """Queue a file; False if it is already queued or running in this process."""
        with self._lock:
            if (slug, file_id) in self._queued:
                return False
            self._queued.add((slug, file_id))
        self._pool.submit(self._run, slug, file_id)
        return True

    def _run(self, slug: str, file_id: str) -> None:
        scope = f"{slug}/{file_id}"
        job = self.jobs.start("ingest", scope)
        try:
            record = self.store.ingest_file(
                slug,
                file_id,
                on_event=(lambda event: self.jobs.log(job["id"], json.dumps(event)))
                if job
                else None,
            )
            if job:
                if record.get("status") == "failed":
                    self.jobs.fail(job["id"], record.get("error") or "failed")
                else:
                    self.jobs.finish(job["id"], {"status": record.get("status")})
        except Exception as error:  # the record already says why; keep the worker alive
            if job:
                self.jobs.fail(job["id"], str(error))
        finally:
            with self._lock:
                self._queued.discard((slug, file_id))

    def resume(self) -> int:
        """Queue every file a previous run left unfinished. Returns how many."""
        count = 0
        for collection in self.store.all():
            for record in collection["files"]:
                if record.get("status") in ("queued", "reading"):
                    count += self.submit(collection["slug"], record["id"])
        return count

    def wait(self, timeout: float = 60) -> None:
        """Block until no job is queued or running (tests and scripts)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                if not self._queued:
                    return
            time.sleep(0.05)
        raise TimeoutError("ingestion did not finish in time")

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
