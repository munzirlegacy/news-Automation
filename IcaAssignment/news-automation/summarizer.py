"""
summarizer.py - Generates concise summaries for each article.

Two back-ends are supported (chosen automatically):
  1. Extractive (default, no API key needed):
       Uses the sumy library with the LSA algorithm.
       Falls back to a simple first-N-sentences heuristic if sumy fails.
  2. OpenAI (optional, requires OPENAI_API_KEY in .env):
       Calls gpt-3.5-turbo for abstractive summaries.
       Only activated when the key is present.

The summariser reads ONLY from article["text"] (and falls back to
article["excerpt"]).  It NEVER invents information.
"""

from __future__ import annotations

import logging
import re
import textwrap
from typing import Optional

from config import (
    OPENAI_API_KEY,
    SUMMARY_SENTENCE_COUNT,
    MIN_ARTICLE_CHARS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sumy imports (optional)
# ---------------------------------------------------------------------------
try:
    from sumy.parsers.plaintext import PlaintextParser
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.summarizers.lsa import LsaSummarizer
    from sumy.nlp.stemmers import Stemmer
    from sumy.utils import get_stop_words
    SUMY_AVAILABLE = True
except ImportError:
    SUMY_AVAILABLE = False
    logger.warning("sumy not available; using fallback sentence splitter.")

# ---------------------------------------------------------------------------
# OpenAI import (optional)
# ---------------------------------------------------------------------------
OPENAI_AVAILABLE = False
if OPENAI_API_KEY:
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        OPENAI_AVAILABLE = True
        logger.info("OpenAI API key detected – abstractive summaries enabled.")
    except ImportError:
        logger.warning("openai package not installed; ignoring API key.")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> list[str]:
    """
    Simple regex-based sentence splitter used as a fallback.
    Handles common abbreviations poorly but is dependency-free.
    """
    # Split on . ! ? followed by whitespace and an uppercase letter
    raw = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text.strip())
    return [s.strip() for s in raw if len(s.strip()) > 20]


def _extractive_sumy(text: str, n_sentences: int) -> Optional[str]:
    """LSA extractive summarisation via sumy."""
    if not SUMY_AVAILABLE:
        return None
    try:
        parser    = PlaintextParser.from_string(text, Tokenizer("english"))
        stemmer   = Stemmer("english")
        summarizer = LsaSummarizer(stemmer)
        summarizer.stop_words = get_stop_words("english")
        sentences = summarizer(parser.document, n_sentences)
        return " ".join(str(s) for s in sentences).strip() or None
    except Exception as exc:  # noqa: BLE001
        logger.debug("sumy error: %s", exc)
        return None


def _extractive_fallback(text: str, n_sentences: int) -> str:
    """Return the first *n_sentences* sentences from *text*."""
    sentences = _split_sentences(text)
    chosen = sentences[:n_sentences] if sentences else [text[:400]]
    return " ".join(chosen).strip()


def _abstractive_openai(text: str) -> Optional[str]:
    """Call OpenAI gpt-3.5-turbo for a 2-4 sentence summary."""
    if not OPENAI_AVAILABLE:
        return None
    try:
        snippet = text[:3000]   # keep prompt within token budget
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a news editor. Summarise the following article text "
                        "in 2-4 concise sentences. Use only information present in the "
                        "text. Do not add facts, opinions or speculation."
                    ),
                },
                {"role": "user", "content": snippet},
            ],
            max_tokens=200,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("OpenAI summarisation failed: %s", exc)
        return None

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def summarize_article(article: dict) -> dict:
    """
    Generate a summary for a single article dict.
    Modifies article["summary"] in-place and returns the dict.
    """
    text    = (article.get("text", "") or "").strip()
    excerpt = (article.get("excerpt", "") or "").strip()

    # Decide which text to summarise
    source_text = text if len(text) >= MIN_ARTICLE_CHARS else excerpt

    if not source_text or len(source_text) < 50:
        article["summary"] = "⚠️ Insufficient article content to generate a summary."
        article["summary_method"] = "none"
        return article

    # Prefer OpenAI abstractive summary (if key provided)
    if OPENAI_AVAILABLE:
        summary = _abstractive_openai(source_text)
        if summary:
            article["summary"]        = summary
            article["summary_method"] = "openai"
            return article

    # Extractive – sumy LSA
    summary = _extractive_sumy(source_text, SUMMARY_SENTENCE_COUNT)
    if summary:
        article["summary"]        = summary
        article["summary_method"] = "extractive-lsa"
        return article

    # Fallback – first N sentences
    summary = _extractive_fallback(source_text, SUMMARY_SENTENCE_COUNT)
    article["summary"]        = summary
    article["summary_method"] = "extractive-firstN"
    return article


def summarize_all(articles: list[dict], progress_callback=None) -> list[dict]:
    """
    Summarise every article in the list.

    Parameters
    ----------
    articles         : List of article dicts (text already extracted).
    progress_callback: Optional callable(current, total) for UI progress.
    """
    total = len(articles)
    for i, article in enumerate(articles, start=1):
        logger.info("Summarising [%d/%d]: %s", i, total, article.get("title", "?"))
        summarize_article(article)
        if progress_callback:
            progress_callback(i, total)
    return articles

