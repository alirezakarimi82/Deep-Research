"""
Reddit (public JSON API) and Hacker News (Algolia API).
Both provide practitioner knowledge not yet in peer-reviewed papers.

Reddit frequently 403s from datacenter IPs; we degrade gracefully to [].
"""
from __future__ import annotations

from utils import log, retryable_get

HN_API = "https://hn.algolia.com/api/v1"

_REDDIT_HEADERS = {
    "User-Agent": "DeepResearch/1.0 (research tool; contact: research@example.com)"
}


# -- Hacker News ---------------------------------------------------------------

def search_hackernews(
    query: str,
    max_results: int = 10,
    tags: str = "story",
) -> list[dict]:
    params = {
        "query":                query,
        "tags":                 tags,
        "hitsPerPage":          max_results,
        "attributesToRetrieve": "title,url,points,num_comments,created_at,objectID",
    }
    try:
        r = retryable_get(f"{HN_API}/search", params=params, timeout=10)
        r.raise_for_status()
    except Exception as exc:
        log.debug("HN search failed for %r: %s", query, exc)
        return []

    results: list[dict] = []
    for h in r.json().get("hits", []):
        url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID','')}"
        results.append({
            "title":               h.get("title", ""),
            "url":                 url,
            "snippet":             f"Points: {h.get('points',0)} | Comments: {h.get('num_comments',0)}",
            "date":                (h.get("created_at") or "")[:10],
            "full_text_available": True,
            "cited_by_count":      0,
            "source":              "hackernews",
        })
    return results


# -- Reddit --------------------------------------------------------------------

def search_reddit(
    query: str,
    subreddit: str = "all",
    max_results: int = 10,
    sort: str = "relevance",
) -> list[dict]:
    if subreddit == "all":
        url = "https://www.reddit.com/search.json"
    else:
        url = f"https://www.reddit.com/r/{subreddit}/search.json"

    params = {
        "q":           query,
        "sort":        sort,
        "limit":       max_results,
        "restrict_sr": subreddit != "all",
    }
    try:
        r = retryable_get(url, params=params, headers=_REDDIT_HEADERS, timeout=10)
        r.raise_for_status()
    except Exception as exc:
        log.debug("Reddit search failed for %r: %s", query, exc)
        return []

    results: list[dict] = []
    for post in r.json().get("data", {}).get("children", []):
        d = post.get("data", {})
        results.append({
            "title":               d.get("title", ""),
            "url":                 f"https://reddit.com{d.get('permalink', '')}",
            "snippet":             (d.get("selftext") or d.get("title") or "")[:400],
            "score":               d.get("score", 0),
            "subreddit":           d.get("subreddit", ""),
            "full_text_available": True,
            "cited_by_count":      0,
            "source":              "reddit",
        })
    return results


def relevant_subreddits(topic: str) -> list[str]:
    _MAP = {
        "machine learning":        ["MachineLearning", "deeplearning"],
        "artificial intelligence": ["MachineLearning", "artificial"],
        "energy":                  ["energy", "RenewableEnergy"],
        "battery":                 ["batteries", "electricvehicles"],
        "finance":                 ["investing", "algotrading", "quant"],
        "programming":             ["programming", "softwareengineering"],
        "medicine":                ["medicine", "askdocs"],
        "climate":                 ["climate", "ClimateChange"],
        "economics":               ["economics", "AskEconomics"],
        "physics":                 ["Physics", "AskPhysics"],
        "robotics":                ["robotics", "robots"],
    }
    t = topic.lower()
    for key, subs in _MAP.items():
        if key in t:
            return subs
    return ["all"]
