# Comment Signal — Twitter/X Sentiment Analyzer

Point it at a tweet, and it pulls the replies, scores each one for sentiment, and lays the whole conversation out on a dashboard: how people reacted, which comments actually drove that reaction, and what the post looked like in the first place.

![Dashboard preview](assets/dashboard-preview.png)

## How it works

The project is three small stages that hand off to each other through plain CSV/JSON files — no database required.

```
extract_comments.py  ──▶  comments.csv, tweet_meta.json, static/tweet_screenshot.png
sentiment_comments.py ──▶  sentiment_results.csv
app.py (dashboard)     ──▶  reads sentiment_results.csv + tweet_meta.json
```

1. **`extract_comments.py`** attaches to a Chrome window you already have open and logged into X/Twitter, opens the tweet you give it, and scrolls through the replies collecting comment text. It also grabs the original post's text, author and a screenshot, so the dashboard can show what the comments are actually about.
2. **`sentiment_comments.py`** runs every collected comment through [`cardiffnlp/twitter-roberta-base-sentiment-latest`](https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest), a RoBERTa model tuned specifically for short, informal social media text, and saves a `positive` / `neutral` / `negative` label with a confidence score for each one.
3. **`app.py`** is a FastAPI app that reads the results and serves the dashboard.

## Dashboard features

- **Source post card** — the original tweet's text, author and a screenshot, so you're never reading reactions out of context.
- **Composition bar + confidence dial** — total comments analyzed, the positive/neutral/negative split, and the model's average confidence across all of them.
- **Trending words** — the terms that came up most often across all the replies.
- **Random sample, and top 10 per sentiment** — rather than one long undifferentiated table, you get a random cross-section of 20 comments plus the 10 highest-confidence comments in each sentiment category, so you can quickly read what a strongly negative reply actually looks like versus a strongly positive one.
- **Full searchable list** — every comment, filterable by sentiment and free-text search.
- **CSV export** and a **light/dark theme toggle**.

## Setup

### 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt
playwright install chromium
```

### 2. Open a logged-in Chrome window with remote debugging on

`extract_comments.py` reuses a real, already-logged-in browser session instead of automating its own login (X/Twitter's login flow is not friendly to automation, and you almost certainly don't want to hand your credentials to a script).

```bash
# Windows
chrome.exe --remote-debugging-port=9222

# macOS
open -a "Google Chrome" --args --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222
```

Log into x.com in that window if you aren't already. You only need to do this once per Chrome profile.

### 3. Collect comments from a tweet

```bash
python extract_comments.py
```

Paste the tweet URL when prompted. It scrolls the replies for a while and stops once no new comments show up for several scrolls in a row, then writes `comments.csv`, `tweet_meta.json` and `static/tweet_screenshot.png`.

### 4. Run sentiment analysis

```bash
python sentiment_comments.py
```

The first run downloads the model (a few hundred MB) and caches it locally; later runs are fast. This writes `sentiment_results.csv`.

### 5. Launch the dashboard

```bash
uvicorn app:app --reload
```

Open **http://127.0.0.1:8000**.

## Project structure

```
twitter-sentiment-analyzer/
├── app.py                  # FastAPI dashboard
├── extract_comments.py     # Scrapes replies + captures the source post
├── sentiment_comments.py   # Runs sentiment classification
├── requirements.txt
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── script.js
└── assets/
    └── dashboard-preview.png
```

## Notes and limitations

- **Selectors will drift.** `extract_comments.py` relies on X/Twitter's internal `data-testid` attributes, which the site changes without notice. If comment collection suddenly returns nothing, that's the first place to check.
- **This scrapes a UI, not an API.** Use it on your own posts or for personal research, be mindful of X/Twitter's Terms of Service, and don't hammer it with rapid repeated runs.
- **English-only model.** `twitter-roberta-base-sentiment-latest` is trained on English tweets; sentiment on other languages will be unreliable.
- **`torch` is a large dependency.** If you only care about the dashboard and already have `sentiment_results.csv` from elsewhere, you can skip installing `transformers`/`torch` and just run `app.py`.

## Tech stack

Python, FastAPI, Playwright, HuggingFace Transformers, Pandas, and a hand-built HTML/CSS/JS dashboard (no frontend framework, no chart library).
