import itertools
import pprint
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from functools import partial

from vulntuts import models, storage
from vulntuts.commands import BaseCommand
from vulntuts.errors import InvalidArgumentError


class DataCommand(BaseCommand):
    def get_name(self):
        return "data"

    def get_help(self):
        return "Manage and print data and calculate statistics"

    def setup_arguments(self, parser):
        parser.add_argument(
            "--info",
            metavar="URL_OR_ID",
            help="Retrieve informations about a tutorial",
        )
        parser.add_argument(
            "--stats",
            help="Retrieve statistics about the data",
            action="store_true",
        )
        parser.add_argument(
            "--full-stats",
            help="Retrieve more detailed statistics about the data",
            action="store_true",
        )

    def main(self, args):
        # initialize storage
        data_dir = args.get("data_dir")
        search_result_storage = storage.SearchResultStorage(data_dir)
        inspection_storage = storage.InspectionStorage(data_dir)
        tutorial_storage = storage.TutorialStorage(data_dir)

        if args.get("info"):
            data_manager = DataManager(
                search_result_storage,
                inspection_storage,
                tutorial_storage,
            )
            data_manager.get_info(args.get("info"))
        elif args.get("stats") or args.get("full_stats"):
            statistics_manager = StatisticsManager(
                search_result_storage,
                inspection_storage,
                tutorial_storage,
            )
            statistics_manager.calculate_statistics(args.get("full_stats"))
            statistics_manager.print_statistics()


class DataManager(object):
    def __init__(self, search_result_storage, inspection_storage, tutorial_storage):
        self.search_result_storage = search_result_storage
        self.inspection_storage = inspection_storage
        self.tutorial_storage = tutorial_storage

    def get_info(self, url_or_id):
        inspections = self.inspection_storage.load_all()

        if url_or_id in inspections:
            tutorial_id = url_or_id
        elif models.create_url_id(url_or_id) in inspections:
            tutorial_id = models.create_url_id(url_or_id)
        else:
            raise InvalidArgumentError("Inspection/Tutorial does not exist")

        inspection = inspections.get(tutorial_id)
        data = asdict(inspection)

        if self.tutorial_storage.has_tutorial(tutorial_id):
            # get data of tutorial
            tutorial = self.tutorial_storage.load_tutorial(tutorial_id)
            data.update(asdict(tutorial))

        pprint.pprint(data)


class StatisticsManager(object):
    def __init__(self, search_result_storage, inspection_storage, tutorial_storage):
        self.search_result_storage = search_result_storage
        self.inspection_storage = inspection_storage
        self.tutorial_storage = tutorial_storage
        self.stats = {}

    def calculate_statistics(self, full_stats):
        # load inspections
        print("Loading inspections...", end="\r")
        inspections = self.inspection_storage.load_all()
        print("\033[K", end="\r")

        # load tutorials
        print("Loading tutorials...", end="\r")
        tutorials = self.tutorial_storage.load_all()
        tutorials = [*tutorials]
        print("\033[K", end="\r")

        if full_stats:
            # load search results
            print("Loading search results...", end="\r")
            search_results = self.search_result_storage.load_all()
            search_results = [*search_results]
            print("\033[K", end="\r")

        # calculate statistics
        print("Calculating statistics...", end="\r")
        if full_stats:
            self._calculate_statistics_for_search_results(search_results)
        self._calculate_statistics_for_inspections(inspections, tutorials)
        self._calculate_statistics_for_tutorials(tutorials, inspections)
        self._calculate_statistics_for_vulnerabilities(tutorials, inspections)
        print("\033[K")

    def print_statistics(self):
        print("Legend")
        print("======")
        print("G: Google")
        print("Y: YouTube")
        print("T: Twitter")

        self._print_statistics_for_search_results()
        self._print_statistics_for_inspections()
        self._print_statistics_for_tutorials()
        self._print_statistics_for_vulnerabilities()

    def _calculate_statistics_for_search_results(self, search_results):
        def _stats(search_results):
            # count search results and search result items
            count = len(search_results)
            item_count = sum(
                [len(search_result.items) for search_result in search_results]
            )

            unique_item_urls = set()
            for search_result in search_results:
                for item in search_result.items:
                    unique_item_urls.add(item.url)
            unique_item_count = len(unique_item_urls)

            return {
                "count": count,
                "item_count": item_count,
                "unique_item_count": unique_item_count,
            }

        # calculate statistics for all search results
        self.stats["search_results"] = _stats(search_results)

        # split search results by engine
        results_by_engine = defaultdict(list)
        for search_result in search_results:
            results_by_engine[search_result.engine].append(search_result)

        # calculate statistics for search results by engine
        self.stats["search_results_by_engine"] = defaultdict(dict)
        for engine, results_for_engine in results_by_engine.items():
            self.stats["search_results_by_engine"][engine] = _stats(results_for_engine)

    def _print_statistics_for_search_results(self):
        if "search_results" not in self.stats:
            return

        s_all = self.stats["search_results"]
        s_engine = self.stats["search_results_by_engine"]

        print("")
        print("")
        print("==============")
        print("Search Results")
        print("==============")
        print(
            f"Results:             {d6(s_all['count'])}"
            f" \t(G: {d6(s_engine[models.SearchEngine.GOOGLE]['count'])}"
            f" | Y: {d6(s_engine[models.SearchEngine.YOUTUBE]['count'])}"
            f" | T: {d6(s_engine[models.SearchEngine.TWITTER]['count'])})"
        )
        print(
            f"Result Items:        {d6(s_all['item_count'])}"
            f" \t(G: {d6(s_engine[models.SearchEngine.GOOGLE]['item_count'])}"
            f" | Y: {d6(s_engine[models.SearchEngine.YOUTUBE]['item_count'])}"
            f" | T: {d6(s_engine[models.SearchEngine.TWITTER]['item_count'])})"
        )
        print(
            f"Unique Result Items: {d6(s_all['unique_item_count'])}"
            f" \t(G: {d6(s_engine[models.SearchEngine.GOOGLE]['unique_item_count'])}"
            f" | Y: {d6(s_engine[models.SearchEngine.YOUTUBE]['unique_item_count'])}"
            f" | T: {d6(s_engine[models.SearchEngine.TWITTER]['unique_item_count'])})"
        )

    def _calculate_statistics_for_inspections(self, inspections, tutorials):
        def _stats_by_group(inspections_by_group):
            result = defaultdict(dict)
            for group, inspections_for_group in inspections_by_group.items():
                result[group] = self._stats_for_inspections(inspections_for_group)
            return result

        # extract values from inspections
        inspections = inspections.values()

        # calculate statistics for all inspections
        self.stats["inspections"] = self._stats_for_inspections(inspections)

        # calculate statistics for inspections by type
        inspections_by_type = self._split_by_lambda(inspections, lambda x: x.type)
        self.stats["inspections_by_type"] = _stats_by_group(inspections_by_type)

        # calculate statistics for inspections by source query
        inspections_by_query = self._split_by_lambda(
            inspections, self._lambda_inspection_source_query_types
        )
        self.stats["inspections_by_query"] = _stats_by_group(inspections_by_query)

        # calculate statistics for inspections by language
        inspections_by_language = self._split_by_lambda(
            inspections, self._lambda_inspection_languages
        )
        self.stats["inspections_by_language"] = _stats_by_group(inspections_by_language)

        # calculate statistics for inspections by scope
        inspections_by_scope = self._split_by_lambda(
            inspections, self._lambda_inspection_scope
        )
        self.stats["inspections_by_scope"] = _stats_by_group(inspections_by_scope)

        # calculate statistics for inspections by vulnerable
        inspections_by_vulnerable = self._split_by_lambda(
            inspections, partial(self._lambda_inspection_vulnerable, tutorials)
        )
        self.stats["inspections_by_vulnerable"] = _stats_by_group(
            inspections_by_vulnerable
        )

        # calculate statistics for inspections by vulnerable and type
        inspections_by_vulnerable_and_type = self._split_by_lambda_tuple(
            inspections,
            partial(self._lambda_inspection_vulnerable, tutorials),
            lambda x: x.type,
        )
        self.stats["inspections_by_vulnerable_and_type"] = _stats_by_group(
            inspections_by_vulnerable_and_type
        )

        # calculate statistics for inspections by scope and type
        inspections_by_scope_and_type = self._split_by_lambda_tuple(
            inspections, self._lambda_inspection_scope, lambda x: x.type
        )
        self.stats["inspections_by_scope_and_type"] = _stats_by_group(
            inspections_by_scope_and_type
        )

        # calculate statistics for inspections by scope and source engine
        inspections_by_scope_and_engine = self._split_by_lambda_tuple(
            inspections,
            self._lambda_inspection_scope,
            self._lambda_inspection_source_engines,
        )
        self.stats["inspections_by_scope_and_engine"] = _stats_by_group(
            inspections_by_scope_and_engine
        )

        # calculate statistics for inspections by source query and source engine
        inspections_by_query_and_engine = self._split_by_lambda_tuple(
            inspections,
            self._lambda_inspection_source_query_types,
            self._lambda_inspection_source_engines,
        )
        self.stats["inspections_by_query_and_engine"] = _stats_by_group(
            inspections_by_query_and_engine
        )

        # calculate statistics for inspections by source query and language
        inspections_by_query_and_language = self._split_by_lambda_tuple(
            inspections,
            self._lambda_inspection_source_query_types,
            self._lambda_inspection_languages,
        )
        self.stats["inspections_by_query_and_language"] = _stats_by_group(
            inspections_by_query_and_language
        )

        # calculate statistics for inspections by source query and type
        inspections_by_query_and_type = self._split_by_lambda_tuple(
            inspections,
            self._lambda_inspection_source_query_types,
            lambda x: x.type,
        )
        self.stats["inspections_by_query_and_type"] = _stats_by_group(
            inspections_by_query_and_type
        )

    def _stats_for_inspections(self, inspections):
        # filter inspected ones
        inspected = self._get_inspected(inspections)

        # calculate number of inspections
        count = len(inspections)
        inspected_count = len(inspected)
        to_be_inspected_count = count - inspected_count

        # calculate total inspection duration
        total_duration = sum(
            [inspection.result.inspection_duration for inspection in inspected]
        )

        # calculate powerset of engines
        engines = [engine for engine in models.SearchEngine]
        powerset_of_engines = self._get_powerset(engines)

        # count the inspections by engine (powerset: combination of engines as well)
        count_by_engine = {
            frozenset(set_of_engines): self._count_with_source_engines(
                inspections, set_of_engines
            )
            for set_of_engines in powerset_of_engines
        }

        # calculate powerset of languages
        langs = ["python", "java", "js", "php"]
        powerset_of_langs = self._get_powerset(langs)

        # count the inspections by language (powerset: combination of langs as well)
        count_by_language = {
            frozenset(set_of_langs): self._count_with_languages(
                inspections, set_of_langs
            )
            for set_of_langs in powerset_of_langs
        }

        inspection_dates = [
            datetime.fromisoformat(inspection.result.inspection_time)
            for inspection in inspections
            if inspection.was_inspected()
        ]
        if inspection_dates:
            min_inspection_date = min(inspection_dates)
            max_inspection_date = max(inspection_dates)
        else:
            min_inspection_date = None
            max_inspection_date = None

        # calculate inspection speed and estimate how long to finish
        if inspected_count > 0:
            inspection_speed = total_duration / inspected_count
            inspection_estimation = round(inspection_speed * to_be_inspected_count)
        else:
            inspection_speed = 0
            inspection_estimation = 0

        return {
            "count": count,
            "count_by_engine": count_by_engine,
            "count_by_language": count_by_language,
            "inspected_count": inspected_count,
            "inspection_duration": total_duration,
            "inspection_speed": inspection_speed,
            "inspection_estimation": inspection_estimation,
            "min_inspection_date": min_inspection_date,
            "max_inspection_date": max_inspection_date,
        }

    def _print_statistics_for_inspections(self):
        if "inspections" not in self.stats:
            return

        s_all = self.stats["inspections"]

        def _print(stats):
            if s_all.get("count", 0) == 0:
                print("No inspections found")
                return

            google = frozenset([models.SearchEngine.GOOGLE])
            youtube = frozenset([models.SearchEngine.YOUTUBE])
            twitter = frozenset([models.SearchEngine.TWITTER])

            print(
                f"Inspections: {d4(stats['inspected_count'])} / {d4(stats['count'])}"
                f" ({percent(stats['inspected_count'] / stats['count'])} %)"
                f" \t(G: {d4(stats['count_by_engine'][google])}"
                f" | Y: {d4(stats['count_by_engine'][youtube])}"
                f" | T: {d4(stats['count_by_engine'][twitter])})"
            )
            print("")
            print(f"Duration:    {timespan(stats['inspection_duration'])} h")
            print(f"Estimation:  {timespan(stats['inspection_estimation'])} h")
            print(f"Speed:       {round(stats['inspection_speed'])} s/inspection")

        def _print_multiple(stats):
            # sort by title/key
            stats = dict(sorted(stats.items()))

            if len(stats) == 0:
                print("No inspections found")
                return

            # print for each title/key/group
            for title, s_for_group in stats.items():
                if isinstance(title, tuple):
                    title1, title2 = title
                    title = f"{title1} / {title2}"
                print(title)
                print("-" * len(str(title)))
                _print(s_for_group)
                print("")

        print("")
        print("")
        print("===========")
        print("Inspections")
        print("===========")
        _print(s_all)
        if s_all["min_inspection_date"] and s_all["max_inspection_date"]:
            print(f"Min Date:    {s_all['min_inspection_date']}")
            print(f"Max Date:    {s_all['max_inspection_date']}")

        print("")
        print("")
        print("Inspections by Type")
        print("===================")
        _print_multiple(self.stats["inspections_by_type"])

        print("")
        print("")
        print("Inspections by Scope")
        print("====================")
        _print_multiple(self.stats["inspections_by_scope"])

        print("")
        print("")
        print("Inspections by Vulnerable")
        print("===========================")
        _print_multiple(self.stats["inspections_by_vulnerable"])

        print("")
        print("")
        print("Inspections by Vulnerable and Type")
        print("==================================")
        _print_multiple(self.stats["inspections_by_vulnerable_and_type"])

        print("")
        print("")
        print("Inspections by Source Query")
        print("===========================")
        _print_multiple(self.stats["inspections_by_query"])

        print("")
        print("")
        print("Inspections by Source Query and Source Engine")
        print("=============================================")
        _print_multiple(self.stats["inspections_by_query_and_engine"])

        print("")
        print("")
        print("Inspections by Scope and Type")
        print("=============================")
        _print_multiple(self.stats["inspections_by_scope_and_type"])

        print("")
        print("")
        print("Inspections by Scope and Source Engine")
        print("======================================")
        _print_multiple(self.stats["inspections_by_scope_and_engine"])

        print("")
        print("")
        print("Inspections by Source Language")
        print("==============================")
        _print_multiple(self.stats["inspections_by_language"])

        print("")
        print("")
        print("Inspections by Source Engine")
        print("============================")
        for set_of_engines, count in s_all["count_by_engine"].items():
            initials_of_engines = [engine.name[0] for engine in set_of_engines]
            string_of_engines = " + ".join(initials_of_engines) + ":"
            print(f"{string_of_engines: <18} {d4(count)}")

        print("")
        print("")
        print("Inspections by Source Language")
        print("==============================")
        for set_of_langs, count in s_all["count_by_language"].items():
            string_of_langs = " + ".join(set_of_langs) + ":"
            print(f"{string_of_langs: <25} {d4(count)}")

    def _calculate_statistics_for_tutorials(self, tutorials, inspections):
        def _stats_by_group(tutorials_by_group):
            result = defaultdict(dict)
            for group, tutorials_for_group in tutorials_by_group.items():
                result[group] = self._stats_for_tutorials(tutorials_for_group)
            return result

        # calculate statistics for all tutorials
        self.stats["tutorials"] = self._stats_for_tutorials(tutorials)

        # calculate statistics for tutorials by type
        tutorials_by_type = self._split_by_lambda(tutorials, lambda tut: tut.type)
        self.stats["tutorials_by_type"] = _stats_by_group(tutorials_by_type)

        # calculate statistics for tutorials by language
        tutorials_by_lang = self._split_by_lambda(tutorials, lambda tut: tut.language)
        self.stats["tutorials_by_language"] = _stats_by_group(tutorials_by_lang)

        # calculate statistics for tutorials by category
        tutorials_by_cat = self._split_by_lambda(tutorials, lambda tut: tut.subject)
        self.stats["tutorials_by_category"] = _stats_by_group(tutorials_by_cat)

        # calculate statistics for tutorials by source query
        tutorials_by_query = self._split_by_lambda(
            tutorials, partial(self._lambda_tutorial_source_query_types, inspections)
        )
        self.stats["tutorials_by_query"] = _stats_by_group(tutorials_by_query)

        # calculate statistics for tutorials by source query and engine
        tutorials_by_query_and_engine = self._split_by_lambda_tuple(
            tutorials,
            partial(self._lambda_tutorial_source_query_types, inspections),
            partial(self._lambda_tutorial_source_engines, inspections),
        )
        self.stats["tutorials_by_query_and_engine"] = _stats_by_group(
            tutorials_by_query_and_engine
        )

        # calculate statistics for tutorials by source query and language
        tutorials_by_query_and_lang = self._split_by_lambda_tuple(
            tutorials,
            partial(self._lambda_tutorial_source_query_types, inspections),
            lambda tut: tut.language,
        )
        self.stats["tutorials_by_query_and_language"] = _stats_by_group(
            tutorials_by_query_and_lang
        )

        # calculate statistics for tutorials by source query and source query
        tutorials_by_query_and_category = self._split_by_lambda_tuple(
            tutorials,
            partial(self._lambda_tutorial_source_query_types, inspections),
            lambda tut: tut.subject,
        )
        self.stats["tutorials_by_query_and_category"] = _stats_by_group(
            tutorials_by_query_and_category
        )

        # calculate statistics for tutorials by source query and type
        tutorials_by_query_and_type = self._split_by_lambda_tuple(
            tutorials,
            partial(self._lambda_tutorial_source_query_types, inspections),
            lambda tut: tut.type,
        )
        self.stats["tutorials_by_query_and_type"] = _stats_by_group(
            tutorials_by_query_and_type
        )

        # calculate statistics for tutorials by engine
        tutorials_by_engine = self._split_by_lambda(
            tutorials, partial(self._lambda_tutorial_source_engines, inspections)
        )
        self.stats["tutorials_by_engine"] = _stats_by_group(tutorials_by_engine)

        # calculate statistics for tutorials by source query
        tutorials_by_query_string = self._split_by_lambda(
            tutorials, partial(self._lambda_tutorial_source_query_strings, inspections)
        )
        self.stats["tutorials_by_query_string"] = _stats_by_group(
            tutorials_by_query_string
        )

        # calculate statistics for tutorials by source query
        tutorials_by_query_category = self._split_by_lambda(
            tutorials,
            partial(self._lambda_tutorial_source_query_categories, inspections),
        )
        self.stats["tutorials_by_query_category"] = _stats_by_group(
            tutorials_by_query_category
        )

        # calculate statistics for tutorials by source rank
        tutorials_by_rank = self._split_by_lambda(
            tutorials, partial(self._lambda_tutorial_source_rank, inspections)
        )
        self.stats["tutorials_by_rank"] = _stats_by_group(tutorials_by_rank)

        # calculate statistics for tutorials by source rank and source engine
        tutorials_by_engine_and_rank = self._split_by_lambda_tuple(
            tutorials_by_query["subjects"],
            partial(self._lambda_tutorial_source_engines, inspections),
            partial(self._lambda_tutorial_source_rank, inspections),
        )
        self.stats["subject_tutorials_by_engine_and_rank"] = _stats_by_group(
            tutorials_by_engine_and_rank
        )

        import csv

        import pandas as pd

        data = []
        for (engine, rank), tutorials in tutorials_by_engine_and_rank.items():
            for tutorial in tutorials:
                data.append(
                    {
                        "rank": rank,
                        "vulnerable": tutorial.has_vulnerabilities(),
                        "engine": engine,
                    }
                )
        with open("google-ranks.csv", "w") as f:
            writer = csv.DictWriter(f, fieldnames=["rank", "vulnerable"])
            writer.writeheader()
            df = pd.DataFrame(data)
            df = df[df["engine"] == models.SearchEngine.GOOGLE]
            writer.writerows(df[["rank", "vulnerable"]].to_dict("records"))
        with open("youtube-ranks.csv", "w") as f:
            writer = csv.DictWriter(f, fieldnames=["rank", "vulnerable"])
            writer.writeheader()
            df = pd.DataFrame(data)
            df = df[df["engine"] == models.SearchEngine.YOUTUBE]
            writer.writerows(df[["rank", "vulnerable"]].to_dict("records"))
        with open("twitter-ranks.csv", "w") as f:
            writer = csv.DictWriter(f, fieldnames=["rank", "vulnerable"])
            writer.writeheader()
            df = pd.DataFrame(data)
            df = df[df["engine"] == models.SearchEngine.TWITTER]
            writer.writerows(df[["rank", "vulnerable"]].to_dict("records"))

        import csv
        import datetime

        data = []
        for tutorial in tutorials_by_query["subjects"]:
            if tutorial.date:
                data.append(
                    {
                        "date": tutorial.date,
                        "year": datetime.datetime.fromisoformat(tutorial.date).year,
                        "vulnerable": tutorial.has_vulnerabilities(),
                    }
                )
            # else:
            #    data.append({
            #        "date": "nöö",
            #        "year": "",
            #        "vulnerable": tutorial.has_vulnerabilities(),
            #    })
        with open("vulntuts-per-date.csv", "w") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "year", "vulnerable"])
            writer.writeheader()
            writer.writerows(data)

        import csv

        data = []
        for tutorial in tutorials_by_query["subjects"]:
            if tutorial.type == models.TutorialType.VIDEO:
                data.append(
                    {
                        "views": tutorial.video.get("info")
                        .get("statistics")
                        .get("viewCount"),
                        "likes": tutorial.video.get("info")
                        .get("statistics")
                        .get("likeCount"),
                        "vulnerable": tutorial.has_vulnerabilities(),
                    }
                )
        with open("vulntuts-videos-statistics.csv", "w") as f:
            writer = csv.DictWriter(f, fieldnames=["views", "likes", "vulnerable"])
            writer.writeheader()
            writer.writerows(data)

        # calculate statistics for tutorials by source rank
        tutorials_by_rank_page = self._split_by_lambda(
            tutorials, partial(self._lambda_tutorial_source_rank_page, inspections)
        )
        self.stats["tutorials_by_rank_page"] = _stats_by_group(tutorials_by_rank_page)

    def _stats_for_tutorials(self, tutorials):
        # filter vulnerable ones
        vulnerable_tutorials = [
            tutorial for tutorial in tutorials if tutorial.has_vulnerabilities()
        ]
        countermeasures_tutorials = [
            tutorial
            for tutorial in tutorials
            if tutorial.has_vulnerability_countermeasures
        ]
        explanations_tutorials = [
            tutorial
            for tutorial in tutorials
            if tutorial.has_vulnerability_explanations
        ]
        warnings_tutorials = [
            tutorial for tutorial in tutorials if tutorial.has_vulnerability_warning
        ]
        some_measure_tutorials = [
            tutorial
            for tutorial in tutorials
            if tutorial.has_vulnerability_countermeasures
            or tutorial.has_vulnerability_explanations
            or tutorial.has_vulnerability_warning
        ]

        # calculate number of tutorials and vulnerabilities
        inspected_count = len(tutorials)
        vulnerable_count = len(vulnerable_tutorials)
        vulnerabilities_count = sum(
            [len(tutorial.vulnerabilities) for tutorial in vulnerable_tutorials]
        )

        # calculate ratios how often vulnerable tutorials occur per inspections
        if inspected_count > 0:
            vulnerable_per_inspected = vulnerable_count / inspected_count
        else:
            vulnerable_per_inspected = 0

        # calculate ratio how many vulnerabilities a vulnerable tutorial has
        if vulnerable_count > 0:
            vulns_per_vulnerable = vulnerabilities_count / vulnerable_count
        else:
            vulns_per_vulnerable = 0

        return {
            "inspected_count": inspected_count,
            "vulnerable_count": vulnerable_count,
            "vulnerable_per_inspected": vulnerable_per_inspected,
            "vulnerabilities_count": vulnerabilities_count,
            "vulnerabilities_per_vulnerable": vulns_per_vulnerable,
            "countermeasures_count": len(countermeasures_tutorials),
            "explanations_count": len(explanations_tutorials),
            "warnings_count": len(warnings_tutorials),
            "some_measure_count": len(some_measure_tutorials),
        }

    def _print_statistics_for_tutorials(self):  # noqa: max-complexity: 14
        if "tutorials" not in self.stats:
            return

        s_all = self.stats["tutorials"]
        s_page = self.stats["tutorials_by_type"][models.TutorialType.WEBPAGE]
        s_video = self.stats["tutorials_by_type"][models.TutorialType.VIDEO]

        s_insp_all = self.stats["inspections"]
        s_insp_page = self.stats["inspections_by_type"][models.InspectionType.WEBPAGE]
        s_insp_video = self.stats["inspections_by_type"][models.InspectionType.VIDEO]

        def _print(s_tuts, s_insp=None):
            if s_tuts.get("inspected_count", 0) == 0:
                print("No inspected tutorials found")
                return

            if s_insp is not None:
                tutorials_per_inspections = (
                    s_tuts["inspected_count"] / s_insp["inspected_count"]
                )
                vulnerable_per_inspections = (
                    s_tuts["vulnerable_count"] / s_insp["inspected_count"]
                )
                print(
                    f"Tutorials:            {d4(s_tuts['inspected_count'])} /"
                    f" {d4(s_insp['inspected_count'])} inspections"
                    f" ({percent(tutorials_per_inspections)} %)"
                )
                print(
                    f"Vulnerable Tutorials: {d4(s_tuts['vulnerable_count'])} /"
                    f" {d4(s_insp['inspected_count'])} inspections"
                    f" ({percent(vulnerable_per_inspections)} %)"
                )
            print(
                f"Vulnerable Tutorials: {d4(s_tuts['vulnerable_count'])}"
                f" / {d4(s_tuts['inspected_count'])} tutorials  "
                f" ({percent(s_tuts['vulnerable_per_inspected'])} %)"
            )
            print(f"Vulnerabilities:      {d4(s_tuts['vulnerabilities_count'])}")
            print(
                f"Vulnerabilities:      {f2(s_tuts['vulnerabilities_per_vulnerable'])}"
                " / vulnerable tutorial"
            )
            print(f"Countermeasures:      {d4(s_tuts['countermeasures_count'])}")
            print(f"Explanations:         {d4(s_tuts['explanations_count'])}")
            print(f"Warnings:             {d4(s_tuts['warnings_count'])}")
            print(f"Some Measure:         {d4(s_tuts['some_measure_count'])}")

        def _print_groups(s_tuts, length=5):
            # sort by title/key
            s_tuts = dict(sorted(s_tuts.items()))

            if len(s_tuts) == 0:
                print("No inspected tutorials found")
                return

            # print for each title/key/group
            for title, s_for_group in s_tuts.items():
                if isinstance(title, int):
                    title = str(title)
                if isinstance(title, tuple):
                    title1, title2 = title
                    title = f"{title1} / {title2}"

                if s_for_group.get("inspected_count", 0) == 0:
                    print(f"{title: <{length}}: No inspected tutorials found")
                    return

                print(
                    f"{(title + ':'): <{length}} {d4(s_for_group['vulnerable_count'])}"
                    f" / {d4(s_for_group['inspected_count'])} tutorials  "
                    f" ({percent(s_for_group['vulnerable_per_inspected'])} %)"
                )

        def _print_multiple(stats, stats_inspections=None):
            # sort by title/key
            stats = dict(sorted(stats.items()))

            if len(stats) == 0:
                print("No inspected tutorials found")
                return

            # print for each title/key/group
            for s_key, s_for_group in stats.items():
                title = s_key
                if isinstance(title, tuple):
                    title1, title2 = title
                    title = f"{title1} / {title2}"
                print(title)
                print("-" * len(str(title)))
                if stats_inspections:
                    _print(s_for_group, stats_inspections[s_key])
                else:
                    _print(s_for_group)
                print("")

        print("")
        print("")
        print("=========")
        print("Tutorials")
        print("=========")
        _print(s_all, s_insp_all)

        print("")
        print("")
        print("Tutorials by Type")
        print("=================")
        print("Webpages")
        print("-------")
        _print(s_page, s_insp_page)
        print("")
        print("Videos")
        print("------")
        _print(s_video, s_insp_video)

        print("")
        print("")
        print("Tutorials by Language")
        print("=====================")
        _print_multiple(
            self.stats["tutorials_by_language"], self.stats["inspections_by_language"]
        )

        print("")
        print("")
        print("Tutorials by Source Engine")
        print("==========================")
        _print_multiple(self.stats["tutorials_by_engine"])

        print("")
        print("")
        print("Tutorials by Source Query")
        print("=========================")
        _print_multiple(
            self.stats["tutorials_by_query"], self.stats["inspections_by_query"]
        )

        print("")
        print("")
        print("Tutorials by Source Query and Engine")
        print("====================================")
        _print_multiple(
            self.stats["tutorials_by_query_and_engine"],
            self.stats["inspections_by_query_and_engine"],
        )

        print("")
        print("")
        print("Tutorials by Source Query and Language")
        print("======================================")
        _print_multiple(
            self.stats["tutorials_by_query_and_language"],
            self.stats["inspections_by_query_and_language"],
        )

        print("")
        print("")
        print("Tutorials by Source Query and Type")
        print("======================================")
        _print_multiple(
            self.stats["tutorials_by_query_and_type"],
            self.stats["inspections_by_query_and_type"],
        )

        print("")
        print("")
        print("Vulnerable Tutorials by Source Rank")
        print("===================================")
        _print_groups(self.stats["tutorials_by_rank"], length=5)

        print("")
        print("")
        print("Vulnerable Subject-Tutorials by Engine and Source Rank")
        print("======================================================")
        _print_groups(self.stats["subject_tutorials_by_engine_and_rank"], length=5)

        print("")
        print("")
        print("Vulnerable Tutorials by Source Rank Page")
        print("========================================")
        _print_groups(self.stats["tutorials_by_rank_page"], length=5)

        print("")
        print("")
        print("Vulnerable Tutorials by Category")
        print("================================")
        _print_groups(self.stats["tutorials_by_category"], length=24)

        print("")
        print("")
        print("Vulnerable Tutorials by Source Query and Category")
        print("=================================================")
        _print_groups(self.stats["tutorials_by_query_and_category"], length=35)

        print("")
        print("")
        print("Vulnerable Tutorials by Source Query Category")
        print("=============================================")
        _print_groups(self.stats["tutorials_by_query_category"], length=32)

        print("")
        print("")
        print("Vulnerable Tutorials by Source Query String")
        print("===========================================")
        _print_groups(self.stats["tutorials_by_query_string"], length=48)

    def _calculate_statistics_for_vulnerabilities(self, tutorials, inspections):
        def _stats(vulnerabilities):
            vulnerability_count = len(vulnerabilities)
            return {
                "count": vulnerability_count,
            }

        def _stats_by_group(vulns_by_group):
            result = defaultdict(dict)
            for group, vulns_for_group in vulns_by_group.items():
                result[group] = _stats(vulns_for_group)
            return result

        # extract vulnerabilitites
        vulnerabilities = []
        for tutorial in tutorials:
            vulnerabilities.extend(tutorial.vulnerabilities)

        # calculate statistics for all vulnerabilities
        self.stats["vulnerabilities"] = _stats(vulnerabilities)

        # calculate statistics for vulnerabilities by type
        vulnerabilities_by_type = self._split_by_lambda(
            vulnerabilities, lambda vuln: vuln.type
        )
        self.stats["vulnerabilities_by_type"] = _stats_by_group(vulnerabilities_by_type)

        # extract vulnerabilitites from tutorials found by security-related subjects
        tutorials_by_query = self._split_by_lambda(
            tutorials, partial(self._lambda_tutorial_source_query_types, inspections)
        )
        subject_vulnerabilities = []
        for tutorial in tutorials_by_query["subjects"]:
            subject_vulnerabilities.extend(tutorial.vulnerabilities)
        vulnerable_snippet_vulnerabilities = []
        for tutorial in tutorials_by_query["vulnerabilities"]:
            vulnerable_snippet_vulnerabilities.extend(tutorial.vulnerabilities)

        # calculate statistics for vulnerabilities by type
        subject_vulnerabilities_by_type = self._split_by_lambda(
            subject_vulnerabilities, lambda vuln: vuln.type
        )
        self.stats["subject_vulnerabilities_by_type"] = _stats_by_group(
            subject_vulnerabilities_by_type
        )

        # calculate statistics for vulnerabilities by type
        vulnerable_snippet_vulnerabilities_by_type = self._split_by_lambda(
            vulnerable_snippet_vulnerabilities, lambda vuln: vuln.type
        )
        self.stats["vulnerable_snippet_vulnerabilities_by_type"] = _stats_by_group(
            vulnerable_snippet_vulnerabilities_by_type
        )

    def _print_statistics_for_vulnerabilities(self):
        if "vulnerabilities" not in self.stats:
            return

        def _print_groups(s_vulns, length):
            # sort by title/key
            s_vulns = dict(sorted(s_vulns.items()))

            if len(s_vulns) == 0:
                print("No vulnerabilities found")
                return

            # print for each title/key/group
            for title, s_for_group in s_vulns.items():
                if isinstance(title, int):
                    title = str(title)

                if s_for_group.get("count", 0) == 0:
                    print(f"{(title + ':'): <{length}} No vulnerabilities found")
                    return

                print(f"{(title + ':'): <{length}} {d4(s_for_group['count'])}")

        print("")
        print("")
        print("===============")
        print("Vulnerabilities")
        print("===============")

        print("")
        print("All Vulnerabilities")
        print("===================")
        _print_groups(self.stats["vulnerabilities_by_type"], length=35)

        print("")
        print("Vulnerabilities in Subject-Tutorials")
        print("====================================")
        _print_groups(self.stats["subject_vulnerabilities_by_type"], length=35)

        print("")
        print("Vulnerabilities in Vulnerable Snippet-Tutorials")
        print("===============================================")
        _print_groups(
            self.stats["vulnerable_snippet_vulnerabilities_by_type"], length=35
        )

    # -----------------
    # General Utilities
    # -----------------

    def _get_powerset(self, iterable):
        "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
        s = list(iterable)
        return itertools.chain.from_iterable(
            itertools.combinations(s, r) for r in range(len(s) + 1)
        )

    def _split_by_lambda(self, items, lambda_fun):
        items_by_attribute = defaultdict(list)
        for item in items:
            key = lambda_fun(item)
            if isinstance(key, list):
                for key_ in key:
                    items_by_attribute[key_].append(item)
            else:
                items_by_attribute[key].append(item)
        return items_by_attribute

    def _split_by_lambda_tuple(self, items, lambda_fun1, lambda_fun2):
        items_by_attribute = defaultdict(list)
        for item in items:
            key1 = lambda_fun1(item)
            key2 = lambda_fun2(item)

            if not isinstance(key1, list):
                key1 = [key1]
            if not isinstance(key2, list):
                key2 = [key2]

            for key_pair in itertools.product(key1, key2):
                items_by_attribute[key_pair].append(item)
        return items_by_attribute

    # -----------------------------------
    # Utilities to split data into groups
    # -----------------------------------

    def _lambda_inspection_scope(self, inspection):
        if inspection.is_in_scope():
            return "tutorials"
        else:
            if inspection.is_tutorial():
                return ["not-tutorials", "tutorials-not-in-scope"]
            else:
                return "not-tutorials"

    def _lambda_inspection_source_engines(self, inspection):
        result = []
        for engine in models.SearchEngine:
            if inspection.has_source_engine(engine):
                result.append(engine)
        return result

    def _lambda_inspection_source_query_types(self, inspection):
        result = []
        if self._has_string_in_source_query("-vulnerabilities", inspection):
            result.append("vulnerabilities")
        if self._has_string_in_source_query(
            "-subjects", inspection
        ) or self._has_string_in_source_query("-tutorials", inspection):
            result.append("subjects")
        return result

    def _lambda_inspection_languages(self, inspection):
        result = []
        langs = ["python", "java", "js", "php"]
        for lang in langs:
            if self._has_language(inspection, lang):
                result.append(lang)
        return result

    def _lambda_inspection_vulnerable(self, tutorials, inspection):
        if inspection.is_in_scope():
            tutorial = self._find_tutorial(tutorials, inspection.id)
            if tutorial.has_vulnerabilities():
                return "vulnerable-tutorial"
            else:
                return "not-vulnerable-tutorial"
        else:
            return "not-tutorial"

    def _find_tutorial(self, tutorials, tutorial_id):
        for tutorial in tutorials:
            if tutorial.id == tutorial_id:
                return tutorial
        return None

    def _lambda_tutorial_source_engines(self, inspections, tutorial):
        inspection = inspections.get(tutorial.id)
        return self._lambda_inspection_source_engines(inspection)

    def _lambda_tutorial_source_query_types(self, inspections, tutorial):
        inspection = inspections.get(tutorial.id)
        return self._lambda_inspection_source_query_types(inspection)

    def _lambda_tutorial_source_query_strings(self, inspections, tutorial):
        inspection = inspections.get(tutorial.id)
        result = set()
        for source in inspection.sources:
            category = " ".join(
                source.query.string.replace("how to", "howto")
                .replace("getting started", "gettingstarted")
                .replace("for beginners", "forbeginners")
                .split(" ")[1:-1]
            )
            result.add(category)
        return list(result)

    def _lambda_tutorial_source_query_categories(self, inspections, tutorial):
        inspection = inspections.get(tutorial.id)
        result = set()
        for source in inspection.sources:
            category = "-".join(source.query.category.split("-")[1:])
            result.add(category)
        return list(result)

    def _lambda_tutorial_source_rank(self, inspections, tutorial):
        inspection = inspections.get(tutorial.id)
        result = set()
        for source in inspection.sources:
            result.add(source.rank)
        return list(result)

    def _lambda_tutorial_source_rank_page(self, inspections, tutorial):
        inspection = inspections.get(tutorial.id)
        result = set()
        for source in inspection.sources:
            rank_page = ((source.rank - 1) // 10) + 1
            result.add(rank_page)
        return list(result)

    # -------------------------
    # Utilities for Inspections
    # -------------------------

    def _get_inspected(self, inspections):
        # only keep inspections that were inspected
        return [inspection for inspection in inspections if inspection.was_inspected()]

    def _has_string_in_source_query(self, string, inspection):
        for source in inspection.sources:
            if string in source.query.category:
                return True
        return False

    def _count_with_source_engines(self, inspections, engines):
        # iterate over engines and filter inspections
        # (list of inspections gets smaller with every iteration)
        for engine in engines:
            # only keep inspections that have the engine as source
            inspections = [
                inspection
                for inspection in inspections
                if inspection.has_source_engine(engine)
            ]
        return len(inspections)

    def _has_language(self, inspection, language):
        return self._has_languages(inspection, [language])

    def _has_languages(self, inspection, languages):
        # iterate over languages and check for each whether it is contained in the query
        for language in languages:
            has_language = False
            for source in inspection.sources:
                if source.query.category.startswith(f"{language}-"):
                    has_language = True
            if not has_language:
                return False
        return True

    def _count_with_languages(self, inspections, languages):
        return len(
            [
                inspection
                for inspection in inspections
                if self._has_languages(inspection, languages)
            ]
        )


def timespan(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def d4(number):
    return f"{number:4d}"


def d6(number):
    return f"{number:6d}"


def f2(number):
    return f"{number:.2f}"


def percent(number):
    return f"{(number*100):5.1f}"
