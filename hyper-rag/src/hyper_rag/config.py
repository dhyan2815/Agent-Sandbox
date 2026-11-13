"""Settings: config.yaml for defaults, environment variables / .env for overrides and secrets."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HYPER_RAG_",
        env_file=".env",
        yaml_file="config.yaml",
        extra="ignore",
    )

    # Generation
    llm_provider: Literal["fake", "groq", "gemini"] = "fake"
    llm_model: str = ""
    control_model: str = ""  # agent's routing/grading/checking calls; empty = use llm_model
    judge_provider: Literal["fake", "groq", "gemini"] = "fake"
    judge_model: str = ""
    reasoning_effort: str = "low"  # Groq only; passed through as reasoning_effort
    judge_reasoning_effort: str = "low"
    min_seconds_between_calls: float = 4.0
    max_retries: int = 6

    # API keys keep their conventional names (no HYPER_RAG_ prefix).
    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")

    # Retrieval
    embedder: Literal["fastembed", "hashing"] = "hashing"
    embedding_model: str = ""
    reranker: Literal["fastembed", "lexical"] = "lexical"
    reranker_model: str = ""
    candidates_per_retriever: int = 30
    rerank_pool: int = 20
    top_k: int = 5
    rrf_k: int = 60

    # Agent
    max_rewrites: int = 2

    # Uploaded documents
    ocr: Literal["rapidocr", "none"] = "rapidocr"  # local OCR for images and scanned pages
    max_upload_mb: int = 25  # direct, one-request uploads; bigger files use resumable uploads
    max_file_mb: int = 2048  # one file through a resumable upload
    max_collection_mb: int = 9000  # all originals in a collection (R2's free tier is 10 GB)
    max_collection_pages: int = 20000  # replaces the old 300-pages-per-file cap
    window_pages: int = 32  # pages read, embedded and committed together
    ingest_processes: int = 0  # >0: parse windows in this many worker processes
    ingest_workers: int = 1  # files read at the same time in the background
    upload_part_mb: float = 8  # resumable upload part size (MB)
    # Book structure (plan v2 phase 5)
    book_structure: bool = True  # outline paths, section summaries, chapter summaries
    max_chapter_summaries: int = 40  # LLM calls a "summarise the book" question may make
    summary_min_pages: int = 20  # shorter PDFs get no summaries: they are their own summary
    jit_wait_seconds: float = 15.0  # how long a question waits for pages it asked for
    upload_chunk_size: int = 1200
    upload_chunk_overlap: int = 150

    # Storage (see hyper_rag.stores). Only the local implementations exist so far;
    # the hosted ones (R2, Qdrant) arrive in plan v2 phase 2.
    blob_store: Literal["local", "s3"] = "local"
    vector_store: Literal["numpy", "qdrant"] = "numpy"
    lexical_store: Literal["bm25", "qdrant"] = "bm25"
    job_store: Literal["sqlite"] = "sqlite"  # copied to the blob store when that is remote
    # S3 / Cloudflare R2. Keys come from AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.
    s3_bucket: str = ""
    s3_endpoint: str = ""  # R2: https://<account id>.r2.cloudflarestorage.com
    s3_region: str = "auto"
    s3_prefix: str = ""
    # Qdrant: a URL (Qdrant Cloud, a server) or ":memory:". Key from QDRANT_API_KEY.
    qdrant_url: str = ""
    qdrant_api_key: str = Field(default="", validation_alias="QDRANT_API_KEY")
    qdrant_prefix: str = "hyper-rag-"

    # Login. Empty password = no login, for use on your own machine. Set HYPER_RAG_PASSWORD
    # (in .env or the host's secrets, never in config.yaml) before exposing the app.
    password: str = ""
    session_days: int = 30
    runs_kept: int = 50  # saved event logs of recent answers, per collection, for replay

    # Paths
    packs_dir: Path = Path("packs")
    data_dir: Path = Path("data")
    ui_dir: Path = Path("web/dist")  # the built React app; missing = serve the classic page

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Earlier sources win: explicit arguments, then env vars, then .env, then config.yaml.
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
        )

    def offline(self) -> "Settings":
        """Same settings, but with every component that needs a network or a key swapped out.

        Used by the tests and the CI eval: fake LLM, hashing embedder, lexical reranker.
        """
        return self.model_copy(
            update={
                "llm_provider": "fake",
                "judge_provider": "fake",
                "embedder": "hashing",
                "reranker": "lexical",
                "min_seconds_between_calls": 0.0,
            }
        )


def load_settings(offline: bool = False) -> Settings:
    settings = Settings()
    return settings.offline() if offline else settings
