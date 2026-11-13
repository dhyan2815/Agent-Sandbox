"""Build, save and load a pack's index.

On disk an index is two files: chunks.jsonl (the passages) and embeddings.npy (one
row per passage). The BM25 index is rebuilt from the chunks at load time, which takes
milliseconds at this scale and avoids pickling a third-party object.
"""

import json
from pathlib import Path

import numpy as np

from hyper_rag.chunking import chunk_documents
from hyper_rag.config import Settings
from hyper_rag.packs import Pack
from hyper_rag.retrieval.bm25 import BM25Index
from hyper_rag.retrieval.dense import DenseIndex
from hyper_rag.retrieval.embedders import Embedder, build_embedder
from hyper_rag.retrieval.rerank import build_reranker
from hyper_rag.retrieval.retriever import Retriever
from hyper_rag.types import Chunk, Document


def pack_data_dir(settings: Settings, pack_name: str) -> Path:
    return settings.data_dir / pack_name


def _index_dir(settings: Settings, pack_name: str, embedder: Embedder) -> Path:
    # One folder per embedder: vectors from different models are not comparable.
    return pack_data_dir(settings, pack_name) / f"index-{embedder.name}"


def ingest_pack(pack: Pack, settings: Settings) -> dict:
    """Fetch the pack's documents, chunk them, embed them and write the index."""
    data_dir = pack_data_dir(settings, pack.name)
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    documents: list[Document] = list(pack.fetch_documents(raw_dir))
    if not documents:
        raise RuntimeError(f"Pack '{pack.name}' produced no documents")
    chunks = chunk_documents(documents, pack.config.chunk_size, pack.config.chunk_overlap)

    embedder = build_embedder(settings)
    embeddings = embedder.embed_documents([chunk.text for chunk in chunks])

    index_dir = _index_dir(settings, pack.name, embedder)
    index_dir.mkdir(parents=True, exist_ok=True)
    with (index_dir / "chunks.jsonl").open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
    np.save(index_dir / "embeddings.npy", embeddings)
    return {
        "pack": pack.name,
        "documents": len(documents),
        "chunks": len(chunks),
        "embedder": embedder.name,
        "index_dir": str(index_dir),
    }


def load_retriever(pack: Pack, settings: Settings) -> Retriever:
    embedder = build_embedder(settings)
    index_dir = _index_dir(settings, pack.name, embedder)
    if not (index_dir / "chunks.jsonl").exists():
        raise FileNotFoundError(
            f"No index for pack '{pack.name}' at {index_dir}. Run: hyper-rag ingest {pack.name}"
        )
    lines = (index_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
    chunks = [Chunk(**json.loads(line)) for line in lines]
    embeddings = np.load(index_dir / "embeddings.npy")
    return Retriever(
        chunks=chunks,
        dense=DenseIndex(embeddings),
        bm25=BM25Index([chunk.text for chunk in chunks]),
        embedder=embedder,
        reranker=build_reranker(settings),
        settings=settings,
    )
