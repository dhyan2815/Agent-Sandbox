import sys
from pathlib import Path

import pytest

from hyper_rag.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))  # so tests can import make_files


@pytest.fixture
def settings(tmp_path) -> Settings:
    """Offline settings: fake LLM, hashing embedder, lexical reranker, data in a temp dir."""
    return Settings(packs_dir=REPO_ROOT / "packs", data_dir=tmp_path / "data").offline()
