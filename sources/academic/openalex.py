"""
OpenAlex source -- 250 M+ works, free, polite-pool via email.

Optional: set OPENALEX_API_KEY env var (or openalex_api_key in config.yaml)
to unlock:
  1. Semantic search (Pass A uses search.semantic)
  2. Full-text access via content.openalex.org (populates content_url)
  3. has_content.pdf:true filter (applied to BOTH passes when a key is set)

Full-text gate: only papers with a usable oa_url, a content_url, OR a
recognized OA status are returned. Closed and abstract-only entries are
dropped before the ranker ever sees them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from utils import retryable_get

BASE         = "https://api.openalex.org"
CONTENT_BASE = "https://content.openalex.org"

_SELECT = (
    "id,title,abstract_inverted_index,publication_year,"
    "doi,open_access,cited_by_count,concepts,authorships,primary_location"
)


def _current_year() -> int:
    return datetime.now().year


@dataclass
class Work:
    id: str
    title: str
    abstract: Optional[str]
    year: Optional[int]
    doi: Optional[str]
    pdf_url: Optional[str]
    content_url: Optional[str]
    oa_status: Optional[str]
    full_text_available: bool
    cited_by_count: int
    concepts: list[str] = field(default_factory=list)
    authors:  list[str] = field(default_factory=list)
    venue:    Optional[str] = None
    source:   str = "openalex"


def search_works(
    query: str,
    max_results: int = 20,
    from_year: Optional[int] = None,
    oa_only: bool = True,
    email: str = "research@example.com",
    api_key: str = "",
    semantic: bool = False,
    require_pdf: bool = False,
    sort: str = "relevance_score:desc",
) -> list[Work]:
    """Single-pass search against GET /works.

    Semantic mode cannot accept filter= or sort=, so those are enforced
    in Python post-fetch.
    """
    params: dict = {
        "per-page": min(max_results, 50),
        "select":   _SELECT,
        "mailto":   email,
    }

    if semantic and api_key:
        params["search.semantic"] = query
        params["api_key"]         = api_key
    else:
        params["search"] = query
        params["sort"]   = sort

        _filters: list[str] = []
        if from_year:
            _filters.append(f"publication_year:>{from_year}")
        if oa_only:
            _filters.append("is_oa:true")
        if require_pdf and api_key:
            _filters.append("has_content.pdf:true")
        if _filters:
            params["filter"] = ",".join(_filters)

        if api_key:
            params["api_key"] = api_key

    r = retryable_get(f"{BASE}/works", params=params, timeout=15)
    r.raise_for_status()
    parsed = [_parse(item, api_key=api_key) for item in r.json().get("results", [])]

    # Post-filter for semantic mode
    if semantic:
        if from_year:
            parsed = [w for w in parsed if w.year and w.year > from_year]
        if oa_only:
            parsed = [w for w in parsed if w.full_text_available]

    return [w for w in parsed if w.full_text_available]


def search_works_two_pass(
    query: str,
    max_per_pass: int = 15,
    email: str = "research@example.com",
    api_key: str = "",
) -> list[Work]:
    """
    Pass A: recent (last 3 years) + OA, relevance-sorted.
            Semantic search + has_content.pdf when an API key is configured.
    Pass B: all years + OA, citation-sorted.
            ALSO applies has_content.pdf when an API key is configured
            (previously missing -- papers without real PDFs were slipping through).
    """
    recent = search_works(
        query,
        max_results=max_per_pass,
        from_year=_current_year() - 3,
        oa_only=True,
        email=email,
        api_key=api_key,
        semantic=bool(api_key),
        require_pdf=bool(api_key),
    )

    classics = search_works(
        query,
        max_results=max_per_pass,
        oa_only=True,
        email=email,
        api_key=api_key,
        semantic=False,                 # keyword + citation sort
        require_pdf=bool(api_key),
        sort="cited_by_count:desc",
    )

    return recent + classics


# -- Internal ------------------------------------------------------------------

def _parse(item: dict, api_key: str = "") -> Work:
    oa        = item.get("open_access") or {}
    oa_url    = oa.get("oa_url") or None
    oa_status = oa.get("oa_status", "closed")
    full_text = bool(oa_url) or oa_status in ("gold", "green", "hybrid", "bronze")

    content_url: Optional[str] = None
    if api_key:
        raw_id  = item.get("id", "")
        work_id = raw_id.split("/")[-1]
        if work_id.startswith("W"):
            content_url = f"{CONTENT_BASE}/works/{work_id}.pdf?api_key={api_key}"
            full_text = True

    concepts = [c["display_name"] for c in item.get("concepts", [])[:5]]
    authors  = [
        a["author"]["display_name"]
        for a in item.get("authorships", [])[:6]
    ]
    venue = None
    loc   = item.get("primary_location") or {}
    if loc.get("source"):
        venue = loc["source"].get("display_name")

    return Work(
        id=item.get("id", ""),
        title=item.get("title") or "",
        abstract=_decode_abstract(item.get("abstract_inverted_index")),
        year=item.get("publication_year"),
        doi=item.get("doi"),
        pdf_url=oa_url,
        content_url=content_url,
        oa_status=oa_status,
        full_text_available=full_text,
        cited_by_count=item.get("cited_by_count", 0),
        concepts=concepts,
        authors=authors,
        venue=venue,
    )


def _decode_abstract(inv: Optional[dict]) -> Optional[str]:
    """Inverted index {word: [positions]} -> plain text, with punctuation cleanup."""
    if not inv:
        return None
    pos: dict[int, str] = {}
    for word, positions in inv.items():
        for p in positions:
            pos[p] = word
    text = " ".join(pos[i] for i in sorted(pos))
    # Collapse space-before-punctuation artifacts from the inverted index
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text
