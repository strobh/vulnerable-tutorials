import hashlib
import tldextract
import yaml

from enum import Enum
from urllib.parse import urlparse


def create_id(url):
    domain = urlparse(url).netloc
    domain = tldextract.extract(domain).registered_domain # first-level
    path = urlparse(url).path
    path_md5 = hashlib.md5(path.encode('utf-8')).hexdigest()
    return f"{domain}-{path_md5[:8]}"


def enum_representer(dumper, data):
    enum_tag = type(data).__name__
    return dumper.represent_scalar(f"!{enum_tag}", str(data.name))

yaml.add_multi_representer(Enum, enum_representer)


class TutorialType(Enum):
    WEBSITE = 1
    VIDEO = 2


class ContactType(Enum):
    NONE = 0
    MAIL = 1
    CONTACT_FORM = 2
    ON_SITE = 3
    TWITTER = 4
    OTHER = 5


class ContactParty(Enum):
    NONE = 0
    AUTHOR = 1
    WEBSITE_OWNER = 2


class VulnerabilityType(Enum):
    SQLI = 1
    SQLI_NO_PREPARED = 2
    STORED_XSS = 3
    REFLECTED_XSS = 4
    CLEARTEXT_PW = 5
    INSECURE_PW_HASHING = 6
    BROKEN_ACCESS_CONTROL = 7


class Tutorial(yaml.YAMLObject):
    yaml_tag = '!Tutorial'
    yaml_loader = yaml.SafeLoader

    def __init__(self, url):
        self.url = url

        self.type = None
        self.is_video = None
        self.date = None
        self.author = None
        self.views = None

        self.contact_type = None
        self.contact_party = None
        self.contact_details = None

        self.is_security_relevant = False
        self.is_security_relevant_details = None
        self.vulnerabilities = []

    def add_vulnerability(self, vulnerability):
        self.vulnerabilities.append(vulnerability)

    def get_id(self):
        return create_id(self.url)


class Vulnerability(yaml.YAMLObject):
    yaml_tag = '!Vulnerability'
    yaml_loader = yaml.SafeLoader

    def __init__(self, type, details, code):
        self.type = type
        self.details = details
        self.code = code


class WebpageInspection(yaml.YAMLObject):
    yaml_tag = '!WebpageInspection'
    yaml_loader = yaml.SafeLoader

    def __init__(self, id, url, is_tutorial, is_video, time, duration):
        self.id = id
        self.url = url
        self.is_tutorial = is_tutorial
        self.is_video = is_video

        self.inspection_time = time
        self.inspection_duration = duration


class WebSearch(yaml.YAMLObject):
    yaml_tag = '!WebSearch'
    yaml_loader = yaml.SafeLoader

    def __init__(self, query, search_time):
        self.query = query
        self.items = []
        self.search_time = search_time

    def add_item(self, item):
        self.items.append(item)


class SearchItem(yaml.YAMLObject):
    yaml_tag = '!SearchItem'
    yaml_loader = yaml.SafeLoader

    def __init__(self, rank, title, url, snippet, metadata):
        self.rank = rank
        self.url = url
        self.title = title
        self.snippet = snippet
        self.metadata = metadata
