import sys
from pathlib import Path

import pytest

from hyper_rag.config import Settings
from hyper_rag.uploads import CollectionStore

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))  # so tests can import make_files


@pytest.fixture(autouse=True)
def no_live_settings(monkeypatch):
    """Tests never see a real deploy's settings: no HYPER_RAG_* variables, no keys, no .env.

    A shell set up for a live check once ran the suite against a real bucket.
    """
    import os

    for name in list(os.environ):
        if name.startswith("HYPER_RAG_") or name in ("HF_TOKEN", "GROQ_API_KEY", "GEMINI_API_KEY"):
            monkeypatch.delenv(name)
    monkeypatch.setitem(Settings.model_config, "env_file", None)


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
