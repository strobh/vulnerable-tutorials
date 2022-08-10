import time
import traceback

import dateparser
from bs4 import BeautifulSoup, NavigableString

from vulntuts import models, storage, terminal_ui
from vulntuts.browser import Browser, start_chromium, stop_chromium
from vulntuts.commands import BaseCommand
from vulntuts.errors import ApiError, InvalidArgumentError
from vulntuts.youtube import YouTubeAPI


class ScanCommand(BaseCommand):
    def get_name(self):
        return "scan"

    def get_help(self):
        return (
            "Scan vulnerable tutorials automatically and try to determine whether the"
            " vulnerabilities that were previously identified during the inspection"
            " were fixed"
        )

    def uses_config(self):
        return True

    def setup_arguments(self, parser):
        parser.add_argument(
            "--manu",
            help=(
                "Scan vulnerable tutorials manually instead, i.e., the user manually"
                " determines whether the vulnerabilities were fixed"
            ),
            action="store_true",
        )
        parser.add_argument(
            "--final",
            help=(
                "Inspect vulnerable tutorials for the last time to determine if the"
                " vulnerability was fixed and how it was fixed."
            ),
            action="store_true",
        )

    def main(self, args):
        data_dir = args.get("data_dir")
        config = args.get("config", {})
        if args.get("final"):
            args["manu"] = True

        try:
            # initialize storage
            tutorial_storage = storage.TutorialStorage(data_dir)
            scan_storage = storage.ScanStorage(data_dir)
            experiment_storage = storage.ExperimentStorage(data_dir)
            experiment = experiment_storage.load_experiment()

            # start chromium browser
            chromium_runner = start_chromium(data_dir)
            time.sleep(5)
            browser = Browser()

            tutorial_scanner = TutorialScanner(
                tutorial_storage, scan_storage, browser, config
            )
            tutorial_scanner.scan(
                experiment.vulnerable_tutorials, args.get("manu"), args.get("final")
            )
        except InvalidArgumentError:
            raise
        except Exception:
            traceback.print_exc()
        finally:
            stop_chromium(chromium_runner)


class TutorialScanner(object):
    def __init__(self, tutorial_storage, scan_storage, browser, config):
        self.tutorial_storage = tutorial_storage
        self.scan_storage = scan_storage
        self.browser = browser
        self.youtube_api = YouTubeAPI(config.get("apis", {}).get("youtube", {}))

    def scan(self, vulnerable_tutorials, mode_manu, mode_final):
        scan_results = self.scan_storage.load_all()

        # load vulnerable tutorials
        for tutorial in vulnerable_tutorials:
            print("")
            print("========================================")
            print(tutorial.url)

            scan_results_for_tutorial = [
                scan_result
                for scan_result in scan_results
                if tutorial.id == scan_result.tutorial_id
            ]
            latest_scan_result = self._get_latest_scan_result(scan_results_for_tutorial)

            try:
                tab = self.browser.create_tab()
                self._scan(tutorial, latest_scan_result, tab, mode_manu, mode_final)
            except KeyboardInterrupt:
                break
            finally:
                self.browser.close_tab(tab)

    def _get_latest_scan_result(self, scan_results):
        sorted_results = sorted(
            scan_results, key=lambda x: x.get_datetime(), reverse=True
        )
        return sorted_results[0] if sorted_results else None

    def _scan(self, tutorial, latest_scan_result, tab, mode_manu, mode_final):
        # if (
        #     latest_scan_result.failed
        #     or (
        #         tutorial.type == models.TutorialType.WEBPAGE
        #         and not latest_scan_result.are_all_vulnerabilities_contained()
        #     )
        #     or (
        #         tutorial.type == models.TutorialType.VIDEO
        #         and latest_scan_result.has_video_changed()
        #     )
        # )

        # create scan result
        scan_id = models.create_scan_id()
        if mode_final:
            scan_type = "final"
        elif mode_manu:
            scan_type = "manu"
        else:
            scan_type = "auto"
        scan_result = models.ScanResult(
            id=scan_id, tutorial_id=tutorial.id, type=scan_type
        )

        # open tutorial in browser
        if mode_final:
            tab_result = tab.navigate(tutorial.url, wait=True, timeout=30)
        else:
            tab_result = tab.navigate(tutorial.url, wait=True)
        time.sleep(2)

        # get status code and failures
        scan_result.status_code = tab_result.status_code
        if tab_result.failed:
            scan_result.failed = True
            scan_result.failed_reason = (
                f"{tab_result.failed_reason} ({tab_result.failed_exception})"
                if tab_result.failed_exception
                else tab_result.failed_reason
            )
            # if final scan: check why it failed
            if mode_final:
                scan_result.vulnerabilities = self._check_remediation_if_failed(
                    tutorial, scan_result.status_code, scan_result.failed_reason
                )
            self.scan_storage.save_scan_result(tutorial.id, scan_id, scan_result)
            return

        # extract last-modified date from headers
        last_modified = self._extract_last_modified(tab_result.headers)
        if last_modified:
            scan_result.set_last_modified(last_modified)

        # extract html
        html = tab.get_html()

        # check if vulnerabilities are still contained
        if mode_manu:
            scan_result.vulnerabilities = self._check_vulnerabilities_manually(
                tutorial, latest_scan_result, tab, mode_final
            )
        else:
            scan_result.vulnerabilities = self._check_vulnerabilities_automatically(
                html, tutorial
            )

        # check if the tutorial is a youtube video
        # if yes, retrieve metadata and check if the description or video was changed
        domain, id_ = models.create_domain_id_tuple(tutorial.url)
        if domain == "youtube.com":
            try:
                scan_result.video = self._check_youtube_video_changed(id_, tutorial)
            except ApiError as e:
                scan_result.failed = True
                scan_result.failed_reason = str(e)

        # archive webpage
        print("Archiving webpage...")
        screenshot = tab.take_screenshot()
        snapshot = tab.take_snapshot()

        # save data
        print("Saving data...")
        self.scan_storage.save_screenshot(
            tutorial.id, scan_id, screenshot, "screenshot"
        )
        self.scan_storage.save_snapshot(tutorial.id, scan_id, snapshot, "archive")
        self.scan_storage.save_html(tutorial.id, scan_id, html, "html")
        self.scan_storage.save_scan_result(tutorial.id, scan_id, scan_result)

    def _extract_last_modified(self, headers):
        header_last_modified = headers.get("last-modified", None)
        if header_last_modified:
            return dateparser.parse(header_last_modified)
        return None

    def _check_vulnerabilities_automatically(self, html, tutorial):
        soup = BeautifulSoup(html, "html.parser")

        vulnerabilities = {}
        for vulnerability in tutorial.vulnerabilities:
            html_contained = self._check_html_contained(html, vulnerability.html_outer)

            selector_contained = {
                "id": None,
                "class": None,
                "attributes": None,
            }

            selectors = vulnerability.html_selectors
            if selectors.get("unique_id"):
                res = soup.find(id=selectors.get("unique_id"))
                if res:
                    selector_contained["id"] = True
                else:
                    selector_contained["id"] = False
            if selectors.get("unique_class_combination"):
                classes = selectors.get("unique_class_combination").split()
                selector = selectors.get("name").lower() + ".".join(classes)
                selector_contained["class"] = self._check_selector_contained(
                    soup, selector
                )
            if selectors.get("unique_attribute_selector"):
                selector_contained["attributes"] = self._check_selector_contained(
                    soup, selectors.get("unique_attribute_selector")
                )

            vulnerabilities[vulnerability.id] = {
                "html_contained": html_contained,
                "selector_contained": selector_contained,
            }
        return vulnerabilities

    def _check_html_contained(self, html, html_test):
        # first check if direct match is contained
        if html_test in html:
            return True

        # otherwise remove root and check again
        return self._get_html_without_root(html_test) in self._normalize_html(html)

    def _get_html_without_root(self, html):
        soup = BeautifulSoup(html, "html.parser")
        element = next(soup.children)
        while True:
            if isinstance(element, NavigableString):
                # https://stackoverflow.com/a/22699187
                return element.output_ready(formatter="html").strip().encode("utf-8")
            non_space_childs = [
                child for child in element.children if not str(child).isspace()
            ]
            if len(non_space_childs) == 1:
                element = non_space_childs[0]
            else:
                # return inner HTML
                return element.encode_contents(
                    encoding="utf-8", formatter="html"
                ).strip()

    def _normalize_html(self, html):
        soup = BeautifulSoup(html, "html.parser")
        return soup.encode(encoding="utf-8", formatter="html")

    def _check_selector_contained(self, soup, selector):
        try:
            res = soup.select(selector)
            if res:
                return True
            else:
                return False
        except Exception:
            return None

    def _check_vulnerabilities_manually(
        self, tutorial, latest_scan_result, tab, ask_for_fix
    ):
        vulnerabilities = {}
        for vulnerability in tutorial.vulnerabilities:
            tab.scroll_to_percentage(vulnerability.html_scroll)
            print(f"Type: {vulnerability.type}")
            print(f"Details: {vulnerability.details}")
            if vulnerability.html_scroll:
                print(f"Scroll: {vulnerability.html_scroll}")
            print("Code:")
            print(vulnerability.code)
            self._print_latest_scan_result(latest_scan_result, tutorial, vulnerability)

            ui = terminal_ui.TerminalUI()
            is_contained = ui._ask_for_boolean("Is vulnerability contained?")

            vuln_result = {
                "manu_contained": is_contained,
            }

            if ask_for_fix:
                if is_contained:
                    vuln_result["remediation"] = None
                else:
                    vuln_result["remediation"] = ui._ask_for_enum(
                        "Remediation",
                        models.RemediationType,
                        default=models.RemediationType.FIXED_CORRECTLY,
                    )

            vulnerabilities[vulnerability.id] = vuln_result

        return vulnerabilities

    def _check_remediation_if_failed(self, tutorial, status_code, failed_reason):
        if status_code == "404":
            remediation = models.RemediationType.DELETED
        else:
            ui = terminal_ui.TerminalUI()
            print(f"Failure: {failed_reason}")
            remediation = ui._ask_for_enum(
                "Remediation",
                models.RemediationType,
                default=models.RemediationType.OFFLINE,
            )

        vulnerabilities = {}
        for vulnerability in tutorial.vulnerabilities:
            vulnerabilities[vulnerability.id] = {
                "manu_contained": False,
                "remediation": remediation,
            }

        return vulnerabilities

    def _print_latest_scan_result(self, latest_scan_result, tutorial, vulnerability):
        if latest_scan_result.failed:
            print(f"Latest Scan: failed ({latest_scan_result.failed_reason})")
        else:
            if tutorial.type == models.TutorialType.WEBPAGE:
                latest_result_str = (
                    "contained"
                    if latest_scan_result.is_vulnerability_contained(vulnerability.id)
                    else "not contained"
                )
                print(f"Latest Scan: {latest_result_str}")
            elif tutorial.type == models.TutorialType.VIDEO:
                latest_result_str = (
                    "video has changed"
                    if latest_scan_result.has_video_changed()
                    else "video has not changed"
                )
                print(f"Latest Scan: {latest_result_str}")

    def _check_youtube_video_changed(self, video_id, tutorial):
        prev_video_info = tutorial.video.get("info")
        prev_creator_comments = tutorial.video.get("creator_comments")

        # retrieve video info
        try:
            video_info = self.youtube_api.get_video_info(video_id)

            # check if something has changed
            snippet_changed = video_info.get("snippet") != prev_video_info.get(
                "snippet"
            )
            content_changed = video_info.get("contentDetails") != prev_video_info.get(
                "contentDetails"
            )
        except ApiError:
            video_info = {}
            snippet_changed = None
            content_changed = None

        # retrieve comments
        try:
            video_comments = self.youtube_api.get_video_comments(video_id)
            creator_comments = self.youtube_api.filter_comments_for_author(
                video_comments,
                video_info.get("snippet").get("channelId"),
            )

            # check if something has changed
            comments_changed = creator_comments != prev_creator_comments
        except ApiError:
            creator_comments = []
            comments_changed = None

        return {
            "info": video_info,
            "creator_comments": creator_comments,
            "has_changed": {
                "snippet": snippet_changed,
                "content_details": content_changed,
                "creator_comments": comments_changed,
            },
        }
