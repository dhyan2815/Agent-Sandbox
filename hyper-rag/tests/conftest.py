import sys
from pathlib import Path

import pytest

from hyper_rag.config import Settings
from hyper_rag.uploads import CollectionStore

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))  # so tests can import make_files


@pytest.fixture
def settings(tmp_path) -> Settings:
    """Offline settings: fake LLM, hashing embedder, lexical reranker, data in a temp dir."""
    return Settings(packs_dir=REPO_ROOT / "packs", data_dir=tmp_path / "data").offline()


class StubOcr:
    """Stands in for the OCR models: says the same thing about every image."""

    name = "stub"

    def read(self, image) -> str:
        return "TEXT FROM IMAGE"


@pytest.fixture
def store(settings) -> CollectionStore:
    return CollectionStore(settings, ocr=StubOcr())


@pytest.fixture
def solar(store, tmp_path) -> CollectionStore:
    """A collection holding one file of every supported format."""
    from make_files import make_all

    store.create("Solar docs")
    for path in make_all(tmp_path / "files"):
        store.add_file("solar-docs", path.name, path.read_bytes())
    return store
