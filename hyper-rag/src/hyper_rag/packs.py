"""Domain packs: a folder with pack.yaml, ingest.py and golden.jsonl.

The engine never imports a pack by name. It lists the packs directory and loads
whatever is there, so adding a domain means adding a folder, not editing engine code.
"""

import importlib.util
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel

from hyper_rag.types import Document


class PackConfig(BaseModel):
    name: str
    description: str  # shown to the router so it can tell in-scope from out-of-scope questions
    # Chunk sizes are in characters. ~1200 characters is roughly 300 tokens: large enough to
    # hold a full step or parameter table, small enough that five passages fit in a small
    # prompt and each one stays under the embedding model's 512-token input limit.
    chunk_size: int = 1200
    chunk_overlap: int = 150
    sources: list = []  # free-form; only the pack's own ingest.py reads it


@dataclass(frozen=True)
class Pack:
    config: PackConfig
    path: Path

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def golden_path(self) -> Path:
        return self.path / "golden.jsonl"

    def fetch_documents(self, raw_dir: Path) -> Iterable[Document]:
        """Run the pack's ingest script. It must define fetch(pack, raw_dir) -> Documents."""
        script = self.path / "ingest.py"
        spec = importlib.util.spec_from_file_location(f"hyper_rag_pack_{self.name}", script)
        if spec is None or spec.loader is None:
            raise FileNotFoundError(f"Pack '{self.name}' has no ingest.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.fetch(self, raw_dir)


@dataclass(frozen=True)
class GoldenQuestion:
    id: str
    question: str
    answerable: bool  # False: the corpus does not contain the answer; the system should decline
    reference_answer: str
    # Information needs: each inner list names documents that each contain that part of
    # the answer. See evaluation/retrieval_metrics.py.
    relevant_sources: list[list[str]]
    key_facts: list[str]  # short strings a correct answer must contain (deterministic check)


def list_packs(packs_dir: Path) -> list[str]:
    return sorted(p.parent.name for p in packs_dir.glob("*/pack.yaml"))


def load_pack(packs_dir: Path, name: str) -> Pack:
    path = packs_dir / name
    config_file = path / "pack.yaml"
    if not config_file.exists():
        available = ", ".join(list_packs(packs_dir)) or "none"
        raise FileNotFoundError(f"No pack '{name}' in {packs_dir}/ (available: {available})")
    config = PackConfig(**yaml.safe_load(config_file.read_text(encoding="utf-8")))
    return Pack(config=config, path=path)


def load_golden(pack: Pack) -> list[GoldenQuestion]:
    questions = []
    for line in pack.golden_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        questions.append(
            GoldenQuestion(
                id=row["id"],
                question=row["question"],
                answerable=row["answerable"],
                reference_answer=row.get("reference_answer", ""),
                # A bare string is shorthand for a need with a single document.
                relevant_sources=[
                    [need] if isinstance(need, str) else need
                    for need in row.get("relevant_sources", [])
                ],
                key_facts=row.get("key_facts", []),
            )
        )
    return questions
