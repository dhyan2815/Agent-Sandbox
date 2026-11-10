"""Payments pack ingestion: Razorpay docs (from the sitemap) and Google Wallet docs (from links)."""

import re
from pathlib import Path

from bs4 import BeautifulSoup

from hyper_rag.types import Document
from hyper_rag.web import PoliteFetcher, html_to_markdown

MIN_CHARS = 200  # shorter pages are redirect stubs or empty landing pages


def _razorpay(source: dict, fetcher: PoliteFetcher):
    sitemap = fetcher.get(source["sitemap"]) or ""
    urls = re.findall(r"<loc>([^<]+)</loc>", sitemap)
    base = source["base_url"]
    for url in sorted(set(urls)):
        path = url.removeprefix(base).strip("/")
        if not any(path == s or path.startswith(s + "/") for s in source["sections"]):
            continue
        html = fetcher.get(url)
        if html is None:
            continue
        title, text = html_to_markdown(html, content_selector="main")
        if len(text) < MIN_CHARS:
            continue
        title = title.removesuffix(" - Razorpay").removesuffix(" | Razorpay Docs")
        yield Document(id=f"razorpay/{path}", title=f"Razorpay: {title}", url=url, text=text)


def _google_wallet(source: dict, fetcher: PoliteFetcher):
    landing = fetcher.get(source["start_url"]) or ""
    links = {source["start_url"]}
    for anchor in BeautifulSoup(landing, "html.parser").find_all("a", href=True):
        href = anchor["href"].split("#")[0].split("?")[0]
        if href.startswith(source["link_prefix"]):
            links.add(f"https://developers.google.com{href}")
    for url in sorted(links):
        html = fetcher.get(url)
        if html is None:
            continue
        title, text = html_to_markdown(html, content_selector=".devsite-article-body")
        if len(text) < MIN_CHARS:
            continue
        path = url.removeprefix(source["base_url"]).strip("/")
        title = title.split("|")[0].strip()
        yield Document(
            id=f"google-wallet/{path}", title=f"Google Wallet: {title}", url=url, text=text
        )


def fetch(pack, raw_dir: Path):
    for source in pack.config.sources:
        if source["name"] == "razorpay":
            # The docs site redirects by visitor location; this cookie pins the India edition.
            fetcher = PoliteFetcher(raw_dir, delay_seconds=1.0, cookies={"preferred_country": "IN"})
            yield from _razorpay(source, fetcher)
        elif source["name"] == "google-wallet":
            yield from _google_wallet(source, PoliteFetcher(raw_dir, delay_seconds=1.0))
