"""
data_processor.py - Filtering, deduplication and data-quality checks.

Responsibilities
----------------
* Remove articles with duplicate URLs.
* Remove near-duplicate articles (same title fuzzy match).
* Validate that required fields are present; mark missing fields clearly.
* Annotate data-quality flags.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone, timedelta

from config import MAX_AGE_DAYS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_title(title: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    t = title.lower()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _title_fingerprint(title: str) -> str:
    words = _normalise_title(title).split()
    # Use first 8 significant words as a fingerprint
    sig = " ".join(w for w in words if len(w) > 3)[:8 * 10]
    return hashlib.md5(sig.encode()).hexdigest()[:12]


def _is_within_window(published: str) -> bool:
    """Return True if the article is within the MAX_AGE_DAYS window."""
    if published == "Unknown":
        return True   # keep articles with no date
    try:
        dt = datetime.fromisoformat(published)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
        return dt >= cutoff
    except Exception:
        return True   # be lenient on parse failure

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def deduplicate(articles: list[dict]) -> list[dict]:
    """Remove articles with duplicate URLs or near-duplicate titles."""
    seen_urls: set[str]  = set()
    seen_fps:  set[str]  = set()
    unique: list[dict]   = []

    for a in articles:
        url = (a.get("url") or "").strip()
        if not url or url in seen_urls:
            logger.debug("Dropped duplicate URL: %s", url)
            continue

        fp = _title_fingerprint(a.get("title", ""))
        if fp in seen_fps:
            logger.debug("Dropped near-duplicate title: %s", a.get("title"))
            continue

        seen_urls.add(url)
        seen_fps.add(fp)
        unique.append(a)

    removed = len(articles) - len(unique)
    if removed:
        logger.info("Deduplication removed %d article(s).", removed)
    return unique


def filter_by_date(articles: list[dict]) -> list[dict]:
    """Keep only articles within the MAX_AGE_DAYS freshness window."""
    fresh = [a for a in articles if _is_within_window(a.get("published", "Unknown"))]
    removed = len(articles) - len(fresh)
    if removed:
        logger.info("Date filter removed %d article(s) older than %d days.", removed, MAX_AGE_DAYS)
    return fresh


def validate_and_annotate(articles: list[dict]) -> list[dict]:
    """
    Ensure every required field exists; fill missing values with a clear
    placeholder so the UI can distinguish 'missing' from 'empty'.
    """
    required_fields = {
        "title":     "No Title Available",
        "url":       "No URL Available",
        "publisher": "Unknown Publisher",
        "published": "Unknown",
        "retrieved": "Unknown",
        "excerpt":   "No excerpt available.",
        "text":      "",
        "summary":   "",
    }

    for a in articles:
        for field, placeholder in required_fields.items():
            if not a.get(field):
                a[field] = placeholder
                a.setdefault("quality_flags", []).append(f"missing:{field}")

        # Ensure quality_flags key always exists
        a.setdefault("quality_flags", [])

    return articles


def process_articles(articles: list[dict]) -> list[dict]:
    """
    Full data-processing pipeline:
      deduplicate → filter_by_date → validate_and_annotate
    """
    articles = deduplicate(articles)
    articles = filter_by_date(articles)
    articles = validate_and_annotate(articles)
    return articles

