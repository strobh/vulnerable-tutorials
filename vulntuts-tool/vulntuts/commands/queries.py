import itertools
import os

import yaml

from vulntuts import storage
from vulntuts.commands import BaseCommand
from vulntuts.errors import InvalidArgumentError


class GenerateQueriesCommand(BaseCommand):
    def get_name(self):
        return "generate-queries"

    def get_help(self):
        return "Generate queries used to search for tutorials"

    def setup_arguments(self, parser):
        parser.add_argument(
            "-q",
            "--queries",
            help=(
                "Specify a config file describing how the queries are constructed"
                f" (default: {storage.QUERIES_CONFIG_FILE})"
            ),
            default=None,
        )

    def main(self, args):
        search_query_storage = storage.SearchQueryStorage(args.get("data_dir"))

        # create backup
        search_query_storage.create_backup()

        generator = QueryGenerator(search_query_storage)
        generator.generate(args.get("queries"))


class QueryGenerator(object):
    def __init__(self, search_query_storage):
        self.search_query_storage = search_query_storage

    def generate(self, query_config_file):
        print("Generating search queries...")

        query_config = self._load_query_config(query_config_file)
        query_templates = query_config.get("templates")
        query_terms = query_config.get("terms")

        self.construct_queries(query_templates, query_terms)

    def _load_query_config(self, config_file):
        # if no config file was specified, use default
        if config_file is None:
            config_file = storage.QUERIES_CONFIG_FILE

        config_path = os.path.abspath(os.path.join(os.getcwd(), config_file))
        if not os.path.isfile(config_path):
            raise InvalidArgumentError(
                f"The query config file '{config_file}' does not exist"
            )

        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
            if not self._is_config_valid(config):
                raise InvalidArgumentError(
                    f"The query config file '{config_file}' is invalid"
                )
            return config

    def _is_config_valid(self, config):
        # check basic structure
        if not isinstance(config, dict):
            return False
        if "templates" not in config or "terms" not in config:
            return False
        if not isinstance(config["templates"], dict) or not isinstance(
            config["terms"], dict
        ):
            return False

        # check templates
        for template in config["templates"].values():
            if not isinstance(template, list) or not all(
                isinstance(template_item, str) for template_item in template
            ):
                return False
        # check terms
        for term in config["terms"].values():
            if not isinstance(term, list) or not all(
                isinstance(term_item, str) for term_item in term
            ):
                return False

        # everything valid
        return True

    def construct_queries(self, query_templates, terms):
        for template_name, query_template in query_templates.items():
            template_parts = list()
            for term_group in query_template:
                template_parts.append(terms.get(term_group))
            queries = self._construct_queries(template_parts)
            self.search_query_storage.save(category=template_name, queries=queries)

    def _construct_queries(self, parts):
        queries = list(itertools.product(*parts))
        return [" ".join(q) for q in queries]
