"""Blob storage: the bytes of originals, parsed units and per-file indexes.

Keys are relative, slash-separated paths such as "collections/solar/files/ab12.pdf".
Today's implementation is a folder on local disk. The hosted one (plan v2, A7) is
Cloudflare R2, because a free host's disk is wiped on every restart.
"""

import re
import shutil
from pathlib import Path
from typing import Protocol

_PART = re.compile(r"[A-Za-z0-9._-]+")


def check_key(key: str) -> str:
    """Refuse a key that could leave the store's root: absolute, empty parts, or "..".

    Callers already build keys from validated slugs and content hashes; this is the second
    lock on the same door, so a future caller that forgets cannot reach other files.
    """
    parts = key.split("/")
    if not key or any(not _PART.fullmatch(part) or part in (".", "..") for part in parts):
        raise ValueError(f"invalid blob key {key!r}")
    return key


class BlobStore(Protocol):
    def read_bytes(self, key: str) -> bytes: ...

    def write_bytes(self, key: str, data: bytes) -> None:
        """Replace the blob atomically: a reader sees the old bytes or the new, never half."""
        ...

    def write_file(self, key: str, source: Path, move: bool = False) -> None:
        """Store a local file as a blob without reading it into memory. With move=True the
        source may be consumed (renamed into place)."""
        ...

    def exists(self, key: str) -> bool: ...

    def delete(self, key: str) -> None:
        """Remove one blob; a missing one is not an error."""
        ...

    def delete_prefix(self, prefix: str) -> None:
        """Remove every blob under `prefix` (a folder, in local terms)."""
        ...

    def list(self, prefix: str) -> list[str]:
        """Every key under `prefix`, sorted."""
        ...

    def local_path(self, key: str) -> Path:
        """A file on local disk holding the blob, for parsers and libraries that need a path.

        Remote stores download it to a local cache. The file is read-only for the caller.
        """
        ...


class LocalBlobStore:
    name = "local"

    def __init__(self, root: Path):
        self.root = root

    def _path(self, key: str) -> Path:
        return self.root / check_key(key)

    def read_bytes(self, key: str) -> bytes:
        try:
            return self._path(key).read_bytes()
        except FileNotFoundError:
            raise KeyError(key) from None

    def write_bytes(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_bytes(data)
        temporary.replace(path)  # atomic on one file system

    def write_file(self, key: str, source: Path, move: bool = False) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        if move:
            try:
                source.replace(path)  # same file system: a rename, no copy
                return
            except OSError:
                pass
        temporary = path.with_name(path.name + ".tmp")
        shutil.copyfile(source, temporary)
        temporary.replace(path)

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def delete_prefix(self, prefix: str) -> None:
        path = self._path(prefix.rstrip("/"))
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)

    def list(self, prefix: str) -> list[str]:
        base = self._path(prefix.rstrip("/"))
        if not base.is_dir():
            return []
        return sorted(
            path.relative_to(self.root).as_posix()
            for path in base.rglob("*")
            if path.is_file() and not path.name.endswith(".tmp")
        )

    def local_path(self, key: str) -> Path:
        path = self._path(key)
        if not path.is_file():
            raise KeyError(key)
        return path
