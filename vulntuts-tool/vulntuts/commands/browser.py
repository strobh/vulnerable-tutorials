import time

from vulntuts import models, storage
from vulntuts.browser import Browser, is_chromium_running, start_chromium, stop_chromium
from vulntuts.commands import BaseCommand
from vulntuts.errors import InvalidArgumentError


class BrowserCommand(BaseCommand):
    def get_name(self):
        return "open-browser"

    def get_help(self):
        return (
            "Open browser with vulntuts' browser profile, e.g., to install extensions"
        )

    def setup_arguments(self, parser):
        parser.add_argument(
            "--tutorial",
            metavar="URL_OR_ID",
            help="Open tutorial in browser tab",
        )

    def main(self, args):
        data_dir = args.get("data_dir")
        tab = None
        try:
            # start chromium browser
            print("Press CTRL+C to stop chromium.")
            chromium_runner = start_chromium(data_dir)
            time.sleep(5)

            if args.get("tutorial"):
                browser = Browser()
                tab = browser.create_tab()
                tab.navigate(self._get_url(args.get("tutorial"), data_dir), wait=False)

            while is_chromium_running(chromium_runner):
                time.sleep(1)
        except KeyboardInterrupt:
            return
        finally:
            if tab:
                browser.close_tab(tab)
            stop_chromium(chromium_runner)

    def _get_url(self, url_or_id, data_dir):
        # initialize storage
        inspection_storage = storage.InspectionStorage(data_dir)
        inspections = inspection_storage.load_all()

        if url_or_id in inspections:
            tutorial_id = url_or_id
        elif models.create_url_id(url_or_id) in inspections:
            tutorial_id = models.create_url_id(url_or_id)
        else:
            raise InvalidArgumentError("Inspection/Tutorial does not exist")

        return inspections.get(tutorial_id).url
