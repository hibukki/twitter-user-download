# Twitter User Tweet Downloader

Downloads all tweets for a given Twitter user and saves them to a JSON file. Uses caching to minimize API calls.

## Installation (macOS)

### Install uv

[https://github.com/astral-sh/uv?tab=readme-ov-file#installation](https://github.com/astral-sh/uv?tab=readme-ov-file#installation)

### Get Twitter developer api key

Sign up as a developer here:

https://developer.twitter.com/en/portal/petition/essential/basic-info

You want a Bearer Token, put it in `.env`

```.env
TWITTER_API_KEY=my_bearer_token
```

## Run

```bash
uv run python src/twitter_downloader/main.py <username>
```

Example:

```bash
uv run python src/twitter_downloader/main.py YonatanCale
```

You can also limit the amount of tweets with `--limit` (for debug, don't overwhelm the Twitter API)

Example:

```bash
uv run python src/twitter_downloader/main.py YonatanCale --limit 10
```
