import pandas as pd
from transformers import pipeline

print("Loading model...")

classifier = pipeline(
    "sentiment-analysis",
    model="cardiffnlp/twitter-roberta-base-sentiment-latest"
)

df = pd.read_csv("comments.csv")

results = []

total = len(df)

for i, comment in enumerate(df["comment"]):

    try:

        prediction = classifier(
            comment[:512]
        )[0]

        results.append({
            "comment": comment,
            "sentiment": prediction["label"],
            "score": round(
                prediction["score"],
                4
            )
        })

        print(
            f"{i+1}/{total} processed"
        )

    except:

        results.append({
            "comment": comment,
            "sentiment": "UNKNOWN",
            "score": 0
        })

result_df = pd.DataFrame(results)

result_df.to_csv(
    "sentiment_results.csv",
    index=False
)

print("\nSaved sentiment_results.csv")