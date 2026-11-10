from pathlib import Path

import pytest

from hyper_rag.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings(tmp_path) -> Settings:
    """Offline settings: fake LLM, hashing embedder, lexical reranker, data in a temp dir."""
    return Settings(packs_dir=REPO_ROOT / "packs", data_dir=tmp_path / "data").offline()
