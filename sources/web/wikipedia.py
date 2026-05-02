"""Wikipedia -- free, unlimited. Good for background, definitions, concepts.

Search titles first, then fetch REST summary for each to populate a real
`abstract` (up to 1500 chars from the article lead).
"""
from __future__ import annotations

import re
from typing import Optional

from utils import log, retryable_get

REST_API   = "https://en.wikipedia.org/api/rest_v1"
SEARCH_API = "https://en.wikipedia.org/w/api.php"
_HEADERS   = {"User-Agent": "deep-research-pipeline/1.0 (research tool)"}


def search_wikipedia(query: str, max_results: int = 5) -> list[dict]:
    """Search Wikipedia and return results with real abstracts."""
    params = {
        "action":   "query",
        "list":     "search",
        "srsearch": query,
        "srlimit":  max_results,
        "format":   "json",
        "srprop":   "snippet",
    }
    try:
        r = retryable_get(SEARCH_API, params=params, headers=_HEADERS, timeout=10)
        r.raise_for_status()
    except Exception as exc:
        log.debug("Wikipedia search failed for %r: %s", query, exc)
        return []

    results: list[dict] = []
    for item in r.json().get("query", {}).get("search", []):
        title = item.get("title", "")
        summary = get_summary(title)
        if summary:
            results.append(summary)
        else:
            snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
            results.append({
                "title":               title,
                "abstract":            snippet or None,
                "url":                 f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                "authors":             ["Wikipedia contributors"],
                "year":                None,
                "full_text_available": False,
                "cited_by_count":      0,
                "source":              "wikipedia",
            })
    return results


def get_summary(title: str) -> Optional[dict]:
    """Fetch the plain-text lead of a Wikipedia article via the REST API."""
    try:
        r = retryable_get(
            f"{REST_API}/page/summary/{title.replace(' ', '_')}",
            headers=_HEADERS,
            timeout=10,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        d = r.json()
        extract = (d.get("extract") or "").strip()
        if not extract:
            return None
        return {
            "title":               d.get("title", title),
            "abstract":            extract[:1500],
            "url":                 (d.get("content_urls") or {})
                                   .get("desktop", {}).get("page", ""),
            "authors":             ["Wikipedia contributors"],
            "year":                None,
            "full_text_available": True,
            "cited_by_count":      0,
            "source":              "wikipedia",
        }
    except Exception as exc:
        log.debug("Wikipedia summary failed for %r: %s", title, exc)
        return None
