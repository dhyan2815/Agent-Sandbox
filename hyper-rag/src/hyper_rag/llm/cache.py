"""Disk cache for LLM replies.

Free tiers are slow and capped, and an eval asks the same questions repeatedly while the
code around them changes. Caching by exact prompt means a re-run only pays for calls
whose prompt actually changed, and a run interrupted by a rate limit loses nothing.
"""

import hashlib
import json
from pathlib import Path

from hyper_rag.llm.base import LLM, complete_with_usage
from hyper_rag.prompts import Prompt


class CachedLLM:
    def __init__(self, inner: LLM, cache_dir: Path):
        self.inner = inner
        self.name = inner.name
        self.cache_dir = cache_dir
        self.hits = 0
        self.misses = 0

    def _path(self, prompt: Prompt) -> Path:
        # The model name is part of the key: switching model must not reuse old replies.
        key = "\x1f".join([self.name, prompt.system, prompt.user, str(prompt.max_tokens)])
        return self.cache_dir / f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.json"

    def complete(self, prompt: Prompt) -> str:
        return self.complete_with_usage(prompt)[0]

    def complete_with_usage(self, prompt: Prompt) -> tuple[str, dict]:
        path = self._path(prompt)
        if path.exists():
            self.hits += 1
            reply = json.loads(path.read_text(encoding="utf-8"))["reply"]
            return reply, {"model": self.name, "cached": True}
        reply, usage = complete_with_usage(self.inner, prompt)
        self.misses += 1
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        record = {"model": self.name, "task": prompt.task, "reply": reply}
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        return reply, usage
