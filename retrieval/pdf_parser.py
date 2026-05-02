"""
PDF Parser -- download a PDF from a URL and extract its text.

Strategy:
  1. pdfplumber  -- best for structured/columnar PDFs (most journal papers)
  2. PyMuPDF     -- fallback; faster, handles more edge cases
  3. Returns None if neither succeeds or the URL is not a PDF

Downloads are streamed with a hard size cap (default 50 MB) so a malicious
or accidentally-huge PDF cannot OOM the server.

Cross-platform: uses tempfile.NamedTemporaryFile with delete=False so the
file can be opened by name on Windows (Windows locks temp files while open).
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

import httpx

from utils import log

MAX_PDF_BYTES = 50 * 1024 * 1024   # 50 MB hard cap


def fetch_and_parse(
    url: str,
    max_pages: int = 40,
    max_bytes: int = MAX_PDF_BYTES,
) -> Optional[str]:
    """
    Stream-download *url*, parse as PDF, return extracted text (<= max_pages).
    Returns None if not a PDF, over size cap, or extraction fails.
    """
    tmp_path: Optional[str] = None
    try:
        with httpx.stream(
            "GET",
            url,
            timeout=15,
            follow_redirects=True,
        ) as r:
            r.raise_for_status()

            ctype = r.headers.get("content-type", "").lower()
            if "pdf" not in ctype and not url.lower().endswith(".pdf"):
                log.debug("Not a PDF (content-type=%s): %s", ctype, url)
                return None

            clen = r.headers.get("content-length")
            if clen and int(clen) > max_bytes:
                log.info(
                    "PDF exceeds size cap (%d > %d bytes): %s",
                    int(clen), max_bytes, url,
                )
                return None

            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmp_path = tmp.name
            total = 0
            try:
                for chunk in r.iter_bytes(chunk_size=64 * 1024):
                    total += len(chunk)
                    if total > max_bytes:
                        log.info(
                            "Aborting download -- streamed past %d bytes: %s",
                            max_bytes, url,
                        )
                        tmp.close()
                        return None
                    tmp.write(chunk)
            finally:
                tmp.close()

        text = _try_pdfplumber(tmp_path, max_pages)
        if not text or len(text) < 200:
            text = _try_pymupdf(tmp_path, max_pages)
        return text or None
    except Exception as exc:
        log.debug("PDF fetch/parse failed for %s: %s", url, exc)
        return None
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def parse_local(path: str | Path, max_pages: int = 40) -> Optional[str]:
    """Parse a PDF already on disk."""
    p = Path(path)
    if not p.is_file():
        return None
    text = _try_pdfplumber(str(p), max_pages)
    if not text or len(text) < 200:
        text = _try_pymupdf(str(p), max_pages)
    return text or None


# -- Backends ------------------------------------------------------------------

def _try_pdfplumber(path: str, max_pages: int) -> Optional[str]:
    try:
        import pdfplumber
        texts: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:max_pages]:
                t = page.extract_text()
                if t:
                    texts.append(t)
        return "\n\n".join(texts) if texts else None
    except Exception as exc:
        log.debug("pdfplumber failed on %s: %s", path, exc)
        return None


def _try_pymupdf(path: str, max_pages: int) -> Optional[str]:
    try:
        import fitz     # PyMuPDF
        doc   = fitz.open(path)
        texts = [page.get_text() for page in doc[:max_pages]]
        doc.close()
        combined = "\n\n".join(t for t in texts if t.strip())
        return combined or None
    except Exception as exc:
        log.debug("PyMuPDF failed on %s: %s", path, exc)
        return None
