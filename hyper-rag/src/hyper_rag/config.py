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
    max_upload_mb: int = 25
    max_units_per_file: int = 300  # pages / slides / sheets read from one file
    upload_chunk_size: int = 1200
    upload_chunk_overlap: int = 150

    # Storage (see hyper_rag.stores). Only the local implementations exist so far;
    # the hosted ones (R2, Qdrant) arrive in plan v2 phase 2.
    blob_store: Literal["local"] = "local"
    vector_store: Literal["numpy"] = "numpy"
    lexical_store: Literal["bm25"] = "bm25"
    job_store: Literal["sqlite"] = "sqlite"

    # Login. Empty password = no login, for use on your own machine. Set HYPER_RAG_PASSWORD
    # (in .env or the host's secrets, never in config.yaml) before exposing the app.
    password: str = ""
    session_days: int = 30
    runs_kept: int = 50  # saved event logs of recent answers, per collection, for replay

    # Paths
    packs_dir: Path = Path("packs")
    data_dir: Path = Path("data")

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
