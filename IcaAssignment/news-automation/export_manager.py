"""
export_manager.py - Writes news.json, news.csv and digest.md.

Each export function accepts the processed+summarised article list and
writes to the paths defined in config.OUTPUT_DIR.
"""

from __future__ import annotations

import csv
import json
import logging
import os
from datetime import datetime, timezone

from config import OUTPUT_DIR, JSON_PATH, CSV_PATH, DIGEST_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def _safe(value: str | None, placeholder: str = "N/A") -> str:
    return value.strip() if value and value.strip() else placeholder

# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

def export_json(articles: list[dict], query: str = "") -> str:
    """
    Write all articles to news.json.
    Returns the file path.
    """
    _ensure_output_dir()
    payload = {
        "query":        query,
        "exported_at":  datetime.now(timezone.utc).isoformat(),
        "total":        len(articles),
        "articles":     articles,
    }
    with open(JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    logger.info("Exported JSON → %s", JSON_PATH)
    return JSON_PATH


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

CSV_FIELDS = [
    "title", "publisher", "url", "published", "retrieved",
    "excerpt", "summary", "summary_method", "word_count",
    "extraction_status",
]

def export_csv(articles: list[dict], query: str = "") -> str:
    """
    Write all articles to news.csv.
    Returns the file path.
    """
    _ensure_output_dir()
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for a in articles:
            row = {f: _safe(str(a.get(f, ""))) for f in CSV_FIELDS}
            writer.writerow(row)
    logger.info("Exported CSV  → %s", CSV_PATH)
    return CSV_PATH


# ---------------------------------------------------------------------------
# Markdown digest
# ---------------------------------------------------------------------------

def export_markdown(articles: list[dict], query: str = "") -> str:
    """
    Write a human-readable Markdown digest to digest.md.
    Returns the file path.
    """
    _ensure_output_dir()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    publishers = sorted({a.get("publisher", "Unknown") for a in articles})

    lines: list[str] = [
        "# 📰 NewsPulse – News Digest",
        "",
        f"**Topic:** {query or 'N/A'}  ",
        f"**Generated:** {now}  ",
        f"**Articles:** {len(articles)}  ",
        f"**Sources:** {', '.join(publishers) or 'N/A'}",
        "",
        "---",
        "",
    ]

    for i, a in enumerate(articles, start=1):
        title     = _safe(a.get("title"), "No Title")
        publisher = _safe(a.get("publisher"), "Unknown Publisher")
        published = _safe(a.get("published"), "Unknown Date")
        url       = _safe(a.get("url"), "No URL")
        excerpt   = _safe(a.get("excerpt"), "No excerpt available.")
        summary   = _safe(a.get("summary"), "No summary generated.")
        method    = a.get("summary_method", "unknown")

        lines += [
            f"## {i}. {title}",
            "",
            f"| Field       | Value |",
            f"|-------------|-------|",
            f"| **Publisher**  | {publisher} |",
            f"| **Published**  | {published} |",
            f"| **URL**        | [{url[:60]}...]({url}) |" if len(url) > 60 else f"| **URL**        | [{url}]({url}) |",
            "",
            "### Excerpt",
            "",
            f"> {excerpt[:400]}{'…' if len(excerpt) > 400 else ''}",
            "",
            "### Summary",
            "",
            f"{summary}",
            "",
            f"*Summarisation method: {method}*",
            "",
            "---",
            "",
        ]

    with open(DIGEST_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    logger.info("Exported MD   → %s", DIGEST_PATH)
    return DIGEST_PATH


# ---------------------------------------------------------------------------
# Convenience: export all three at once
# ---------------------------------------------------------------------------

def export_all(articles: list[dict], query: str = "") -> dict[str, str]:
    """
    Call all three export functions.
    Returns a dict: {"json": path, "csv": path, "markdown": path}
    """
    return {
        "json":     export_json(articles, query),
        "csv":      export_csv(articles, query),
        "markdown": export_markdown(articles, query),
    }

