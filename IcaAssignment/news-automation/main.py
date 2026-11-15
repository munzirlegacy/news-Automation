"""
main.py - Command-line entry point for NewsPulse.

Usage:
    python main.py --query "Artificial Intelligence" --limit 10
    python main.py --query "Cybersecurity" --limit 5

This script runs the full pipeline without the Streamlit frontend,
which is useful for quick testing and scheduled automation.
"""

from __future__ import annotations

import argparse
import logging
import sys
import os

# ---------------------------------------------------------------------------
# Logging setup (must happen before any module imports that use logging)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Project modules
# ---------------------------------------------------------------------------
from news_fetcher      import fetch_articles
from article_extractor import extract_all
from summarizer        import summarize_all
from data_processor    import process_articles
from export_manager    import export_all
from config            import OUTPUT_DIR


def run_pipeline(query: str, max_articles: int = 10) -> list[dict]:
    """
    Execute the full NewsPulse pipeline.

    1. Discover articles from RSS feeds (no LLM).
    2. Filter, deduplicate and validate.
    3. Extract full article text.
    4. Generate extractive summaries.
    5. Export JSON, CSV and Markdown.

    Returns the final list of processed article dicts.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    logger.info("=" * 60)
    logger.info("NewsPulse – News Discovery & Summarisation Pipeline")
    logger.info("Query: %r   Max articles: %d", query, max_articles)
    logger.info("=" * 60)

    # Step 1 – Discovery
    logger.info("[1/5] Discovering articles …")
    raw_articles = fetch_articles(query, max_articles=max_articles * 3)
    logger.info("      Discovered %d raw articles.", len(raw_articles))

    if not raw_articles:
        logger.warning("No articles found for query %r.", query)
        return []

    # Step 2 – Filter + dedup
    logger.info("[2/5] Filtering and deduplicating …")
    articles = process_articles(raw_articles)
    articles = articles[:max_articles]
    logger.info("      %d articles after processing.", len(articles))

    if len(articles) < 5:
        logger.warning(
            "Only %d article(s) found (target: 5). "
            "This may be due to limited source coverage for this topic.",
            len(articles),
        )

    # Step 3 – Article extraction
    logger.info("[3/5] Extracting article text …")
    articles = extract_all(articles)

    # Step 4 – Summarisation
    logger.info("[4/5] Generating summaries …")
    articles = summarize_all(articles)

    # Step 5 – Export
    logger.info("[5/5] Exporting outputs …")
    paths = export_all(articles, query=query)
    logger.info("      JSON     → %s", paths["json"])
    logger.info("      CSV      → %s", paths["csv"])
    logger.info("      Markdown → %s", paths["markdown"])

    # Summary report
    successful_summaries = sum(
        1 for a in articles
        if a.get("summary") and not a["summary"].startswith("⚠️")
    )
    publishers = {a.get("publisher", "Unknown") for a in articles}

    logger.info("=" * 60)
    logger.info("Pipeline complete.")
    logger.info("  Articles collected  : %d", len(articles))
    logger.info("  Unique publishers   : %d (%s)", len(publishers), ", ".join(sorted(publishers)))
    logger.info("  Successful summaries: %d", successful_summaries)
    logger.info("=" * 60)

    return articles


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="NewsPulse – Automated News Discovery & Summarisation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --query "Artificial Intelligence" --limit 10
  python main.py --query "Cybersecurity" --limit 5
  python main.py --query "Space Exploration" --limit 15
        """,
    )
    parser.add_argument(
        "--query", "-q",
        required=True,
        help="Topic to search for (e.g. 'Artificial Intelligence')",
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=5,
        help="Maximum number of articles to collect (default: 5)",
    )
    args = parser.parse_args()

    articles = run_pipeline(args.query, args.limit)

    if not articles:
        logger.error("Pipeline returned no articles. Exiting.")
        sys.exit(1)

    # Quick results preview
    print("\n" + "=" * 60)
    print(f"Results for: {args.query!r}")
    print("=" * 60)
    for i, a in enumerate(articles, start=1):
        print(f"\n[{i}] {a['title']}")
        print(f"    Publisher : {a['publisher']}")
        print(f"    Published : {a['published']}")
        print(f"    URL       : {a['url']}")
        print(f"    Summary   : {a['summary'][:180]}…" if len(a.get('summary', '')) > 180 else f"    Summary   : {a.get('summary', 'N/A')}")


if __name__ == "__main__":
    main()

