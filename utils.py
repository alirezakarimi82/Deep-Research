"""
Shared utilities:
  * `log`  -- stderr logger (stdout is reserved for the MCP stdio protocol)
  * `retryable_get` -- httpx.get with exponential backoff on 429 / 5xx / connect errors
"""
from __future__ import annotations

import logging
import sys

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# ---------------------------------------------------------------------------
# Logging -- MUST go to stderr because stdout carries the MCP JSON-RPC stream.
# ---------------------------------------------------------------------------

log = logging.getLogger("deep_research")
if not log.handlers:
    _h = logging.StreamHandler(stream=sys.stderr)
    _h.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    log.addHandler(_h)
    log.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# HTTP retry
# ---------------------------------------------------------------------------

_RETRYABLE = (
    httpx.HTTPStatusError,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(_RETRYABLE),
    reraise=True,
)
def _do_get(
    url: str,
    params: dict | None,
    headers: dict | None,
    timeout: int,
) -> httpx.Response:
    r = httpx.get(url, params=params, headers=headers, timeout=timeout)
    # Raise on 429 / 5xx so tenacity retries; let 4xx propagate as-is
    if r.status_code == 429 or r.status_code >= 500:
        r.raise_for_status()
    return r


def retryable_get(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = 15,
) -> httpx.Response:
    """
    httpx.get with automatic retry (3 attempts, 1/2/4s backoff) on
    429, 5xx, and connection errors. 4xx responses pass through unchanged.
    """
    return _do_get(url, params, headers, timeout)
