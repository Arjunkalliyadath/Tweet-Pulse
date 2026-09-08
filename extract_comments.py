"""
extract_comments.py
--------------------
Connects to an already-open Chrome window (launched with remote debugging
enabled) that is logged into X/Twitter, opens the given tweet, scrolls
through the replies and collects the comment text.

It also grabs a screenshot + basic metadata (author, handle, avatar, text)
of the *original* tweet so the dashboard can show what post the comments
belong to.

Before running this, start Chrome with its debugging port open, e.g.:
    Windows : chrome.exe --remote-debugging-port=9222
    macOS   : open -a "Google Chrome" --args --remote-debugging-port=9222
    Linux   : google-chrome --remote-debugging-port=9222
Then log into x.com in that window (only needs to be done once per profile).
"""

import json
import sys

import pandas as pd
from playwright.sync_api import sync_playwright

MAIN_TWEET_SELECTOR = '[data-testid="tweet"]'
TWEET_TEXT_SELECTOR = '[data-testid="tweetText"]'
USER_NAME_SELECTOR = '[data-testid="User-Name"]'
AVATAR_SELECTOR = 'img[src*="profile_images"]'

SCREENSHOT_PATH = "static/tweet_screenshot.png"
META_PATH = "tweet_meta.json"
COMMENTS_PATH = "comments.csv"

MAX_SCROLLS = 40
SAME_COUNT_LIMIT = 5


def capture_source_tweet(page) -> dict:
    """Grab text/author/avatar + a screenshot of the original tweet."""

    meta = {
        "text": None,
        "author": None,
        "handle": None,
        "avatar": None,
        "screenshot": None,
    }

    try:
        main_tweet = page.locator(MAIN_TWEET_SELECTOR).first
        main_tweet.wait_for(timeout=15000)

        try:
            meta["text"] = main_tweet.locator(
                TWEET_TEXT_SELECTOR
            ).first.inner_text().strip()
        except Exception:
            pass

        try:
            name_block = main_tweet.locator(
                USER_NAME_SELECTOR
            ).first.inner_text().strip()
            lines = [l for l in name_block.split("\n") if l.strip()]
            if lines:
                meta["author"] = lines[0]
            handle_line = next(
                (l for l in lines if l.startswith("@")), None
            )
            meta["handle"] = handle_line
        except Exception:
            pass

        try:
            meta["avatar"] = main_tweet.locator(
                AVATAR_SELECTOR
            ).first.get_attribute("src")
        except Exception:
            pass

        try:
            main_tweet.screenshot(path=SCREENSHOT_PATH)
            meta["screenshot"] = SCREENSHOT_PATH
        except Exception as e:
            print(f"Could not capture screenshot: {e}")

    except Exception as e:
        print(f"Could not read the source tweet: {e}")

    return meta


def main():

    tweet_url = input("Paste Tweet URL: ").strip()

    if not tweet_url:
        print("No URL given, exiting.")
        sys.exit(1)

    comments = set()

    with sync_playwright() as p:

        try:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        except Exception:
            print(
                "\nCould not connect to Chrome on port 9222.\n"
                "Make sure Chrome is running with --remote-debugging-port=9222 "
                "and that you're logged into X/Twitter in it.\n"
            )
            sys.exit(1)

        if not browser.contexts:
            print("No open browser tabs/context found. Open x.com in that Chrome window first.")
            sys.exit(1)

        context = browser.contexts[0]
        page = context.new_page()

        page.goto(tweet_url, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(8000)

        print("Reading source post...")
        tweet_meta = capture_source_tweet(page)
        tweet_meta["url"] = tweet_url

        main_text_normalized = (tweet_meta.get("text") or "").strip()

        print("Collecting comments...")

        last_count = 0
        same_count = 0

        for i in range(MAX_SCROLLS):

            tweets = page.locator(TWEET_TEXT_SELECTOR).all()

            for tweet in tweets:
                try:
                    text = tweet.inner_text().strip()

                    # Skip the original post itself so it isn't
                    # double-counted as a "comment".
                    if len(text) > 10 and text != main_text_normalized:
                        comments.add(text)

                except Exception:
                    pass

            print(f"Scroll {i + 1} | Comments: {len(comments)}")

            page.mouse.wheel(0, 5000)
            page.wait_for_timeout(2500)

            if len(comments) == last_count:
                same_count += 1
            else:
                same_count = 0

            last_count = len(comments)

            if same_count >= SAME_COUNT_LIMIT:
                break

        df = pd.DataFrame(list(comments), columns=["comment"])
        df.to_csv(COMMENTS_PATH, index=False)

        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump(tweet_meta, f, ensure_ascii=False, indent=2)

        print(f"\nSaved {len(comments)} comments to {COMMENTS_PATH}")
        print(f"Saved source post info to {META_PATH}")
        if tweet_meta.get("screenshot"):
            print(f"Saved post screenshot to {SCREENSHOT_PATH}")


if __name__ == "__main__":
    main()
