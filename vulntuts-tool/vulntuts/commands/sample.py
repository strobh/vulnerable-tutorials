import random
from urllib.parse import urlparse

import numpy as np
import requests
import requests.exceptions
import tldextract
from bs4 import BeautifulSoup
from tqdm import tqdm

from vulntuts import models, storage
from vulntuts.commands import BaseCommand
from vulntuts.errors import InvalidArgumentError, InvalidInspectionError

DEFAULT_CONFIG = {
    "max_rank": {
        models.SearchEngine.GOOGLE: 30,
        models.SearchEngine.YOUTUBE: 50,
        models.SearchEngine.TWITTER: 50,
    },
    "proportion": {
        "type": {
            models.InspectionType.VIDEO: 0.5,
            models.InspectionType.WEBPAGE: 0.5,
        },
        "engine": {
            models.InspectionType.VIDEO: None,
            models.InspectionType.WEBPAGE: {
                models.SearchEngine.GOOGLE: 0.8,
                models.SearchEngine.TWITTER: 0.2,
            },
        },
    },
    "excluded_domains": [],
}


class SampleCommand(BaseCommand):
    def get_name(self):
        return "sample"

    def get_help(self):
        return "Randomly sample search results to be inspected manually"

    def uses_config(self):
        return True

    def setup_arguments(self, parser):
        parser.add_argument(
            "-n",
            "--number",
            metavar="SAMPLE_SIZE",
            help="The number of search results to sample [default: 2000]",
            dest="sample_size",
            type=int,
            default=2000,
        )
        parser.add_argument(
            "--weighted",
            help="Weight the search results by the number of occurences",
            action="store_true",
        )
        parser.add_argument(
            "--keep-previous",
            help="Keep the previous inspections and add SAMPLE_SIZE new inspections.",
            action="store_true",
        )

    def main(self, args):
        data_dir = args.get("data_dir")
        weighted = args.get("weighted")
        sample_size = args.get("sample_size")

        sampling_metadata_storage = storage.SamplingMetadataStorage(data_dir)
        inspection_storage = storage.InspectionStorage(data_dir)
        search_result_storage = storage.SearchResultStorage(data_dir)

        # load search results to sample inspections from
        print("Loading search results...")
        search_results = search_result_storage.load_all()

        # load config
        config = args.get("config", {}).get("sampling", {})
        config = self._process_config(config)

        # load previous inspections
        print("Loading previous inspections...")
        prev_inspections = inspection_storage.load_all()

        # load resolved urls and metadata
        print("Loading previous sampling metadata...")
        sampling_metadata = sampling_metadata_storage.load_all()

        # create backup
        inspection_storage.create_backup()

        print("Creating inspections...")
        try:
            # create inspections
            inspection_creator = InspectionCreator(
                sampling_metadata,
                config.get("excluded_domains"),
                config.get("max_rank"),
            )
            inspections = inspection_creator.create_inspections(search_results)
            inspection_creator.copy_inspection_results(inspections, prev_inspections)
        except KeyboardInterrupt:
            # re-raise interrupt
            raise
        finally:
            sampling_metadata_storage.save(inspection_creator.sampling_metadata)

        # check if there are search results to sample from
        if len(inspections) == 0:
            raise InvalidArgumentError("No search results to sample from")

        print("Sampling inspections...")
        sampler = InspectionSampler(config.get("proportion"))

        # if previous inspections should be kept, remove them from new sample pool
        if args.get("keep_previous"):
            sampler.remove_previous_sample(inspections, prev_inspections)

        # sample inspections
        sampled_inspections = sampler.sample(
            inspections, sample_size, weighted=weighted
        )

        # if previous inspections should be kept, add them to new sample
        if args.get("keep_previous"):
            sampler.merge_with_previous_sample(sampled_inspections, prev_inspections)

        inspection_storage.save(sampled_inspections)

    def _process_config(self, config):
        # copy default config
        result = dict(DEFAULT_CONFIG)

        # copy and check values for max_rank and proportion
        result["max_rank"].update(
            self._process_config_max_rank(config.get("max_rank", {}))
        )
        result["proportion"]["type"].update(
            self._process_config_proportion_type(
                config.get("proportion", {}).get("type", {})
            )
        )
        result["proportion"]["engine"].update(
            self._process_config_proportion_engine(
                config.get("proportion", {}).get("engine", {})
            )
        )

        # check excluded_domains
        if "excluded_domains" in config:
            try:
                result["excluded_domains"] = list(config.get("excluded_domains"))
            except ValueError:
                raise InvalidArgumentError(
                    "The list of excluded domains is invalid"
                    " (config option 'sampling.excluded_domains')"
                )

        # return config
        return result

    def _process_config_max_rank(self, config_max_rank):
        result = {}

        # check and copy max_rank
        for engine, max_rank in config_max_rank.items():
            try:
                engine_enum = models.SearchEngine(engine.upper())
                result[engine_enum] = int(max_rank)
            except ValueError:
                raise InvalidArgumentError(
                    f"The search engine '{engine}' or its value '{max_rank}' is invalid"
                    " (config option 'sampling.max_rank')"
                )

        return result

    def _process_config_proportion_type(self, proportion_type):
        result = {}

        # check and copy proportion.type (inspection type: video/webpage)
        for type_, proportion_for_type in proportion_type.items():
            try:
                type_enum = models.InspectionType(type_.upper())
                result[type_enum] = float(proportion_for_type)
            except ValueError:
                raise InvalidArgumentError(
                    f"The inspection type '{type_}' or its value"
                    f" '{proportion_for_type}' is invalid (config option"
                    " 'sampling.proportion.type')"
                )

        return result

    def _process_config_proportion_engine(self, proportion_engine):
        result = {}

        # check and copy proportion.engine (inspection type: video/webpage)
        for type_, proportion_for_type in proportion_engine.items():
            if proportion_for_type is None:
                continue

            try:
                type_enum = models.InspectionType(type_.upper())
                result[type_enum] = {}
            except ValueError:
                raise InvalidArgumentError(
                    f"The inspection type '{type_}' or its value is invalid"
                    " (config option 'sampling.proportion.engine')"
                )

            # check and copy proportion for search engines (google/youtube/twitter)
            for engine, proportion_for_engine in proportion_for_type.items():
                try:
                    engine_enum = models.SearchEngine(engine.upper())
                    result[type_enum][engine_enum] = float(proportion_for_engine)
                except ValueError:
                    raise InvalidArgumentError(
                        f"The search engine '{engine}' or its value"
                        f" '{proportion_for_engine}' is invalid (config option"
                        " 'sampling.proportion.engine')"
                    )

        return result


class InspectionCreator(object):
    def __init__(self, sampling_metadata, excluded_domains, max_rank):
        self.sampling_metadata = sampling_metadata
        self.excluded_domains = set(excluded_domains)
        self.max_rank = max_rank

    def create_inspections(self, search_results):
        inspections_list = self.create_inspections_list(search_results)
        return self.merge_duplicate_inspections(inspections_list)

    def create_inspections_list(self, search_results):
        inspections_list = list()

        # iterate over search results and save into inspections
        for search_result in tqdm(search_results, desc="Search results"):
            # if the search result has no items, continue
            if len(search_result.items) == 0:
                continue

            for search_result_item in tqdm(
                search_result.items,
                desc=f"{search_result.engine} ({search_result.query.string})",
                leave=False,
            ):
                # skip items whose rank is higher than the max_rank
                if search_result_item.rank > self.max_rank[search_result.engine]:
                    continue

                inspection_source = models.InspectionSource(
                    engine=search_result.engine,
                    query=search_result.query,
                    rank=search_result_item.rank,
                    snippet=search_result_item.snippet,
                )

                if search_result.engine == models.SearchEngine.TWITTER:
                    inspections_list.extend(
                        self.create_inspections_for_tweet(
                            search_result_item, inspection_source
                        )
                    )
                else:
                    inspections_list.extend(
                        self.create_inspections_for_search_result(
                            search_result_item, inspection_source
                        )
                    )

        return inspections_list

    def create_inspections_for_tweet(self, search_result_item, inspection_source):
        inspections = list()
        urls = search_result_item.metadata.get("entities", {}).get("urls", [])
        for url_data in urls:
            # exclude images embedded into Tweet
            # ugly work-around: twitter does not offer a possibility to
            # distinguish between 'normal' URLs and media embedded into a Tweet
            if url_data.get("display_url", "").startswith("pic.twitter.com"):
                continue

            try:
                url = self._resolve_url(url_data.get("expanded_url"))
                metadata = self._retrieve_metadata(url)
                inspection = self.create_inspection(
                    url,
                    metadata.get("title"),
                )
                inspection.add_source(inspection_source)
                inspection.update_metadata(metadata)
                inspections.append(inspection)
            except InvalidInspectionError:
                continue
        return inspections

    def _resolve_url(self, url):
        # check if url was already resolved
        if url in self.sampling_metadata.resolved_urls:
            return self.sampling_metadata.resolved_urls[url]

        resolved_url = None
        try:
            result = requests.head(url, allow_redirects=True, timeout=5)
            resolved_url = result.url
        except requests.exceptions.RequestException as e:
            raise InvalidInspectionError("Resolving url failed") from e
        finally:
            # add resolved url to storage (prevents duplicate resolving)
            self.sampling_metadata.resolved_urls[url] = resolved_url

        return resolved_url

    def _retrieve_metadata(self, url):
        # check if page failed before
        if url in self.sampling_metadata.request_errors:
            error = self.sampling_metadata.request_errors[url]
            raise InvalidInspectionError(f"Request failed: {error}")

        # check if metadata was already retrieved
        if url in self.sampling_metadata.page_metadata:
            return self.sampling_metadata.page_metadata[url]

        # set default values for metadata
        metadata = {
            "title": "",
        }

        try:
            result = requests.get(url, allow_redirects=True, timeout=5)
            result.raise_for_status()

            # extract metadata from html response
            metadata.update(self._extract_metadata(result.text))
        except requests.exceptions.RequestException as e:
            # set request to be failed
            self.sampling_metadata.request_errors[url] = str(e)

            # raise exception
            raise InvalidInspectionError("Request failed") from e

        # add page metadata to storage (prevents duplicate retrieving)
        self.sampling_metadata.page_metadata[url] = metadata

        return metadata

    def _extract_metadata(self, html):
        soup = BeautifulSoup(html, "html.parser")
        metadata = dict()

        # retrieve metadata from meta tags
        for meta_tag in soup.find_all("meta"):
            value = meta_tag.get("content")
            if value:
                if meta_tag.get("property"):
                    metadata[meta_tag.get("property")] = value
                elif meta_tag.get("name"):
                    metadata[meta_tag.get("name")] = value

        # retrieve title
        if not metadata.get("title"):
            if soup.title:
                metadata["title"] = str(soup.title.string)
            elif "og:title" in metadata:
                metadata["title"] = metadata.get("og:title")

        return metadata

    def create_inspections_for_search_result(
        self, search_result_item, inspection_source
    ):
        try:
            inspection = self.create_inspection(
                search_result_item.url,
                search_result_item.title,
            )
            inspection.add_source(inspection_source)
            inspection.update_metadata(search_result_item.metadata)
            return [inspection]
        except InvalidInspectionError:
            return list()

    def create_inspection(self, url, title):
        if self._is_domain_excluded(url):
            raise InvalidInspectionError("Domain is excluded")

        # create inspection
        inspection_id = models.create_url_id(url)
        inspection = models.Inspection(
            id=inspection_id, url=url, title=title, type=self._get_inspection_type(url)
        )

        return inspection

    def _is_domain_excluded(self, url):
        domain = self._get_first_level_domain(url)
        return domain in self.excluded_domains

    def _get_inspection_type(self, url):
        domain = self._get_first_level_domain(url)
        if domain == "youtube.com":
            return models.InspectionType.VIDEO
        else:
            return models.InspectionType.WEBPAGE

    def _get_first_level_domain(self, url):
        url_parts = urlparse(url)
        domain = url_parts.netloc
        return tldextract.extract(domain).registered_domain

    def merge_duplicate_inspections(self, inspections_list):
        # create dict of inspections
        inspections = dict()

        for inspection in inspections_list:
            # retrieve or create inspection
            if inspection.id in inspections:
                corresponding_inspection = inspections.get(inspection.id)
                corresponding_inspection.add_source(inspection.sources[0])
                corresponding_inspection.update_metadata(inspection.metadata)
            else:
                inspections[inspection.id] = inspection

        return inspections

    def copy_inspection_results(self, inspections, prev_inspections):
        # copy previous inspection results to new inspections
        # (prevent overwriting them)
        for inspection in inspections.values():
            if inspection.id in prev_inspections:
                prev_inspection = prev_inspections.get(inspection.id)
                inspection.result = prev_inspection.result


class InspectionSampler(object):
    def __init__(self, proportion):
        self.proportion = proportion

    def sample(self, inspections, sample_size, weighted=False):
        # convert inspections to list to be sampled
        inspections_list = [inspection for inspection in inspections.values()]
        sample_list = []

        for type_, type_proportion in self.proportion.get("type").items():
            # filter inspections for type
            inspections_for_type = [
                inspection
                for inspection in inspections_list
                if inspection.type == type_
            ]

            sample_list.extend(
                self._sample_by_type(
                    inspections_for_type,
                    type_,
                    int(sample_size * type_proportion),
                    weighted,
                )
            )

        # convert inspections to dict
        sample_dict = dict()
        for inspection in sample_list:
            sample_dict[inspection.id] = inspection

        return sample_dict

    def _sample_by_type(self, inspections_list, type_, sample_size, weighted):
        sample_list = []
        proportion_for_type = self.proportion.get("engine").get(type_)

        # if no proportion is defined, sample from all engines
        if not proportion_for_type:
            return self._sample(inspections_list, sample_size, weighted)

        # otherwise sample from seach engines according to proportion
        for engine, engine_proportion in proportion_for_type.items():
            # filter inspections for engine
            inspections_for_engine = [
                inspection
                for inspection in inspections_list
                if inspection.has_source_engine(engine)
            ]

            # sample inspections
            sample_list_for_engine = self._sample(
                inspections_for_engine, int(sample_size * engine_proportion), weighted
            )

            # remove already sampled search results to prevent duplicates
            inspections_list = [
                x for x in inspections_list if x not in sample_list_for_engine
            ]

            # add sampled search results to result list
            sample_list.extend(sample_list_for_engine)

        return sample_list

    def _sample(self, inspections_list, sample_size, weighted=False):
        if weighted:
            inspections_sources_count = [
                len(inspection.sources) for inspection in inspections_list
            ]
            inspections_sources_total = sum(inspections_sources_count)
            inspections_weight = [
                count / inspections_sources_total for count in inspections_sources_count
            ]

            # sample n inspections from list weighted by the number of sources
            return list(
                np.random.choice(
                    inspections_list, sample_size, replace=False, p=inspections_weight
                )
            )
        else:
            # sample n inspections from list
            return random.sample(inspections_list, sample_size)

    def remove_previous_sample(self, inspections, previous_inspections):
        for previous_inspection_id in previous_inspections.keys():
            if previous_inspection_id in inspections:
                del inspections[previous_inspection_id]

    def merge_with_previous_sample(self, inspections, previous_inspections):
        for previous_inspection in previous_inspections.values():
            inspections[previous_inspection.id] = previous_inspection
