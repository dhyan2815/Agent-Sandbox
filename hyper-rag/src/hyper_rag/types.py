"""Plain data types shared by ingestion, retrieval, the agent and the eval."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Document:
    """One source page/file, as produced by a pack's ingest script."""

    id: str  # stable identifier; golden sets refer to documents by this id
    title: str
    url: str  # where a reader can open the source (file path for local corpora)
    text: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Chunk:
    """A passage of a document: the unit that is embedded, retrieved and cited."""

    id: str  # "<doc_id>#<n>"
    doc_id: str
    title: str
    url: str
    text: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float
