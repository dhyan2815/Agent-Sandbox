"""LLM providers behind one interface. `build_llm` is the only place that picks one."""

from hyper_rag.config import Settings
from hyper_rag.llm.base import LLM, LLMError, complete_with_usage, parse_json
from hyper_rag.llm.cache import CachedLLM
from hyper_rag.llm.fake import FakeLLM
from hyper_rag.llm.gemini import GeminiLLM
from hyper_rag.llm.groq import GroqLLM

__all__ = ["LLM", "LLMError", "build_llm", "complete_with_usage", "parse_json"]


def build_llm(settings: Settings, role: str = "generator") -> LLM:
    """Create the LLM for a role.

    "generator" writes answers, "control" makes the agent's routing/grading/checking
    decisions, "judge" scores answers in evals.

    Hosted providers are wrapped in the disk cache. The fake provider is not: it is
    instant and deterministic already.
    """
    effort = settings.reasoning_effort
    if role == "judge":
        provider, model = settings.judge_provider, settings.judge_model
        effort = settings.judge_reasoning_effort
    elif role == "control":
        provider, model = settings.llm_provider, settings.control_model or settings.llm_model
    else:
        provider, model = settings.llm_provider, settings.llm_model
    pacing = (settings.min_seconds_between_calls, settings.max_retries)

    if provider == "fake":
        return FakeLLM()
    if provider == "groq":
        _require_key(settings.groq_api_key, "GROQ_API_KEY")
        llm: LLM = GroqLLM(model, settings.groq_api_key, *pacing, reasoning_effort=effort)
    elif provider == "gemini":
        _require_key(settings.gemini_api_key, "GEMINI_API_KEY")
        llm = GeminiLLM(model, settings.gemini_api_key, *pacing)
    else:
        raise ValueError(f"Unknown LLM provider '{provider}'")
    return CachedLLM(llm, settings.data_dir / "cache" / "llm")


def _require_key(value: str, name: str) -> None:
    if not value:
        raise LLMError(f"{name} is not set. Add it to .env, or run with --offline.")
