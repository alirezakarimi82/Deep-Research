"""
Pure-logic tests for analysis.ranker.

No network, no I/O. Run with:  pytest tests/
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# Put project root on the path (so `from analysis.ranker import ...` works)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.ranker import (
    _bucket,
    _extract_year,
    _merge,
    _norm_doi,
    _norm_title,
    corpus_summary,
    deduplicate,
    filter_full_text,
    has_full_text,
    rank_and_filter,
)

CURRENT_YEAR = datetime.now().year


# ---------------------------------------------------------------------------
# has_full_text / filter_full_text
# ---------------------------------------------------------------------------

def test_has_full_text_pdf_url():
    assert has_full_text({"pdf_url": "https://example.com/x.pdf"}) is True


def test_has_full_text_closed_academic_rejected():
    assert has_full_text({"source": "crossref", "title": "X"}) is False


def test_has_full_text_openalex_oa_url():
    assert has_full_text({"source": "openalex", "oa_url": "https://oa.com/x"}) is True


def test_has_full_text_wikipedia_with_url():
    assert has_full_text({"source": "wikipedia", "url": "https://en.wikipedia.org/wiki/Foo"}) is True


def test_has_full_text_web_source_without_url_or_snippet_rejected():
    # Previously this slipped through because the old whitelist was unconditional
    assert has_full_text({"source": "wikipedia"}) is False


def test_has_full_text_web_source_short_snippet_rejected():
    assert has_full_text({"source": "duckduckgo", "snippet": "short"}) is False


def test_has_full_text_web_source_long_snippet_accepted():
    long_snip = "x" * 250
    assert has_full_text({"source": "duckduckgo", "snippet": long_snip}) is True


def test_filter_full_text_counts_dropped():
    sources = [
        {"pdf_url": "https://x.com/1.pdf"},
        {"title": "no access"},
        {"source": "openalex", "oa_url": "https://y.com"},
    ]
    kept, dropped = filter_full_text(sources)
    assert len(kept) == 2
    assert dropped == 1


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def test_norm_title_collapses_whitespace_and_punctuation():
    assert _norm_title("  Foo,  Bar!  Baz  ") == "foo bar baz"


def test_norm_doi_strips_prefixes():
    assert _norm_doi("https://doi.org/10.1/abc") == "10.1/abc"
    assert _norm_doi("DOI:10.1/ABC") == "10.1/abc"
    assert _norm_doi(None) == ""


def test_extract_year_from_various_formats():
    assert _extract_year(2023) == 2023
    assert _extract_year("2024-03-15") == 2024
    assert _extract_year("March 2022") == 2022
    assert _extract_year("n/a") == 0
    assert _extract_year(None) == 0
    assert _extract_year(12) == 0          # implausible year


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def test_dedup_by_doi_exact_merges_fields():
    a = {
        "title": "Paper A",
        "doi": "10.1/xyz",
        "pdf_url": "https://a.com/p.pdf",
        "source": "openalex",
    }
    b = {
        "title": "Paper A",
        "doi": "https://doi.org/10.1/XYZ",   # same DOI, different prefix/case
        "tldr": "A cool paper",
        "cited_by_count": 42,
        "source": "semantic_scholar",
    }
    out = deduplicate([a, b])
    assert len(out) == 1
    merged = out[0]
    assert merged["pdf_url"] == "https://a.com/p.pdf"
    assert merged["tldr"] == "A cool paper"            # preserved from b
    assert merged["cited_by_count"] == 42              # preserved from b


def test_dedup_by_fuzzy_title_when_no_doi():
    a = {"title": "Battery Energy Storage Systems: A Review"}
    b = {"title": "Battery Energy Storage Systems - A Review"}
    assert len(deduplicate([a, b])) == 1


def test_dedup_keeps_distinct_titles():
    a = {"title": "Solar PV grid integration"}
    b = {"title": "Offshore wind farm optimization"}
    assert len(deduplicate([a, b])) == 2


def test_dedup_empty_title_is_skipped():
    assert deduplicate([{"title": ""}, {"title": None}]) == []


def test_merge_takes_max_citation_count():
    out = _merge({"cited_by_count": 10}, {"cited_by_count": 50})
    assert out["cited_by_count"] == 50


def test_merge_keeps_longer_author_list():
    out = _merge({"authors": ["A"]}, {"authors": ["A", "B", "C"]})
    assert out["authors"] == ["A", "B", "C"]


# ---------------------------------------------------------------------------
# Bucketing
# ---------------------------------------------------------------------------

def test_bucket_recent_non_seminal():
    assert _bucket({"year": CURRENT_YEAR, "cited_by_count": 5}) == "recent"


def test_bucket_seminal_beats_recent():
    assert _bucket({"year": CURRENT_YEAR, "cited_by_count": 500}) == "seminal"


def test_bucket_old_low_citation_is_middle():
    assert _bucket({"year": 2005, "cited_by_count": 10}) == "middle"


def test_bucket_old_high_citation_is_seminal():
    assert _bucket({"year": 2001, "cited_by_count": 1000}) == "seminal"


def test_bucket_missing_year_is_middle():
    assert _bucket({"cited_by_count": 5}) == "middle"


# ---------------------------------------------------------------------------
# rank_and_filter end-to-end
# ---------------------------------------------------------------------------

def _make(title, **kw):
    base = {"title": title, "source": "openalex", "oa_url": "https://x.com/p"}
    base.update(kw)
    return base


def test_rank_top_n_zero_returns_empty():
    assert rank_and_filter([_make("a")], "q", [], top_n=0) == []


def test_rank_top_n_one_does_not_crash():
    # Previously: n_recent=1, n_seminal=1, n_middle=-1 -> buckets[:-1] bug
    sources = [
        _make("A", year=CURRENT_YEAR, cited_by_count=5),
        _make("B", year=2005, cited_by_count=1000),
        _make("C", year=2010, cited_by_count=5),
    ]
    out = rank_and_filter(sources, "q", [], top_n=1)
    assert len(out) == 1


def test_rank_respects_top_n_cap():
    # Use distinct titles so fuzzy-title dedup doesn't collapse them
    titles = [
        "Battery storage economics", "Wind farm siting", "Solar panel degradation",
        "Grid frequency regulation", "Hydrogen fuel cells", "Nuclear small reactors",
        "Geothermal deep drilling", "Tidal energy turbines", "Carbon capture limestone",
        "Demand response pricing", "Electric vehicle charging", "Smart meter rollout",
        "Microgrid islanding control", "Power line transmission losses", "Energy storage arbitrage",
        "Photovoltaic cell efficiency", "Offshore wind foundations", "Biofuel feedstock yield",
        "Heat pump retrofits", "Distribution transformer aging",
    ]
    sources = [
        _make(t, year=CURRENT_YEAR, cited_by_count=i)
        for i, t in enumerate(titles)
    ]
    out = rank_and_filter(sources, "energy", ["energy"], top_n=10)
    assert len(out) == 10


def test_rank_drops_inaccessible_sources():
    sources = [
        _make("With PDF"),
        {"title": "No access", "source": "crossref"},   # no pdf_url, no OA flag
    ]
    out = rank_and_filter(sources, "q", [], top_n=10)
    assert len(out) == 1
    assert out[0]["title"] == "With PDF"


def test_rank_sets_score_and_bucket_metadata():
    out = rank_and_filter(
        [_make("Battery storage", year=CURRENT_YEAR, cited_by_count=5)],
        "battery",
        ["battery"],
        top_n=5,
    )
    assert "_score" in out[0]
    assert out[0]["_bucket"] in ("recent", "seminal", "middle")
    assert 0.0 <= out[0]["_score"] <= 1.0


def test_rank_balances_buckets_on_mixed_corpus():
    recent = [_make(f"R{i}", year=CURRENT_YEAR, cited_by_count=1) for i in range(20)]
    seminal = [_make(f"S{i}", year=2000, cited_by_count=500) for i in range(20)]
    middle = [_make(f"M{i}", year=2010, cited_by_count=5) for i in range(20)]
    out = rank_and_filter(recent + seminal + middle, "q", [], top_n=10)
    buckets = {s["_bucket"] for s in out}
    # All three buckets should be represented
    assert buckets == {"recent", "seminal", "middle"}


# ---------------------------------------------------------------------------
# corpus_summary
# ---------------------------------------------------------------------------

def test_corpus_summary_handles_missing_years():
    s = corpus_summary([
        {"year": 2020, "source": "openalex"},
        {"year": None, "source": "crossref"},
    ])
    assert "2020" in s
    assert "openalex" in s
    assert "crossref" in s
