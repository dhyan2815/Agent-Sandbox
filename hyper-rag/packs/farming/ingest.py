"""Farming pack ingestion: a fixed list of Wikipedia articles."""

from pathlib import Path

from hyper_rag.types import Document
from hyper_rag.web import PoliteFetcher, html_to_markdown

# Parts of a Wikipedia page that are not article prose.
DROP = (
    ".mw-editsection", "sup.reference", ".reflist", ".navbox", ".infobox", ".hatnote",
    ".metadata", ".sidebar", ".thumb", "figure", ".mw-references-wrap", ".refbegin",
    ".catlinks", ".noprint", ".toc", ".shortdescription",
)  # fmt: skip
# Sections after the prose: lists of links and citations add noise, not answers.
STOP_HEADINGS = (
    "## See also",
    "## References",
    "## External links",
    "## Notes",
    "## Further reading",
)


def fetch(pack, raw_dir: Path):
    fetcher = PoliteFetcher(raw_dir, delay_seconds=3.0)
    for source in pack.config.sources:
        for article in source["articles"]:
            url = source["base_url"] + article
            html = fetcher.get(url)
            if html is None:
                continue
            title, text = html_to_markdown(html, "#mw-content-text", drop_selectors=DROP)
            for heading in STOP_HEADINGS:
                text = text.split(f"\n\n{heading}")[0]
            title = title.removesuffix(" - Wikipedia")
            yield Document(id=article, title=title, url=url, text=text)
