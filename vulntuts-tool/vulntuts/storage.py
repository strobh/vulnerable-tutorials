import base64
import csv
import datetime
import json
import os
import re
import shutil
from dataclasses import asdict
from enum import Enum
from pathlib import Path

import unidecode
from dacite import Config, from_dict

from vulntuts import models

CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.yaml")
QUERIES_CONFIG_FILE = os.path.join(CONFIG_DIR, "queries.yaml")

SUGGESTIONS_DIR = "term-suggestions"
QUERIES_DIR = "search-queries"
RESULTS_DIR = "search-results"
TUTORIALS_DIR = "tutorials"
REPORTS_DIR = "reports"
NOTIFICATION_REPORTS_DIR = "notification-reports"
FULL_REPORTS_DIR = "full-reports"
MESSAGES_DIR = "messages"
NOTIFICATIONS_DIR = "notifications"
REMINDERS_DIR = "reminders"
DEBRIEFINGS_DIR = "debriefings"
SCANS_DIR = "scans"

INSPECTIONS_FILE = "inspections.json"
SAMPLING_METADATA_FILE = "sampling-metadata.json"
VULNTUTS_FILE = "vulnerable-tutorials.json"
EXPERIMENT_FILE = "experiment.json"
CONTACTS_FILE_JSON = "contacts.json"
CONTACTS_FILE_CSV = "contacts.csv"
RESULTS_FILE_JSON = "results.json"
RESULTS_FILE_CSV = "results.csv"


class BaseStorage(object):
    def __init__(self, data_dir=None):
        self.data_dir = data_dir

    def _generate_path(self, dir_or_file):
        return os.path.join(self.data_dir, dir_or_file)

    def _generate_backup_name(self):
        return f"backup-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"

    def _find_files_with_ext(self, dir_path, search_ext):
        result = []
        for cur_path, _, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(cur_path, file)
                file_ext = Path(file_path).suffix
                if file_ext == search_ext:
                    result.append(file_path)
        return result

    def _find_files_with_name(self, dir_path, search_name):
        result = []
        for cur_path, _, files in os.walk(dir_path):
            for file in files:
                if file == search_name:
                    file_path = os.path.join(cur_path, file)
                    result.append(file_path)
        return result

    def _load_json(self, file_path, default=None, default_factory=None, fail=False):
        if os.path.isfile(file_path):
            with open(file_path, "r") as file:
                return json.load(file)
        elif fail:
            raise ValueError(f"File '{file_path}' does not exist")
        else:
            if default_factory is not None:
                return default_factory()
            else:
                return default

    def _load_list(self, file_path):
        if os.path.isfile(file_path):
            with open(file_path, "r") as file:
                lines = file.readlines()
                return [line.rstrip() for line in lines]
        else:
            raise ValueError(f"File '{file_path}' does not exist")

    def _load_txt(self, file_path):
        if os.path.isfile(file_path):
            with open(file_path, "r") as file:
                return file.read()
        else:
            raise ValueError(f"File '{file_path}' does not exist")

    def _save_json(self, data, file_path, convert=False):
        if convert:
            data = self._convert_to_dict(data)
        with open(file_path, "w") as file:
            json.dump(data, file, indent=2)

    def _save_list(self, data, file_path):
        with open(file_path, "w") as file:
            for row in data:
                file.write(f"{row}\n")

    def _save_csv(self, data, file_path, convert=False):
        if convert:
            data = self._convert_to_dict(data)
        if not data:
            return
        keys = data[0].keys()
        with open(file_path, "w") as file:
            dict_writer = csv.DictWriter(file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(data)

    def _convert_to_dict(self, data):
        if isinstance(data, list):
            return [self._convert_to_dict(item) for item in data]
        elif isinstance(data, dict):
            return {key: self._convert_to_dict(value) for (key, value) in data.items()}
        else:
            return asdict(data)

    def _convert_to_dataclass_dict(self, data_class, data):
        return {
            key: from_dict(
                data_class=data_class, data=value, config=Config(cast=[Enum])
            )
            for (key, value) in data.items()
        }

    def _convert_to_dataclass_dict_of_list(self, data_class, data):
        return {
            key: [
                from_dict(data_class=data_class, data=item, config=Config(cast=[Enum]))
                for item in items
            ]
            for (key, items) in data.items()
        }

    def _convert_to_dataclass(self, data_class, data):
        return from_dict(data_class=data_class, data=data, config=Config(cast=[Enum]))


class JSONFileLoadingIterator(BaseStorage):
    def __init__(self, filepaths, data_class):
        self.idx = 0
        self.filepaths = filepaths
        self.data_class = data_class

    def __iter__(self):
        return self

    def __next__(self):
        self.idx += 1
        try:
            filepath = self.filepaths[self.idx - 1]
            return self._load(filepath)
        except IndexError:
            self.idx = 0
            raise StopIteration

    def _load(self, filepath):
        data = super()._load_json(filepath, fail=True)
        return super()._convert_to_dataclass(self.data_class, data)


class SearchQueryStorage(BaseStorage):
    file_ext = ".txt"

    def __init__(self, data_dir):
        super().__init__(data_dir)
        self.dir_queries = super()._generate_path(QUERIES_DIR)

    def create_backup(self):
        if not os.path.isdir(self.dir_queries):
            return
        dir_backup = f"{self.dir_queries}.{super()._generate_backup_name()}"
        os.rename(self.dir_queries, dir_backup)

    def load_all(self):
        category_filepaths = super()._find_files_with_ext(
            self.dir_queries, SearchQueryStorage.file_ext
        )
        queries = list()
        for category_filepath in category_filepaths:
            category_name = Path(category_filepath).stem
            queries_in_category = self._transform_search_queries(
                category_name, self._load_search_queries(category_filepath)
            )
            queries.extend(queries_in_category)
        return queries

    def _load_search_queries(self, file_name):
        with open(file_name, "r") as file:
            search_queries = file.readlines()
            search_queries = [line.rstrip() for line in search_queries]
            return search_queries

    def save(self, category, queries):
        Path(self.dir_queries).mkdir(parents=True, exist_ok=True)
        file_path = self._build_file_path(category)
        super()._save_list(queries, file_path)

    def _build_file_path(self, category_name):
        file_name = category_name + SearchQueryStorage.file_ext
        return os.path.join(self.dir_queries, file_name)

    def _transform_search_queries(self, category_name, queries):
        return [
            models.SearchQuery(category=category_name, string=query)
            for query in queries
        ]


class SuggestionStorage(SearchQueryStorage):
    def __init__(self, data_dir):
        super().__init__(data_dir)
        self.dir_queries = super()._generate_path(SUGGESTIONS_DIR)


class SearchResultStorage(BaseStorage):
    file_ext = ".json"

    def __init__(self, data_dir):
        super().__init__(data_dir)
        self.dir_results = super()._generate_path(RESULTS_DIR)

    def create_backup(self):
        if not os.path.isdir(self.dir_results):
            return
        dir_backup = f"{self.dir_results}.{super()._generate_backup_name()}"
        os.rename(self.dir_results, dir_backup)

    def load_all(self, engine=None):
        dir_results = self._build_dir_path(engine)
        return JSONFileLoadingIterator(
            super()._find_files_with_ext(dir_results, SearchResultStorage.file_ext),
            data_class=models.SearchResult,
        )

    def was_searched(self, engine, query):
        if isinstance(query, models.SearchQuery):
            query = query.string
        file_path = self._build_file_path(engine, query)
        return os.path.isfile(file_path)

    def save(self, search_result):
        file_path = self._build_file_path(
            search_result.engine, search_result.query.string
        )
        Path(self._build_dir_path(search_result.engine)).mkdir(
            parents=True, exist_ok=True
        )
        super()._save_json(search_result, file_path, convert=True)

    def _build_file_path(self, engine, query):
        q_dash = self._normalize_string(query)
        file_name = q_dash + SearchResultStorage.file_ext
        return os.path.join(self._build_dir_path(engine), file_name)

    def _normalize_string(self, s):
        # transliterate unicode characters to ascii text
        s = unidecode.unidecode(s)
        # remove non-alphanumeric characters
        s = re.sub(r"[^A-Za-z0-9]+", "-", s)
        # replace multiple dashes with single dash
        return re.sub(r"[\-]+", "-", s)

    def _build_dir_path(self, engine):
        if engine:
            return os.path.join(self.dir_results, engine.lower())
        else:
            return self.dir_results


class SamplingMetadataStorage(BaseStorage):
    def __init__(self, data_dir):
        super().__init__(data_dir)
        self.file_path = super()._generate_path(SAMPLING_METADATA_FILE)

    def load_all(self):
        data = super()._load_json(self.file_path)
        if data:
            return super()._convert_to_dataclass(models.SamplingMetadata, data)
        else:
            return models.SamplingMetadata()

    def save(self, sampling_metadata):
        super()._save_json(sampling_metadata, self.file_path, convert=True)


class InspectionStorage(BaseStorage):
    def __init__(self, data_dir):
        super().__init__(data_dir)
        self.file_path = super()._generate_path(INSPECTIONS_FILE)

    def create_backup(self):
        if not os.path.isfile(self.file_path):
            return
        file_name = Path(self.file_path).stem
        file_suffix = Path(self.file_path).suffix
        file_backup = f"{file_name}.{super()._generate_backup_name()}{file_suffix}"
        os.rename(self.file_path, file_backup)

    def load_all(self):
        data = super()._load_json(self.file_path, default_factory=dict)
        return super()._convert_to_dataclass_dict(models.Inspection, data)

    def save(self, inspections):
        super()._save_json(inspections, self.file_path, convert=True)


class TutorialStorage(BaseStorage):
    file_name = "data.json"

    def __init__(self, data_dir):
        super().__init__(data_dir)
        self.dir_tutorials = super()._generate_path(TUTORIALS_DIR)

    def load_all(self):
        return JSONFileLoadingIterator(
            super()._find_files_with_name(
                self.dir_tutorials, TutorialStorage.file_name
            ),
            data_class=models.Tutorial,
        )

    def load_tutorial(self, tutorial_id):
        dir_tutorial = self._build_dir_path(tutorial_id)
        file_path = os.path.join(dir_tutorial, TutorialStorage.file_name)
        if not os.path.isfile(file_path):
            raise ValueError(f"Tutorial with id #{tutorial_id} does not exist")
        data = super()._load_json(file_path, fail=True)
        return super()._convert_to_dataclass(models.Tutorial, data)

    def has_tutorial(self, tutorial_id):
        dir_tutorial = self._build_dir_path(tutorial_id)
        file_path = os.path.join(dir_tutorial, TutorialStorage.file_name)
        return os.path.isfile(file_path)

    def save_snapshot(self, tutorial_id, snapshot, name):
        dir_tutorial = self.create_tutorial_dir(tutorial_id)
        with open(os.path.join(dir_tutorial, f"{name}.mhtml"), "w") as file:
            file.write(snapshot)

    def save_screenshot(self, tutorial_id, screenshot, name):
        dir_tutorial = self.create_tutorial_dir(tutorial_id)
        with open(os.path.join(dir_tutorial, f"{name}.png"), "wb") as file:
            file.write(base64.b64decode(screenshot))

    def save_html(self, tutorial_id, html, name):
        dir_tutorial = self.create_tutorial_dir(tutorial_id)
        with open(os.path.join(dir_tutorial, f"{name}.html"), "w") as file:
            file.write(html)

    def save_tutorial(self, tutorial_id, tutorial):
        dir_tutorial = self.create_tutorial_dir(tutorial_id)
        file_path = os.path.join(dir_tutorial, TutorialStorage.file_name)
        super()._save_json(tutorial, file_path, convert=True)

    def create_tutorial_dir(self, tutorial_id):
        dir_tutorial = self._build_dir_path(tutorial_id)
        Path(dir_tutorial).mkdir(parents=True, exist_ok=True)
        return dir_tutorial

    def _build_dir_path(self, tutorial_id):
        return os.path.join(self.dir_tutorials, tutorial_id)


class ExperimentStorage(BaseStorage):
    def __init__(self, data_dir):
        super().__init__(data_dir)
        self.file_path = super()._generate_path(EXPERIMENT_FILE)
        self.tutorial_storage = TutorialStorage(data_dir)

    def create_backup(self):
        if not os.path.isfile(self.file_path):
            return
        file_name = Path(self.file_path).stem
        file_suffix = Path(self.file_path).suffix
        file_backup = f"{file_name}.{super()._generate_backup_name()}{file_suffix}"
        os.rename(self.file_path, file_backup)

    def load_experiment(self):
        data = super()._load_json(self.file_path, fail=True)
        # load vulnerable tutorials by list of IDs
        data["vulnerable_tutorials"] = [
            self.tutorial_storage.load_tutorial(tutorial_id)
            for tutorial_id in data["vulnerable_tutorials"]
        ]
        return super()._convert_to_dataclass(models.Experiment, data)

    def save(self, experiment):
        # convert vulnerable tutorials to list of IDs
        experiment.vulnerable_tutorials = [
            tutorial.id for tutorial in experiment.vulnerable_tutorials
        ]
        super()._save_json(experiment, self.file_path, convert=True)


class ContactStorage(BaseStorage):
    def __init__(self, data_dir):
        super().__init__(data_dir)
        self.file_path_json = super()._generate_path(CONTACTS_FILE_JSON)
        self.file_path_csv = super()._generate_path(CONTACTS_FILE_CSV)

    def create_backup(self):
        self._create_backup(self.file_path_json)
        self._create_backup(self.file_path_csv)

    def _create_backup(self, file_path):
        if not os.path.isfile(file_path):
            return
        file_name = Path(file_path).stem
        file_suffix = Path(file_path).suffix
        file_backup = f"{file_name}.{super()._generate_backup_name()}{file_suffix}"
        os.rename(file_path, file_backup)

    def load_contacts(self):
        data = super()._load_json(self.file_path_json, default_factory=dict)
        return super()._convert_to_dataclass_dict_of_list(models.Contact, data)

    def save(self, contacts):
        super()._save_json(contacts, self.file_path_json, convert=True)
        super()._save_csv(self._convert_to_csv(contacts), self.file_path_csv)

    def _convert_to_csv(self, contacts):
        csv_data = []
        for tutorial_id, contacts_for_tutorial in contacts.items():
            for contact in contacts_for_tutorial:
                row_data = {"tutorial": tutorial_id}
                row_data.update(super()._convert_to_dict(contact))
                csv_data.append(row_data)
        return csv_data


class ReportStorage(BaseStorage):
    def __init__(self, data_dir):
        super().__init__(data_dir)
        self.dir_reports = super()._generate_path(REPORTS_DIR)

    def create_backup(self):
        if not os.path.isdir(self.dir_reports):
            return
        dir_backup = f"{self.dir_reports}.{super()._generate_backup_name()}"
        os.rename(self.dir_reports, dir_backup)

    def save_notification_report(self, report_id, report):
        self._save_report(NOTIFICATION_REPORTS_DIR, report_id, report)

    def save_full_report(self, report_id, report):
        self._save_report(FULL_REPORTS_DIR, report_id, report)

    def _save_report(self, reports_subdir, report_id, report):
        reports_dir = os.path.join(self.dir_reports, reports_subdir)
        Path(reports_dir).mkdir(parents=True, exist_ok=True)
        file_path = self._build_report_path(reports_dir, report_id)
        with open(file_path, "w") as file:
            file.write(report)

    def _build_report_path(self, reports_dir, report_id):
        return os.path.join(reports_dir, f"{report_id}.html")

    def copy_to_reports_dir(self, source_dir):
        self._copy_to_reports_dir(NOTIFICATION_REPORTS_DIR, source_dir)
        self._copy_to_reports_dir(FULL_REPORTS_DIR, source_dir)

    def _copy_to_reports_dir(self, reports_subdir, source_dir):
        reports_dir = os.path.join(self.dir_reports, reports_subdir)
        dest_dir = os.path.join(reports_dir, os.path.basename(source_dir))
        shutil.copytree(source_dir, dest_dir)


class MessageType(Enum):
    NOTIFICATION = "NOTIFICATION"
    REMINDER = "REMINDER"
    DEBRIEFING = "DEBRIEFING"


class MessageStorage(BaseStorage):
    def __init__(self, data_dir):
        super().__init__(data_dir)
        self.dir_messages = super()._generate_path(MESSAGES_DIR)

    def create_backup(self):
        if not os.path.isdir(self.dir_messages):
            return
        dir_backup = f"{self.dir_messages}.{super()._generate_backup_name()}"
        os.rename(self.dir_messages, dir_backup)

    def load_message(self, tutorial_id, message_type):
        file_path = self._build_message_path(tutorial_id, message_type)
        if not os.path.isfile(file_path):
            raise ValueError(
                f"Message for tutorial with id #{tutorial_id} does not exist"
            )
        return super()._load_txt(file_path)

    def save_message(self, tutorial_id, message, message_type):
        file_path = self._build_message_path(tutorial_id, message_type, create_dir=True)
        with open(file_path, "w") as file:
            file.write(message)

    def save_mailmerge(self, data, message_type):
        file_path = self._build_mailmerge_path(message_type, create_dir=True)
        super()._save_csv(data, file_path)

    def _build_message_path(self, tutorial_id, message_type, create_dir=False):
        return os.path.join(
            self._build_dir_path(message_type, create_dir), f"{tutorial_id}.txt"
        )

    def _build_mailmerge_path(self, message_type, create_dir=False):
        return os.path.join(
            self._build_dir_path(message_type, create_dir), "_mailmerge.csv"
        )

    def _build_dir_path(self, message_type, create_dir):
        if message_type == MessageType.NOTIFICATION:
            dir_path = os.path.join(self.dir_messages, NOTIFICATIONS_DIR)
        elif message_type == MessageType.REMINDER:
            dir_path = os.path.join(self.dir_messages, REMINDERS_DIR)
        elif message_type == MessageType.DEBRIEFING:
            dir_path = os.path.join(self.dir_messages, DEBRIEFINGS_DIR)
        else:
            raise ValueError(f"Invalid message type '{message_type}'")
        if create_dir:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        return dir_path


class ScanStorage(BaseStorage):
    file_name = "data.json"

    def __init__(self, data_dir):
        super().__init__(data_dir)
        self.dir_scans = super()._generate_path(SCANS_DIR)

    def load_all(self):
        return JSONFileLoadingIterator(
            super()._find_files_with_name(self.dir_scans, ScanStorage.file_name),
            data_class=models.ScanResult,
        )

    def save_snapshot(self, tutorial_id, scan_id, snapshot, name):
        dir_scan = self.create_scan_dir(tutorial_id, scan_id)
        with open(os.path.join(dir_scan, f"{name}.mhtml"), "w") as file:
            file.write(snapshot)

    def save_screenshot(self, tutorial_id, scan_id, screenshot, name):
        dir_scan = self.create_scan_dir(tutorial_id, scan_id)
        with open(os.path.join(dir_scan, f"{name}.png"), "wb") as file:
            file.write(base64.b64decode(screenshot))

    def save_html(self, tutorial_id, scan_id, html, name):
        dir_scan = self.create_scan_dir(tutorial_id, scan_id)
        with open(os.path.join(dir_scan, f"{name}.html"), "w") as file:
            file.write(html)

    def save_scan_result(self, tutorial_id, scan_id, scan_result):
        dir_scan = self.create_scan_dir(tutorial_id, scan_id)
        file_path = os.path.join(dir_scan, "data.json")
        super()._save_json(scan_result, file_path, convert=True)

    def create_scan_dir(self, tutorial_id, scan_id):
        dir_scan = self._build_dir_path(tutorial_id, scan_id)
        Path(dir_scan).mkdir(parents=True, exist_ok=True)
        return dir_scan

    def _build_dir_path(self, tutorial_id, scan_id):
        return os.path.join(self.dir_scans, tutorial_id, scan_id)


class ResultStorage(BaseStorage):
    def __init__(self, data_dir):
        super().__init__(data_dir)
        self.file_path_json = super()._generate_path(RESULTS_FILE_JSON)
        self.file_path_csv = super()._generate_path(RESULTS_FILE_CSV)

    def create_backup(self):
        self._create_backup(self.file_path_json)
        self._create_backup(self.file_path_csv)

    def _create_backup(self, file_path):
        if not os.path.isfile(file_path):
            return
        file_name = Path(file_path).stem
        file_suffix = Path(file_path).suffix
        file_backup = f"{file_name}.{super()._generate_backup_name()}{file_suffix}"
        os.rename(file_path, file_backup)

    def save(self, results):
        super()._save_json(results, self.file_path_json, convert=True)
        super()._save_csv(self._convert_to_csv(results), self.file_path_csv)

    def _convert_to_csv(self, results):
        csv_data = []
        for tutorial_id, result_for_tutorial in results.items():
            row = super()._convert_to_dict(result_for_tutorial)
            row["group_coding"] = self._get_coding_for_group(result_for_tutorial.group)
            csv_data.append(self._process_csv_row(row))
        return csv_data

    def _get_coding_for_group(self, group):
        if group == models.ExperimentGroup.SUPPORT_NONE:
            return 1
        elif group == models.ExperimentGroup.SUPPORT_REASON:
            return 2
        elif group == models.ExperimentGroup.SUPPORT_EXPLANATION:
            return 3
        elif group == models.ExperimentGroup.SUPPORT_INDIVIDUAL:
            return 4
        elif group == models.ExperimentGroup.CONTROL_GROUP:
            return 0

    def _process_csv_row(self, csv_data):
        result = {}
        for key, value in csv_data.items():
            if isinstance(value, bool):
                result[key] = int(value)
            else:
                result[key] = value
        return result
