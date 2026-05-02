"""
Semantic Scholar -- free API with citation graph, AI TLDRs, and OA PDF links.

Tiers:
  Unauthenticated : 100 req / 5 min
  Free API key    : 10k req / min (semanticscholar.org/product/api)

Full-text gate: only papers with openAccessPdf.url are returned.
"""
from __future__ import annotations

from datetime import datetime

from utils import retryable_get

BASE = "https://api.semanticscholar.org/graph/v1"

_FIELDS = (
    "paperId,title,abstract,year,citationCount,"
    "openAccessPdf,authors,venue,externalIds,tldr,isOpenAccess"
)


def _current_year() -> int:
    return datetime.now().year


def search_papers(
    query: str,
    max_results: int = 20,
    api_key: str = "",
    oa_only: bool = True,
) -> list[dict]:
    headers = {"x-api-key": api_key} if api_key else {}
    params: dict = {
        "query":  query,
        "limit":  min(max_results, 100),
        "fields": _FIELDS,
    }
    if oa_only:
        params["openAccessPdf"] = ""

    r = retryable_get(
        f"{BASE}/paper/search",
        params=params,
        headers=headers,
        timeout=15,
    )
    r.raise_for_status()
    papers = [_norm(p) for p in r.json().get("data", [])]
    return [p for p in papers if p["full_text_available"]]


def search_papers_two_pass(
    query: str,
    max_per_pass: int = 15,
    api_key: str = "",
) -> list[dict]:
    headers = {"x-api-key": api_key} if api_key else {}
    recent_year = _current_year() - 3

    # Pass A -- recent OA
    params_a = {
        "query":         query,
        "limit":         max_per_pass,
        "fields":        _FIELDS,
        "year":          f"{recent_year}-",
        "openAccessPdf": "",
    }
    r_a = retryable_get(
        f"{BASE}/paper/search",
        params=params_a,
        headers=headers,
        timeout=15,
    )
    r_a.raise_for_status()
    recent = [
        _norm(p) for p in r_a.json().get("data", [])
    ]
    recent = [p for p in recent if p["full_text_available"]]

    # Pass B -- all years, fetch 3x and sort client-side by citations
    params_b = {
        "query":         query,
        "limit":         min(max_per_pass * 3, 100),
        "fields":        _FIELDS,
        "openAccessPdf": "",
    }
    r_b = retryable_get(
        f"{BASE}/paper/search",
        params=params_b,
        headers=headers,
        timeout=15,
    )
    r_b.raise_for_status()
    all_oa = [_norm(p) for p in r_b.json().get("data", [])]
    all_oa = [p for p in all_oa if p["full_text_available"]]
    classics = sorted(
        all_oa,
        key=lambda p: p["cited_by_count"],
        reverse=True,
    )[:max_per_pass]

    return recent + classics


def get_open_access_references(
    paper_id: str,
    max_refs: int = 8,
    api_key: str = "",
) -> list[dict]:
    """
    Citation-chain expansion: return top-cited OA references of a paper.

    Previously made N+1 network calls (one parent + one per ref).  Now
    requests the full nested fields in a single call.
    """
    headers = {"x-api-key": api_key} if api_key else {}
    nested = ",".join(f"references.{f}" for f in [
        "paperId", "title", "abstract", "year", "citationCount",
        "openAccessPdf", "authors", "venue", "externalIds", "tldr", "isOpenAccess",
    ])
    r = retryable_get(
        f"{BASE}/paper/{paper_id}",
        params={"fields": nested},
        headers=headers,
        timeout=15,
    )
    r.raise_for_status()
    refs = r.json().get("references", []) or []

    # Keep only refs with an OA PDF, sort by citation count, cap at max_refs
    oa_refs = [
        ref for ref in refs
        if (ref.get("openAccessPdf") or {}).get("url")
    ]
    oa_refs.sort(key=lambda x: x.get("citationCount") or 0, reverse=True)
    return [_norm(ref) for ref in oa_refs[:max_refs]]


# -- Internal ------------------------------------------------------------------

def _norm(p: dict) -> dict:
    oa_pdf = (p.get("openAccessPdf") or {}).get("url", "") or ""
    return {
        "id":                  p.get("paperId", ""),
        "title":               p.get("title") or "",
        "abstract":            p.get("abstract") or "",
        "year":                p.get("year"),
        "doi":                 (p.get("externalIds") or {}).get("DOI"),
        "arxiv_id":            (p.get("externalIds") or {}).get("ArXiv"),
        "pdf_url":             oa_pdf or None,
        "full_text_available": bool(oa_pdf) or bool(p.get("isOpenAccess")),
        "citations":           p.get("citationCount", 0) or 0,
        "cited_by_count":      p.get("citationCount", 0) or 0,
        "authors":             [a.get("name", "") for a in (p.get("authors") or [])[:6]],
        "venue":               p.get("venue"),
        "tldr":                (p.get("tldr") or {}).get("text"),
        "source":              "semantic_scholar",
    }
