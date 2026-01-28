#!/usr/bin/env python3
import sys
import json
from datetime import datetime


def parse_twitter_date(date_str):
    """Convert Twitter's legacy created_at string into ISO8601."""
    try:
        dt = datetime.strptime(date_str, "%a %b %d %H:%M:%S +0000 %Y")
        return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    except Exception:
        return None


def extract_media(media_list):
    """Extract media URLs from media entities (optional)."""
    urls = []
    if not media_list:
        return urls
    for m in media_list:
        t = m.get("type")
        if t in ("photo", "video", "animated_gif"):
            if t in ("video", "animated_gif"):
                urls.append(
                    m.get("media_url_https")
                    or m.get("video_info", {}).get("thumbnail_url")
                )
            else:
                urls.append(m.get("media_url_https"))
    return [u for u in urls if u]


def transform_tweet(t):
    """Transform one tweet result into desired structure, aborting if required keys are missing."""

    type_name = t["__typename"]
    if type_name == "TweetWithVisibilityResults":
        t = t["tweet"]
    elif type_name == "Tweet":
        t = t
    else:
        raise ValueError(f"Unrecognized object {type_name}")

    # Required fields (will raise KeyError if missing).
    rest_id = str(t["rest_id"])
    core = t["core"]
    user = core["user_results"]["result"]
    user_name = user["core"]["name"]
    user_screen_name = user["core"]["screen_name"]
    legacy = t["legacy"]

    out = {
        "id": rest_id,
        "user_id": str(user["rest_id"]),
        "media_array": extract_media(legacy.get("extended_entities", {}).get("media")),
        "tweet": f"https://twitter.com/{user_screen_name}/status/{rest_id}",
        "name": user_name,
        "created_at": parse_twitter_date(legacy["created_at"]),
        "full_text": legacy["full_text"],
        "is_quote_status": 1 if legacy["is_quote_status"] else 0,
        "favorite_count": legacy["favorite_count"],
        "favorited": 1 if legacy["favorited"] else 0,
        "retweeted": 1 if legacy["retweeted"] else 0,
        "lang": legacy["lang"],
        "possibly_sensitive": 1 if legacy.get("possibly_sensitive") else 0,
        "retweeted_status": (
            legacy.get("retweeted_status_result", {}).get("result", {}).get("rest_id")
        ),
        "quoted_status": (
            t.get("quoted_status_result", {}).get("result", {}).get("rest_id")
        ),
        "thumbnail": None,
    }

    # Optional thumbnail (first media only)
    media0 = legacy.get("extended_entities", {}).get("media", [{}])
    if media0 and media0[0]:
        m = media0[0]
        if m.get("type") in ("video", "animated_gif"):
            out["thumbnail"] = m.get("media_url_https") or m.get("video_info", {}).get(
                "thumbnail_url"
            )
        else:
            out["thumbnail"] = m.get("media_url_https")

    return out


def main():
    raw = json.load(sys.stdin)

    entries = raw["data"]["user"]["result"]["timeline"]["timeline"]["instructions"][0][
        "entries"
    ]

    # i = 0
    results = []
    for e in entries:
        # print(i)
        if e["content"]["entryType"] != "TimelineTimelineItem":
            # This skips over e.g. the `TimelineTimelineCursor` items, which are
            # usually the last two entries.
            continue
        tweet = e["content"]["itemContent"]["tweet_results"]["result"]
        results.append(transform_tweet(tweet))
        # i += 1

    json.dump(results, sys.stdout, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
