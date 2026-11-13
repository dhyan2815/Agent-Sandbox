import httpx
import pytest

from hyper_rag.llm.base import LLMError
from hyper_rag.llm.gemini import extract_text
from hyper_rag.llm.groq import GroqLLM
from hyper_rag.llm.http import parse_retry_after
from hyper_rag.prompts import Prompt

PROMPT = Prompt("generate", "system", "user")


def groq_with(handler, max_retries=2) -> GroqLLM:
    """A Groq provider whose HTTP calls are answered by `handler` instead of the network."""
    llm = GroqLLM("test-model", "key", min_seconds_between_calls=0, max_retries=max_retries)
    llm._client = httpx.Client(transport=httpx.MockTransport(handler))
    return llm


def reply(text: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


def test_retry_after_formats():
    assert parse_retry_after("7") == 7.0
    assert parse_retry_after("2m30s") == 150.0
    assert parse_retry_after("12.5s") == 12.5
    assert parse_retry_after(None) is None and parse_retry_after("soon") is None


def test_groq_sends_prompt_and_strips_inline_reasoning():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.read().decode()
        seen["auth"] = request.headers["authorization"]
        return reply("<think>hmm</think>The answer [1]")

    assert groq_with(handler).complete(PROMPT) == "The answer [1]"
    assert '"temperature":0' in seen["body"].replace(" ", "") and seen["auth"] == "Bearer key"


def test_rate_limit_is_retried_using_retry_after():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, headers={"retry-after": "0"}, json={})
        return reply("ok")

    assert groq_with(handler).complete(PROMPT) == "ok"
    assert len(calls) == 2


def test_long_wait_stops_instead_of_sleeping():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"retry-after": "3600"}, json={})

    with pytest.raises(LLMError, match="daily quota"):
        groq_with(handler).complete(PROMPT)


def test_client_errors_are_not_retried():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(401, json={"error": "bad key"})

    with pytest.raises(LLMError, match="HTTP 401"):
        groq_with(handler).complete(PROMPT)
    assert len(calls) == 1


def test_gemini_text_extraction_skips_thought_steps():
    response = {
        "id": "v1_x",
        "status": "completed",
        "steps": [
            {"type": "thought", "signature": "abc"},
            {"type": "model_output", "content": [{"type": "text", "text": "Refunds take "}]},
            {"type": "model_output", "content": [{"type": "text", "text": "5-7 days [1]"}]},
        ],
    }
    assert extract_text(response) == "Refunds take 5-7 days [1]"
    with pytest.raises(LLMError):
        extract_text({"steps": []})
