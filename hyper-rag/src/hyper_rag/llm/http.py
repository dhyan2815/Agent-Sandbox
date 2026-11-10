"""Shared HTTP plumbing for the hosted providers: pacing, retry with backoff, error handling."""

import re
import time

import httpx

from hyper_rag.llm.base import LLMError

# If the provider asks us to wait longer than this, the per-minute budget is not the
# problem: a daily quota is exhausted. Stop instead of sleeping for hours; cached
# replies and resumable eval runs mean nothing is lost.
MAX_WAIT_SECONDS = 90.0


def parse_retry_after(value: str | None) -> float | None:
    """Read a Retry-After style value: '7', '7.5', '2m30s' or '12.3s'."""
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        match = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:([\d.]+)s)?", value.strip())
        if not match or not any(match.groups()):
            return None
        hours, minutes, seconds = (float(g) if g else 0.0 for g in match.groups())
        return hours * 3600 + minutes * 60 + seconds


class HttpLLM:
    """Base class: subclasses build the request and pick the text out of the response."""

    name = "http"

    def __init__(self, min_seconds_between_calls: float, max_retries: int):
        self.min_seconds_between_calls = min_seconds_between_calls
        self.max_retries = max_retries
        self._client = httpx.Client(timeout=60)
        self._last_call = 0.0

    def _pace(self) -> None:
        # A fixed gap between calls keeps a long eval under the requests-per-minute cap
        # without tracking a sliding window.
        pause = self.min_seconds_between_calls - (time.monotonic() - self._last_call)
        if pause > 0:
            time.sleep(pause)
        self._last_call = time.monotonic()

    def _post(self, url: str, headers: dict, body: dict) -> dict:
        for attempt in range(self.max_retries + 1):
            self._pace()
            try:
                response = self._client.post(url, headers=headers, json=body)
            except httpx.TransportError as error:
                reason, wait = f"network error: {error}", None
            else:
                if response.status_code < 400:
                    return response.json()
                if response.status_code != 429 and response.status_code < 500:
                    # 400/401/403/404: retrying the same request cannot succeed.
                    raise LLMError(
                        f"{self.name}: HTTP {response.status_code}: {response.text[:300]}"
                    )
                reason = f"HTTP {response.status_code}"
                wait = parse_retry_after(response.headers.get("retry-after"))
            # Prefer the provider's own hint; otherwise exponential backoff: 2, 4, 8, ... seconds.
            wait = wait if wait is not None else min(2.0 ** (attempt + 1), 60.0)
            if wait > MAX_WAIT_SECONDS:
                raise LLMError(
                    f"{self.name}: {reason}, asked to wait {wait:.0f}s (daily quota?). "
                    "Re-run later: finished work is cached."
                )
            if attempt < self.max_retries:
                time.sleep(wait + 0.5)
        raise LLMError(f"{self.name}: gave up after {self.max_retries + 1} attempts ({reason})")
