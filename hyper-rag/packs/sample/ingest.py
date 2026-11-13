"""Sample pack ingestion: read the hand-written markdown files that ship with the repo."""

from pathlib import Path

from hyper_rag.types import Document


def fetch(pack, raw_dir: Path):
    for path in sorted((pack.path / "corpus").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = text.splitlines()[0].lstrip("# ").strip()
        yield Document(id=path.stem, title=title, url=f"packs/sample/corpus/{path.name}", text=text)
