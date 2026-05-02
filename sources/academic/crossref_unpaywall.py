"""
Crossref -- free DOI metadata, 50 req/sec polite pool.
Unpaywall -- OA PDFs for paywalled papers (100k req/day, email only).

Workflow:
  1. search_crossref()       -> list of papers
  2. enrich_with_unpaywall() -> parallel fan-out, fills pdf_url where Unpaywall
                                finds an OA copy, drops papers that remain
                                inaccessible when drop_inaccessible=True.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from utils import log, retryable_get

CROSSREF_BASE  = "https://api.crossref.org/works"
UNPAYWALL_BASE = "https://api.unpaywall.org/v2"

_VERSION_RANK = {"publishedVersion": 0, "acceptedVersion": 1, "submittedVersion": 2}
_DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "doi:")


def search_crossref(
    query: str,
    max_results: int = 20,
    from_year: Optional[int] = None,
    email: str = "research@example.com",
) -> list[dict]:
    params: dict = {
        "query":  query,
        "rows":   min(max_results, 100),
        "select": (
            "DOI,title,abstract,author,published,"
            "container-title,is-referenced-by-count,type,URL"
        ),
        "mailto": email,
        "sort":   "score",
        "order":  "desc",
    }
    if from_year:
        params["filter"] = f"from-pub-date:{from_year}"

    r = retryable_get(CROSSREF_BASE, params=params, timeout=15)
    r.raise_for_status()

    results: list[dict] = []
    for item in r.json().get("message", {}).get("items", []):
        title_list = item.get("title") or []
        title      = title_list[0] if title_list else ""
        if not title:
            continue

        authors: list[str] = []
        for a in item.get("author", [])[:6]:
            parts = [a.get("given", ""), a.get("family", "")]
            authors.append(" ".join(p for p in parts if p))

        pub        = item.get("published") or {}
        date_parts = (pub.get("date-parts") or [[]])[0]
        year       = date_parts[0] if date_parts else None

        venue_list = item.get("container-title") or []
        doi        = item.get("DOI", "")

        results.append({
            "id":                  doi,
            "title":               title,
            "abstract":            item.get("abstract", ""),
            "authors":             authors,
            "year":                year,
            "doi":                 doi,
            "pdf_url":             None,
            "full_text_available": False,
            "venue":               venue_list[0] if venue_list else None,
            "cited_by_count":      item.get("is-referenced-by-count", 0),
            "type":                item.get("type", ""),
            "url":                 item.get("URL", ""),
            "source":              "crossref",
        })
    return results


def _clean_doi(doi: str) -> str:
    for prefix in _DOI_PREFIXES:
        if doi.lower().startswith(prefix.lower()):
            return doi[len(prefix):]
    return doi


def find_oa_pdf(doi: str, email: str = "research@example.com") -> dict:
    """Query Unpaywall for a single DOI. Uses retryable_get.

    Returns {} on 404 or error, otherwise a dict with:
      pdf_url, landing_url, oa_status, is_oa
    """
    if not doi:
        return {}
    clean = _clean_doi(doi.strip())
    try:
        r = retryable_get(
            f"{UNPAYWALL_BASE}/{clean}",
            params={"email": email},
            timeout=10,
        )
        if r.status_code == 404:
            return {}
        r.raise_for_status()
        data = r.json()

        is_oa     = data.get("is_oa", False)
        oa_status = data.get("oa_status")

        if not is_oa:
            return {
                "pdf_url":     None,
                "landing_url": None,
                "oa_status":   oa_status,
                "is_oa":       False,
            }

        best    = data.get("best_oa_location") or {}
        pdf_url = best.get("url_for_pdf") or None

        if not pdf_url:
            candidates = [
                loc for loc in (data.get("oa_locations") or [])
                if loc.get("url_for_pdf")
            ]
            if candidates:
                candidates.sort(
                    key=lambda loc: _VERSION_RANK.get(loc.get("version", ""), 99)
                )
                pdf_url = candidates[0]["url_for_pdf"]

        landing_url = None
        if not pdf_url:
            landing_url = (
                best.get("url_for_landing_page")
                or best.get("url")
                or None
            )

        return {
            "pdf_url":     pdf_url,
            "landing_url": landing_url,
            "oa_status":   oa_status,
            "is_oa":       is_oa,
        }
    except Exception as exc:
        log.debug("Unpaywall lookup failed for %s: %s", clean, exc)
        return {}


def enrich_with_unpaywall(
    sources: list[dict],
    email: str = "research@example.com",
    drop_inaccessible: bool = True,
    max_workers: int = 8,
) -> list[dict]:
    """
    Concurrent Unpaywall enrichment. ~8x faster than the old sequential loop
    for a typical 20-item Crossref batch.
    """
    # Only sources that need lookup
    pending_idx = [
        i for i, s in enumerate(sources)
        if not s.get("pdf_url") and s.get("doi")
    ]

    if pending_idx:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_to_idx = {
                pool.submit(find_oa_pdf, sources[i]["doi"], email): i
                for i in pending_idx
            }
            for fut in as_completed(future_to_idx):
                i = future_to_idx[fut]
                try:
                    result = fut.result()
                except Exception as exc:
                    log.debug("Unpaywall worker failed: %s", exc)
                    result = {}
                s = sources[i]
                if result:
                    if result.get("pdf_url"):
                        s["pdf_url"]             = result["pdf_url"]
                        s["full_text_available"] = True
                    elif result.get("landing_url"):
                        s["landing_url"]         = result["landing_url"]
                        s["full_text_available"] = True
                    if result.get("oa_status"):
                        s["oa_status"] = result["oa_status"]

    if not drop_inaccessible:
        return sources
    return [s for s in sources if s.get("full_text_available")]


def resolve_doi(doi: str, email: str = "research@example.com") -> Optional[dict]:
    """Full Crossref metadata for a single DOI."""
    try:
        r = retryable_get(
            f"{CROSSREF_BASE}/{doi}",
            params={"mailto": email},
            timeout=10,
        )
        if r.status_code != 200:
            return None
        return r.json().get("message")
    except Exception as exc:
        log.debug("Crossref resolve failed for %s: %s", doi, exc)
        return None
