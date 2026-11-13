"""Storage behind interfaces, so the hosted stores of plan v2 can replace the local ones.

    BlobStore     originals, parsed units, indexes   local folder   (hosted: R2)
    VectorStore   chunk embeddings per collection    numpy, exact   (hosted: Qdrant)
    LexicalStore  keyword search per collection      rank_bm25      (hosted: Qdrant sparse, FTS5)
    JobStore      long-running jobs and their logs   SQLite         (hosted: SQLite + R2 replica)

The local implementations are the defaults, and the tests and offline mode use them. The
built-in packs keep their own on-disk index (hyper_rag.index): they are evaluation corpora
built by a command, not user data, and their published numbers must not move.
"""

from hyper_rag.config import Settings
from hyper_rag.stores.blob import BlobStore, LocalBlobStore
from hyper_rag.stores.jobs import JobStore, SqliteJobStore
from hyper_rag.stores.lexical import BM25LexicalStore, LexicalStore
from hyper_rag.stores.vectors import NumpyVectorStore, VectorStore

__all__ = [
    "BlobStore",
    "JobStore",
    "LexicalStore",
    "VectorStore",
    "build_blob_store",
    "build_job_store",
    "build_lexical_store",
    "build_vector_store",
]


def build_blob_store(settings: Settings) -> BlobStore:
    if settings.blob_store == "local":
        return LocalBlobStore(settings.data_dir)
    raise ValueError(f"Unknown blob store '{settings.blob_store}'")


def build_vector_store(settings: Settings) -> VectorStore:
    if settings.vector_store == "numpy":
        return NumpyVectorStore()
    raise ValueError(f"Unknown vector store '{settings.vector_store}'")


def build_lexical_store(settings: Settings) -> LexicalStore:
    if settings.lexical_store == "bm25":
        return BM25LexicalStore()
    raise ValueError(f"Unknown lexical store '{settings.lexical_store}'")


def build_job_store(settings: Settings) -> JobStore:
    if settings.job_store == "sqlite":
        return SqliteJobStore(settings.data_dir / "jobs.sqlite3")
    raise ValueError(f"Unknown job store '{settings.job_store}'")
