"""Storage behind interfaces, so the hosted stores of plan v2 can replace the local ones.

    BlobStore     originals, parsed units, indexes   local folder   hf (a Hugging Face bucket)
                                                                    or s3 (Cloudflare R2)
    VectorStore   chunk embeddings per collection    numpy, exact   qdrant (int8, on disk)
    LexicalStore  keyword search per collection      rank_bm25      qdrant (sparse, IDF)
    JobStore      long-running jobs and their logs   SQLite         SQLite copied to the blobs

The local implementations are the defaults, and the tests and offline mode use them; the
hosted ones need the `hosted` extra (pip install -e ".[hosted]") and are chosen in
settings (docs/DECISIONS.md 32). The
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
    if settings.blob_store == "s3":
        from hyper_rag.stores.s3 import S3BlobStore

        if not settings.s3_bucket:
            raise ValueError("blob_store is s3 but HYPER_RAG_S3_BUCKET is not set")
        return S3BlobStore(
            settings.s3_bucket,
            cache_dir=settings.data_dir / "blob-cache",
            endpoint_url=settings.s3_endpoint,
            region=settings.s3_region,
            prefix=settings.s3_prefix,
        )
    if settings.blob_store == "hf":
        from hyper_rag.stores.hf import HfBucketBlobStore

        if not settings.hf_bucket:
            raise ValueError("blob_store is hf but HYPER_RAG_HF_BUCKET is not set")
        return HfBucketBlobStore(
            settings.hf_bucket,
            cache_dir=settings.data_dir / "blob-cache",
            prefix=settings.hf_prefix,
        )
    raise ValueError(f"Unknown blob store '{settings.blob_store}'")


_QDRANT_CLIENTS: dict[tuple[str, str], object] = {}


def _qdrant_client(settings: Settings):
    # One client per URL: the vector and keyword stores share it (and, for ":memory:",
    # its in-process database).
    from qdrant_client import QdrantClient

    if not settings.qdrant_url:
        raise ValueError("a Qdrant store is selected but HYPER_RAG_QDRANT_URL is not set")
    key = (settings.qdrant_url, settings.qdrant_api_key)
    if key not in _QDRANT_CLIENTS:
        if settings.qdrant_url == ":memory:":
            _QDRANT_CLIENTS[key] = QdrantClient(location=":memory:")
        else:
            _QDRANT_CLIENTS[key] = QdrantClient(
                url=settings.qdrant_url, api_key=settings.qdrant_api_key or None, timeout=60
            )
    return _QDRANT_CLIENTS[key]


def build_vector_store(settings: Settings) -> VectorStore:
    if settings.vector_store == "numpy":
        return NumpyVectorStore()
    if settings.vector_store == "qdrant":
        from hyper_rag.stores.qdrant import QdrantVectorStore

        return QdrantVectorStore(
            settings.qdrant_url, prefix=settings.qdrant_prefix, client=_qdrant_client(settings)
        )
    raise ValueError(f"Unknown vector store '{settings.vector_store}'")


def build_lexical_store(settings: Settings) -> LexicalStore:
    if settings.lexical_store == "bm25":
        return BM25LexicalStore()
    if settings.lexical_store == "qdrant":
        from hyper_rag.stores.qdrant import QdrantLexicalStore

        return QdrantLexicalStore(
            settings.qdrant_url, prefix=settings.qdrant_prefix, client=_qdrant_client(settings)
        )
    raise ValueError(f"Unknown lexical store '{settings.lexical_store}'")


def build_job_store(settings: Settings, blobs: BlobStore | None = None) -> JobStore:
    if settings.job_store == "sqlite":
        path = settings.data_dir / "jobs.sqlite3"
        if settings.blob_store != "local":
            from hyper_rag.stores.jobs import ReplicatedJobStore

            return ReplicatedJobStore(path, blobs or build_blob_store(settings))
        return SqliteJobStore(path)
    raise ValueError(f"Unknown job store '{settings.job_store}'")
