"""
Ranker -- filters, deduplicates, scores, and temporally balances sources.

Hard constraints:

1. FULL-TEXT ONLY
   Sources without a credible path to real content are dropped before
   scoring.  Web sources must have either a snippet long enough to be
   useful or a fetchable URL.

2. TEMPORAL BALANCE
   Pure relevance ranking buries classics (old, highly-cited) and fresh
   preprints (no citations yet).  Partition into three buckets and draw
   proportionally:
     recent  = published within recent_years         (default 40 %)
     seminal = cited_by_count >= seminal_threshold   (default 30 %)
     middle  = everything else                        (default 30 %)
"""
from __future__ import annotations

import math
import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Literal

from utils import log

# Defaults (overridable per call and via config)
SEMINAL_THRESHOLD = 100
RECENT_YEARS      = 3
RECENT_SHARE      = 0.40
SEMINAL_SHARE     = 0.30

# Web-source names that are allowed past the full-text gate provided they
# carry either a long-enough snippet or a fetchable URL (Stage 4 extracts).
_WEB_SOURCES = frozenset({
    "duckduckgo", "duckduckgo_news", "wikipedia",
    "reddit", "hackernews", "brave", "playwright",
})

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _current_year() -> int:
    """Dynamic so long-running servers don't mis-bucket across a year boundary."""
    return datetime.now().year


# ---------------------------------------------------------------------------
# 1. Full-text gate
# ---------------------------------------------------------------------------

def has_full_text(source: dict) -> bool:
    """True iff there is a credible path to the source's real content."""
    if source.get("full_text"):
        return True
    if source.get("full_text_available"):
        return True
    pdf = source.get("pdf_url") or ""
    if isinstance(pdf, str) and pdf.startswith("http"):
        return True
    if source.get("openAccessPdf"):
        return True
    if source.get("is_oa") or source.get("oa_url"):
        return True
    if source.get("content_url"):
        return True
    # Web sources: allow only if there's something fetchable or a meaty snippet
    if source.get("source") in _WEB_SOURCES:
        if source.get("url"):
            return True
        snippet = source.get("snippet") or source.get("abstract") or ""
        if len(snippet) >= 200:
            return True
    return False


def filter_full_text(sources: list[dict]) -> tuple[list[dict], int]:
    ok = [s for s in sources if has_full_text(s)]
    return ok, len(sources) - len(ok)


# ---------------------------------------------------------------------------
# 2. Deduplication -- DOI first, then fuzzy title with field-level merge
# ---------------------------------------------------------------------------

def _norm_title(t: str) -> str:
    t = re.sub(r"[^\w\s]", "", (t or "").lower())
    return re.sub(r"\s+", " ", t).strip()


def _norm_doi(doi: str | None) -> str:
    if not doi:
        return ""
    d = doi.strip().lower()
    for p in ("https://doi.org/", "http://doi.org/", "doi:"):
        if d.startswith(p):
            d = d[len(p):]
    return d


def _completeness(s: dict) -> int:
    return (
        bool(s.get("pdf_url"))    * 3 +
        bool(s.get("abstract"))   * 2 +
        bool(s.get("full_text"))  * 4 +
        bool(s.get("doi"))            +
        bool(s.get("authors"))        +
        bool(s.get("tldr"))
    )


def _merge(primary: dict, other: dict) -> dict:
    """Field-level merge -- prefer primary's non-empty values, fill gaps from other.

    For citation counts, take the max.  For lists (authors, concepts) keep the
    longer one.  This is how we preserve, e.g., SS's TLDR when OpenAlex wins.
    """
    out = dict(primary)
    for k, v in other.items():
        cur = out.get(k)
        if cur in (None, "", [], 0, False) and v not in (None, "", [], 0, False):
            out[k] = v
        elif k in ("cited_by_count", "citations") and isinstance(v, (int, float)):
            out[k] = max(int(cur or 0), int(v))
        elif k in ("authors", "concepts") and isinstance(v, list) and len(v) > len(cur or []):
            out[k] = v
    return out


def deduplicate(sources: list[dict], threshold: float = 0.85) -> list[dict]:
    """DOI-exact dedup first, then fuzzy title dedup. Merges fields rather than
    discarding the loser."""
    # Pass 1: DOI-exact (O(n), cheap)
    by_doi: dict[str, dict] = {}
    no_doi: list[dict] = []
    for s in sources:
        d = _norm_doi(s.get("doi"))
        if d:
            if d in by_doi:
                by_doi[d] = _merge(by_doi[d], s) if _completeness(by_doi[d]) >= _completeness(s) \
                    else _merge(s, by_doi[d])
            else:
                by_doi[d] = s
        else:
            no_doi.append(s)

    # Pass 2: fuzzy title on the union, with first-word bucketing for speed
    kept: list[dict]        = []
    kept_norms: list[str]   = []
    kept_first: list[str]   = []

    for cand in list(by_doi.values()) + no_doi:
        cn = _norm_title(cand.get("title", ""))
        if not cn:
            continue
        first = cn.split(" ", 1)[0] if cn else ""

        dup_idx: int | None = None
        for i, kn in enumerate(kept_norms):
            # Skip obviously-different titles: different first word rules out most
            if kept_first[i] and first and kept_first[i] != first:
                continue
            if SequenceMatcher(None, cn, kn).ratio() > threshold:
                dup_idx = i
                break

        if dup_idx is None:
            kept.append(cand)
            kept_norms.append(cn)
            kept_first.append(first)
        else:
            winner, loser = (cand, kept[dup_idx]) \
                if _completeness(cand) > _completeness(kept[dup_idx]) \
                else (kept[dup_idx], cand)
            kept[dup_idx] = _merge(winner, loser)
            kept_norms[dup_idx] = _norm_title(kept[dup_idx].get("title", ""))

    return kept


# ---------------------------------------------------------------------------
# 3. Relevance scoring
# ---------------------------------------------------------------------------

def _relevance(source: dict, query: str, concepts: list[str]) -> float:
    text = " ".join([
        source.get("title") or "",
        source.get("abstract") or "",
        source.get("snippet") or "",
        source.get("tldr") or "",
    ]).lower()

    query_words = set(re.sub(r"[^\w\s]", "", query.lower()).split())
    kw = sum(1 for w in query_words if w in text) / max(len(query_words), 1)

    concept_hit = 0.0
    if concepts:
        concept_hit = sum(1 for c in concepts if c.lower() in text) / len(concepts)

    cites = int(source.get("cited_by_count") or source.get("citations") or 0)
    # Intentional saturation at ~10k cites -- prevents citation count from
    # dominating the score.
    cite_score = min(1.0, math.log10(cites + 1) / 4) if cites > 0 else 0.0

    has_ft   = 1.0 if has_full_text(source) else 0.0
    has_tldr = 1.0 if source.get("tldr") else 0.0

    return min(
        0.40 * kw +
        0.20 * concept_hit +
        0.20 * cite_score +
        0.10 * has_ft +
        0.10 * has_tldr,
        1.0,
    )


# ---------------------------------------------------------------------------
# 4. Temporal bucketing
# ---------------------------------------------------------------------------

def _extract_year(raw) -> int:
    """Best-effort year extraction from ints, ISO dates, and messy strings."""
    if raw is None:
        return 0
    if isinstance(raw, int):
        return raw if 1800 < raw < 2200 else 0
    m = _YEAR_RE.search(str(raw))
    return int(m.group(0)) if m else 0


def _bucket(
    source: dict,
    recent_years: int = RECENT_YEARS,
    seminal_threshold: int = SEMINAL_THRESHOLD,
) -> Literal["recent", "seminal", "middle"]:
    year  = _extract_year(source.get("year") or source.get("published"))
    cites = int(source.get("cited_by_count") or source.get("citations") or 0)

    is_recent  = year > 0 and year >= (_current_year() - recent_years)
    is_seminal = cites >= seminal_threshold

    if is_recent and not is_seminal:
        return "recent"
    if is_seminal:
        return "seminal"
    return "middle"


# ---------------------------------------------------------------------------
# 5. Main entry point
# ---------------------------------------------------------------------------

def rank_and_filter(
    sources: list[dict],
    query: str,
    key_concepts: list[str],
    top_n: int = 30,
    dedup_threshold: float = 0.85,
    recent_years: int = RECENT_YEARS,
    seminal_threshold: int = SEMINAL_THRESHOLD,
    recent_share: float = RECENT_SHARE,
    seminal_share: float = SEMINAL_SHARE,
) -> list[dict]:
    """
    Full pipeline: filter -> deduplicate -> score -> bucket-balanced selection.
    """
    if top_n < 1:
        return []

    # 1. Filter
    sources, n_dropped = filter_full_text(sources)
    if n_dropped:
        log.info("Dropped %d abstract-only / inaccessible sources", n_dropped)

    # 2. Deduplicate
    sources = deduplicate(sources, dedup_threshold)

    # 3. Score + bucket annotation
    for s in sources:
        s["_score"]  = _relevance(s, query, key_concepts)
        s["_bucket"] = _bucket(
            s,
            recent_years=recent_years,
            seminal_threshold=seminal_threshold,
        )

    # 4. Partition (sorted by score within each bucket)
    buckets: dict[str, list[dict]] = {"recent": [], "seminal": [], "middle": []}
    for s in sorted(sources, key=lambda x: x["_score"], reverse=True):
        buckets[s["_bucket"]].append(s)

    # 5. Quota math -- clamped so negatives can't happen at small top_n
    n_recent  = min(top_n, max(0, round(top_n * recent_share)))
    n_seminal = min(top_n - n_recent, max(0, round(top_n * seminal_share)))
    n_middle  = max(0, top_n - n_recent - n_seminal)

    # Guarantee at least one slot per non-empty bucket when top_n >= 3
    if top_n >= 3:
        if buckets["recent"]  and n_recent  == 0: n_recent  = 1
        if buckets["seminal"] and n_seminal == 0: n_seminal = 1
        if buckets["middle"]  and n_middle  == 0: n_middle  = 1
        # Re-trim to top_n if we over-allocated
        overflow = (n_recent + n_seminal + n_middle) - top_n
        while overflow > 0:
            for k in ("middle", "seminal", "recent"):
                if overflow <= 0:
                    break
                if {"recent": n_recent, "seminal": n_seminal, "middle": n_middle}[k] > 1:
                    if k == "middle":  n_middle  -= 1
                    if k == "seminal": n_seminal -= 1
                    if k == "recent":  n_recent  -= 1
                    overflow -= 1

    selected = (
        buckets["recent"][:n_recent] +
        buckets["seminal"][:n_seminal] +
        buckets["middle"][:n_middle]
    )

    # 6. Pad from leftovers if any bucket ran short
    used = {id(s) for s in selected}
    leftovers = sorted(
        (s for s in sources if id(s) not in used),
        key=lambda x: x["_score"],
        reverse=True,
    )
    selected.extend(leftovers[: top_n - len(selected)])

    n_r = sum(1 for s in selected if s["_bucket"] == "recent")
    n_s = sum(1 for s in selected if s["_bucket"] == "seminal")
    n_m = sum(1 for s in selected if s["_bucket"] == "middle")
    log.info(
        "Corpus: %d sources -- recent(<=%dy):%d seminal(>=%d cites):%d other:%d",
        len(selected), recent_years, n_r, seminal_threshold, n_s, n_m,
    )

    return selected[:top_n]


def corpus_summary(sources: list[dict]) -> str:
    years = [_extract_year(s.get("year")) for s in sources]
    years = [y for y in years if y]
    src_counts: dict[str, int] = {}
    for s in sources:
        k = s.get("source", "unknown")
        src_counts[k] = src_counts.get(k, 0) + 1
    yr = f"{min(years)}-{max(years)}" if years else "unknown"
    srcs = ", ".join(
        f"{k}:{v}" for k, v in sorted(src_counts.items(), key=lambda x: -x[1])
    )
    return f"Year range: {yr} | Sources: {srcs}"
