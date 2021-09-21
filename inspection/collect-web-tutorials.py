import datetime
import itertools
import os
import requests
import pprint
import yaml

from pathlib import Path

import models


search_engine_id = os.environ.get("GOOGLE_SEARCH_ENGINE_ID")
api_key = os.environ.get("GOOGLE_API_KEY")

queries = [
    'php database tutorial',
    'php database example',
    'php database how to',
    'php database learn',
    'php database course',
    'php database for beginners',
    'php database for dummies',
    'php login tutorial',
    'php login example',
    'php login how to',
    'php login learn',
    'php login course',
    'php login for beginners',
    'php login for dummies',
    'php authentication tutorial',
    'php authentication example',
    'php authentication how to',
    'php authentication learn',
    'php authentication course',
    'php authentication for beginners',
    'php authentication for dummies',
    'php authentication system tutorial',
    'php authentication system example',
    'php authentication system how to',
    'php authentication system learn',
    'php authentication system course',
    'php authentication system for beginners',
    'php authentication system for dummies']

result_count = 30

data_dir = os.path.join('data', 'search-results', 'google')
Path(data_dir).mkdir(parents=True, exist_ok=True)

for q in queries:
    q_dash = q.replace(' ', '-')
    filename = os.path.join(data_dir, f'{q_dash}.yaml')

    # was query already searched?
    if os.path.isfile(filename):
        continue

    search_time = datetime.datetime.now().astimezone().isoformat()
    web_search = models.WebSearch(q, search_time)

    start = 1
    while start < result_count:
        # https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list
        url = 'https://customsearch.googleapis.com/customsearch/v1'
        headers = {'Accept': 'application/json'}
        params = {
            'q': q,
            'cx': search_engine_id,
            'key': api_key,
            'start': start,
            'num': 10,
        }
        r = requests.get(url, params=params, headers=headers)
        data = r.json()

        for i, item in enumerate(data.get('items'), start=start):
            search_item = models.SearchItem(
                i,
                item.get('title'),
                item.get('link'),
                item.get('snippet'),
                item.get('pagemap', {}).get('metatags', [{}])[0])
            web_search.add_item(search_item)

        start += 10

    with open(filename, 'w') as file:
        yaml.dump(web_search, file)
