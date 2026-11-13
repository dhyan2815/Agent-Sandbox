"""Groq: an OpenAI-compatible chat completions endpoint."""

import re

from hyper_rag.llm.base import LLMError
from hyper_rag.llm.http import HttpLLM
from hyper_rag.prompts import Prompt

URL = "https://api.groq.com/openai/v1/chat/completions"

# The models on Groq's free tier reason before answering, and reasoning tokens count
# against max_completion_tokens. Without headroom a short JSON reply gets cut off.
REASONING_HEADROOM = 600


class GroqLLM(HttpLLM):
    def __init__(
        self,
        model: str,
        api_key: str,
        min_seconds_between_calls: float,
        max_retries: int,
        reasoning_effort: str = "low",
    ):
        super().__init__(min_seconds_between_calls, max_retries)
        self.name = f"groq:{model}"
        self.model = model
        self.api_key = api_key
        self.reasoning_effort = reasoning_effort

    def complete(self, prompt: Prompt) -> str:
        headroom = 0 if self.reasoning_effort == "none" else REASONING_HEADROOM
        body = {
            "model": self.model,
            "temperature": 0,  # evals need the most repeatable output the model can give
            # Groq charges the whole max_completion_tokens against the per-minute output
            # limit when the request arrives, so asking for more than needed slows a run.
            "max_completion_tokens": prompt.max_tokens + headroom,
            "reasoning_effort": self.reasoning_effort,
            "include_reasoning": False,  # only the final answer is used
            "messages": [
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": prompt.user},
            ],
        }
        data = self._post(URL, {"Authorization": f"Bearer {self.api_key}"}, body)
        try:
            content = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as error:
            raise LLMError(f"{self.name}: unexpected response shape: {str(data)[:300]}") from error
        # Some models inline their reasoning in <think> tags; never let that reach the user.
        return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
