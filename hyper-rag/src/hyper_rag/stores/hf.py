"""Blob storage in a Hugging Face Storage Bucket: one account for the host and its storage.

A bucket is the Hub's mutable, non-versioned object store. With `blob_store: hf` the
originals, parsed pages, per-file indexes (chunk vectors included) and the job log copy all
live in one private bucket, so the default numpy and BM25 stores are rebuilt from it after
a restart and no separate vector database or S3 account is needed (docs/DECISIONS.md 44).

    HYPER_RAG_BLOB_STORE=hf
    HYPER_RAG_HF_BUCKET=<user>/<bucket>      create it once: hf buckets create <bucket> --private
    HF_TOKEN=<a token with write access>     a secret, never in config.yaml

Every Hub call is an HTTPS round trip of about a second (measured), and reading a book
makes two per page, so this store avoids most of them. It assumes it is the only writer
under its prefix, which is true for one running app:

    keys     listed once, on first use, then kept in memory: `exists`, `list` and a read
             of a missing key cost nothing.
    reads    everything written or downloaded is kept in the cache folder and read there.
    writes   `write_bytes` queues the blob and returns; the queue is sent as one request
             when it holds WRITE_BATCH blobs or WRITE_BYTES bytes, after WRITE_DELAY
             seconds, before any delete or file upload, and at exit. Order is kept, so a
             checkpoint never reaches the bucket before the pages it names. A killed
             process loses at most the queue, and the job resumes from the checkpoint
             that did arrive.

A write replaces the whole object, which is the atomic write the other stores give.
"""

import atexit
import logging
import shutil
import threading
from pathlib import Path

from hyper_rag.stores.blob import check_key

log = logging.getLogger("hyper_rag.stores.hf")

WRITE_BATCH, WRITE_BYTES, WRITE_DELAY = 64, 32_000_000, 2.0


class HfBucketBlobStore:
    name = "hf"

    def __init__(self, bucket: str, cache_dir: Path, prefix: str = "", api=None):
        if api is None:
            from huggingface_hub import HfApi

            api = HfApi()  # reads HF_TOKEN from the environment
        self.api = api
        self.bucket = bucket
        self.prefix = prefix.strip("/") + "/" if prefix.strip("/") else ""
        self.cache_dir = cache_dir
        self._lock = threading.RLock()  # the key set, the queue and the cache folder
        self._sending = threading.Lock()  # one batch at a time, so order is kept
        self._known: set[str] | None = None
        self._queue: dict[str, bytes] = {}
        self._timer: threading.Timer | None = None
        atexit.register(self._flush_quietly)

    def _remote(self, key: str) -> str:
        return self.prefix + key

    def _keys(self) -> set[str]:
        with self._lock:
            if self._known is None:
                tree = self.api.list_bucket_tree(
                    self.bucket, prefix=self.prefix or None, recursive=True
                )
                self._known = {
                    entry.path[len(self.prefix) :]
                    for entry in tree
                    if entry.type == "file" and entry.path.startswith(self.prefix)
                }
            return self._known

    def _cached(self, key: str) -> Path:
        return self.cache_dir / key

    # Writes

    def write_bytes(self, key: str, data: bytes) -> None:
        check_key(key)
        with self._lock:
            path = self._cached(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            partial = path.with_name(path.name + ".part")
            partial.write_bytes(data)
            partial.replace(path)
            self._keys().add(key)
            self._queue.pop(key, None)  # a rewrite moves to the back, like any later write
            self._queue[key] = data
            full = (
                len(self._queue) >= WRITE_BATCH
                or sum(map(len, self._queue.values())) >= WRITE_BYTES
            )
            if not full and self._timer is None:
                self._timer = threading.Timer(WRITE_DELAY, self._flush_quietly)
                self._timer.daemon = True
                self._timer.start()
        if full:
            self.flush()

    def flush(self) -> None:
        """Send the queued writes now. Raises if the Hub refuses; the queue is kept."""
        with self._sending:
            with self._lock:
                batch, self._queue = self._queue, {}
                if self._timer is not None:
                    self._timer.cancel()
                    self._timer = None
            if not batch:
                return
            try:
                self.api.batch_bucket_files(
                    self.bucket, add=[(data, self._remote(key)) for key, data in batch.items()]
                )
            except Exception:
                with self._lock:  # keep them for the next flush, behind nothing newer
                    self._queue = {**batch, **self._queue}
                raise

    def _flush_quietly(self) -> None:
        try:
            self.flush()
        except Exception as error:  # a timer thread has nobody to raise to
            log.warning("could not send %d queued blobs: %s", len(self._queue), error)

    def write_file(self, key: str, source: Path, move: bool = False) -> None:
        check_key(key)
        self.flush()
        # The client uploads in chunks from disk, so a 1 GB original never sits in memory.
        self.api.batch_bucket_files(self.bucket, add=[(str(source), self._remote(key))])
        with self._lock:
            self._keys().add(key)
            cached = self._cached(key)
            cached.parent.mkdir(parents=True, exist_ok=True)
            if move:
                try:
                    source.replace(cached)  # same disk: a rename, and no download later
                    return
                except OSError:
                    pass
            shutil.copyfile(source, cached)
            if move:
                source.unlink(missing_ok=True)

    # Reads

    def exists(self, key: str) -> bool:
        return check_key(key) in self._keys()

    def local_path(self, key: str) -> Path:
        path = self._cached(check_key(key))
        with self._lock:
            if key not in self._keys():
                raise KeyError(key)
            if not path.is_file():
                from huggingface_hub.errors import EntryNotFoundError

                path.parent.mkdir(parents=True, exist_ok=True)
                partial = path.with_name(path.name + ".part")
                try:
                    self.api.download_bucket_files(
                        self.bucket, [(self._remote(key), partial)], raise_on_missing_files=True
                    )
                except EntryNotFoundError:  # removed by someone else since the listing
                    self._keys().discard(key)
                    raise KeyError(key) from None
                partial.replace(path)
        return path

    def read_bytes(self, key: str) -> bytes:
        return self.local_path(key).read_bytes()

    # Deletes

    def _remove(self, keys: list[str]) -> None:
        self.flush()
        for start in range(0, len(keys), 1000):
            self.api.batch_bucket_files(
                self.bucket, delete=[self._remote(key) for key in keys[start : start + 1000]]
            )
        with self._lock:
            self._keys().difference_update(keys)
            for key in keys:
                self._cached(key).unlink(missing_ok=True)

    def delete(self, key: str) -> None:
        if self.exists(key):
            self._remove([key])

    def delete_prefix(self, prefix: str) -> None:
        name = check_key(prefix.rstrip("/"))
        self._remove([*self.list(name), *([name] if name in self._keys() else [])])
        shutil.rmtree(self._cached(name), ignore_errors=True)

    # Defined last: inside the class body, `list` would shadow the built-in in annotations.
    def list(self, prefix: str) -> list[str]:
        folder = check_key(prefix.rstrip("/")) + "/"
        with self._lock:
            return sorted(key for key in self._keys() if key.startswith(folder))
