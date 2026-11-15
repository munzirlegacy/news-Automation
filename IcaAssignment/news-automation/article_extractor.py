"""
article_extractor.py - High-speed concurrent text extractor.
"""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)

# Try importing newspaper3k
try:
    from newspaper import Article as NewspaperArticle
    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False

_CONTENT_TAGS = [
    {"name": "article"},
    {"name": "div", "class_": re.compile(r"article|post|content|story|body|main", re.I)},
    {"name": "section", "class_": re.compile(r"article|content|story|body", re.I)},
    {"name": "main"},
]

_JUNK_TAGS = [
    "script", "style", "nav", "header", "footer", "aside",
    "figure", "figcaption", "noscript", "form", "button",
    "iframe", "svg", "advertisement",
]

_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _extract_via_newspaper(url: str) -> Optional[str]:
    if not NEWSPAPER_AVAILABLE:
        return None
    try:
        article = NewspaperArticle(url, request_timeout=REQUEST_TIMEOUT)
        article.download()
        article.parse()
        text = (article.text or "").strip()
        return text if len(text) > 100 else None
    except Exception:
        return None


def _extract_via_bs4(html: str) -> Optional[str]:
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(_JUNK_TAGS):
        tag.decompose()

    container = None
    for selector in _CONTENT_TAGS:
        name = selector["name"]
        cls  = selector.get("class_")
        container = soup.find(name, class_=cls) if cls else soup.find(name)
        if container:
            break

    target = container or soup.find("body") or soup
    paragraphs = target.find_all("p")
    text = " ".join(p.get_text(separator=" ").strip() for p in paragraphs)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) > 100 else None


def _clean_text(text: str) -> str:
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line or len(line) < 20:
            continue
        if re.search(r"cookie|subscribe|newsletter|javascript|sign in|log in|advertisement", line, re.I):
            continue
        cleaned.append(line)
    return " ".join(cleaned)


def extract_article_text(article: dict, session: requests.Session | None = None) -> dict:
    url = article.get("url", "")
    if not url:
        article["extraction_status"] = "No URL"
        return article

    text = None
    # Skip full download if URL is a Google News redirect shell (it won't have body)
    if "news.google.com/rss/articles" not in url:
        # Fast extraction via newspaper3k
        text = _extract_via_newspaper(url)

        # Fallback to direct HTTP + BS4
        if not text:
            try:
                s = session or requests
                resp = s.get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
                if resp.status_code == 200:
                    text = _extract_via_bs4(resp.text)
            except Exception:
                pass

    # Fallback to feed excerpt
    if not text:
        excerpt = article.get("excerpt", "")
        if len(excerpt) >= 40:
            text = excerpt
            article["extraction_status"] = "Excerpt only"
        else:
            article["extraction_status"] = "Failed"
            article["text"] = ""
            article["word_count"] = 0
            return article
    else:
        article["extraction_status"] = "Success"

    text = _clean_text(text)
    article["text"]       = text
    article["word_count"] = len(text.split())
    return article


def extract_all(articles: list[dict], progress_callback=None) -> list[dict]:
    total = len(articles)
    completed = 0
    session = requests.Session()
    session.headers.update(_HEADERS)

    # Parallel extraction using up to 8 threads
    with ThreadPoolExecutor(max_workers=min(8, max(1, total))) as executor:
        futures = {executor.submit(extract_article_text, a, session): a for a in articles}
        for future in as_completed(futures):
            completed += 1
            if progress_callback:
                progress_callback(completed, total)

    return articles
