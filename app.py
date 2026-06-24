from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import pandas as pd

app = FastAPI()

templates = Jinja2Templates(
    directory="templates"
)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


@app.get("/")
def home(request: Request):

    total = 0
    positive = 0
    neutral = 0
    negative = 0

    positive_pct = 0
    neutral_pct = 0
    negative_pct = 0

    comments = []

    try:

        df = pd.read_csv("sentiment_results.csv")

        total = len(df)

        positive = len(
            df[df["sentiment"] == "positive"]
        )

        neutral = len(
            df[df["sentiment"] == "neutral"]
        )

        negative = len(
            df[df["sentiment"] == "negative"]
        )

        if total > 0:

            positive_pct = round(
                (positive / total) * 100, 2
            )

            neutral_pct = round(
                (neutral / total) * 100, 2
            )

            negative_pct = round(
                (negative / total) * 100, 2
            )

        comments = df.to_dict(
            orient="records"
        )

    except Exception as e:

        print(e)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "total": total,
            "positive": positive,
            "neutral": neutral,
            "negative": negative,
            "positive_pct": positive_pct,
            "neutral_pct": neutral_pct,
            "negative_pct": negative_pct,
            "comments": comments
        }
    )