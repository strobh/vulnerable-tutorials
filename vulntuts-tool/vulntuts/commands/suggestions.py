import time

import requests
from tqdm import tqdm

from vulntuts import storage
from vulntuts.commands import BaseCommand
from vulntuts.errors import InvalidArgumentError


class SuggestQueriesCommand(BaseCommand):
    def get_name(self):
        return "suggest-terms"

    def get_help(self):
        return (
            "Retrieve term suggestions for search queries used to search for tutorials"
        )

    def setup_arguments(self, parser):
        parser.add_argument(
            "--source",
            help="Data source to generate queries from [default: google-suggest]",
            choices=["google-suggest", "stack-overflow"],
            default="google-suggest",
        )

    def main(self, args):
        source = args.get("source")
        suggestion_storage = storage.SuggestionStorage(args.get("data_dir"))

        # create backup
        suggestion_storage.create_backup()

        # retrieve suggestions from Google Suggestions
        if source == "google-suggest":
            google_suggestions = GoogleSuggestions(suggestion_storage)
            google_suggestions.fetch()
        # retrieve suggestions from Stack Overflow
        elif source == "stack-overflow":
            so_suggestions = StackOverflowSuggestions()
            so_suggestions.fetch()
        else:
            raise InvalidArgumentError(f"Invalid suggestions source '{source}'")


class GoogleSuggestions(object):
    url = "https://suggestqueries.google.com/complete/search"

    def __init__(self, suggestion_storage):
        self.suggestion_storage = suggestion_storage

    def fetch(self):
        languages = [
            "java",
            "javascript",
            "python",
            "php",
        ]

        for language in tqdm(languages, desc="Languages"):
            search_terms = [
                f"{language} tutorial ",
                f"{language} tutorial how to implement ",
                f"{language} tutorial how to create ",
                f"{language} example ",
                f"{language} how to ",
                f"{language} learn ",
                f"learn {language} ",
            ]
            suggestions = self.fetch_suggestions(search_terms)
            self.suggestion_storage.save(category=language, queries=suggestions)

    def fetch_suggestions(self, search_terms):
        suggestions = list()

        # iterate over search terms and fetch suggestions for them
        for term in tqdm(search_terms, desc="Terms", leave=False):
            # fetch suggestions
            suggestions_for_term = self._call_api(term)
            suggestions.extend(suggestions_for_term)

            # API might block too many requests
            time.sleep(1)

        return suggestions

    def _call_api(self, query):
        # https://shreyaschand.com/blog/2013/01/03/google-autocomplete-api/
        # q: search term [separate words with %20 or +]
        # client: firefox (json), toolbar (xml), youtube (jsonp)
        # hl: language (e.g. en)
        # gl: country (e.g. de) [only with "client=toolbar"]
        params = {"client": "firefox", "hl": "en", "q": query}
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:94.0) Gecko/20100101"
                " Firefox/94.0"
            )
        }
        response = requests.get(GoogleSuggestions.url, params=params, headers=headers)
        return response.json()[1]


class StackOverflowSuggestions(object):
    url = "https://data.stackexchange.com/stackoverflow/query/new"
    query = """
        select
          t.tagName,
          count(t.tagName) as tagCount
        from
          posts p
          inner join posttags pt on pt.postid = p.id
          inner join tags t on t.id = pt.tagid
        where
          p.lastActivityDate >= DATEADD(year, -3, GETDATE())
          and p.tags like '%<##tag##>%'
          and p.postTypeId = 1
          and t.tagName != '##tag##'
        group by
          t.tagName
        order by
          tagCount DESC"""

    def fetch(self):
        print("Open the StackExchange Data Explorer:")
        print(StackOverflowSuggestions.url)
        print("")
        print("Enter the following query:")
        print(StackOverflowSuggestions.query)
        print("")
        print("Press 'Run Query'.")
        print("Enter the programming language as tag parameter (e.g., 'php', 'java').")
        print("Press 'Run Query'.")
        print("Download the result as CSV.")
