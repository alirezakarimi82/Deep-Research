"""
Jina AI Reader -- converts any URL to clean Markdown.
No API key for basic use (~200 req/day on the free tier).
Handles JS-rendered pages, strips nav/ads/footers automatically.
Better than raw scraping for the vast majority of sites.
"""
from __future__ import annotations
import time
import httpx

JINA_BASE = "https://r.jina.ai/"


def fetch_as_markdown(url: str, timeout: int = 10) -> str:
    """Fetch *url* and return clean Markdown via the Jina Reader proxy."""
    headers = {
        "Accept":             "text/plain",
        "X-Return-Format":    "markdown",
        "X-Remove-Selector":  "header,footer,nav,.ads,.sidebar,.cookie",
        "X-Timeout":          str(timeout),
    }
    r = httpx.get(f"{JINA_BASE}{url}", headers=headers, timeout=timeout + 5)
    r.raise_for_status()
    return r.text


def batch_fetch(
    urls: list[str],
    delay: float = 0.5,
    skip_errors: bool = True,
) -> dict[str, str]:
    """
    Fetch multiple URLs sequentially with a small delay between requests.
    Returns {url: markdown} mapping.  Errors stored as "ERROR: ..." strings
    unless skip_errors=False, in which case they're propagated.
    """
    results: dict[str, str] = {}
    for url in urls:
        try:
            results[url] = fetch_as_markdown(url)
            time.sleep(delay)
        except Exception as exc:
            if not skip_errors:
                raise
            results[url] = f"ERROR: {exc}"
    return results
