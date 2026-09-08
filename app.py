import json
import os
import re
from collections import Counter
from datetime import datetime

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Twitter / X Sentiment Analyzer")

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

RESULTS_CSV = "sentiment_results.csv"
TWEET_META_JSON = "tweet_meta.json"

RANDOM_SAMPLE_SIZE = 20
TOP_N_PER_SENTIMENT = 10
TRENDING_WORD_COUNT = 15

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "be",
    "been", "being", "to", "of", "in", "on", "for", "with", "at", "by",
    "from", "up", "about", "into", "over", "after", "this", "that", "these",
    "those", "it", "its", "i", "you", "he", "she", "we", "they", "them",
    "my", "your", "his", "her", "our", "their", "me", "him", "us", "am",
    "just", "so", "not", "no", "yes", "will", "would", "can", "could",
    "should", "do", "does", "did", "have", "has", "had", "as", "if", "then",
    "than", "there", "here", "what", "when", "where", "who", "why", "how",
    "all", "any", "very", "too", "also", "http", "https", "amp", "rt",
}


def build_trending_words(comments: list[str], limit: int = TRENDING_WORD_COUNT):
    """Very lightweight keyword frequency, excluding stopwords/mentions/links."""

    counter = Counter()

    for comment in comments:
        words = re.findall(r"[A-Za-z#][A-Za-z0-9'_-]{2,}", comment.lower())
        for word in words:
            if word.startswith("http"):
                continue
            if word in STOPWORDS:
                continue
            counter[word] += 1

    return counter.most_common(limit)


def load_tweet_meta():
    if not os.path.exists(TWEET_META_JSON):
        return None

    try:
        with open(TWEET_META_JSON, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        return None

    # Make the screenshot path web-servable (it's stored under static/).
    screenshot = meta.get("screenshot")
    if screenshot and os.path.exists(screenshot):
        meta["screenshot_url"] = "/" + screenshot.replace("\\", "/")
    else:
        meta["screenshot_url"] = None

    if not any(meta.get(k) for k in ("text", "author", "screenshot_url")):
        return None

    return meta


@app.get("/")
def home(request: Request):

    total = 0
    positive = neutral = negative = 0
    positive_pct = neutral_pct = negative_pct = 0.0
    avg_confidence = 0.0

    random_sample = []
    top_positive = []
    top_neutral = []
    top_negative = []
    trending_words = []
    comments_json = "[]"

    try:
        df = pd.read_csv(RESULTS_CSV)
        df["comment"] = df["comment"].astype(str).str.strip()
        df["sentiment"] = df["sentiment"].astype(str).str.strip().str.lower()
        df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0)
        df = df[df["comment"].str.len() > 0].reset_index(drop=True)

        total = len(df)

        if total > 0:
            positive = int((df["sentiment"] == "positive").sum())
            neutral = int((df["sentiment"] == "neutral").sum())
            negative = int((df["sentiment"] == "negative").sum())

            positive_pct = round((positive / total) * 100, 2)
            neutral_pct = round((neutral / total) * 100, 2)
            negative_pct = round((negative / total) * 100, 2)

            avg_confidence = round(df["score"].mean() * 100, 2)

            sample_n = min(RANDOM_SAMPLE_SIZE, total)
            random_sample = df.sample(n=sample_n).to_dict(orient="records")

            top_positive = (
                df[df["sentiment"] == "positive"]
                .sort_values("score", ascending=False)
                .head(TOP_N_PER_SENTIMENT)
                .to_dict(orient="records")
            )
            top_neutral = (
                df[df["sentiment"] == "neutral"]
                .sort_values("score", ascending=False)
                .head(TOP_N_PER_SENTIMENT)
                .to_dict(orient="records")
            )
            top_negative = (
                df[df["sentiment"] == "negative"]
                .sort_values("score", ascending=False)
                .head(TOP_N_PER_SENTIMENT)
                .to_dict(orient="records")
            )

            trending_words = build_trending_words(df["comment"].tolist())

            comments_json = json.dumps(
                df[["comment", "sentiment", "score"]].to_dict(orient="records")
            )

    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Error loading results: {e}")

    tweet_meta = load_tweet_meta()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "has_data": total > 0,
            "total": total,
            "positive": positive,
            "neutral": neutral,
            "negative": negative,
            "positive_pct": positive_pct,
            "neutral_pct": neutral_pct,
            "negative_pct": negative_pct,
            "avg_confidence": avg_confidence,
            "random_sample": random_sample,
            "top_positive": top_positive,
            "top_neutral": top_neutral,
            "top_negative": top_negative,
            "trending_words": trending_words,
            "comments_json": comments_json,
            "tweet_meta": tweet_meta,
            "generated_at": datetime.now().strftime("%b %d, %Y  %I:%M %p"),
        },
    )


@app.get("/download-csv")
def download_csv():
    if not os.path.exists(RESULTS_CSV):
        return JSONResponse(
            status_code=404,
            content={"error": "No sentiment_results.csv found yet."},
        )
    return FileResponse(
        RESULTS_CSV,
        media_type="text/csv",
        filename="sentiment_results.csv",
    )
