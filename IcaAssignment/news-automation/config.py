"""
config.py - Streamlined, high-speed configuration for NewsPulse.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Request / network settings (Fast, snappy defaults)
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT = 3.5         # tight timeout for quick response
MAX_RETRIES     = 0           # no retries on slow/dead endpoints
USER_AGENT      = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ---------------------------------------------------------------------------
# Article freshness window
# ---------------------------------------------------------------------------
MAX_AGE_DAYS = 7   # articles from the past 7 days

# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------
OUTPUT_DIR    = os.path.join(os.path.dirname(__file__), "output")
JSON_PATH     = os.path.join(OUTPUT_DIR, "news.json")
CSV_PATH      = os.path.join(OUTPUT_DIR, "news.csv")
DIGEST_PATH   = os.path.join(OUTPUT_DIR, "digest.md")

# ---------------------------------------------------------------------------
# Summarizer settings
# ---------------------------------------------------------------------------
SUMMARY_SENTENCE_COUNT = 3
MIN_ARTICLE_CHARS      = 120

# ---------------------------------------------------------------------------
# Optional: OpenAI key
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ---------------------------------------------------------------------------
# Curated, High-Speed, Top-Tier News Feeds
# Query-aware feeds search dynamically for ANY user topic in ~1.5s.
# Direct feeds provide instant access to major global publications.
# ---------------------------------------------------------------------------
NEWS_SOURCES = [
    # --- Instant Dynamic Search (Covers 100% of topics in ~1.5s) ---
    {
        "publisher": "Google News",
        "feeds": [
            "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en",
        ],
        "use_query": True,
    },
    {
        "publisher": "Bing News",
        "feeds": [
            "https://www.bing.com/news/search?q={query}&format=rss",
        ],
        "use_query": True,
    },

    # --- Top Fast Direct Global Publishers ---
    {
        "publisher": "The Guardian",
        "feeds": [
            "https://www.theguardian.com/technology/rss",
            "https://www.theguardian.com/science/rss",
            "https://www.theguardian.com/business/rss",
        ],
        "use_query": False,
    },
    {
        "publisher": "BBC News",
        "feeds": [
            "http://feeds.bbci.co.uk/news/technology/rss.xml",
            "http://feeds.bbci.co.uk/news/business/rss.xml",
            "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        ],
        "use_query": False,
    },
    {
        "publisher": "TechCrunch",
        "feeds": [
            "https://techcrunch.com/feed/",
        ],
        "use_query": False,
    },
    {
        "publisher": "Wired",
        "feeds": [
            "https://www.wired.com/feed/rss",
        ],
        "use_query": False,
    },
    {
        "publisher": "Ars Technica",
        "feeds": [
            "https://feeds.arstechnica.com/arstechnica/index",
        ],
        "use_query": False,
    },
    {
        "publisher": "CNBC",
        "feeds": [
            "https://www.cnbc.com/id/100003114/device/rss/rss.html",
            "https://www.cnbc.com/id/19854910/device/rss/rss.html",
        ],
        "use_query": False,
    },
    {
        "publisher": "NPR",
        "feeds": [
            "https://feeds.npr.org/1001/rss.xml",
            "https://feeds.npr.org/1019/rss.xml",
        ],
        "use_query": False,
    },
    {
        "publisher": "NASA",
        "feeds": [
            "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        ],
        "use_query": False,
    },
]
