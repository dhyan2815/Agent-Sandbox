"""The one interface every LLM provider implements."""

import json
import re
from typing import Protocol

from hyper_rag.prompts import Prompt


class LLM(Protocol):
    name: str  # "<provider>:<model>", used in cache keys and eval reports

    def complete(self, prompt: Prompt) -> str:
        """Return the model's text reply to one system + user prompt."""
        ...


def complete_with_usage(llm: LLM, prompt: Prompt) -> tuple[str, dict]:
    """Call the model and also return what the call cost, where the provider says.

    Providers that know their usage implement `complete_with_usage` themselves and return
    any of: tokens_in, tokens_out, cached (True when the reply came from the disk cache)
    and the provider's rate-limit counters. The rest return an empty dict. Usage travels
    with the reply instead of sitting on the LLM object, because one LLM object serves
    several requests at once.
    """
    method = getattr(llm, "complete_with_usage", None)
    if method is None:
        return llm.complete(prompt), {}
    return method(prompt)


class LLMError(RuntimeError):
    """A provider call failed and retrying did not help."""


def parse_json(reply: str) -> dict:
    """Read a JSON object out of a model reply.

    Models often wrap JSON in a code fence or add a sentence around it, so take the
    outermost {...} rather than trusting the whole reply. Returns {} if there is none:
    callers treat a missing field as the conservative choice.
    """
    match = re.search(r"\{.*\}", reply, flags=re.DOTALL)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
