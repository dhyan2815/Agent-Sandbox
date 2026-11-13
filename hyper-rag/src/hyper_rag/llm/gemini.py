"""Gemini through the Interactions API (the interface Google's docs recommend since June 2026).

Status: written from the public REST reference. It has unit tests against a recorded
response shape but has NOT been run against the live API in this project, because no
Gemini key was available when the evals were run. See README, "Known limitations".
"""

from hyper_rag.llm.base import LLMError
from hyper_rag.llm.http import HttpLLM
from hyper_rag.prompts import Prompt

URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
API_REVISION = "2026-05-20"

# max_output_tokens includes the model's thinking tokens, so leave room for them.
THINKING_HEADROOM = 600


class GeminiLLM(HttpLLM):
    def __init__(
        self, model: str, api_key: str, min_seconds_between_calls: float, max_retries: int
    ):
        super().__init__(min_seconds_between_calls, max_retries)
        self.name = f"gemini:{model}"
        self.model = model
        self.api_key = api_key

    def complete(self, prompt: Prompt) -> str:
        body = {
            "model": self.model,
            "system_instruction": prompt.system,
            "input": prompt.user,
            # No temperature: current Gemini models ignore custom sampling parameters.
            "generation_config": {
                "thinking_level": "low",
                "max_output_tokens": prompt.max_tokens + THINKING_HEADROOM,
            },
        }
        headers = {"x-goog-api-key": self.api_key, "Api-Revision": API_REVISION}
        return extract_text(self._post(URL, headers, body), self.name)


def extract_text(data: dict, name: str = "gemini") -> str:
    """Join the text blocks of the model_output steps; thought steps are skipped."""
    interaction = data.get("interaction", data)
    parts = [
        block.get("text", "")
        for step in interaction.get("steps", [])
        if step.get("type") == "model_output"
        for block in step.get("content", [])
        if block.get("type") == "text"
    ]
    if not parts:
        raise LLMError(f"{name}: no text in response: {str(data)[:300]}")
    return "".join(parts).strip()
