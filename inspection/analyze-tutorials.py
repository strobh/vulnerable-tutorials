import dateparser
import datetime
import os
import pprint
import signal
import subprocess
import sys
import time
import traceback
import yaml
import youtube_dl

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import models

from browser import Browser, Tab, Webpage


class TutorialEntryMask:
    def __init__(self, tutorial, field_metadata):
        self.tutorial = tutorial
        self.field_metadata = field_metadata

    def print_header(self):
        print("")
        print("========================================")
        print(self.tutorial.url)

    def ask_is_tutorial(self):
        return self._ask_for_boolean('Is tutorial?', default=True)

    def ask_is_video(self):
        self.tutorial.is_video = self._ask_for_boolean('Is video?', default=False)
        return self.tutorial.is_video

    def show_entry_mask(self):
        self.tutorial.type = models.TutorialType.WEBSITE
        self.tutorial.is_security_relevant = self._ask_for_boolean('Security Relevant?', default=True)
        if self.tutorial.is_security_relevant:
            self._print_meta('date')
            self.tutorial.date = self._ask_for_date('Date')
            self._print_meta('author')
            self.tutorial.author = self._ask_for_string('Author')
            self._print_meta('contact')
            self.tutorial.contact_type = self._ask_for_enum('Contact Type', models.ContactType, default=models.ContactType.MAIL)
            if self.tutorial.contact_type != models.ContactType.NONE:
                self.tutorial.contact_party = self._ask_for_enum('Contact Party', models.ContactParty, default=models.ContactParty.AUTHOR)
                self.tutorial.contact_details = self._ask_for_string('Contact Details')
            while self._ask_loop('Security Vulnerability'):
                vulnerability = models.Vulnerability(
                    self._ask_for_enum('Vulnerability Type', models.VulnerabilityType, default=models.VulnerabilityType.SQLI),
                    self._ask_for_string('Vulnerability Details'),
                    self._ask_for_multiline_string('Code'))
                self.tutorial.add_vulnerability(vulnerability)
        else:
            self.tutorial.is_security_relevant_details = self._ask_for_string('Security Relevance Details')
        return self.tutorial

    def _print_meta(self, field_name):
        if not field_name in self.field_metadata:
            return
        for key, value in self.field_metadata.get(field_name):
            if value:
                print(f"> {key:<25}: {value}")
    
    def _ask_for_date(self, field_name, default=None):
        if default:
            answer = input(f"{field_name} [{default}]: ")
        else:
            answer = input(f"{field_name}: ")
        date = dateparser.parse(answer)
        if date:
            return date.astimezone().isoformat()
        else:
            return default

    def _ask_for_string(self, field_name, default=''):
        if default:
            answer = input(f"{field_name} [{default}]: ")
        else:
            answer = input(f"{field_name}: ")
        return answer if answer else default

    def _ask_for_multiline_string(self, field_name, default=''):
        text = ''
        print(f'{field_name} [stop with "end"]: ')
        i = 0
        while True:
            line = input()
            if line == 'end' or (i == 0 and line == ''):
                break
            text += line + "\n"
            i += 1
        text = text.rstrip("\n")
        return text if text else default

    def _ask_for_enum(self, field_name, enum_class, default):
        if not isinstance(default, enum_class):
            raise ValueError("Given default is not an intance of the enum")
        for enum_item in enum_class:
            print(f"[{enum_item.value}] {enum_item.name}")
        answer = input(f"{field_name} [{default.value}/{default.name}]: ")
        if answer and self._has_enum_value(enum_class, int(answer)):
            return enum_class(int(answer))
        else:
            return default

    def _ask_for_boolean(self, field_name, default=True):
        default_text = "y" if default else "n"
        answer = input(f'{field_name} (y,n) [{default_text}]: ')
        answer = answer.lower()

        if answer == '1' or answer == 'y' or answer == 'yes':
            return True
        elif answer == '0' or answer == 'n' or answer == 'no':
            return False
        else:
            return default

    def _ask_loop(self, name):
        return self._ask_for_boolean(f'Next {name}?', default=False)

    def _has_enum_value(self, enum_class, value):
        values = set(enum_item.value for enum_item in enum_class)
        return value in values


def download_sub_titles(url, tutorial_dir, executor):
    # subtitles: auto
    ydl_opts = {
        'skip_download': True,
        'writeautomaticsub': True,
        'quiet': True,
        'outtmpl': os.path.join(tutorial_dir, 'video-subtitles-auto.%(ext)s')
    }
    executor.submit(_youtube_dl, ydl_opts, url)

    # subtitles: manual
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'subtitleslangs': ['en', 'de'],
        'quiet': True,
        'outtmpl': os.path.join(tutorial_dir, 'video-subtitles.%(ext)s')
    }
    executor.submit(_youtube_dl, ydl_opts, url)


def download_audio(url, tutorial_dir, executor):
    ydl_opts = {
        'format': 'bestaudio',
        'quiet': True,
        'outtmpl': os.path.join(tutorial_dir, 'video-audio.%(ext)s')
    }
    executor.submit(_youtube_dl, ydl_opts, url)


def _youtube_dl(ydl_opts, url):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


class WebpageInspections:
    def __init__(self, filename):
        self.filename = filename
        self.inspections = dict()

    def was_inspected(self, url):
        return models.create_id(url) in self.inspections

    def add_inspection(self, url, is_tutorial, is_video, duration):
        tutorial_id = models.create_id(url)
        self.inspections[tutorial_id] = models.WebpageInspection(
            tutorial_id, url, is_tutorial, is_video,
            datetime.datetime.now().astimezone().isoformat(), duration)

    def get_inspection(self, url):
        return self.inspections.get(models.create_id(url), None)

    def load(self):
        if os.path.isfile(self.filename):
            with open(self.filename, 'r') as file:
                self.inspections = yaml.safe_load(file)

    def save(self):
        with open(self.filename, 'w') as file:
            yaml.dump(self.inspections, file)


class WebSearchesIterator(object):
    def __init__(self, web_search_files):
        self.idx = 0
        self.web_search_files = web_search_files

    def __iter__(self):
        return self

    def __next__(self):
        self.idx += 1
        try:
            web_search_file = self.web_search_files[self.idx-1]
            return self._load_web_search(web_search_file)
        except IndexError:
            self.idx = 0
            raise StopIteration

    def _load_web_search(self, filename):
        with open(filename, 'r') as file:
            return yaml.safe_load(file)


class WebSearches:
    def __init__(self, dirname):
        self.dirname = dirname
        self.web_search_files = list()
        self.cur_index = 0

    def load(self):
        self.web_search_files = [os.path.join(self.dirname, file)
            for file in os.listdir(self.dirname)
            if os.path.isfile(os.path.join(self.dirname, file)) and \
                Path(os.path.join(self.dirname, file)).suffix == '.yaml']

    def __iter__(self):
       return WebSearchesIterator(self.web_search_files)


data_dir = 'data'
inspections_file = os.path.join(data_dir, 'webpages.yaml')
tutorials_dir = os.path.join(data_dir, 'tutorials')
web_searches_dir = os.path.join(data_dir, 'search-results', 'google')


if __name__ == '__main__':
    try:
        # start chromium browser
        chromium_runner = subprocess.Popen(["./run-chromium.sh"], 
            start_new_session=True)
        time.sleep(3)
        browser = Browser()

        # load inspections to know which pages have already been inspected
        inspections = WebpageInspections(inspections_file)
        inspections.load()

        # load search results to know which pages to inspect
        web_searches = WebSearches(web_searches_dir)
        web_searches.load()

        with ThreadPoolExecutor(max_workers=2) as executor:
            for web_search in web_searches:
                for search_item in web_search.items:
                    url = search_item.url

                    # was the webpage already inspected?
                    if inspections.was_inspected(url):
                        continue

                    try:
                        tutorial = models.Tutorial(url)
                        tutorial_id = tutorial.get_id()

                        # open tutorial in browser
                        start_time = time.time()
                        tab = browser.create_tab()
                        webpage = tab.navigate(url, wait=False)

                        # get fields from metadata
                        meta_date = [
                            (key, dateparser.parse(value))
                            for key, value
                            in search_item.metadata.items()
                            if 'date' in key.lower() or 'time' in key.lower()]
                        header_last_modified = webpage.headers.get('last-modified', None)
                        if header_last_modified:
                            meta_date.append(('last-modified', dateparser.parse(header_last_modified)))
                        meta_author = [
                            (key, value)
                            for key, value
                            in search_item.metadata.items()
                            if 'author' in key.lower()]
                        meta_twitter = [
                            (key, value)
                            for key, value
                            in search_item.metadata.items()
                            if 'twitter:site' in key.lower() or 'twitter:creator' in key.lower()]

                        field_metadata = {
                            'date': meta_date,
                            'author': meta_author,
                            'contact': meta_twitter,
                        }

                        # create console-based entry mask
                        tem = TutorialEntryMask(tutorial, field_metadata)
                        tem.print_header()

                        # is tutorial?
                        is_tutorial = tem.ask_is_tutorial()
                        if not is_tutorial:
                            # save inspection
                            duration = int(time.time() - start_time)
                            inspections.add_inspection(url, is_tutorial, None, duration)
                            continue

                        # directory to save data for tutorial to
                        tutorial_dir = os.path.join(tutorials_dir, tutorial_id)
                        Path(tutorial_dir).mkdir(parents=True, exist_ok=True)

                        # is video?
                        is_video = tem.ask_is_video()
                        if is_video:
                            # save inspection
                            duration = int(time.time() - start_time)
                            inspections.add_inspection(url, is_tutorial, is_video, duration)
                            download_sub_titles(url, tutorial_dir, executor)
                            download_audio(url, tutorial_dir, executor)
                            continue

                        # analyze tutorial
                        tem.show_entry_mask()

                        # archive webpage
                        print("Archiving webpage...")
                        webpage.take_screenshot('screenshot')
                        webpage.capture_snapshot()

                        # save data
                        print("Saving data...")
                        webpage.save_screenshots(tutorial_dir)
                        webpage.save_snapshot(tutorial_dir)
                        with open(os.path.join(tutorial_dir, 'data.yaml'), 'w') as file:
                            yaml.dump(vars(tutorial), file)

                        # save inspection
                        duration = int(time.time() - start_time)
                        inspections.add_inspection(url, is_tutorial, is_video, duration)
                    except KeyboardInterrupt:
                        break
                    finally:
                        browser.close_tab(tab)
                        inspections.save()
                else:
                    # continue if innter loop was not broken
                    continue 
                # inner loop was broken, break the outer loop
                break

    except Exception:
        traceback.print_exc()
    finally:
        # close chromium
        chromium_runner.send_signal(signal.SIGINT)
        chromium_runner.wait()
        time.sleep(1)
