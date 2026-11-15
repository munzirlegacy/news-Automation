# 📰 NewsPulse – Automated News Discovery & Summarisation

> **Python Automation Internship Assessment Project**

NewsPulse is a fully automated, production-ready news aggregation and summarisation application.
A user enters any topic (e.g. *Artificial Intelligence*, *Cybersecurity*, *Space Exploration*, *Electric Vehicles*, *Business*, *Technology*), and the system automatically discovers recent news from multiple distinct publishers via Python RSS feeds and public APIs, retrieves article text, generates concise grounded summaries using extractive NLP, and presents the results in an interactive, modern Streamlit dashboard and exported files (JSON, CSV, Markdown).

---

## ⚡ Core Compliance Note (Assessment Requirement)

> **Mandatory Separation of Responsibilities:**
> - **Discovery & Retrieval:** 100% implemented using actual Python code (`feedparser`, `requests`, `newspaper3k`, `BeautifulSoup4`). **No LLMs, chatbots, or AI search assistants are used to discover, search for, or fetch news articles.**
> - **Summarisation:** Implemented via offline Python extractive summarisation (`sumy` LSA / LexRank). An LLM is entirely optional and strictly isolated to summarisation when an API key is supplied.
> - **Integrity:** Never uses hardcoded articles, placeholder databases, or fabricated news records.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| **Multi-Source Discovery** | Discovers news across 12+ verified global publishers (BBC News, The Guardian, TechCrunch, Wired, NPR, Ars Technica, New York Times, NASA, CNBC, MIT Technology Review, Al Jazeera, Bing News, Google News). |
| **Dynamic Topic Querying** | Handles any runtime keyword or phrase (e.g. "Artificial Intelligence", "Cybersecurity", "Electric Vehicles", "Space Exploration"). |
| **Past 7-Day Freshness Window** | Evaluates publication timestamps and guarantees all returned stories are from the past 7 days. |
| **Deduplication & Quality Filter** | Strips duplicate URLs, near-duplicate headlines (fuzzy fingerprinting), and filters out irrelevant content. |
| **Full Article Text Extraction** | Polite, multi-stage fallback extraction: `newspaper3k` → `BeautifulSoup4` heuristic DOM parsing → RSS excerpt. |
| **Faithful Summarisation** | Produces concise 2–4 sentence summaries grounded strictly in retrieved text; flags short/insufficient content transparently. |
| **Multi-Format Data Exports** | Automatically generates `news.json`, `news.csv`, and `digest.md` with active links back to original articles. |
| **Modern news dashboard** | Responsive Streamlit interface with a polished teal theme, at-a-glance stats, publisher filters, readable article cards, and one-click exports. |

---

## 🛠️ Technology Stack

| Layer | Tools & Libraries |
|---|---|
| **Language** | Python 3.10+ (tested on Python 3.12) |
| **Feed Ingestion** | `feedparser` |
| **HTTP Networking** | `requests` (with timeout, retries, and headers) |
| **HTML & DOM Extraction** | `beautifulsoup4`, `lxml` |
| **Article Extraction** | `newspaper3k` |
| **Extractive Summarisation** | `sumy` (LSA algorithm), `nltk` |
| **Frontend UI** | `streamlit` |
| **Configuration** | `python-dotenv` |
| **Data Formats** | JSON, CSV, Markdown |
| **Version Control** | Git |

---

## 📂 Project Structure

```
news-automation/
│
├── app.py               # Streamlit web dashboard
├── main.py              # CLI entry point (standalone automated pipeline)
├── news_fetcher.py      # Multi-source RSS news discovery engine
├── article_extractor.py # Web scraping and text cleaning pipeline
├── summarizer.py        # Extractive (sumy LSA) & optional abstractive summariser
├── data_processor.py    # Deduplication, 7-day date filter, and quality validator
├── export_manager.py    # Exporters for news.json, news.csv, and digest.md
├── config.py            # Central configuration, timeouts, sources, and thresholds
│
├── output/              # Runtime output folder (news.json, news.csv, digest.md)
├── sample_output/       # Pre-generated sample run deliverables for assessment review
│   ├── news.json        # Machine-readable JSON records
│   ├── news.csv         # Tabular CSV with metadata and summaries
│   └── digest.md        # Human-readable Markdown digest
│
├── requirements.txt     # Python package dependencies
├── README.md            # Comprehensive documentation
├── .env.example         # Sample environment configuration file
└── .gitignore           # Git ignore rules
```

---

## ⚙️ Installation & Setup

### 1. Clone or Open the Repository

```bash
cd news-automation
```

### 2. Set Up a Virtual Environment (Recommended)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Required Dependencies

```bash
pip install -r requirements.txt
```

### 4. Download Required NLTK Corpora

```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('stopwords')"
```

### 5. Optional Environment Configuration

```bash
cp .env.example .env
```
*(By default, NewsPulse uses the built-in extractive summariser and requires zero API keys or external accounts. If you want optional OpenAI GPT summarisation, set `OPENAI_API_KEY=your_key` in `.env`.)*

---

## 🚀 Running the Application

### A. Modern Streamlit Web Dashboard (Recommended)

To launch the interactive dashboard:

```bash
streamlit run app.py
```

Then open your browser at `http://localhost:8501`.

**Dashboard Features:**
1. **Search Bar:** Enter any topic (e.g. `Artificial Intelligence`, `Cybersecurity`, `Space Exploration`).
2. **Limit Selector:** Choose 5, 10, or 15 articles.
3. **Real-Time KPIs:** Live counts of collected articles, distinct news sources, and completed summaries.
4. **Interactive News Cards:** Title, publisher badge, publication date, word count, 2-4 sentence summary, and direct "Read Original Article" link.
5. **Publisher Filter:** Dynamically slice and view articles by specific news outlets.
6. **One-Click Downloads:** Download `news.json`, `news.csv`, and `digest.md` directly from the UI.

### B. Command-Line Interface (CLI)

The CLI runs the entire pipeline end-to-end and writes outputs directly to disk:

```bash
# Basic search with default limit (5)
python main.py --query "Artificial Intelligence"

# Specify custom limit
python main.py --query "Cybersecurity" --limit 5

# Additional examples
python main.py --query "Space Exploration" --limit 5
python main.py --query "Electric Vehicles" --limit 10
python main.py --query "Technology"        --limit 10
python main.py --query "Business"          --limit 5
```

---

## 📰 Sample Execution Deliverables

As required by the assessment guidelines, sample execution outputs from real automated runs are preserved in the `sample_output/` folder:

- **`sample_output/news.json`**: Structured JSON dataset containing article records, timestamps, URLs, word counts, and grounded summaries.
- **`sample_output/news.csv`**: Tabular export ready for spreadsheet or analytical review.
- **`sample_output/digest.md`**: Clean, formatted Markdown digest with source attribution links and extractive summaries.

---

## 🔍 Technical Implementation Details

### 1. News Discovery & Collection
- **Zero-LLM Retrieval:** RSS feeds from top international publishers are polled concurrently using `feedparser` and `requests`.
- **Query Feeds:** Dynamic topic search feeds query real-time publisher indexes (e.g., Google News RSS, Bing News RSS) using URL-encoded search topics.
- **URL Unwrapping:** Aggregator redirect parameters (such as Bing `apiclick.aspx?url=...`) are automatically parsed and decoded into direct destination URLs.
- **Source Prioritization:** Direct publisher URLs are prioritized to maximize full article body extraction.

### 2. Cleaning & Deduplication
- **URL Normalisation:** Strips tracking parameters and removes duplicate URLs.
- **Title Fingerprinting:** MD5-based fuzzy fingerprinting detects syndicated or near-duplicate articles across different outlets.
- **Freshness Window:** Converts feed datetime structures (`published_parsed`, `updated_parsed`) to timezone-aware UTC timestamps and validates that articles fall within the last 7 days (`MAX_AGE_DAYS = 7`).

### 3. Full-Text Extraction
- Primary attempt: `newspaper3k` downloads and parses DOM content into clean prose.
- Secondary fallback: Heuristic `BeautifulSoup4` search targeting `<article>`, `<main>`, and content divs.
- Tertiary fallback: RSS feed description/summary with explicit `Excerpt only` labeling.

### 4. Grounded Summarisation
- Uses the **Latent Semantic Analysis (LSA)** extractive summarisation algorithm from the `sumy` library.
- Extracts the top 2–4 most representative sentences strictly from the harvested article text.
- Never introduces hallucinations, external knowledge, or fabricated statements.

---

## ⚠️ Known Limitations & Mitigations

- **Paywalled & Anti-Bot Sites:** Certain sites (e.g., Bloomberg, FT) block automated requests. The system gracefully catches HTTP 401/403/429/503 errors and falls back to clean feed excerpts without crashing.
- **Niche Topics:** For highly esoteric keywords, fewer than 5 recent articles might exist within the strict 7-day window. In such cases, the system honestly reports the shortfall and presents all verified records found without inventing fake data.

---

## 🔮 Future Improvements

1. **Scheduled Monitoring (Daemon/Cron):** Integrate automated hourly or daily digests dispatched via email or Slack webhooks.
2. **Clustering & Topic Modeling:** Use TF-IDF or LDA to group related articles covering the same breaking story across different publications.
3. **Sentiment Analysis:** Add an NLP sentiment score (Positive / Neutral / Negative) to track public perception of business or tech trends over time.
4. **Historical Database Storage:** Persist past scrapes into a SQLite / PostgreSQL database for trend analysis and historical news retrieval.

---

## 📄 Licence

MIT License. Developed for the Python Automation Internship Assessment.
