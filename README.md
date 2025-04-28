# Twitter User Tweet Downloader

Downloads all tweets for a given Twitter user and saves them to a JSON file. Uses caching to minimize API calls.

## Installation (macOS)

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd twitter_user_download
    ```
2.  **Install uv (if you don't have it):**
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
    ```
3.  **Install dependencies:**
    ```bash
    uv sync
    ```

## Configuration

This tool requires a Twitter API v2 Bearer Token.

1.  Obtain a Bearer Token from the Twitter Developer Portal.
2.  Set it as an environment variable:
    ```bash
    export TWITTER_BEARER_TOKEN="YOUR_BEARER_TOKEN_HERE"
    ```
    Alternatively, you can add this line to your shell profile (e.g., `~/.zshrc` or `~/.bash_profile`) for persistence.

## Usage

Run the script with the target Twitter username:

```bash
uv run python src/twitter_downloader/main.py <username>
```

Example:

```bash
uv run python src/twitter_downloader/main.py YonatanCale
```

This will create a file named `<username>_tweets.json` (e.g., `YonatanCale_tweets.json`) in the current directory containing the downloaded tweets. API responses are cached in `twitter_cache.sqlite` for 1 hour.
