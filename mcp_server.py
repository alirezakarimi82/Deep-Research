"""
Deep Research MCP Server
========================
Wraps the pipeline source, retrieval, and analysis modules as MCP tools so
the AI agent (OpenCode / Claude Code) can call them directly.

Run with:
    python mcp_server.py

The server speaks stdio (compatible with OpenCode's "local" MCP type).
IMPORTANT: nothing in this server may write to stdout; stdout carries the
JSON-RPC protocol. All logging goes to stderr via `utils.log`.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

# Ensure the project root is on sys.path so all sub-packages are importable.
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from fastmcp import FastMCP

from config import load_config
from utils import log

# ---------------------------------------------------------------------------
# Config (file + env-var overlay)
# ---------------------------------------------------------------------------

_cfg             = load_config()
_openalex_key    = _cfg["openalex_api_key"]
_ss_key          = _cfg["semantic_scholar_key"]
_unpaywall_email = _cfg["unpaywall_email"]
_analysis        = _cfg["analysis"]

log.info(
    "deep-research MCP starting (openalex=%s, ss=%s, unpaywall_email=%s)",
    "on" if _openalex_key else "off",
    "on" if _ss_key else "off",
    _unpaywall_email,
)

mcp = FastMCP("deep-research")


# ---------------------------------------------------------------------------
# Academic search tools
# ---------------------------------------------------------------------------

@mcp.tool()
def search_openalex(query: str, max_results: int = 20) -> str:
    """Search OpenAlex for open-access academic papers.

    Two-pass strategy (recent + seminal). With an API key, uses semantic
    search and provides full-text PDF links via content.openalex.org.

    Returns: JSON array of source dicts.
    """
    from sources.academic.openalex import search_works_two_pass
    works = search_works_two_pass(
        query,
        max_per_pass=max_results,
        email=_unpaywall_email,
        api_key=_openalex_key,
    )
    return json.dumps([dataclasses.asdict(w) for w in works])


@mcp.tool()
def search_semantic_scholar(query: str, max_results: int = 20) -> str:
    """Search Semantic Scholar for open-access papers.

    Returns AI-generated TLDRs, citation counts, and OA PDF links.
    Two-pass strategy (recent + all-time by citation count).
    """
    from sources.academic.semantic_scholar import search_papers_two_pass
    papers = search_papers_two_pass(
        query,
        max_per_pass=max_results,
        api_key=_ss_key,
    )
    return json.dumps(papers)


@mcp.tool()
def search_crossref(
    query: str,
    max_results: int = 20,
    from_year: int | None = None,
) -> str:
    """Search Crossref, enrich with Unpaywall OA PDFs in parallel.

    Args:
        query: research query
        max_results: max Crossref hits
        from_year: optional lower-bound publication year
    """
    from sources.academic.crossref_unpaywall import (
        search_crossref as _search,
        enrich_with_unpaywall,
    )
    sources = _search(
        query,
        max_results=max_results,
        from_year=from_year,
        email=_unpaywall_email,
    )
    sources = enrich_with_unpaywall(sources, email=_unpaywall_email)
    return json.dumps(sources)


# ---------------------------------------------------------------------------
# Web search tools
# ---------------------------------------------------------------------------

@mcp.tool()
def search_wikipedia(query: str, max_results: int = 5) -> str:
    """Search Wikipedia for background context and definitions."""
    from sources.web.wikipedia import search_wikipedia as _search
    return json.dumps(_search(query, max_results=max_results))


@mcp.tool()
def search_hackernews(query: str, max_results: int = 10) -> str:
    """Search Hacker News via Algolia."""
    from sources.web.reddit_hn import search_hackernews as _search
    return json.dumps(_search(query, max_results=max_results))


@mcp.tool()
def search_reddit(
    query: str,
    subreddit: str = "all",
    max_results: int = 10,
) -> str:
    """Search Reddit for community knowledge."""
    from sources.web.reddit_hn import search_reddit as _search
    return json.dumps(_search(query, subreddit=subreddit, max_results=max_results))


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

@mcp.tool()
def rank_and_filter(
    sources_json: str,
    query: str,
    key_concepts_json: str,
    top_n: int | None = None,
) -> str:
    """Deduplicate, score, and temporally balance a merged source list.

    All ranker tuning is taken from config.yaml's `analysis:` block by
    default, but `top_n` can be overridden per call.

    Args:
        sources_json: JSON array of merged source dicts
        query: the research query (used for keyword scoring)
        key_concepts_json: JSON array of 3-5 key concept terms
        top_n: override for analysis.max_sources_for_synthesis
    """
    from analysis.ranker import rank_and_filter as _rank

    sources      = json.loads(sources_json)
    key_concepts = json.loads(key_concepts_json)
    effective_top_n = top_n if top_n is not None else int(_analysis["max_sources_for_synthesis"])

    result = _rank(
        sources,
        query,
        key_concepts,
        top_n=effective_top_n,
        dedup_threshold=float(_analysis["dedup_threshold"]),
        recent_years=int(_analysis["recent_years"]),
        seminal_threshold=int(_analysis["seminal_threshold"]),
        recent_share=float(_analysis["recent_share"]),
        seminal_share=float(_analysis["seminal_share"]),
    )
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Content retrieval
# ---------------------------------------------------------------------------

@mcp.tool()
def extract_content(url: str) -> str:
    """Fetch and clean the text of a web page (Jina -> trafilatura -> BS4)."""
    from retrieval.content_extractor import extract
    return extract(url) or ""


@mcp.tool()
def parse_pdf(url: str) -> str:
    """Download a PDF (streamed, 50 MB cap) and extract its text."""
    from retrieval.pdf_parser import fetch_and_parse
    return fetch_and_parse(url) or ""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
