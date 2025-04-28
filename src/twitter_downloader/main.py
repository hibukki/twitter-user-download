import argparse
import json
import os
import sys
from typing import List, Optional

import requests
import requests_cache
from dotenv import load_dotenv
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


TWITTER_API_BASE_URL = "https://api.twitter.com/2"


# Implement API fetching logic
def get_user_id_by_username(username: str, bearer_token: str) -> Optional[str]:
    """Fetches the Twitter User ID for a given username using the Twitter API v2."""
    print(f"Fetching user ID for {username}...")
    url = f"{TWITTER_API_BASE_URL}/users/by/username/{username}"
    headers = {"Authorization": f"Bearer {bearer_token}"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        data = response.json()
        if "data" in data and "id" in data["data"]:
            user_id = data["data"]["id"]
            print(f"Found user ID: {user_id}")
            return user_id
        else:
            print(f"Could not find user ID in API response for username: {username}", file=sys.stderr)
            print(f"API Response: {data}", file=sys.stderr)
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching user ID for {username}: {e}", file=sys.stderr)
        if e.response is not None:
            print(f"Response status: {e.response.status_code}", file=sys.stderr)
            print(f"Response body: {e.response.text}", file=sys.stderr)
        return None


def get_user_tweets(user_id: str, bearer_token: str, limit: Optional[int] = None, max_results_per_page: int = 100) -> List[Tweet]:
    print(f"Fetching tweets for user ID {user_id}...")
    # Placeholder - Replace with actual Twitter API v2 call
    # Endpoint: /2/users/:id/tweets
    # Handle pagination using next_token
    # Requires Bearer Token authentication
    # Consider the 'limit' parameter
    # Parse response into Tweet objects
    dummy_tweets = [
        Tweet(id="1", text="Hello world!", created_at="2023-01-01T12:00:00Z"),
        Tweet(id="2", text="Another tweet", created_at="2023-01-02T12:00:00Z"),
        Tweet(id="3", text="Third tweet!", created_at="2023-01-03T12:00:00Z"),
        # Add more dummy tweets if needed for testing limit
    ]
    if limit is not None:
        print(f"Applying limit: Fetching max {limit} tweets.")
        return dummy_tweets[:limit]
    else:
        print(f"No limit specified, fetching up to {max_results_per_page} tweets (implement pagination later).")
        return dummy_tweets[:max_results_per_page] # Replace with actual API call result


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
    load_dotenv() # Load environment variables from .env file

    parser = argparse.ArgumentParser(description="Download all tweets for a given Twitter user.")
    parser.add_argument("username", help="The Twitter username (without @) to download tweets for.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of tweets to download (optional).") # Added limit argument
    args = parser.parse_args()

    username = args.username
    limit = args.limit # Get limit value

    # --- Configuration & Setup ---
    # Use TWITTER_API_KEY instead of TWITTER_BEARER_TOKEN
    bearer_token = os.environ.get("TWITTER_API_KEY")
    if not bearer_token:
        print("Error: TWITTER_API_KEY environment variable not set.", file=sys.stderr)
        print("Please create a .env file with TWITTER_API_KEY=YOUR_BEARER_TOKEN", file=sys.stderr)
        sys.exit(1)

    # Setup caching (cache API responses in a file)
    # Clear cache for debugging if needed: os.remove('twitter_cache.sqlite')
    requests_cache.install_cache('twitter_cache', backend='sqlite', expire_after=3600) # Cache for 1 hour
    print("Using requests_cache with sqlite backend (twitter_cache.sqlite)")

    # --- Fetching Data ---
    user_id = get_user_id_by_username(username, bearer_token)

    if not user_id:
        # Error message already printed in get_user_id_by_username
        sys.exit(1)

    try:
        # Pass limit to get_user_tweets
        tweets = get_user_tweets(user_id, bearer_token, limit=limit)
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