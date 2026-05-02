"""
Centralized config loader.

Loads config.yaml from the project root, then overlays environment variables
for any secret field that is set:

    SEMANTIC_SCHOLAR_KEY  -> semantic_scholar_key
    UNPAYWALL_EMAIL       -> unpaywall_email
    OPENALEX_API_KEY      -> openalex_api_key

Environment variables always win over file values when both are present.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).parent
_CONFIG_PATH = _ROOT / "config.yaml"

_DEFAULT_ANALYSIS: dict[str, Any] = {
    "max_sources_for_synthesis": 30,
    "dedup_threshold": 0.85,
    "recent_years": 3,
    "seminal_threshold": 100,
    "recent_share": 0.40,
    "seminal_share": 0.30,
}


def load_config() -> dict[str, Any]:
    """Load config.yaml and overlay env vars. Safe if the file is missing."""
    cfg: dict[str, Any] = {}
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

    # Env var overrides (only if set and non-empty)
    env_overrides = {
        "semantic_scholar_key": os.getenv("SEMANTIC_SCHOLAR_KEY"),
        "unpaywall_email":      os.getenv("UNPAYWALL_EMAIL"),
        "openalex_api_key":     os.getenv("OPENALEX_API_KEY"),
    }
    for k, v in env_overrides.items():
        if v:
            cfg[k] = v

    # Ensure analysis subtree exists with all defaults
    analysis = dict(_DEFAULT_ANALYSIS)
    analysis.update(cfg.get("analysis") or {})
    cfg["analysis"] = analysis

    # Defaults for top-level keys
    cfg.setdefault("semantic_scholar_key", "")
    cfg.setdefault("unpaywall_email", "research@example.com")
    cfg.setdefault("openalex_api_key", "")

    return cfg
