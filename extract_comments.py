from playwright.sync_api import sync_playwright
import pandas as pd

tweet_url = input("Paste Tweet URL: ")

comments = set()

with sync_playwright() as p:

    browser = p.chromium.connect_over_cdp(
        "http://127.0.0.1:9222"
    )

    context = browser.contexts[0]

    page = context.new_page()

    page.goto(
        tweet_url,
        wait_until="domcontentloaded",
        timeout=120000
    )

    page.wait_for_timeout(8000)

    print("Collecting comments...")

    last_count = 0
    same_count = 0

    for i in range(40):

        tweets = page.locator(
            '[data-testid="tweetText"]'
        ).all()

        for tweet in tweets:

            try:
                text = tweet.inner_text().strip()

                if len(text) > 10:
                    comments.add(text)

            except:
                pass

        print(
            f"Scroll {i+1} | Comments: {len(comments)}"
        )

        page.mouse.wheel(0, 5000)

        page.wait_for_timeout(2500)

        if len(comments) == last_count:
            same_count += 1
        else:
            same_count = 0

        last_count = len(comments)

        if same_count >= 5:
            break

    df = pd.DataFrame(
        list(comments),
        columns=["comment"]
    )

    df.to_csv(
        "comments.csv",
        index=False
    )

    print(
        f"Saved {len(comments)} comments"
    )