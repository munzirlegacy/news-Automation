"""
news_fetcher.py - High-speed parallel news discovery with early cutoff.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Any

import feedparser
import requests
from bs4 import BeautifulSoup

from config import (
    NEWS_SOURCES,
    REQUEST_TIMEOUT,
    MAX_AGE_DAYS,
    USER_AGENT,
)

logger = logging.getLogger(__name__)

# Common topic synonym / acronym mappings
QUERY_EXPANSIONS = {
    "artificial intelligence": ["ai", "machine learning", "deep learning", "llm", "generative ai"],
    "cybersecurity": ["cyber", "ransomware", "malware", "infosec", "hacker", "breach"],
    "electric vehicles": ["ev", "evs", "electric vehicle", "electric car", "tesla", "battery"],
    "space exploration": ["space", "nasa", "spacex", "orbit", "astronomy", "starship", "cosmic"],
    "technology": ["tech", "software", "hardware", "digital", "gadget", "computing"],
    "business": ["market", "economy", "finance", "shares", "stocks", "earnings", "ceo"],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_published(entry: Any) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _is_recent(pub_dt: datetime | None) -> bool:
    if pub_dt is None:
        return True
    cutoff = _now_utc() - timedelta(days=MAX_AGE_DAYS)
    return pub_dt >= cutoff


def _keyword_match(text: str, query: str, keywords: list[str]) -> bool:
    lower = text.lower()
    q_lower = query.lower().strip()

    if q_lower in lower:
        return True

    for exp in QUERY_EXPANSIONS.get(q_lower, []):
        if re.search(r"\b" + re.escape(exp) + r"\b", lower):
            return True

    if len(keywords) > 1:
        matched = sum(1 for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", lower))
        if matched >= max(1, len(keywords) // 2 + 1):
            return True
    elif len(keywords) == 1:
        if re.search(r"\b" + re.escape(keywords[0]) + r"\b", lower):
            return True

    return False


def _unwrap_url(raw_url: str, publisher: str) -> str:
    if "bing.com/news/apiclick.aspx" in raw_url:
        try:
            parsed = urllib.parse.urlparse(raw_url)
            qs = urllib.parse.parse_qs(parsed.query)
            target = qs.get("url", [None])[0]
            if target and target.startswith("http"):
                return target
        except Exception:
            pass
    return raw_url


def _fetch_feed(url: str, session: requests.Session) -> feedparser.FeedParserDict | None:
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            return feedparser.parse(resp.content)
    except Exception:
        pass
    return None


def _entry_to_dict(entry: Any, publisher: str, is_direct: bool = True) -> dict:
    pub_dt = _parse_published(entry)
    summary_raw = ""
    for attr in ("summary", "description", "content"):
        val = getattr(entry, attr, None)
        if val:
            if isinstance(val, list):
                val = val[0].get("value", "") if val else ""
            summary_raw = val
            break

    excerpt = BeautifulSoup(summary_raw, "html.parser").get_text(separator=" ").strip()
    excerpt = " ".join(excerpt.split())[:500]

    raw_title = getattr(entry, "title", "No Title").strip()
    raw_url   = getattr(entry, "link",  "").strip()
    clean_url = _unwrap_url(raw_url, publisher)

    display_publisher = publisher
    source_obj = getattr(entry, "source", None)
    if isinstance(source_obj, dict) and source_obj.get("title"):
        display_publisher = source_obj["title"].strip()

    if display_publisher in ("Google News", "Bing News") and " - " in raw_title:
        parts = raw_title.rsplit(" - ", 1)
        if len(parts) == 2 and 2 <= len(parts[1]) <= 50:
            display_publisher = parts[1].strip()
            raw_title = parts[0].strip()

    return {
        "title":       raw_title,
        "url":         clean_url,
        "publisher":   display_publisher,
        "published":   pub_dt.isoformat() if pub_dt else "Unknown",
        "retrieved":   _now_utc().isoformat(),
        "excerpt":     excerpt or "No excerpt available.",
        "text":        "",
        "summary":     "",
        "word_count":  0,
        "is_direct":   is_direct,
    }


def _process_single_feed(source_info: dict, clean_query: str, keywords: list[str], session: requests.Session) -> list[dict]:
    publisher = source_info["publisher"]
    feed_url = source_info["url"]
    use_query = source_info["use_query"]

    feed = _fetch_feed(feed_url, session)
    if not feed or not feed.entries:
        return []

    hits = []
    for entry in feed.entries:
        raw_url = getattr(entry, "link", "").strip()
        target_url = _unwrap_url(raw_url, publisher)
        if not target_url:
            continue

        pub_dt = _parse_published(entry)
        if not _is_recent(pub_dt):
            continue

        title   = getattr(entry, "title", "")
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
        combined = f"{title} {summary}"

        if not use_query and not _keyword_match(combined, clean_query, keywords):
            continue

        hits.append(_entry_to_dict(entry, publisher, is_direct=not use_query))
    return hits

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_articles(query: str, max_articles: int = 10) -> list[dict]:
    clean_query = query.strip()
    keywords = [w.strip() for w in clean_query.lower().split() if len(w.strip()) > 2]
    if not keywords:
        keywords = [clean_query.lower()]

    encoded_query = urllib.parse.quote_plus(clean_query)

    # Separate query-aware feeds (fastest & 100% relevant) from direct feeds
    query_tasks = []
    direct_tasks = []

    for source in NEWS_SOURCES:
        publisher = source["publisher"]
        use_query = source.get("use_query", False)
        for feed_url_template in source["feeds"]:
            feed_url = (
                feed_url_template.format(query=encoded_query)
                if use_query
                else feed_url_template
            )
            item = {"publisher": publisher, "url": feed_url, "use_query": use_query}
            if use_query:
                query_tasks.append(item)
            else:
                direct_tasks.append(item)

    all_tasks = query_tasks + direct_tasks
    articles: list[dict] = []
    seen_urls: set[str] = set()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # High-concurrency worker pool (up to 16 workers) for fast feed gathering
    with ThreadPoolExecutor(max_workers=min(16, len(all_tasks))) as executor:
        futures = {
            executor.submit(_process_single_feed, task, clean_query, keywords, session): task
            for task in all_tasks
        }
        for future in as_completed(futures):
            try:
                results = future.result()
                for art in results:
                    if art["url"] not in seen_urls:
                        seen_urls.add(art["url"])
                        articles.append(art)
                # Quick-exit when we have plenty of candidates
                if len(articles) >= max_articles * 2:
                    break
            except Exception:
                pass

    # Sort: direct source priority first, then publication date descending
    def sort_key(a: dict) -> tuple[int, str]:
        is_dir = 1 if a.get("is_direct", False) else 0
        pub = a.get("published", "Unknown")
        pub_val = pub if pub != "Unknown" else "0000"
        return (is_dir, pub_val)

    articles.sort(key=sort_key, reverse=True)

    # Final deduplication
    final: list[dict] = []
    seen_final_urls: set[str] = set()
    seen_titles: set[str] = set()

    for a in articles:
        u = a["url"]
        t = a["title"].lower().strip()
        if u not in seen_final_urls and t not in seen_titles:
            seen_final_urls.add(u)
            seen_titles.add(t)
            final.append(a)

    return final[:max_articles]
