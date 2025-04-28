import argparse
import json
import os
import sys
from typing import List, Optional

import requests
import requests_cache
from pydantic import BaseModel, Field, ValidationError


# TODO: Define Pydantic models for User and Tweet
class Tweet(BaseModel):
    id: str
    text: str
    created_at: str # Or use datetime? Consider timezone


class User(BaseModel):
    id: str
    name: str
    username: str


# TODO: Implement API fetching logic
def get_user_id_by_username(username: str, bearer_token: str) -> Optional[str]:
    print(f"Fetching user ID for {username}...")
    # Placeholder - Replace with actual Twitter API v2 call
    # Endpoint: /2/users/by/username/:username
    # Requires Bearer Token authentication
    return "dummy_user_id" # Replace with actual API call result


def get_user_tweets(user_id: str, bearer_token: str, max_results: int = 100) -> List[Tweet]:
    print(f"Fetching tweets for user ID {user_id}...")
    # Placeholder - Replace with actual Twitter API v2 call
    # Endpoint: /2/users/:id/tweets
    # Handle pagination using next_token
    # Requires Bearer Token authentication
    # Parse response into Tweet objects
    return [
        Tweet(id="1", text="Hello world!", created_at="2023-01-01T12:00:00Z"),
        Tweet(id="2", text="Another tweet", created_at="2023-01-02T12:00:00Z"),
    ] # Replace with actual API call result


def save_tweets_to_json(tweets: List[Tweet], username: str):
    filename = f"{username}_tweets.json"
    print(f"Saving {len(tweets)} tweets to {filename}...")
    # Convert Pydantic models to dicts for JSON serialization
    tweets_data = [tweet.model_dump() for tweet in tweets]
    try:
        with open(filename, "w") as f:
            json.dump(tweets_data, f, indent=2)
        print(f"Successfully saved tweets to {filename}")
    except IOError as e:
        print(f"Error saving tweets to {filename}: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Download all tweets for a given Twitter user.")
    parser.add_argument("username", help="The Twitter username (without @) to download tweets for.")
    # parser.add_argument("--max-tweets", type=int, default=None, help="Maximum number of tweets to download (optional).") # Maybe add later
    args = parser.parse_args()

    username = args.username

    # --- Configuration & Setup ---
    bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
    if not bearer_token:
        print("Error: TWITTER_BEARER_TOKEN environment variable not set.", file=sys.stderr)
        sys.exit(1)

    # Setup caching (cache API responses in a file)
    requests_cache.install_cache('twitter_cache', backend='sqlite', expire_after=3600) # Cache for 1 hour
    print("Using requests_cache with sqlite backend (twitter_cache.sqlite)")

    # --- Fetching Data ---
    user_id = get_user_id_by_username(username, bearer_token)

    if not user_id:
        print(f"Could not find user ID for username: {username}", file=sys.stderr)
        sys.exit(1)

    try:
        tweets = get_user_tweets(user_id, bearer_token) # TODO: Add max_tweets handling if needed
    except requests.exceptions.RequestException as e:
        print(f"Error fetching tweets: {e}", file=sys.stderr)
        # Print detailed error if available (e.g., response content)
        if e.response is not None:
             print(f"Response status: {e.response.status_code}", file=sys.stderr)
             print(f"Response body: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except ValidationError as e:
         print(f"Data validation error: {e}", file=sys.stderr)
         sys.exit(1)


    # --- Saving Data ---
    if tweets:
        save_tweets_to_json(tweets, username)
    else:
        print("No tweets found or failed to fetch tweets.")


if __name__ == "__main__":
    main() 