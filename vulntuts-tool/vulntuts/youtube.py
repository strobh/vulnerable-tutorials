import time

import googleapiclient.discovery
import googleapiclient.errors
from tqdm import tqdm

from vulntuts.errors import ApiError, InvalidArgumentError


class YouTubeAPI(object):
    def __init__(self, config):
        self.api_keys = self._process_config(config).get("api_key")
        self.quota_exceeded = False

        # get first API key and create API object
        self.api_key_iter = enumerate(self.api_keys, start=1)
        self._use_next_api_key()

    def _process_config(self, config):
        # validate config
        if not config.get("api_key", None):
            raise InvalidArgumentError(
                "Please specify an API key for YouTube in the config file"
            )

        # convert api key to list if only one is given
        if not isinstance(config.get("api_key"), list):
            config["api_key"] = [config.get("api_key")]

        return config

    def _use_next_api_key(self):
        self.api_key_id, self.api_key = next(self.api_key_iter)
        self._create_api()

    def _create_api(self):
        # information for YouTube Data API
        api_service_name = "youtube"
        api_version = "v3"

        self.youtube_api = googleapiclient.discovery.build(
            api_service_name, api_version, developerKey=self.api_key
        )

    def search(self, query, num_results, language):
        return self._call_api_wrapper(
            lambda: self._search(query, num_results, language)
        )

    def get_video_info(self, video_id):
        return self._call_api_wrapper(lambda: self._get_video_info(video_id))

    def get_video_comments(self, video_id):
        return self._call_api_wrapper(lambda: self._get_video_comments(video_id))

    def _call_api_wrapper(self, func):
        if self.quota_exceeded:
            raise ApiError("API quota exceeded. Try tomorrow...")

        # try different API keys as only 100 req/day/key are allowed
        result = None
        while result is None:
            try:
                result = func()
            except googleapiclient.errors.Error as e:
                # only 100 req/day/key are allowed, try next API key
                if self._is_quota_exceeded(e):
                    try:
                        tqdm.write(
                            f"API key #{self.api_key_id}: API Quota exceeded. Using"
                            " next API key..."
                        )
                        self._use_next_api_key()
                    except StopIteration:
                        self.quota_exceeded = True
                        raise ApiError("API quota exceeded. Try tomorrow...")
                else:
                    raise ApiError(f"YouTube API error: {e.reason}")

        return result

    def _is_quota_exceeded(self, api_error):
        for error in api_error.error_details:
            if error.get("reason", None) == "quotaExceeded":
                return True
        return False

    def _search(self, query, num_results, language):
        search_api = self.youtube_api.search()
        items = []

        # search videos
        # https://developers.google.com/youtube/v3/docs/search/list
        # https://developers.google.com/youtube/v3/docs/videos#resource-representation
        request = search_api.list(
            q=query,
            part="id,snippet",
            maxResults=50,
            type="video",
            relevanceLanguage=language,
        )

        while request is not None and len(items) < num_results:
            response = request.execute()

            # retrieve search result items from response
            if len(response.get("items")) > 0:
                items.extend(response.get("items"))

            # prepare request for next page
            request = search_api.list_next(request, response)

            # wait 1 second so as not to flood the API with calls
            time.sleep(1)

        return items

    def _get_video_info(self, video_id):
        videos_api = self.youtube_api.videos()

        # retrieve data about video
        # https://developers.google.com/youtube/v3/docs/videos
        # https://developers.google.com/youtube/v3/docs/videos#resource-representation
        request = videos_api.list(
            id=video_id, part="id,snippet,contentDetails,statistics", maxResults=1
        )
        response = request.execute()

        # if the video does not exist, return an empty dict
        if len(response.get("items")) == 0:
            return dict()
        return response.get("items")[0]

    def _get_video_comments(self, video_id):
        comments_api = self.youtube_api.commentThreads()

        # retrieve comments threads for video
        # https://developers.google.com/youtube/v3/docs/commentThreads/list
        # https://developers.google.com/youtube/v3/docs/commentThreads#resource-representation
        request = comments_api.list(
            videoId=video_id,
            part="id,snippet",  # replies
            order="relevance",
            maxResults=20,
        )
        response = request.execute()

        # extract top-level comments from comment threads
        comments = [
            comment_thread.get("snippet").get("topLevelComment")
            for comment_thread in response.get("items")
        ]

        # remove like count from comments to make it easier to check for changes
        for comment in comments:
            del comment["snippet"]["likeCount"]

        return comments

    def filter_comments_for_author(self, comments, author):
        return [
            comment
            for comment in comments
            if comment.get("snippet").get("authorChannelId").get("value") == author
        ]
