"""
sentiment_comments.py
----------------------
Runs every comment in comments.csv through the CardiffNLP Twitter-RoBERTa
sentiment model and writes the results to sentiment_results.csv, which is
what app.py reads for the dashboard.

NOTE: the model's pipeline returns labels capitalised as "Positive",
"Neutral" or "Negative". We lower-case them before saving so they line up
with the rest of the app (the dashboard filters/groups on lower-case
sentiment strings).
"""

import sys

import pandas as pd
from transformers import pipeline

INPUT_PATH = "comments.csv"
OUTPUT_PATH = "sentiment_results.csv"
MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"


def main():

    try:
        df = pd.read_csv(INPUT_PATH)
    except FileNotFoundError:
        print(
            f"'{INPUT_PATH}' not found. Run extract_comments.py first "
            "to collect comments from a tweet."
        )
        sys.exit(1)

    df["comment"] = df["comment"].astype(str).str.strip()
    df = df[df["comment"].str.len() > 0].reset_index(drop=True)

    if df.empty:
        print("No comments to analyze.")
        sys.exit(1)

    print("Loading model...")
    classifier = pipeline("sentiment-analysis", model=MODEL_NAME)

    results = []
    total = len(df)

    for i, comment in enumerate(df["comment"]):

        try:
            prediction = classifier(comment[:512])[0]

            results.append({
                "comment": comment,
                "sentiment": prediction["label"].lower(),
                "score": round(prediction["score"], 4),
            })

        except Exception:
            results.append({
                "comment": comment,
                "sentiment": "unknown",
                "score": 0,
            })

        print(f"{i + 1}/{total} processed")

    result_df = pd.DataFrame(results)
    result_df.to_csv(OUTPUT_PATH, index=False)

    counts = result_df["sentiment"].value_counts().to_dict()
    print(f"\nSaved {OUTPUT_PATH}")
    print(f"Breakdown: {counts}")


if __name__ == "__main__":
    main()
