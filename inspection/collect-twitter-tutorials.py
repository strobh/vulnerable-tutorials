# Example code from:
# https://github.com/twitterdev/Twitter-API-v2-sample-code/blob/main/Full-Archive-Search/full-archive-search.py

# Library:
# https://github.com/twitterdev/search-tweets-python

import requests
import os
import json


bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")

search_url = "https://api.twitter.com/2/tweets/search/all"

# Query: https://developer.twitter.com/en/docs/twitter-api/tweets/search/integrate/build-a-query
# Tweet object: https://developer.twitter.com/en/docs/twitter-api/data-dictionary/object-model/tweet
query_params = {
    'query': '-is:retweet (has:media OR has:links) lang:en #php #tutorial',
    'tweet.fields': 'public_metrics,entities,lang'}


def bearer_oauth(r):
    """
    Method required by bearer token authentication.
    """

    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2FullArchiveSearchPython"
    return r


def connect_to_endpoint(url, params):
    response = requests.request("GET", search_url, auth=bearer_oauth, params=params)
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    return response.json()


def main():
    json_response = connect_to_endpoint(search_url, query_params)
    print(json.dumps(json_response, indent=4, sort_keys=True))


if __name__ == "__main__":
    main()
