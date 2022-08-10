import datetime
import os
import time

import googleapiclient.discovery
import googleapiclient.errors
import searchtweets
from dateutil.relativedelta import relativedelta
from tqdm import tqdm

from vulntuts import models, storage
from vulntuts.commands import BaseCommand
from vulntuts.errors import ApiError, InvalidArgumentError, SearchError
from vulntuts.youtube import YouTubeAPI

DEFAULT_SEARCH_CONFIG = {
    "google": {
        "language": "en",
        "num_results": 30,
    },
    "youtube": {
        "language": "en",
        "num_results": 50,
    },
    "twitter": {
        "language": "en",
        "num_results": 500,
    },
}


class SearchCommand(BaseCommand):
    def get_name(self):
        return "search"

    def get_help(self):
        return (
            "Execute search queries on different search engines and collect the results"
        )

    def uses_config(self):
        return True

    def setup_arguments(self, parser):
        parser.add_argument(
            "--engine",
            help="Search engine to execute the search on [default: google]",
            choices=["google", "youtube", "twitter"],
            required=True,
        )

    def main(self, args):
        data_dir = args.get("data_dir")
        engine = args.get("engine")
        config = args.get("config", {})

        # process search config for engine
        search_config = self._process_search_config(config.get("search", {}))
        search_config = search_config.get(engine)
        num_results = search_config.get("num_results")
        language = search_config.get("language")

        # retrieve API config for engine
        api_config = config.get("apis", {}).get(engine, {})

        # load search queries
        query_storage = storage.SearchQueryStorage(data_dir)
        queries = query_storage.load_all()

        # create storage for search results
        search_result_storage = storage.SearchResultStorage(data_dir)

        if engine == "google":
            google = GoogleSearch(search_result_storage, api_config)
            google.search(queries, num_results, language)
        elif engine == "youtube":
            youtube = YouTubeSearch(search_result_storage, api_config)
            youtube.search(queries, num_results, language)
        elif engine == "twitter":
            twitter = TwitterSearch(search_result_storage, api_config)
            twitter.search(queries, num_results, language)
        else:
            raise InvalidArgumentError(f"Invalid search engine '{engine}'")

    def _process_search_config(self, search_config):
        # copy default config
        result = dict(DEFAULT_SEARCH_CONFIG)

        # check and copy values for search engines
        for engine, engine_config in search_config.items():
            if engine not in result:
                raise InvalidArgumentError(
                    f"The search engine '{engine}' is invalid (config option 'search')"
                )

            # check and copy value for language and num_results
            if "language" in engine_config:
                result[engine]["language"] = engine_config.get("language")
            if "num_results" in engine_config:
                result[engine]["num_results"] = engine_config.get("num_results")

        # return config
        return result


class GoogleSearch(object):
    engine = models.SearchEngine.GOOGLE

    def __init__(self, search_result_storage, config):
        self.search_result_storage = search_result_storage

        # process and validate config
        config = self._process_config(config)

        # retrieve values from config
        self.search_engine_id = config.get("search_engine_id")
        self.api_key = config.get("api_key")

    def search(self, queries, num_results, language):
        # information for Custom Search API
        api_service_name = "customsearch"
        api_version = "v1"

        # get first API key and create API object
        api_key_iter = enumerate(self.api_key, start=1)
        api_key_id, api_key = next(api_key_iter)
        google_search_api = self._create_api(api_service_name, api_version, api_key)

        # iterate over queries
        for query in tqdm(queries, desc="Queries"):
            # was already searched?
            if self.search_result_storage.was_searched(GoogleSearch.engine, query):
                continue

            # search: try different API keys as only 100 req/day/key are allowed
            items = None
            while items is None:
                try:
                    items = self._call_api(
                        google_search_api,
                        self.search_engine_id,
                        query.string,
                        num_results,
                        language,
                    )
                except googleapiclient.errors.Error as e:
                    # only 100 req/day/key are allowed, try next API key
                    if self._is_quota_exceeded(e):
                        try:
                            tqdm.write(
                                f"API key #{api_key_id}: API quota exceeded. Using"
                                " next API key..."
                            )
                            api_key_id, api_key = next(api_key_iter)
                            google_search_api = self._create_api(
                                api_service_name, api_version, api_key
                            )
                        except StopIteration:
                            raise SearchError("API quota exceeded. Try tomorrow...")
                    else:
                        raise SearchError(f"API error: {e.reason}")

            # create result object and store it
            search_result = models.SearchResult(
                engine=GoogleSearch.engine,
                query=query,
                items=items,
            )
            self.search_result_storage.save(search_result)

    def _process_config(self, config):
        # validate config
        if not config.get("search_engine_id", None):
            raise InvalidArgumentError(
                "Please specify a search engine ID for Google in the config file"
            )
        if not config.get("api_key", None):
            raise InvalidArgumentError(
                "Please specify an API key for Google in the config file"
            )

        # convert api key to list if only one is given
        if not isinstance(config.get("api_key"), list):
            config["api_key"] = [config.get("api_key")]

        return config

    def _create_api(self, api_service_name, api_version, api_key):
        # build API object
        google_api = googleapiclient.discovery.build(
            api_service_name, api_version, developerKey=api_key
        )
        return google_api.cse()

    def _call_api(self, search_api, search_engine_id, query, num_results, language):
        items = []
        while len(items) < num_results:
            start = len(items) + 1

            # search webpages
            # https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list
            request = search_api.list(
                q=query,
                num=10,
                start=start,
                cx=search_engine_id,
                lr=f"lang_{language}",
            )
            response = request.execute()

            # check response
            if response.get("searchInformation").get("totalResults") == "0":
                break

            # retrieve search result items from response
            for rank, item in enumerate(response.get("items"), start=start):
                search_result_item = models.SearchResultItem(
                    rank=rank,
                    title=item.get("title"),
                    url=item.get("link"),
                    snippet=item.get("snippet"),
                    metadata=item.get("pagemap", {}).get("metatags", [{}])[0],
                )
                items.append(search_result_item)

            # wait 1 second so as not to flood the API with calls
            time.sleep(1)

        return items

    def _is_quota_exceeded(self, api_error):
        for error in api_error.error_details:
            if error.get("reason", None) == "rateLimitExceeded":
                return True
        return False


class YouTubeSearch(object):
    engine = models.SearchEngine.YOUTUBE

    def __init__(self, search_result_storage, youtube_config):
        self.search_result_storage = search_result_storage

        # create wrapper for YouTube API
        self.youtube_api = YouTubeAPI(youtube_config)

    def search(self, queries, num_results, language):
        # iterate over queries
        for query in tqdm(queries, desc="Queries"):
            # was already searched?
            if self.search_result_storage.was_searched(YouTubeSearch.engine, query):
                continue

            # perform search
            try:
                items = self.youtube_api.search(query.string, num_results, language)
            except ApiError as e:
                raise SearchError("YouTube search failed") from e

            search_result_items = []
            for rank, item in enumerate(items, start=1):
                # retrieve metadata (snippet and id object)
                metadata = item.get("snippet")
                metadata.update(item.get("id"))

                # create search result item
                search_result_item = models.SearchResultItem(
                    rank=rank,
                    title=metadata.get("title"),
                    url=self._create_video_url(metadata.get("videoId")),
                    snippet=metadata.get("description"),
                    metadata=metadata,
                )
                search_result_items.append(search_result_item)

            # create result object and store it
            search_result = models.SearchResult(
                engine=YouTubeSearch.engine,
                query=query,
                items=search_result_items,
            )
            self.search_result_storage.save(search_result)

    def _create_video_url(self, video_id):
        return f"https://www.youtube.com/watch?v={video_id}"


class TwitterSearch(object):
    engine = models.SearchEngine.TWITTER

    def __init__(self, search_result_storage, config):
        self.search_result_storage = search_result_storage

        # process and validate config
        config = self._process_config(config)

        # retrieve bearer token from config
        self.bearer_token = config.get("bearer_token")

    def search(self, queries, num_results, language):
        # information for Twitter API v2
        os.environ[
            "SEARCHTWEETS_ENDPOINT"
        ] = "https://api.twitter.com/2/tweets/search/all"
        os.environ["SEARCHTWEETS_BEARER_TOKEN"] = self.bearer_token

        # load API credentials
        api_credentials = searchtweets.load_credentials()

        # iterate over queries
        for query in tqdm(queries, desc="Queries"):
            # was already searched?
            if self.search_result_storage.was_searched(TwitterSearch.engine, query):
                continue

            # search tweets
            items = self._search_tweets(
                api_credentials, query.string, num_results, language
            )

            # create result object and store it
            search_result = models.SearchResult(
                engine=TwitterSearch.engine,
                query=query,
                items=items,
            )
            self.search_result_storage.save(search_result)

            # API allows only one request/s
            time.sleep(1)

    def _process_config(self, config):
        # validate config
        if not config.get("bearer_token", None):
            raise InvalidArgumentError(
                "Please specify a Bearer Token for Twitter in the config file"
            )

        return config

    def _search_tweets(self, api_credentials, query, num_results, language):
        items = []

        # setup parameters for query
        # https://developer.twitter.com/en/docs/twitter-api/tweets/search/integrate/build-a-query
        query_params = f"-is:retweet -is:nullcast has:links lang:{language} {query}"
        # https://developer.twitter.com/en/docs/twitter-api/data-dictionary/object-model/tweet
        tweet_fields = "author_id,created_at,lang,attachments,entities,public_metrics"

        # only search tweets from the last three years
        start_time = datetime.datetime.now() - relativedelta(years=3)
        start_time = start_time.strftime("%Y-%m-%d")

        # to retrieve information about media:
        # https://developer.twitter.com/en/docs/twitter-api/data-dictionary/using-fields-and-expansions
        # https://developer.twitter.com/en/docs/twitter-api/data-dictionary/object-model/media
        # expansions = "attachments.media_keys"
        # media_fields = "media_key,type,preview_image_url,url"
        # query_params = query_params + " (has:media OR has:links)"

        # search tweets
        # https://developer.twitter.com/en/docs/twitter-api/tweets/search/api-reference/get-tweets-search-all
        rule = searchtweets.gen_request_parameters(
            query_params,
            tweet_fields=tweet_fields,
            # expansions=expansions,
            # media_fields=media_fields,
            start_time=start_time,
            results_per_call=500,
            granularity=None,
            stringify=False,
        )

        # gen_request_parameters does not accept sort_order parameter, hack it manually
        rule["sort_order"] = "relevancy"

        # create result stream (paginates if necessary)
        response = searchtweets.ResultStream(
            request_parameters=rule,
            max_tweets=num_results,
            max_pages=1,
            output_format="a",
            **api_credentials,
        )

        # retrieve tweets from response
        tweets = list(response.stream())
        for rank, item in enumerate(tweets, start=1):
            # create search result item
            search_result_item = models.SearchResultItem(
                rank=rank,
                title="",
                url=self._create_tweet_url(item.get("id")),
                snippet=item.get("text"),
                metadata=item,
            )
            items.append(search_result_item)

        return items

    def _create_tweet_url(self, tweet_id):
        return f"https://twitter.com/i/web/status/{tweet_id}"
