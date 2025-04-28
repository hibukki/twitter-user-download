import argparse
import json
import os
import sys
import time # Added import
from typing import List, Optional, Dict, Iterator, Any
from datetime import datetime

import requests
import requests_cache
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError


# TODO: Define Pydantic models for User and Tweet
class PublicMetrics(BaseModel):
    retweet_count: int
    reply_count: int
    like_count: int
    quote_count: int
    impression_count: int

class Tweet(BaseModel):
    id: str
    text: str
    created_at: datetime # Use datetime object
    public_metrics: Optional[PublicMetrics] = None # Add public metrics


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


def get_user_tweets(user_id: str, bearer_token: str, limit: Optional[int] = None, max_results_per_page: int = 100) -> Iterator[List[Tweet]]:
    """Fetches tweets for a given user ID, yielding pages of tweets. Handles pagination, rate limits, and optional limit."""
    print(f"Fetching tweets for user ID {user_id}...")
    tweets_fetched_count = 0 # Track total tweets fetched across pages
    next_token: Optional[str] = None
    url = f"{TWITTER_API_BASE_URL}/users/{user_id}/tweets"
    headers = {"Authorization": f"Bearer {bearer_token}"}

    results_per_page = max_results_per_page
    if limit is not None and limit < results_per_page:
         # If limit is smaller than default page size, request only that many initially.
         # Subsequent requests within the loop will adjust based on remaining limit.
         results_per_page = limit

    while True:
        # Explicitly type params for linter
        params: Dict[str, Any] = {
            "max_results": results_per_page,
            "tweet.fields": "created_at,public_metrics"
        }
        if next_token:
            params["pagination_token"] = next_token

        print(f"Fetching page... (max_results={results_per_page}, next_token={next_token})")

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            current_page_tweets: List[Tweet] = []
            if "data" in data:
                for tweet_data in data["data"]:
                    try:
                        tweet = Tweet(**tweet_data)
                        current_page_tweets.append(tweet)
                        tweets_fetched_count += 1
                        if limit is not None and tweets_fetched_count >= limit:
                            # Stop fetching immediately if limit is reached mid-page
                            break # Break inner loop
                    except ValidationError as e:
                        print(f"Skipping tweet due to validation error: {e}", file=sys.stderr)
                        print(f"Problematic tweet data: {tweet_data}", file=sys.stderr)

            if current_page_tweets:
                yield current_page_tweets # Yield the fetched page

            # Check if limit was reached after processing the page
            if limit is not None and tweets_fetched_count >= limit:
                print(f"Reached limit of {limit} tweets.")
                break # Break outer loop (stop fetching pages)

            if "meta" in data and "next_token" in data["meta"]:
                next_token = data["meta"]["next_token"]
                # Adjust results per page for the next request if near the limit
                if limit is not None:
                    remaining_limit = limit - tweets_fetched_count
                    if remaining_limit <= 0:
                         # Should not happen if limit check above works, but safety break
                         print("Limit reached exactly.")
                         break
                    results_per_page = min(remaining_limit, max_results_per_page)
            else:
                print("No more pages found.")
                break # No more pages

        except requests.exceptions.RequestException as e:
            print(f"Error fetching page of tweets: {e}", file=sys.stderr)
            if e.response is not None:
                print(f"Response status: {e.response.status_code}", file=sys.stderr)
                print(f"Response body: {e.response.text}", file=sys.stderr)

                # --- Rate Limit Handling (429) ---
                if e.response.status_code == 429:
                    retry_after_header = e.response.headers.get("Retry-After")
                    wait_time = 60 # Default wait time in seconds
                    if retry_after_header and retry_after_header.isdigit():
                        wait_time = int(retry_after_header)
                        print(f"Rate limit hit. Waiting for {wait_time} seconds (from Retry-After header)...", file=sys.stderr)
                    else:
                        # Check for x-rate-limit-reset header (Unix timestamp)
                        reset_time_header = e.response.headers.get("x-rate-limit-reset")
                        if reset_time_header and reset_time_header.isdigit():
                            reset_timestamp = int(reset_time_header)
                            current_timestamp = int(time.time())
                            wait_time = max(0, reset_timestamp - current_timestamp) + 1 # Add 1 sec buffer
                            print(f"Rate limit hit. Waiting until reset time: {datetime.fromtimestamp(reset_timestamp)} ({wait_time} seconds)...", file=sys.stderr)
                        else:
                            print(f"Rate limit hit. No specific wait time found in headers. Waiting for default {wait_time} seconds...", file=sys.stderr)

                    time.sleep(wait_time)
                    print("Retrying request...")
                    continue # Retry the same request
                # --- End Rate Limit Handling ---

            # For other request errors, break the loop for now
            print("Aborting due to non-rate-limit request error.", file=sys.stderr)
            break
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response: {e}", file=sys.stderr)
            print(f"Response text: {response.text}", file=sys.stderr)
            break

    print(f"Finished fetching generator. Total tweets yielded: {tweets_fetched_count}")
    # Removed final return, as it's a generator


# Function to append tweets, handling duplicates and file I/O
def append_tweets_to_json(new_tweets: List[Tweet], filename: str):
    existing_tweets: List[Dict[str, Any]] = []
    existing_ids = set()

    try:
        with open(filename, "r") as f:
            try:
                existing_tweets = json.load(f)
                if not isinstance(existing_tweets, list):
                    print(f"Warning: Existing file {filename} does not contain a JSON list. Overwriting.", file=sys.stderr)
                    existing_tweets = []
                else:
                    # Ensure items are dicts and have 'id'
                    valid_existing = []
                    for item in existing_tweets:
                        if isinstance(item, dict) and "id" in item:
                            existing_ids.add(item["id"])
                            valid_existing.append(item)
                        else:
                            print(f"Warning: Skipping invalid item in {filename}: {item}", file=sys.stderr)
                    existing_tweets = valid_existing # Keep only valid items
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from {filename}. Starting fresh.", file=sys.stderr)
                existing_tweets = [] # Start fresh if file is corrupted
    except FileNotFoundError:
        print(f"File {filename} not found. Creating new file.")
        existing_tweets = [] # File doesn't exist yet
    except IOError as e:
        print(f"Error reading file {filename}: {e}. Aborting append.", file=sys.stderr)
        return # Don't proceed if we can't read the file

    # Filter new tweets to only include those not already present by ID
    truly_new_tweets = [tweet for tweet in new_tweets if tweet.id not in existing_ids]
    appended_count = len(truly_new_tweets)

    if appended_count > 0:
        print(f"Appending {appended_count} new tweets to {filename}...")
        # Convert new Pydantic models to JSON-serializable dicts
        new_tweets_data = [tweet.model_dump(mode='json') for tweet in truly_new_tweets]
        updated_tweets = existing_tweets + new_tweets_data

        try:
            with open(filename, "w") as f:
                json.dump(updated_tweets, f, indent=2)
            print(f"Successfully appended tweets. Total tweets in file now: {len(updated_tweets)}")
        except IOError as e:
            print(f"Error writing updates to {filename}: {e}", file=sys.stderr)
    else:
        print(f"No new tweets to append to {filename} (duplicates found or empty page).")


def main():
    load_dotenv() # Load environment variables from .env file

    parser = argparse.ArgumentParser(description="Download all tweets for a given Twitter user.")
    parser.add_argument("username", help="The Twitter username (without @) to download tweets for.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of tweets to download (optional).")
    args = parser.parse_args()

    username = args.username
    limit = args.limit

    # --- Configuration & Setup ---
    bearer_token = os.environ.get("TWITTER_API_KEY")
    if not bearer_token:
        print("Error: TWITTER_API_KEY environment variable not set.", file=sys.stderr)
        print("Please create a .env file with TWITTER_API_KEY=YOUR_BEARER_TOKEN", file=sys.stderr)
        sys.exit(1)

    # Setup caching, ignoring pagination_token for better cache hits on timeline requests
    print("Setting up requests_cache, ignoring 'pagination_token' parameter...")
    requests_cache.install_cache(
        'twitter_cache',
        backend='sqlite',
        expire_after=3600, # Cache for 1 hour
        ignored_parameters=['pagination_token'] # Ignore this param for caching
    )
    print("Using requests_cache with sqlite backend (twitter_cache.sqlite)")

    # --- Fetching Data ----
    user_id = get_user_id_by_username(username, bearer_token)

    if not user_id:
        sys.exit(1)

    output_filename = f"{username}_tweets.json"
    total_tweets_processed = 0

    try:
        # Iterate through pages yielded by the generator
        print("Starting tweet fetching...")
        for tweet_page in get_user_tweets(user_id, bearer_token, limit=limit):
            print(f"Received page with {len(tweet_page)} tweets.")
            append_tweets_to_json(tweet_page, output_filename)
            total_tweets_processed += len(tweet_page)
            # Optional: Add a small delay between page appends if needed?
            # time.sleep(0.1)

        print(f"Finished processing all pages. Total tweets processed in this run: {total_tweets_processed}")

    except Exception as e:
         # Catch potential errors during iteration/saving not caught within get_user_tweets
         # (Requests errors and JSON errors inside get_user_tweets are already handled there)
         print(f"An unexpected error occurred during tweet processing: {e}", file=sys.stderr)
         # Consider printing traceback for debugging
         import traceback
         traceback.print_exc()
         sys.exit(1)

    # --- Saving Data --- (Now handled incrementally)
    # No final save needed here anymore
    # if tweets: # 'tweets' list no longer exists here
    #     save_tweets_to_json(tweets, username)
    # else:
    #     print("No tweets found or failed to fetch tweets.")


if __name__ == "__main__":
    main() 