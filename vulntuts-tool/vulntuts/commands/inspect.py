import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

import dateparser
from yt_dlp import YoutubeDL

from vulntuts import models, storage
from vulntuts.browser import Browser, start_chromium, stop_chromium
from vulntuts.commands import BaseCommand
from vulntuts.errors import ApiError, InspectionTypeChangedError, InvalidArgumentError
from vulntuts.terminal_ui import TerminalUI
from vulntuts.youtube import YouTubeAPI


class InspectCommand(BaseCommand):
    def get_name(self):
        return "inspect"

    def get_help(self):
        return "Inspect search results manually to identify vulnerable tutorials"

    def uses_config(self):
        return True

    def setup_arguments(self, parser):
        parser.add_argument(
            "--type",
            help="Search result type to be inspected",
            choices=["all", "webpage", "video"],
            default="webpage",
        )
        parser.add_argument(
            "--language",
            help="Programming language to be inspected",
        )
        parser.add_argument(
            "--reinspect",
            help=(
                "Re-inspect all search results that have already been inspected or only"
                " those that have been identified as tutorials. Only basic data is"
                " asked again, vulnerabilities or contact information cannot be added"
                " [default: search-results]"
            ),
            nargs="?",
            choices=["search-results", "tutorials"],
            const="search-results",
        )

    def main(self, args):
        data_dir = args.get("data_dir")
        config = args.get("config", {})
        reinspection_type = args.get("reinspect")
        inspection_language = args.get("language")

        # setup inspection type
        if args.get("type") == "all":
            inspection_type = None
        elif args.get("type") == "webpage":
            inspection_type = models.InspectionType.WEBPAGE
        elif args.get("type") == "video":
            inspection_type = models.InspectionType.VIDEO

        # storage for tutorials
        tutorial_storage = storage.TutorialStorage(data_dir)

        # load inspections to know which what pages need to be inspected
        inspection_storage = storage.InspectionStorage(data_dir)
        inspections = inspection_storage.load_all()

        try:
            # set up thread pool
            executor = ThreadPoolExecutor(max_workers=2)

            # start chromium browser
            chromium_runner = start_chromium(data_dir)
            time.sleep(5)
            browser = Browser()

            inspector = TutorialInspector(
                inspection_storage, tutorial_storage, browser, executor, config
            )
            inspector.inspect(
                inspections,
                inspection_type,
                inspection_language,
                reinspection_type,
            )
        except InvalidArgumentError:
            raise
        except Exception:
            traceback.print_exc()
        finally:
            stop_chromium(chromium_runner)
            executor.shutdown()
            print("Might continue to download videos...")


class TutorialInspector(object):
    def __init__(self, inspection_storage, tutorial_storage, browser, executor, config):
        self.inspection_storage = inspection_storage
        self.tutorial_storage = tutorial_storage
        self.browser = browser
        self.executor = executor
        self.youtube_api = YouTubeAPI(config.get("apis", {}).get("youtube", {}))

    def inspect(
        self, inspections, inspection_type, inspection_language, reinspection_type
    ):
        # filter inspections according to inspection type and reinspection type
        filtered_inspections = self._filter_inspections(
            inspections.values(),
            inspection_type,
            inspection_language,
            reinspection_type,
        )

        for inspection in filtered_inspections:
            try:
                # save start time of inspection
                start_time = time.time()

                # previous result
                prev_result = inspection.result

                # inspect
                result = self._inspect(inspection)

                # measure inspection time
                duration = int(time.time() - start_time)
                print(f"Duration: {duration} s")

                # if first inspection
                if prev_result is None:
                    result.inspection_duration = duration
                # if reinspection
                else:
                    if inspection.has_failed():
                        # I might have found vulnerabilitites before
                        # -> do not use failed result
                        # -> copy previous result that did not fail
                        # -> do not delete tutorial
                        result = prev_result

                    # keep inspection time and add inspection duration
                    result.inspection_time = prev_result.inspection_time
                    result.inspection_duration += duration

                # save inspection result
                inspection.result = result

            except InspectionTypeChangedError:
                # do not save a result
                continue
            except KeyboardInterrupt:
                # stop the loop
                return
            finally:
                # save ALL inspections, not only the filtered ones!
                self.inspection_storage.save(inspections)

    def _filter_inspections(
        self, inspections, inspection_type, inspection_language, reinspection_type
    ):
        if inspection_type is None:
            # copy list of all inspections
            inspections = list(inspections)
        else:
            # filter inspections for type
            inspections = [
                inspection
                for inspection in inspections
                if inspection.type == inspection_type
            ]

        # filter inspections for language
        if inspection_language:
            inspections = [
                inspection
                for inspection in inspections
                if self._has_language(inspection, inspection_language)
            ]

        if reinspection_type is not None:
            # reinspection: retrieve inspections that were already inspected
            inspections = [
                inspection
                for inspection in inspections
                if inspection.was_inspected() and not inspection.has_failed()
            ]

            if reinspection_type == "tutorials":
                inspections = [
                    inspection
                    for inspection in inspections
                    if inspection.result.is_tutorial and inspection.result.is_in_scope
                ]

            return inspections
        else:
            # first inspection: retrieve inspections that were not inspected yet
            return [
                inspection
                for inspection in inspections
                if not inspection.was_inspected()
            ]

    def _has_language(self, inspection, language):
        for source in inspection.sources:
            if source.query.category.startswith(f"{language}-"):
                return True
        return False

    def _inspect(self, inspection):
        url = inspection.url
        tutorial_id = models.create_url_id(url)

        # load or create tutorial object
        if self.tutorial_storage.has_tutorial(tutorial_id):
            tutorial = self.tutorial_storage.load_tutorial(tutorial_id)
        else:
            tutorial = self._construct_tutorial(inspection)

        # open tutorial in browser
        tab = self.browser.create_tab()

        try:
            tab_result = tab.navigate(url, wait=False)
            time.sleep(3)
            if tab_result.failed:
                failed_reason = self._create_failed_reason(tab_result)
                print(f"Inspection failed: {failed_reason}")
                return models.InspectionResult(failed=True, failed_reason=failed_reason)

            # extract last-modified date from headers
            tutorial.set_last_modified(self._extract_last_modified(tab_result.headers))

            # create text-based UI for tutorial
            tutorial_ui = TutorialUI(
                inspection,
                tutorial,
                self._extract_fields_meta(inspection, tab_result.headers),
                tab,
                self.tutorial_storage,
            )
            tutorial_ui.print_header()

            if inspection.was_inspected():
                default_is_tutorial = inspection.result.is_tutorial
                default_is_in_scope = inspection.result.is_in_scope
            else:
                default_is_tutorial = True
                default_is_in_scope = True

            # is tutorial?
            is_tutorial = tutorial_ui.ask_is_tutorial(default=default_is_tutorial)
            if not is_tutorial:
                return models.InspectionResult(is_tutorial=False, is_in_scope=False)

            # is in scope?
            is_in_scope = tutorial_ui.ask_is_in_scope(default=default_is_in_scope)
            if not is_in_scope:
                return models.InspectionResult(is_tutorial=True, is_in_scope=False)

            # analyze tutorial
            tutorial_ui.show_tutorial_ui()

            if tutorial.type == models.TutorialType.VIDEO:
                video_utils = VideoInspectionUtils(
                    self.tutorial_storage, self.executor, self.youtube_api
                )
                video_utils.inspect(tutorial)

            if not inspection.was_inspected():
                self._archive_page(tab, tutorial)
            self.tutorial_storage.save_tutorial(tutorial.id, tutorial)

            return models.InspectionResult(is_tutorial=True, is_in_scope=True)
        finally:
            self.browser.close_tab(tab)

    def _construct_tutorial(self, inspection):
        tutorial = models.Tutorial(inspection.url)

        # set tutorial type
        if inspection.type == models.InspectionType.WEBPAGE:
            tutorial.type = models.TutorialType.WEBPAGE
            if "article:published_time" in inspection.metadata:
                tutorial.date = (
                    dateparser.parse(inspection.metadata.get("article:published_time"))
                    .astimezone()
                    .isoformat()
                )
        elif inspection.type == models.InspectionType.VIDEO:
            tutorial.type = models.TutorialType.VIDEO
            tutorial.author = inspection.metadata.get("channelTitle", None)
            if "publishTime" in inspection.metadata:
                tutorial.date = (
                    dateparser.parse(inspection.metadata.get("publishTime"))
                    .astimezone()
                    .isoformat()
                )

        # extract default subject from inspection
        languages = {
            "php": 0,
            "python": 0,
            "java": 0,
            "js": 0,
        }
        for source in inspection.sources:
            if source.query.category.startswith("php-"):
                languages["php"] += 1
            elif source.query.category.startswith("python-"):
                languages["python"] += 1
            elif source.query.category.startswith("java-"):
                languages["java"] += 1
            elif source.query.category.startswith("js-"):
                languages["js"] += 1
        tutorial.language = max(languages, key=languages.get)

        return tutorial

    def _create_failed_reason(self, tab_result):
        if tab_result.failed_exception:
            return f"{tab_result.failed_reason} ({tab_result.failed_exception})"
        else:
            return tab_result.failed_reason

    def _extract_fields_meta(self, inspection, headers):
        meta_date = [
            (key, dateparser.parse(value))
            for key, value in inspection.metadata.items()
            if "date" in key.lower() or "time" in key.lower()
        ]
        header_last_modified = self._extract_last_modified(headers)
        if header_last_modified:
            meta_date.append(("last-modified", header_last_modified))
        meta_author = [
            (key, value)
            for key, value in inspection.metadata.items()
            if "author" in key.lower()
        ]
        meta_twitter = [
            (key, value)
            for key, value in inspection.metadata.items()
            if "twitter:site" in key.lower() or "twitter:creator" in key.lower()
        ]

        return {
            "date": meta_date,
            "author": meta_author,
            "contact": meta_twitter,
        }

    def _extract_last_modified(self, headers):
        header_last_modified = headers.get("last-modified", None)
        if header_last_modified:
            return dateparser.parse(header_last_modified)
        return None

    def _archive_page(self, tab, tutorial):
        # archive webpage
        print("Archiving webpage...")
        screenshot = tab.take_screenshot()
        snapshot = tab.take_snapshot()
        html = tab.get_html()

        # save data
        print("Saving data...")
        self.tutorial_storage.save_screenshot(tutorial.id, screenshot, "screenshot")
        self.tutorial_storage.save_snapshot(tutorial.id, snapshot, "archive")
        self.tutorial_storage.save_html(tutorial.id, html, "html")


class VideoInspectionUtils(object):
    def __init__(self, tutorial_storage, executor, youtube_api):
        self.tutorial_storage = tutorial_storage
        self.executor = executor
        self.youtube_api = youtube_api

    def inspect(self, tutorial):
        # create directory to save data for tutorial to
        tutorial_dir = self.tutorial_storage.create_tutorial_dir(tutorial.id)

        # download subtitles and audio in background
        self.executor.submit(self.download_sub_titles, tutorial.url, tutorial_dir)
        self.executor.submit(self.download_audio, tutorial.url, tutorial_dir)

        # if the tutorial is a youtube video, retrieve its metadata to be able to
        # check during scanning later if the description or video was changed
        domain, id_ = models.create_domain_id_tuple(tutorial.url)
        if domain == "youtube.com":
            try:
                video_info = self.youtube_api.get_video_info(id_)
                views = video_info.get("statistics").get("viewCount")
            except ApiError:
                video_info = {}
                views = None

            try:
                video_comments = self.youtube_api.get_video_comments(id_)
                creator_comments = self.youtube_api.filter_comments_for_author(
                    video_comments,
                    video_info.get("snippet").get("channelId"),
                )
            except ApiError:
                creator_comments = []

            tutorial.video = {
                "info": video_info,
                "creator_comments": creator_comments,
                "views": views,
            }

        # # extract view count
        # node_id = tab.get_node_id_by_selector(".view-count2")
        # if node_id:
        #     view_count_str = tab.get_text_of_node(node_id)
        #     digits = re.findall(r"\d+", view_count_str)
        #     print(f"Views (HTML): {int(''.join(digits))}")
        #     tutorial.video = {
        #         "views": int("".join(digits)),
        #     }

    def download_sub_titles(self, url, tutorial_dir):
        # subtitles: auto
        ydl_opts = {
            "skip_download": True,
            "writeautomaticsub": True,
            "quiet": True,
            "noprogress": True,
            "outtmpl": os.path.join(tutorial_dir, "video-subtitles-auto.%(ext)s"),
        }
        self._youtube_dl(ydl_opts, url)

        # subtitles: manual
        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "subtitleslangs": ["en", "de"],
            "quiet": True,
            "noprogress": True,
            "outtmpl": os.path.join(tutorial_dir, "video-subtitles.%(ext)s"),
        }
        self._youtube_dl(ydl_opts, url)

    def download_audio(self, url, tutorial_dir):
        ydl_opts = {
            "format": "bestaudio",
            "quiet": True,
            "noprogress": True,
            "outtmpl": os.path.join(tutorial_dir, "video-audio.%(ext)s"),
        }
        self._youtube_dl(ydl_opts, url)

    def _youtube_dl(self, ydl_opts, url):
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])


class TutorialUI(TerminalUI):
    def __init__(self, inspection, tutorial, field_metadata, tab, tutorial_storage):
        self.inspection = inspection
        self.tutorial = tutorial
        self.field_metadata = field_metadata
        self.tab = tab
        self.tutorial_storage = tutorial_storage

    def _print_meta(self, field_name):
        if not self.field_metadata or field_name not in self.field_metadata:
            return
        for key, value in self.field_metadata.get(field_name):
            if value:
                print(f"> {key:<25}: {value}")

    def print_header(self):
        print("")
        print("========================================")
        print(self.tutorial.id)
        print(self.tutorial.url)

        print("---")
        for source in self.inspection.sources:
            print(
                f"{source.engine.name}:"
                f" {source.query.string} ({source.rank}) [{source.query.category}]"
            )
        print("---")

    def ask_is_tutorial(self, default=True):
        return self._ask_for_boolean("Is programming tutorial?", default=default)

    def ask_is_in_scope(self, default=True):
        return self._ask_for_boolean("Is in scope?", default=default)

    def show_tutorial_ui(self):
        # tutorial type
        prev_type = self.tutorial.type
        self.tutorial.type = self._ask_for_enum(
            "Type", models.TutorialType, default=self.tutorial.type
        )
        if self.tutorial.type != prev_type:
            self.inspection.type = models.InspectionType.from_tutorial_type(
                self.tutorial.type
            )
            raise InspectionTypeChangedError(
                f"Inspection type of inspection with id '{self.inspection.id}' changed."
            )

        # language
        self.tutorial.language = self._ask_for_string(
            "Language", default=self.tutorial.language
        )

        if not self.inspection.was_inspected():
            self._ask_for_vulnerabilities()

        # set defaults
        if self.inspection.was_inspected():
            has_vuln_countermeasures = self.tutorial.has_vulnerability_countermeasures
            has_vuln_explanations = self.tutorial.has_vulnerability_explanations
            has_vuln_warning = self.tutorial.has_vulnerability_warning
            tutorial_subject = self.tutorial.subject
        else:
            has_vuln_countermeasures = False
            has_vuln_explanations = False
            has_vuln_warning = False
            tutorial_subject = models.TutorialSubject.OTHER

        if has_vuln_countermeasures is None:
            has_vuln_countermeasures = False
        if has_vuln_explanations is None:
            has_vuln_explanations = False
        if has_vuln_warning is None:
            has_vuln_warning = False

        # measures against vulnerabilities / addresses vulnerabilities
        self.tutorial.has_vulnerability_countermeasures = self._ask_for_boolean(
            "Takes measures against vulnerabilities?",
            default=has_vuln_countermeasures,
        )
        self.tutorial.has_vulnerability_explanations = self._ask_for_boolean(
            "Explains vulnerabilities?",
            default=has_vuln_explanations,
        )
        self.tutorial.has_vulnerability_warning = self._ask_for_boolean(
            "Has warning about vulnerabilities?",
            default=has_vuln_warning,
        )

        # tutorial subject
        self.tutorial.subject = self._ask_for_enum(
            "Tutorial Subject",
            models.TutorialSubject,
            default=tutorial_subject,
        )

        # date
        self._print_meta("date")
        self.tutorial.date = self._ask_for_date("Date", default=self.tutorial.date)

        if self.tutorial.has_vulnerabilities() and not self.inspection.was_inspected():
            self._ask_for_author_and_contact()

    def _ask_for_vulnerabilities(self):
        while self._ask_loop("Security Vulnerability", default=False):
            # add vulnerability to tutorial
            self.tutorial.add_vulnerability(self._ask_for_vulnerability())

    def _ask_for_author_and_contact(self):
        # author
        self._print_meta("author")
        self.tutorial.author = self._ask_for_string(
            "Author", default=self.tutorial.author
        )

        # contact
        while self._ask_loop("Contact", default=True):
            self.tutorial.add_contact(self._ask_for_contact())

    def _ask_for_vulnerability(self):
        # ask for basic fields of vulnerability
        vulnerability = models.Vulnerability(
            models.create_vulnerability_id(),
            self._ask_for_enum(
                "Vulnerability Type",
                models.VulnerabilityType,
                default=models.VulnerabilityType.A03_89,  # SQLI
            ),
            self._ask_for_string("Description"),
            self._ask_for_text("Code"),
            self._ask_for_string("Language", default=self.tutorial.language),
        )

        # ask for line number
        print("Please enter the line number(s).")
        print(self._insert_line_numbers(vulnerability.code))
        vulnerability.line_numbers = self._ask_for_string("Line number(s)")

        # if video, ask for the timestamp
        if self.tutorial.type == models.TutorialType.VIDEO:
            vulnerability.video_timestamp = self._ask_for_string("Video Timestamp")

        # let user select the container and retrieve metadata
        print("Please select the node containing the vulnerability.")
        selected_backend_node = self._ask_user_for_node()
        vulnerability.html_attributes = self.tab.get_attributes_of_backend_node(
            selected_backend_node
        )
        vulnerability.html_selectors = self.tab.get_unique_selectors_of_backend_node(
            selected_backend_node
        )
        vulnerability.html_outer = self.tab.get_html_of_backend_node(
            selected_backend_node
        )
        vulnerability.html_text = self.tab.get_text_of_backend_node(
            selected_backend_node
        )
        vulnerability.html_scroll = self.tab.get_scroll_percentage()

        # take screenshot of the selected container
        screenshot = self.tab.take_screenshot_of_backend_node(selected_backend_node)
        self.tutorial_storage.save_screenshot(
            self.tutorial.id, screenshot, f"screenshot-{vulnerability.id}"
        )

        return vulnerability

    def _ask_for_contact(self):
        self._print_meta("contact")
        return models.Contact(
            self._ask_for_enum(
                "Contact Type",
                models.ContactType,
                default=models.ContactType.EMAIL,
            ),
            self._ask_for_enum(
                "Contact Party",
                models.ContactParty,
                default=models.ContactParty.AUTHOR,
            ),
            self._ask_for_string("Contact Details"),
        )

    def _insert_line_numbers(self, text):
        lines = text.split("\n")
        numbered_lines = [f"{n:03d} {line}" for n, line in enumerate(lines, start=1)]
        return "\n".join(numbered_lines)

    def _ask_user_for_node(self):
        self.tab.start_node_selection()
        return self.tab.get_selected_backend_node()
