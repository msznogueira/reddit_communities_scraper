import os
import json
from pathlib import Path

import praw
from dotenv import load_dotenv


# --------------------------------------------------
# Configuration
# --------------------------------------------------

load_dotenv()

COMMUNITY = "shrooms"
OUTPUT_FILE = Path(f"{COMMUNITY}.json")
LIMIT = 1000

SORT_CONFIGS = [
    ("top", "all"),
    ("top", "year"),
    ("top", "month"),
    ("top", "week"),
    ("controversial", "all"),
    ("controversial", "year"),
    ("controversial", "month"),
    ("hot", None),
    ("new", None),
    ("rising", None),
]


# --------------------------------------------------
# Reddit
# --------------------------------------------------

def create_reddit_client():
    return praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ["REDDIT_USER_AGENT"],
    )


def fetch_posts(subreddit, sort, time_filter=None, limit=1000):
    method = getattr(subreddit, sort)

    kwargs = {"limit": limit}

    if time_filter is not None:
        kwargs["time_filter"] = time_filter

    return method(**kwargs)


# --------------------------------------------------
# Data processing
# --------------------------------------------------

def submission_to_dict(submission):
    return {
        "id": submission.id,
        "title": submission.title,
        "body": submission.selftext,
        "created_utc": submission.created_utc,
        "author": submission.author.name if submission.author else None,
        "num_comments": submission.num_comments,
        "score": submission.score,
        "upvote_ratio": submission.upvote_ratio,
        "sources": [],
    }


def load_posts(filename):
    if not filename.exists():
        return {}

    with open(filename, "r", encoding="utf8") as f:
        data = json.load(f)

    return {post["id"]: post for post in data}


def save_posts(posts, filename):
    temp_file = filename.with_suffix(".tmp")

    with open(temp_file, "w", encoding="utf8") as f:
        json.dump(
            list(posts.values()),
            f,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(temp_file, filename)


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    reddit = create_reddit_client()
    subreddit = reddit.subreddit(COMMUNITY)

    posts = load_posts(OUTPUT_FILE)

    print(f"Loaded {len(posts)} existing submissions.")

    try:
        for sort, time_filter in SORT_CONFIGS:
            source = (
                f"{sort}:{time_filter}"
                if time_filter is not None
                else sort
            )

            print(f"\nFetching {source}...")

            fetched = 0
            added = 0

            for submission in fetch_posts(
                subreddit,
                sort=sort,
                time_filter=time_filter,
                limit=LIMIT,
            ):
                fetched += 1

                if submission.id not in posts:
                    posts[submission.id] = submission_to_dict(submission)
                    added += 1

                # Track which listings returned this submission.
                sources = posts[submission.id].setdefault("sources", [])

                if source not in sources:
                    sources.append(source)

            save_posts(posts, OUTPUT_FILE)

            print(f"Fetched: {fetched}")
            print(f"New unique posts: {added}")
            print(f"Total unique posts: {len(posts)}")

    finally:
        # Preserve completed work if a later request fails.
        save_posts(posts, OUTPUT_FILE)

    print(f"\nFinished! Saved {len(posts)} posts to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()