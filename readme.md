liked-tweets-scraper
====================

Download your liked tweets.

```json
[
    {
        "id": 1810309078289137700,
        "user_id": 1326389646,
        "media_array": [
            "https://pbs.twimg.com/media/GR-Cgr0XMAAOGCz.jpg"
        ],
        "tweet": "https://twitter.com/xruiztru/status/1810309078289137687",
        "name": "Xavi Ruiz",
        "created_at": "2024-07-08T13:44:52+00:00",
        "full_text": "On July 8th each year around 11:15 UTC, roughly 99.16% of the global population is experiencing daylight. https://t.co/Zir7srbxkE",
        "is_quote_status": 0,
        "favorite_count": 3688,
        "favorited": 1,
        "retweeted": 0,
        "lang": "en",
        "possibly_sensitive": 0,
        "retweeted_status": null,
        "quoted_status": null,
        "thumbnail": "https://pbs.twimg.com/media/GR-Cgr0XMAAOGCz.jpg"
    },
    ...
]
```

Motivation
----------

In April 2023, Twitter[^1] deprecated their v1 API access plans, which [started
failing around July][twitter-v1-api-shutdown]. [Retrieving your liked
tweets][likes-lookup-docs] using the new X API is now [prohibitively expensive
or impractical][twitter-api-pricing] for individuals.

But there's an alternative: use the API that the official frontend itself invokes.
This program works by using browser automation: it opens your browser at your
liked tweets tab page and scrolls down, progressively loading your liked
tweets, saving all HTTP response bodies made to the liked tweets endpoint.

[twitter-v1-api-shutdown]: https://github.com/dogsheep/twitter-to-sqlite/issues/73
[likes-lookup-docs]: https://docs.x.com/x-api/posts/likes/quickstart/likes-lookup
[twitter-api-pricing]: https://developer.x.com/en/portal/products/pro

[^1]: Now officially known as X (but does anyone call it X?)

Prerequisites
-------------

The program requires authentication cookies for x.com to be provided in this
format:

```json
[
    {
        "name": "auth_token",
        "value": "eu2h97gtc5ru8smjqkrh22g2g8me2okz6ciikbzk",
        "path": "/",
        "domain": ".x.com",
        "secure": true,
        "expiry": 1747587658,
        "sameSite": "None"
    },
    ...
]
```

The easiest way to get these is to log in using your browser and extract them
from wherever your browser stores cookies. Below is how you can extract them
from Firefox's cookies SQLite database into the above JSON format:

```sh
# The location of your Firefox cookies database in your system may vary.
sqlite3 "~/snap/firefox/common/.mozilla/firefox/t2r85i5x.default/cookies.sqlite" \
"SELECT json_group_array(
    json_object(
        'name', name,
        'value', value,
        'path', path,
        'domain', host,
        'secure', CASE WHEN isSecure = 1 THEN 1 ELSE 0 END,
        'expiry', expiry,
        'sameSite', CASE sameSite WHEN 0 THEN 'None' WHEN 1 THEN 'Lax' WHEN 2 THEN 'Strict' ELSE NULL END
    )
) AS cookies
FROM moz_cookies WHERE host LIKE '%x.com';" | jq --indent 4 'map(.secure = (.secure | if . == 1 then true else false end))' > x.com-cookies.json
```

Usage
-----

Provide your Twitter username and the cookies file. The example usage below
assumes you have [`uv`][uv].

```sh
uv run main.py --target_href '/xruiztru/status/1810309078289137687' x.com-cookies.json 'David_835'
```

The stopping condition may be either seeing a given tweet provided with the
`--target_href` option, or scrolling the viewport a maximum number of times.
Run `uv run main.py --help` for detailed usage information.

The above will save all HTTP response bodies made to the liked tweets endpoint
under a `response_bodies` directory. The payloads there contain all of the
downloaded tweets with their associated metadata, but you'll most likely want to
postprocess and concatenate them into a more digestible format. We provide a
handy shell script leveraging a [`jq`][jq] transform, which will output them in
the format showcased in the beginning of this readme document:

```sh
./process_jsons.sh response_bodies
```

You can (almost surely) safely ignore any warnings, since they (most likely)
arise from failed API calls or tweets that have been removed.

[uv]: https://docs.astral.sh/uv/
[jq]: https://jqlang.github.io/jq/

Caveats
-------

- Occasionally the scraper will fail if Twitter enforces throttling or the
  program scrolls too fast. But I've found that watching the scraper work in
  headful mode whilst leaving the computer idle with the scraper doing its thing
  is most reliable, downloading ~2000 tweets in just a couple of minutes.
