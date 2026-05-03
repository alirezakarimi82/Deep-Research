"""
Centralized config loader.

Resolution order (highest → lowest priority):
  1. Shell environment variables         — always win; set by CI, Docker, shell profile
  2. .env file in the project root       — convenient local secret store; gitignored
  3. config.yaml in the project root     — non-secret tuning (analysis: block)
  4. Hard-coded defaults                 — safe fallback so the server always starts

Secret variables loaded from any of the above:
    SEMANTIC_SCHOLAR_KEY  -> semantic_scholar_key
    UNPAYWALL_EMAIL       -> unpaywall_email
    OPENALEX_API_KEY      -> openalex_api_key

python-dotenv is an optional dependency: if it is not installed the loader
silently skips .env loading and falls back to levels 3 and 4.  Install it
with:  pip install python-dotenv
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).parent
_CONFIG_PATH = _ROOT / "config.yaml"
_DOTENV_PATH = _ROOT / ".env"

_DEFAULT_ANALYSIS: dict[str, Any] = {
    "max_sources_for_synthesis": 30,
    "dedup_threshold": 0.85,
    "recent_years": 3,
    "seminal_threshold": 100,
    "recent_share": 0.40,
    "seminal_share": 0.30,
}


def _load_dotenv() -> None:
    """
    Load .env into os.environ using python-dotenv if available.

    Behaviour mirrors dotenv's default: existing env vars are NOT overwritten,
    so a variable already set in the shell takes precedence over the .env file.
    This preserves the intended priority order without any extra logic here.
    """
    if not _DOTENV_PATH.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=_DOTENV_PATH, override=False)
    except ImportError:
        # python-dotenv is optional; skip silently
        pass


def load_config() -> dict[str, Any]:
    """
    Load configuration from all sources and return a merged dict.

    Safe to call at any time; never raises on missing files.
    """
    # Layer 2: load .env into os.environ (does not overwrite existing vars)
    _load_dotenv()

    # Layer 3: load config.yaml
    cfg: dict[str, Any] = {}
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

    # Layers 1 + 2: env var overrides (reads os.environ which now includes .env)
    env_overrides = {
        "semantic_scholar_key": os.getenv("SEMANTIC_SCHOLAR_KEY"),
        "unpaywall_email":      os.getenv("UNPAYWALL_EMAIL"),
        "openalex_api_key":     os.getenv("OPENALEX_API_KEY"),
    }
    for k, v in env_overrides.items():
        if v:
            cfg[k] = v

    # Layer 4: defaults
    cfg.setdefault("semantic_scholar_key", "")
    cfg.setdefault("unpaywall_email", "research@example.com")
    cfg.setdefault("openalex_api_key", "")

    # Ensure analysis subtree exists with all defaults filled in
    analysis = dict(_DEFAULT_ANALYSIS)
    analysis.update(cfg.get("analysis") or {})
    cfg["analysis"] = analysis

    return cfg
