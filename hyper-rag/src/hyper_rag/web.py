"""Helpers for pack ingest scripts that read public web pages.

Two jobs: fetch politely (robots.txt, a delay between requests, an on-disk copy so a
re-run downloads nothing) and turn an HTML page into markdown-like text whose headings
the chunker can use.
"""

import hashlib
import os
import re
import time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag

# Sites such as Wikipedia ask automated clients to say who they are. Set
# HYPER_RAG_CONTACT (a project URL or an email address) to include it in the User-Agent.
_CONTACT = os.environ.get("HYPER_RAG_CONTACT", "educational portfolio project; polite crawler")
USER_AGENT = f"hyper-rag-ingest/0.1 ({_CONTACT})"

_BLOCK_TAGS = frozenset(
    "div p li ul ol section article table thead tbody blockquote dl dt dd br details summary "
    "figure figcaption".split()
)
_NOISE_TAGS = ["script", "style", "nav", "aside", "footer", "header", "button", "svg", "form"]


class PoliteFetcher:
    def __init__(self, raw_dir: Path, delay_seconds: float = 1.0, cookies: dict | None = None):
        self.raw_dir = raw_dir
        self.delay_seconds = delay_seconds
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT}, cookies=cookies, follow_redirects=True, timeout=30
        )
        self._robots: dict[str, RobotFileParser] = {}
        self._last_request = 0.0

    def _wait(self) -> None:
        pause = self.delay_seconds - (time.monotonic() - self._last_request)
        if pause > 0:
            time.sleep(pause)
        self._last_request = time.monotonic()

    def _allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self._robots:
            parser = RobotFileParser()
            self._wait()
            response = self._client.get(f"{host}/robots.txt")
            if response.status_code in (401, 403):
                parser.disallow_all = True  # the site refuses crawlers: treat as "no"
            elif response.status_code >= 400:
                parser.allow_all = True  # no robots.txt: nothing is disallowed
            else:
                parser.parse(response.text.splitlines())
            self._robots[host] = parser
        parser = self._robots[host]
        # Honour a Crawl-delay directive when it asks for more time than our default.
        requested = parser.crawl_delay(USER_AGENT)
        if requested:
            self.delay_seconds = max(self.delay_seconds, float(requested))
        return parser.can_fetch(USER_AGENT, url)

    def get_bytes(self, url: str, suffix: str = ".html") -> bytes | None:
        """Return the response body, or None if robots.txt disallows it or the request fails."""
        cached = self.raw_dir / f"{hashlib.sha256(url.encode()).hexdigest()[:24]}{suffix}"
        if cached.exists():
            return cached.read_bytes()
        if not self._allowed(url):
            print(f"  skipped (robots.txt): {url}")
            return None
        for attempt in range(3):
            self._wait()
            try:
                response = self._client.get(url)
                if response.status_code in (429, 503) and attempt < 2:
                    # The site is asking us to slow down: wait as told, then try again.
                    time.sleep(float(response.headers.get("retry-after", 20)))
                    continue
                response.raise_for_status()
                break
            except (httpx.HTTPError, ValueError) as error:
                print(f"  skipped ({error.__class__.__name__}): {url}")
                return None
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(response.content)
        return response.content

    def get(self, url: str) -> str | None:
        """Return the page as text (HTML, XML), or None if it could not be fetched."""
        body = self.get_bytes(url)
        return None if body is None else body.decode("utf-8", errors="replace")


def _clean(text: str) -> str:
    # Zero-width spaces and non-breaking spaces show up in rendered docs sites.
    return re.sub(r"\s+", " ", text.replace("​", "").replace("\xa0", " ")).strip()


def html_to_markdown(
    html: str, content_selector: str = "main", drop_selectors: tuple[str, ...] = ()
) -> tuple[str, str]:
    """Convert a page to (title, markdown-like text).

    Headings become '#' lines, table rows become 'a | b | c' lines, list items get a
    '- ' prefix, and all other text is grouped into paragraphs at block boundaries.
    Navigation, scripts and buttons are dropped.
    """
    soup = BeautifulSoup(html, "html.parser")
    page_title = _clean(soup.title.get_text()) if soup.title else ""
    root = soup.select_one(content_selector) or soup.body or soup
    for element in root.find_all(_NOISE_TAGS):
        element.decompose()
    for selector in drop_selectors:
        for element in root.select(selector):
            element.decompose()

    lines: list[str] = []
    buffer: list[str] = []  # inline text collected since the last block boundary

    def flush() -> None:
        text = _clean(" ".join(buffer))
        buffer.clear()
        # Skip fragments with no words in them (stray bullets, icon glyphs).
        if re.search(r"[A-Za-z0-9]{2}", text):
            lines.append(text)

    def walk(node: Tag) -> None:
        for child in node.children:
            if isinstance(child, NavigableString):
                buffer.append(str(child))
            elif not isinstance(child, Tag):
                continue
            elif re.fullmatch(r"h[1-6]", child.name):
                flush()
                heading = _clean(child.get_text(" "))
                if heading:
                    lines.append(f"{'#' * int(child.name[1])} {heading}")
            elif child.name == "tr":
                flush()
                cells = [_clean(cell.get_text(" ")) for cell in child.find_all(["th", "td"])]
                row = " | ".join(cell for cell in cells if cell)
                if row:
                    lines.append(row)
            elif child.name == "pre":
                flush()
                lines.append(child.get_text().strip())
            elif child.name in _BLOCK_TAGS:
                # Docs sites often put paragraphs in <div>s, so any block-level tag
                # ends the current paragraph, not just <p>.
                flush()
                if child.name == "li":
                    buffer.append("- ")
                walk(child)
                flush()
            else:
                walk(child)  # inline tag (<a>, <code>, <span>, <b>): text stays in the paragraph

    walk(root)
    flush()
    return page_title, "\n\n".join(lines)
