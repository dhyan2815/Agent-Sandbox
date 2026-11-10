"""LLM providers behind one interface. `build_llm` is the only place that picks one."""

from hyper_rag.config import Settings
from hyper_rag.llm.base import LLM, LLMError, parse_json
from hyper_rag.llm.cache import CachedLLM
from hyper_rag.llm.fake import FakeLLM

__all__ = ["LLM", "LLMError", "build_llm", "parse_json"]


def build_llm(settings: Settings, provider: str | None = None) -> LLM:
    """Create the configured provider, wrapped in the disk cache (the fake needs no cache)."""
    provider = provider or settings.llm_provider
    if provider == "fake":
        return FakeLLM()
    raise ValueError(f"Unknown LLM provider '{provider}'")


def _cached(llm: LLM, settings: Settings) -> LLM:
    return CachedLLM(llm, settings.data_dir / "cache" / "llm")
