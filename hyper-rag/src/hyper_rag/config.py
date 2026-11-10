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
    groq_model: str = ""
    gemini_model: str = ""
    judge_provider: Literal["fake", "groq", "gemini"] = "fake"
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
