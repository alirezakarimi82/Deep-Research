"""
Content extractor -- fetches and cleans the text of a web page.

Preference order:
  1. Jina Reader  (r.jina.ai proxy)       -- best quality, handles JS
  2. trafilatura  (local, no rate limit)  -- excellent article extraction
  3. BeautifulSoup fallback               -- last resort
"""
from __future__ import annotations

from typing import Optional

import httpx

from utils import log

MIN_USEFUL_LEN = 300


def extract(url: str, timeout: int = 15) -> Optional[str]:
    """Fetch *url* and return clean article text, or None if all strategies fail."""
    text = _jina(url, timeout)
    if text and len(text) > MIN_USEFUL_LEN:
        return text

    text = _trafilatura(url, timeout)
    if text and len(text) > MIN_USEFUL_LEN:
        return text

    text = _bs4(url, timeout)
    return text if text and len(text) > MIN_USEFUL_LEN else None


# -- Strategies ----------------------------------------------------------------

def _jina(url: str, timeout: int) -> Optional[str]:
    try:
        from retrieval.jina_reader import fetch_as_markdown
        return fetch_as_markdown(url, timeout=timeout)
    except Exception as exc:
        log.debug("Jina Reader failed for %s: %s", url, exc)
        return None


def _trafilatura(url: str, timeout: int) -> Optional[str]:
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            log.debug("trafilatura.fetch_url returned empty for %s", url)
            return None
        return trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
        )
    except Exception as exc:
        log.debug("trafilatura failed for %s: %s", url, exc)
        return None


def _bs4(url: str, timeout: int) -> Optional[str]:
    try:
        from bs4 import BeautifulSoup
        r = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 DeepResearch/1.0"},
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)
    except Exception as exc:
        log.debug("BS4 fallback failed for %s: %s", url, exc)
        return None
