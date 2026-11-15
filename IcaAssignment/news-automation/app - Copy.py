"""
app.py - NewsPulse Streamlit Dashboard

Professional news aggregation and summarisation dashboard.
Runs the full Python-based pipeline (no LLMs for discovery).
"""

from __future__ import annotations

import io
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

import streamlit as st

# ---------------------------------------------------------------------------
# Page config MUST be the very first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="NewsPulse",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Project modules
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))

from news_fetcher      import fetch_articles
from article_extractor import extract_all
from summarizer        import summarize_all
from data_processor    import process_articles
from export_manager    import export_all, export_json, export_csv, export_markdown
from config            import OUTPUT_DIR, MAX_AGE_DAYS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom styling for the NewsPulse dashboard
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
  .stApp {
    background:
      radial-gradient(ellipse at 92% 2%, rgba(20, 116, 113, 0.08), transparent 28rem),
      #F3F6F8;
    color: #172B3A;
  }
  .block-container {
    max-width: 1180px;
    padding-top: 2.25rem;
    padding-bottom: 1.5rem;
  }

  .np-header {
    position: relative;
    overflow: hidden;
    isolation: isolate;
    background:
      radial-gradient(circle at 88% 18%, rgba(115, 214, 188, 0.24), transparent 15rem),
      linear-gradient(125deg, #102A43 0%, #123D53 52%, #12645F 100%);
    padding: 2.5rem 2.75rem 2.35rem;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 24px;
    margin-bottom: 1.6rem;
    box-shadow: 0 20px 50px rgba(16, 42, 67, 0.16);
  }
  .np-header::after {
    position: absolute;
    z-index: -1;
    content: "";
    width: 15rem;
    height: 15rem;
    right: -5rem;
    bottom: -10rem;
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 50%;
    box-shadow: 0 0 0 2rem rgba(255, 255, 255, 0.035), 0 0 0 4rem rgba(255, 255, 255, 0.025);
  }
  .np-header-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1.3rem;
  }
  .np-kicker {
    color: #A7E4D0;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }
  .np-live {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    color: rgba(255, 255, 255, 0.82);
    font-size: 0.78rem;
    font-weight: 500;
  }
  .np-live-dot {
    width: 0.48rem;
    height: 0.48rem;
    background: #75D6BC;
    border-radius: 50%;
    box-shadow: 0 0 0 4px rgba(117, 214, 188, 0.15);
  }
  .np-header h1 {
    color: #FFFFFF;
    font-size: clamp(2.2rem, 5vw, 3.25rem);
    font-weight: 700;
    margin: 0 0 0.45rem;
    letter-spacing: -0.055em;
    line-height: 1.05;
  }
  .np-header h1 span {
    color: #85DDC3;
  }
  .np-header p {
    max-width: 38rem;
    color: rgba(255, 255, 255, 0.78);
    font-size: 1.04rem;
    line-height: 1.6;
    margin: 0 0 1.25rem;
  }
  .np-badge {
    display: inline-flex;
    align-items: center;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.17);
    color: rgba(255, 255, 255, 0.92);
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.025em;
    padding: 0.42rem 0.75rem;
    border-radius: 999px;
  }

  .np-stat-card {
    position: relative;
    overflow: hidden;
    background: linear-gradient(145deg, #FFFFFF 0%, #F8FBFC 100%);
    border: 1px solid #E1E9ED;
    border-radius: 16px;
    padding: 1.15rem 1.3rem;
    box-shadow: 0 5px 16px rgba(25, 52, 69, 0.045);
    margin-bottom: 0.35rem;
  }
  .np-stat-card::before {
    position: absolute;
    top: 0;
    left: 0;
    width: 3px;
    height: 100%;
    background: linear-gradient(180deg, #27A889, #7BD6BB);
    content: "";
  }
  .np-stat-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: #71818C;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-bottom: 0.6rem;
  }
  .np-stat-value {
    color: #153B4A;
    font-size: 1.85rem;
    font-weight: 700;
    letter-spacing: -0.04em;
    line-height: 1.1;
  }

  .np-article-card {
    background: #FFFFFF;
    border: 1px solid #E2E9ED;
    border-left: 4px solid #27A889;
    border-radius: 16px;
    padding: 1.35rem 1.55rem;
    margin-bottom: 0.9rem;
    box-shadow: 0 5px 18px rgba(25, 52, 69, 0.045);
    transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
  }
  .np-article-card:hover {
    transform: translateY(-2px);
    border-color: #C6DDD7;
    box-shadow: 0 12px 28px rgba(25, 73, 78, 0.1);
  }
  .np-article-title {
    color: #153B4A;
    font-size: 1.08rem;
    font-weight: 600;
    line-height: 1.5;
    margin-bottom: 0.7rem;
  }
  .np-article-meta {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-bottom: 0.95rem;
  }
  .np-meta-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.78rem;
    font-weight: 500;
    color: #536873;
    background: #F1F6F5;
    border: 1px solid #E6EEEB;
    padding: 0.28rem 0.62rem;
    border-radius: 999px;
  }
  .np-article-summary {
    color: #40545E;
    font-size: 0.92rem;
    line-height: 1.75;
    margin-bottom: 1rem;
    padding: 0.85rem 1rem;
    background: #F6F9F8;
    border: 1px solid #EDF2F0;
    border-radius: 10px;
  }
  .np-read-btn {
    display: inline-flex;
    align-items: center;
    background: #176F65;
    color: #FFFFFF !important;
    font-size: 0.8rem;
    font-weight: 600;
    padding: 0.55rem 0.85rem;
    border-radius: 9px;
    text-decoration: none !important;
    transition: background 160ms ease, transform 160ms ease;
  }
  .np-read-btn:hover {
    background: #10584F;
    transform: translateY(-1px);
  }

  .np-section-head {
    color: #183B49;
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: -0.015em;
    margin-bottom: 0.55rem;
  }
  .np-section-caption {
    color: #74838D;
    font-size: 0.86rem;
    margin: 0 0 1.15rem;
  }

  .np-info-box {
    background: #EEF8F5;
    border: 1px solid #CFE9DF;
    border-radius: 12px;
    padding: 0.9rem 1rem;
    margin-bottom: 1rem;
    font-size: 0.9rem;
    color: #236657;
  }
  .np-warn-box {
    background: #FFF8E9;
    border: 1px solid #F3E0B4;
    border-radius: 12px;
    padding: 0.9rem 1rem;
    margin-bottom: 1rem;
    font-size: 0.9rem;
    color: #80591C;
  }
  .np-error-box {
    background: #FFF1EF;
    border: 1px solid #F0D0CA;
    border-radius: 12px;
    padding: 0.9rem 1rem;
    margin-bottom: 1rem;
    font-size: 0.9rem;
    color: #913F34;
  }

  .np-empty {
    background: rgba(255, 255, 255, 0.72);
    border: 1px dashed #C9D7D8;
    border-radius: 18px;
    text-align: center;
    padding: 2.4rem 1rem;
    color: #73848E;
  }
  .np-empty-icon {
    color: #258C7C;
    font-size: 2.3rem;
    margin-bottom: 0.45rem;
  }
  .np-empty-title {
    color: #294A56;
    font-size: 1.05rem;
    font-weight: 600;
    margin-bottom: 0.35rem;
  }

  .np-flag {
    display: inline-flex;
    font-size: 0.7rem;
    background: #FFF5DC;
    border: 1px solid #F4E2B6;
    color: #825E21;
    padding: 0.12rem 0.45rem;
    border-radius: 999px;
    margin-left: 0.4rem;
    font-weight: 500;
  }

  div[data-testid="stButton"] > button {
    width: 100%;
    min-height: 2.7rem;
    background: #176F65;
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.9rem;
    box-shadow: 0 5px 12px rgba(23, 111, 101, 0.16);
    transition: background 160ms ease, box-shadow 160ms ease, transform 160ms ease;
  }
  div[data-testid="stButton"] > button:hover {
    background: #10584F;
    color: #FFFFFF;
    box-shadow: 0 8px 16px rgba(23, 111, 101, 0.22);
    transform: translateY(-1px);
  }
  div[data-testid="stButton"] > button:focus-visible,
  div[data-testid="stDownloadButton"] > button:focus-visible,
  .np-read-btn:focus-visible {
    outline: 3px solid rgba(39, 168, 137, 0.4);
    outline-offset: 3px;
  }
  div[data-testid="stDownloadButton"] > button {
    width: 100%;
    min-height: 2.7rem;
    background: #FFFFFF;
    color: #176F65;
    border: 1px solid #C9DED8;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.86rem;
    transition: background 160ms ease, border-color 160ms ease;
  }
  div[data-testid="stDownloadButton"] > button:hover {
    background: #F0F8F5;
    border-color: #81BCAE;
    color: #10584F;
  }
  div[data-testid="stTextInput"] input {
    min-height: 2.7rem;
    background: #FFFFFF;
    border: 1px solid #D6E0E4;
    border-radius: 10px;
    color: #183B49;
    padding: 0.55rem 0.8rem;
    transition: border-color 160ms ease, box-shadow 160ms ease;
  }
  div[data-testid="stTextInput"] input:focus {
    border-color: #55A998;
    box-shadow: 0 0 0 3px rgba(39, 168, 137, 0.12);
  }
  .stProgress > div > div {
    background: #27A889;
  }
  div[data-testid="stMultiSelect"] > label,
  div[data-testid="stSelectbox"] > label {
    color: #536873;
    font-weight: 600;
  }
  hr {
    border-color: #E1E8EB;
    opacity: 0.8;
  }

  @media (max-width: 700px) {
    .block-container {
      padding-top: 1.1rem;
      padding-bottom: 1rem;
    }
    .np-header {
      padding: 1.55rem 1.35rem 1.45rem;
      border-radius: 18px;
    }
    .np-header-top {
      align-items: flex-start;
      flex-direction: column;
      gap: 0.6rem;
      margin-bottom: 1.1rem;
    }
    .np-article-card {
      padding: 1.05rem 1rem;
    }
    .np-article-meta {
      gap: 0.4rem;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      scroll-behavior: auto !important;
      transition-duration: 0.01ms !important;
    }
  }
</style>
"""

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
def init_session() -> None:
    defaults = {
        "articles": [],
        "query":    "",
        "ran":      False,
        "error":    None,
        "stats": {
            "total":      0,
            "sources":    0,
            "summarised": 0,
        },
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ---------------------------------------------------------------------------
# Pipeline runner (cached per query+limit)
# ---------------------------------------------------------------------------
def run_pipeline(query: str, limit: int) -> tuple[list[dict], dict]:
    """
    Run the full news pipeline and return (articles, stats).
    Uses Streamlit progress bars for user feedback.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    status_area = st.empty()
    prog_bar    = st.progress(0)

    def step(msg: str, pct: int) -> None:
        status_area.info(f"⏳ {msg}")
        prog_bar.progress(pct)

    try:
        # 1 — Discover
        step("Discovering articles from RSS feeds …", 10)
        raw = fetch_articles(query, max_articles=limit * 3)

        if not raw:
            status_area.empty()
            prog_bar.empty()
            return [], {"total": 0, "sources": 0, "summarised": 0}

        # 2 — Filter / dedup
        step(f"Filtering and deduplicating {len(raw)} candidates …", 25)
        articles = process_articles(raw)
        articles = articles[:limit]

        # 3 — Extract text
        step(f"Extracting full text for {len(articles)} articles …", 45)
        total_ext = len(articles)
        ext_prog  = st.progress(0, text="Extracting article text…")

        def ext_cb(cur: int, tot: int) -> None:
            ext_prog.progress(int(cur / tot * 100), text=f"Extracting {cur}/{tot}…")

        articles = extract_all(articles, progress_callback=ext_cb)
        ext_prog.empty()

        # 4 — Summarise
        step(f"Generating summaries for {len(articles)} articles …", 70)
        sum_prog = st.progress(0, text="Summarising…")

        def sum_cb(cur: int, tot: int) -> None:
            sum_prog.progress(int(cur / tot * 100), text=f"Summarising {cur}/{tot}…")

        articles = summarize_all(articles, progress_callback=sum_cb)
        sum_prog.empty()

        # 5 — Export
        step("Saving exports (JSON / CSV / Markdown) …", 90)
        export_all(articles, query=query)

        prog_bar.progress(100)
        status_area.success("✅ Pipeline complete!")
        time.sleep(0.8)
        status_area.empty()
        prog_bar.empty()

        successful = sum(
            1 for a in articles
            if a.get("summary") and not a["summary"].startswith("⚠️")
        )
        sources = len({a.get("publisher", "?") for a in articles})
        stats = {
            "total":      len(articles),
            "sources":    sources,
            "summarised": successful,
        }
        return articles, stats

    except Exception as exc:  # noqa: BLE001
        status_area.empty()
        prog_bar.empty()
        logger.exception("Pipeline error: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _fmt_date(iso: str) -> str:
    if not iso or iso == "Unknown":
        return "Unknown date"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y, %H:%M UTC")
    except Exception:
        return iso


def render_stat_card(label: str, value: str | int, col) -> None:
    col.markdown(
        f"""<div class="np-stat-card">
              <div class="np-stat-label">{label}</div>
              <div class="np-stat-value">{value}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def render_article_card(a: dict, idx: int) -> None:
    title     = a.get("title",     "No Title")
    publisher = a.get("publisher", "Unknown Publisher")
    published = _fmt_date(a.get("published", "Unknown"))
    url       = a.get("url",       "#")
    summary   = a.get("summary",   "No summary available.")
    flags     = a.get("quality_flags", [])
    method    = a.get("summary_method", "unknown")
    words     = a.get("word_count", 0)

    flag_html = "".join(
        f'<span class="np-flag">{f.replace("missing:", "⚠ missing ")}</span>'
        for f in flags
    )

    # Warn icon if summary is empty / insufficient
    sum_prefix = "💬 " if not summary.startswith("⚠️") else ""
    method_label = {
        "openai":           "OpenAI",
        "extractive-lsa":   "Extractive (LSA)",
        "extractive-firstN":"Extractive",
        "none":             "—",
    }.get(method, method)

    st.markdown(
        f"""<div class="np-article-card">
          <div class="np-article-title">#{idx} &nbsp; {title}{flag_html}</div>
          <div class="np-article-meta">
            <span class="np-meta-chip">🏢 {publisher}</span>
            <span class="np-meta-chip">📅 {published}</span>
            <span class="np-meta-chip">📝 {words} words</span>
            <span class="np-meta-chip">🔎 {method_label}</span>
          </div>
          <div class="np-article-summary">{sum_prefix}{summary}</div>
          <a class="np-read-btn" href="{url}" target="_blank" rel="noopener">
            🔗 Read Original Article
          </a>
        </div>""",
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    st.markdown(
        """<div class="np-empty">
            <div class="np-empty-icon">🔍</div>
            <div class="np-empty-title">No articles yet</div>
            <div>Enter a topic above and click <strong>Search News</strong> to start.</div>
           </div>""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Export helpers (in-memory bytes for download buttons)
# ---------------------------------------------------------------------------

def _articles_to_json_bytes(articles: list[dict], query: str) -> bytes:
    payload = {
        "query":       query,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "total":       len(articles),
        "articles":    articles,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def _articles_to_csv_bytes(articles: list[dict]) -> bytes:
    import csv
    fields = [
        "title", "publisher", "url", "published", "retrieved",
        "excerpt", "summary", "summary_method", "word_count", "extraction_status",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for a in articles:
        writer.writerow({f: str(a.get(f, "")) for f in fields})
    return buf.getvalue().encode("utf-8")


def _articles_to_md_bytes(articles: list[dict], query: str) -> bytes:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pubs = sorted({a.get("publisher", "?") for a in articles})
    lines = [
        "# 📰 NewsPulse – News Digest",
        "",
        f"**Topic:** {query}  ",
        f"**Generated:** {now}  ",
        f"**Articles:** {len(articles)}  ",
        f"**Sources:** {', '.join(pubs)}",
        "",
        "---",
        "",
    ]
    for i, a in enumerate(articles, 1):
        url = a.get("url", "#")
        lines += [
            f"## {i}. {a.get('title','No Title')}",
            "",
            f"**Publisher:** {a.get('publisher','?')}  ",
            f"**Published:** {_fmt_date(a.get('published','Unknown'))}  ",
            f"**URL:** [{url}]({url})",
            "",
            "**Summary:**",
            "",
            a.get("summary", "No summary."),
            "",
            "---",
            "",
        ]
    return "\n".join(lines).encode("utf-8")


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main() -> None:
    init_session()
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # ── Header ──────────────────────────────────────────────────────────────
    st.markdown(
        """<div class="np-header">
            <div class="np-header-top">
              <span class="np-kicker">Your daily news briefing</span>
              <span class="np-live"><span class="np-live-dot"></span>Fresh stories from public feeds</span>
            </div>
            <h1>NewsPulse<span>.</span></h1>
            <p>A clearer view of what’s happening. Search a topic to discover recent stories and concise summaries from trusted publishers.</p>
            <span class="np-badge">Python-powered · Public RSS feeds · Transparent summaries</span>
           </div>""",
        unsafe_allow_html=True,
    )

    # ── Search section ───────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown('<div class="np-section-head">Find your next story</div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="np-section-caption">Choose a topic and we’ll gather recent coverage across publishers.</p>',
            unsafe_allow_html=True,
        )

        col_q, col_lim, col_btn = st.columns([4, 1.5, 1.2])
        with col_q:
            query = st.text_input(
                "Topic",
                placeholder="e.g. Artificial Intelligence, Cybersecurity, Space Exploration …",
                label_visibility="collapsed",
            )
        with col_lim:
            limit = st.selectbox(
                "Articles",
                options=[5, 10, 15],
                index=0,
                label_visibility="visible",
            )
        with col_btn:
            st.write("")
            search_clicked = st.button("Search news")

    # ── Run pipeline on button click ─────────────────────────────────────────
    if search_clicked:
        q = query.strip()
        if not q:
            st.markdown(
                '<div class="np-warn-box">⚠️ Please enter a topic before searching.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.session_state["ran"]      = False
            st.session_state["articles"] = []
            st.session_state["error"]    = None
            st.session_state["query"]    = q

            try:
                articles, stats = run_pipeline(q, limit)
                st.session_state["articles"] = articles
                st.session_state["stats"]    = stats
                st.session_state["ran"]      = True
            except Exception as exc:
                st.session_state["error"] = str(exc)
                st.session_state["ran"]   = True

    # ── Error display ────────────────────────────────────────────────────────
    if st.session_state.get("error"):
        st.markdown(
            f'<div class="np-error-box">❌ An error occurred: {st.session_state["error"]}</div>',
            unsafe_allow_html=True,
        )

    # ── Dashboard (shown only after a successful run) ─────────────────────────
    if st.session_state.get("ran") and not st.session_state.get("error"):
        articles = st.session_state["articles"]
        stats    = st.session_state["stats"]
        q        = st.session_state["query"]

        # -- Stats row --------------------------------------------------------
        st.markdown("---")
        st.markdown('<div class="np-section-head">Your briefing at a glance</div>', unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        render_stat_card("Articles Collected", stats["total"],      c1)
        render_stat_card("News Sources",       stats["sources"],    c2)
        render_stat_card("Summaries Generated",stats["summarised"], c3)
        render_stat_card("Freshness Window",   f"{MAX_AGE_DAYS} days", c4)

        # -- Shortfall notice -------------------------------------------------
        if 0 < stats["total"] < 5:
            st.markdown(
                f'<div class="np-warn-box">⚠️ Only <strong>{stats["total"]}</strong> article(s) found '
                f'(target: 5). This topic may have limited recent coverage from the '
                f'configured RSS sources. Try a broader or alternative search term.</div>',
                unsafe_allow_html=True,
            )
        elif stats["total"] == 0:
            st.markdown(
                '<div class="np-error-box">❌ No articles were found for this topic. '
                'Please try a different search term.</div>',
                unsafe_allow_html=True,
            )

        # -- Articles ---------------------------------------------------------
        if articles:
            st.markdown("---")
            st.markdown(
                f'<div class="np-section-head">Latest coverage for “{q}”</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<p class="np-section-caption">Concise summaries with direct links to the original reporting.</p>',
                unsafe_allow_html=True,
            )

            # Publisher filter
            publishers = sorted({a.get("publisher", "?") for a in articles})
            selected_pub = st.multiselect(
                "Filter by publisher",
                options=["All"] + publishers,
                default=["All"],
            )
            filtered = (
                articles
                if "All" in selected_pub or not selected_pub
                else [a for a in articles if a.get("publisher") in selected_pub]
            )

            if not filtered:
                st.markdown(
                    '<div class="np-warn-box">No articles match the selected filter.</div>',
                    unsafe_allow_html=True,
                )
            else:
                for i, a in enumerate(filtered, 1):
                    render_article_card(a, i)

            # -- Export section -----------------------------------------------
            st.markdown("---")
            with st.container(border=True):
                st.markdown('<div class="np-section-head">Take your briefing with you</div>', unsafe_allow_html=True)
                st.markdown(
                    '<p class="np-section-caption">Export these stories to read, share, or archive.</p>',
                    unsafe_allow_html=True,
                )

                ec1, ec2, ec3 = st.columns(3)

                json_bytes = _articles_to_json_bytes(articles, q)
                csv_bytes  = _articles_to_csv_bytes(articles)
                md_bytes   = _articles_to_md_bytes(articles, q)

                with ec1:
                    st.download_button(
                        "Download JSON",
                        data=json_bytes,
                        file_name="news.json",
                        mime="application/json",
                    )
                with ec2:
                    st.download_button(
                        "Download CSV",
                        data=csv_bytes,
                        file_name="news.csv",
                        mime="text/csv",
                    )
                with ec3:
                    st.download_button(
                        "Download digest",
                        data=md_bytes,
                        file_name="digest.md",
                        mime="text/markdown",
                    )

                st.markdown(
                    '<div class="np-info-box" style="margin-top:0.8rem;">Files are also saved automatically '
                    'to the <code>output/</code> folder in the project directory.</div>',
                    unsafe_allow_html=True,
                )

    elif not st.session_state.get("ran"):
        # Empty state
        render_empty_state()

    # ── Footer ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        """<div style="text-align:center; color:#94A3B8; font-size:0.82rem; padding:0.5rem 0 1rem;">
            <strong>NewsPulse</strong> · News discovery powered by Python RSS feeds &amp; public APIs ·
            Summarisation via extractive NLP (sumy LSA) ·
            No LLMs used for article discovery or retrieval.
           </div>""",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
