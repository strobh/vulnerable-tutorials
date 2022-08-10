import datetime
import hashlib
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import tldextract


def create_url_id(url):
    domain, id_ = create_domain_id_tuple(url)
    return f"{domain}-{id_}"


def create_domain_id_tuple(url):
    domain = extract_first_level_domain(url)
    url_parts = urlparse(url)
    path = url_parts.path
    query = url_parts.query

    # if youtube, use video id
    if domain == "youtube.com" and path == "/watch":
        video_id = parse_qs(query).get("v")[0]
        return (domain, video_id)
    else:
        path_md5 = hashlib.md5(path.encode("utf-8")).hexdigest()
        return (domain, path_md5[:8])


def extract_domain(url):
    url_parts = urlparse(url)
    return url_parts.netloc


def extract_first_level_domain(url):
    domain = extract_domain(url)
    return tldextract.extract(domain).registered_domain


def create_vulnerability_id():
    return str(uuid.uuid4())


def create_report_id(tutorial_id):
    return hashlib.md5(tutorial_id.encode("utf-8")).hexdigest()


def create_scan_id():
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%d-%H-%M-%S")


def datetime_now_isoformat():
    return datetime.datetime.now().astimezone().isoformat()


class SearchEngine(str, Enum):
    GOOGLE = "GOOGLE"
    YOUTUBE = "YOUTUBE"
    TWITTER = "TWITTER"


class InspectionType(str, Enum):
    WEBPAGE = "WEBPAGE"
    VIDEO = "VIDEO"

    @staticmethod
    def from_tutorial_type(tutorial_type):
        return __class__(tutorial_type.value)


class TutorialType(str, Enum):
    WEBPAGE = "WEBPAGE"
    VIDEO = "VIDEO"

    @staticmethod
    def from_inspection_type(inspection_type):
        return __class__(inspection_type.value)


class TutorialSubject(str, Enum):
    A01_ACCESS_CONTROL = "A01_ACCESS_CONTROL"
    A01_FILE_FOR_DOWNLOAD = "A01_FILE_FOR_DOWNLOAD"
    A01_TEMP_FILE = "A01_TEMP_FILE"
    A01_REDIRECT = "A01_REDIRECT"

    A02_ENCRYPTION = "A02_ENCRYPTION"
    A02_SIGNATURE = "A02_SIGNATURE"
    A02_MAC = "A02_MAC"
    A02_HASH = "A02_HASH"
    A02_PASSWORD_HASH = "A02_PASSWORD_HASH"
    A02_RANDOM = "A02_RANDOM"

    A03_PAGE_GENERATION = "A03_PAGE_GENERATION"
    A03_VALIDATION = "A03_VALIDATION"
    A03_DATABASE = "A03_DATABASE"
    A03_COMMAND = "A03_COMMAND"
    A03_SEND_EMAIL = "A03_SEND_EMAIL"
    A03_CONTACT_FORM = "A03_CONTACT_FORM"
    A03_SEARCH_FORM = "A03_SEARCH_FORM"
    A03_WEB_FORM = "A03_WEB_FORM"
    A03_XPATH = "A03_XPATH"

    A07_LOGIN_REGISTRATION = "A07_LOGIN_REGISTRATION"
    A07_AUTHENTICATION = "A07_AUTHENTICATION"
    A07_CHANGE_PASSWORD = "A07_CHANGE_PASSWORD"
    A07_FORGOT_PASSWORD = "A07_FORGOT_PASSWORD"
    A07_SESSION = "A07_SESSION"

    A04_FILE_UPLOAD = "A04_FILE_UPLOAD"
    A05_XML_ENTITY = "A05_XML_ENTITY"
    A08_DESERIALIZATION = "A08_DESERIALIZATION"
    A09_LOGGING = "A09_LOGGING"

    BASIC_TUTORIAL = "BASIC_TUTORIAL"
    NETWORK_REQUEST = "NETWORK_REQUEST"
    MULTITHREADING = "MULTITHREADING"
    COOKIES = "COOKIES"
    SERIALIZATION = "SERIALIZATION"

    OTHER = "OTHER"


class ContactType(str, Enum):
    EMAIL = "EMAIL"
    CONTACT_FORM = "CONTACT_FORM"
    ON_SITE = "ON_SITE"
    COMMENT_SECTION = "COMMENT_SECTION"
    TWITTER = "TWITTER"
    FACEBOOK = "FACEBOOK"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    PHONE = "PHONE"
    POSTAL_MAIL = "POSTAL_MAIL"
    OTHER = "OTHER"


class ContactParty(str, Enum):
    AUTHOR = "AUTHOR"
    WEBSITE = "WEBSITE"


class VulnerabilityType(str, Enum):
    A01_22 = "PATH_TRAVERSAL"  # OWASP-A01:2021, CWE-22 (CWE-23)
    A01_284 = "BROKEN_ACCESS_CONTROL"  # OWASP-A01:2021, CWE-284
    A01_219 = "SENSITIVE_FILE_UNDER_WEB_ROOT"  # OWASP-A01:2021, CWE-219 (CWE-552)
    A01_352 = "CSRF"  # OWASP-A01:2021, CWE-352
    A01_601 = "OPEN_REDIRECT"  # OWASP-A01:2021, CWE-601
    A01_377 = "INSECURE_TEMPORARY_FILE"  # OWASP-A01:2021, CWE-377

    A02_327 = "BROKEN_CRYPTO"  # OWASP-A02:2021, CWE-327
    A02_328 = "WEAK_HASH"  # OWASP-A02:2021, CWE-328
    A02_916 = "INSECURE_PW_HASHING"  # OWASP-A02:2021, CWE-916 (CWE-759/CWE-760/CWE-261)
    A02_760 = "FIXED_SALT"  # OWASP-A02:2021, CWE-760
    A02_330 = "INSECURE_RANDOM"  # OWASP-A02:2021, CWE-330

    A03_89 = "SQLI"  # OWASP-A03:2021, CWE-89
    A03_79_REFLECTED = "REFLECTED_XSS"  # OWASP-A03:2021, CWE-79 (type 1)
    A03_79_STORED = "STORED_XSS"  # OWASP-A03:2021, CWE-79 (type 2)
    A03_79_MAIL = "STORED_XSS_IN_MAIL"  # OWASP-A03:2021, CWE-79 (email)
    A03_93 = "CRLF_INJECTION"  # OWASP-A03:2021, CWE-93
    A03_93_MAIL = "CRLF_INJECTION_IN_MAIL"  # OWASP-A03:2021, CWE-93
    A03_77 = "COMMAND_INJECTION"  # OWASP-A03:2021, CWE-77
    A03_91 = "XML_INJECTION"  # OWASP-A03:2021, CWE-91
    A03_643 = "XPATH_INJECTION"  # OWASP-A03:2021, CWE-643

    A04_312 = "CLEARTEXT_PW"  # OWASP-A04:2021, CWE-312
    A04_434 = "UNRESTRICTED_FILE_UPLOAD"  # OWASP-A04:2021, CWE-434
    A04_602 = "CLIENT_SIDE_VALIDATION"  # OWASP-A04:2021, CWE-602

    A05_611 = "XXE_ATTACK"  # OWASP-A04:2021, CWE-611

    A07_287 = "BROKEN_AUTHENTICATION"  # OWASP-A07:2021, CWE-287
    # https://www.acunetix.com/blog/articles/safely-handling-redirects-die-exit-php/
    A07_287_BROKEN_REDIRECT = "BROKEN_REDIRECT_UNAUTHORIZED"  # OWASP-A07:2021, CWE-287
    A07_384 = "SESSION_FIXATION"  # OWASP-A07:2021, CWE-384
    A07_798 = "HARDCODED_PW"  # OWASP-A07:2021, CWE-798/CWE-259
    A07_798_FIXED_SECRET = "FIXED_SECRET"  # OWASP-A07:2021, CWE-798
    A07_640 = "BROKEN_FORGOT_PASSWORD"  # OWASP-A07:2021, CWE-640
    A07_620 = "BROKEN_CHANGE_PASSWORD"  # OWASP-A07:2021, CWE-620
    A07_295 = "INVALID_CERTIFICATE_VALIDATION"  # OWASP-A07:2021, CWE-295

    A08_502 = "DESERIALIZATION_UNTRUSTED_DATA"  # OWASP-A08:2021, CWE-502
    A08_565 = "COOKIE_WITHOUT_INTEGRITY_CHECK"  # OWASP-A08:2021, CWE-565

    A09_117 = "LOG_FILE_INJECTION"  # OWASP-A09:2021, CWE-117
    A09_532 = "LOG_FILE_SENSITIVE_INFORMATION"  # OWASP-A09:2021, CWE-532


class ExperimentGroup(str, Enum):
    SUPPORT_NONE = "SUPPORT_NONE"
    SUPPORT_REASON = "SUPPORT_REASON"
    SUPPORT_EXPLANATION = "SUPPORT_EXPLANATION"
    SUPPORT_INDIVIDUAL = "SUPPORT_INDIVIDUAL"
    CONTROL_GROUP = "CONTROL_GROUP"


class SupportFactor(str, Enum):
    SUPPORT_REASON = "SUPPORT_REASON"
    SUPPORT_EXPLANATION = "SUPPORT_EXPLANATION"
    SUPPORT_INDIVIDUAL = "SUPPORT_INDIVIDUAL"

    @staticmethod
    def get_factors_for_experiment_group(experiment_group):
        factor_mapping = {
            ExperimentGroup.SUPPORT_NONE: [],
            ExperimentGroup.SUPPORT_REASON: [SupportFactor.SUPPORT_REASON],
            ExperimentGroup.SUPPORT_EXPLANATION: [
                SupportFactor.SUPPORT_REASON,
                SupportFactor.SUPPORT_EXPLANATION,
            ],
            ExperimentGroup.SUPPORT_INDIVIDUAL: [
                SupportFactor.SUPPORT_REASON,
                SupportFactor.SUPPORT_EXPLANATION,
                SupportFactor.SUPPORT_INDIVIDUAL,
            ],
        }

        return factor_mapping.get(experiment_group, [])

    @staticmethod
    def get_all_factors():
        return [factor for factor in SupportFactor]


class RemediationType(str, Enum):
    OFFLINE = "OFFLINE"
    DELETED = "DELETED"
    OUTDATED_WARNING = "OUTDATED_WARNING"
    FIXED_INCORRECTLY = "FIXED_INCORRECTLY"
    FIXED_PARTIALLY = "FIXED_PARTIALLY"
    FIXED_CORRECTLY = "FIXED_CORRECTLY"


@dataclass
class SearchQuery(object):
    category: str
    string: str


Suggestion = SearchQuery


@dataclass
class SearchResultItem(object):
    rank: int
    url: str
    title: str
    snippet: str
    metadata: dict[str, Any]

    def __post_init__(self):
        if self.snippet is None:
            self.snippet = ""


@dataclass
class SearchResult(object):
    engine: SearchEngine
    query: SearchQuery
    items: list[SearchResultItem]
    search_time: str = field(default_factory=datetime_now_isoformat, init=False)

    def add_item(self, item):
        self.items.append(item)


@dataclass
class InspectionSource(object):
    engine: SearchEngine
    query: SearchQuery
    snippet: str
    rank: Optional[int] = field(default=None)


@dataclass
class InspectionResult(object):
    failed: bool = field(default=False)
    failed_reason: Optional[str] = field(default=None)
    is_tutorial: Optional[bool] = field(default=None)
    is_in_scope: Optional[bool] = field(default=None)
    inspection_duration: Optional[int] = field(default=None, init=False)
    inspection_time: Optional[str] = field(
        default_factory=datetime_now_isoformat, init=False
    )


@dataclass
class Inspection(object):
    id: str
    url: str
    title: str
    type: InspectionType
    metadata: dict[str, Any] = field(default_factory=dict)
    sources: list[InspectionSource] = field(default_factory=list, init=False)
    result: Optional[InspectionResult] = field(default=None, init=False)

    def add_source(self, source):
        self.sources.append(source)

    def has_source_engine(self, engine):
        for source in self.sources:
            if source.engine == engine:
                return True
        return False

    def update_metadata(self, metadata):
        self.metadata.update(metadata)

    def was_inspected(self):
        return self.result is not None

    def has_failed(self):
        return self.result is not None and self.result.failed

    def is_tutorial(self):
        return (
            self.was_inspected() and not self.has_failed() and self.result.is_tutorial
        )

    def is_in_scope(self):
        return (
            self.was_inspected()
            and not self.has_failed()
            and self.result.is_tutorial
            and self.result.is_in_scope
        )


@dataclass
class SamplingMetadata(object):
    resolved_urls: dict[str, Any] = field(default_factory=dict, init=False)
    request_errors: dict[str, Any] = field(default_factory=dict, init=False)
    page_metadata: dict[str, Any] = field(default_factory=dict, init=False)


@dataclass
class Contact(object):
    type: ContactType
    party: ContactParty
    details: str


@dataclass
class Vulnerability(object):
    id: str
    type: VulnerabilityType
    details: str
    code: str
    language: str
    line_numbers: str = field(default="", init=False)
    video_timestamp: Optional[str] = field(default=None, init=False)
    html_attributes: dict[str, str] = field(default_factory=dict, init=False)
    html_selectors: dict[str, Optional[str]] = field(default_factory=dict, init=False)
    html_outer: str = field(default="", init=False)
    html_text: str = field(default="", init=False)
    html_scroll: Optional[float] = field(default=None, init=False)


@dataclass
class Tutorial(object):
    url: str
    id: str = field(default=None, init=False)
    type: TutorialType = field(default=TutorialType.WEBPAGE, init=False)
    language: Optional[str] = field(default=None, init=False)
    date: Optional[str] = field(default=None, init=False)
    author: Optional[str] = field(default=None, init=False)
    contact: list[Contact] = field(default_factory=list, init=False)
    has_vulnerability_countermeasures: Optional[bool] = field(default=None, init=False)
    has_vulnerability_explanations: Optional[bool] = field(default=None, init=False)
    has_vulnerability_warning: Optional[bool] = field(default=None, init=False)
    subject: Optional[TutorialSubject] = field(default=None, init=False)
    vulnerabilities: list[Vulnerability] = field(default_factory=list, init=False)
    video: Optional[dict[str, Any]] = field(default=None, init=False)
    last_modified: Optional[str] = field(default=None, init=False)

    def __post_init__(self):
        if self.id is None:
            self.id = create_url_id(self.url)

    def add_vulnerability(self, vulnerability):
        self.vulnerabilities.append(vulnerability)

    def has_vulnerabilities(self):
        return len(self.vulnerabilities) > 0

    def add_contact(self, contact):
        self.contact.append(contact)

    def has_contacts(self):
        return len(self.contact) > 0

    def set_last_modified(self, last_modified):
        if last_modified:
            self.last_modified = last_modified.isoformat()
        else:
            self.last_modified = None

    def get_last_modified(self):
        if not self.last_modified:
            return None
        return datetime.datetime.fromisoformat(self.last_modified)


@dataclass
class ScanResult(object):
    id: str
    tutorial_id: str
    type: Optional[str] = field(default=None)
    failed: bool = field(default=False)
    failed_reason: Optional[str] = field(default=None)
    status_code: Optional[str] = field(default=None, init=False)
    vulnerabilities: dict[str, dict] = field(default_factory=dict, init=False)
    video: Optional[dict[str, Any]] = field(default=None, init=False)
    last_modified: Optional[str] = field(default=None, init=False)

    def set_last_modified(self, last_modified):
        self.last_modified = last_modified.isoformat()

    def get_last_modified(self):
        if not self.last_modified:
            return None
        return datetime.datetime.fromisoformat(self.last_modified)

    def get_datetime(self):
        return datetime.datetime.strptime(self.id, "%Y-%m-%d-%H-%M-%S")

    def was_today(self):
        scan_date = self.get_datetime()
        return scan_date.date() == datetime.datetime.today().date()

    def are_all_vulnerabilities_contained(self):
        for vulnerability in self.vulnerabilities.values():
            if self.type == "auto" and not vulnerability.get("html_contained"):
                return False
            elif self.type == "manu" and not vulnerability.get("manu_contained"):
                return False
            elif self.type == "final" and not vulnerability.get("manu_contained"):
                return False
        return True

    def is_at_least_one_vulnerability_fixed(self):
        return not self.are_all_vulnerabilities_contained()

    def is_vulnerability_contained(self, vulnerability_id):
        vulnerability = self.vulnerabilities.get(vulnerability_id)
        auto_contained = self.type == "auto" and vulnerability.get("html_contained")
        manu_contained = self.type == "manu" and vulnerability.get("manu_contained")
        final_contained = self.type == "final" and vulnerability.get("manu_contained")
        return auto_contained or manu_contained or final_contained

    def has_video_changed(self):
        if self.video:
            has_changed = self.video.get("has_changed")
            return (
                has_changed.get("snippet")
                or has_changed.get("content_details")
                or has_changed.get("creator_comments")
            )


@dataclass
class ExperimentResult(object):
    tutorial_id: str
    tutorial_type: TutorialType
    tutorial_language: str
    tutorial_subject: TutorialSubject
    tutorial_vulnerabilities: str
    tutorial_contact: ContactType
    group: ExperimentGroup
    has_watched_report: bool = field(default=False)
    has_watched_report_after_initial: bool = field(default=False)
    has_watched_report_after_reminder: bool = field(default=False)
    has_watched_report_after_days: Optional[int] = field(default=None)
    notification_undeliverable: bool = field(default=False)
    has_replied: bool = field(default=False)
    reply_type: Optional[str] = field(default=None)
    reply_grateful: Optional[bool] = field(default=None)
    reply_annoyed: Optional[bool] = field(default=None)
    has_fixed: bool = field(default=False)
    has_fixed_after_initial: bool = field(default=False)
    has_fixed_after_reminder: bool = field(default=False)
    has_fixed_after_days: Optional[int] = field(default=None)
    remediation: Optional[RemediationType] = field(default=None)


@dataclass
class Experiment(object):
    vulnerable_tutorials: list[Tutorial] = field(default_factory=list)
    groups: dict[str, ExperimentGroup] = field(default_factory=dict)
    results: dict[str, ExperimentResult] = field(default_factory=dict)

    def assign_tutorial_to_group(self, tutorial, experiment_group):
        self.groups[tutorial.id] = experiment_group

    def get_group_for_tutorial(self, tutorial):
        return self.groups[tutorial.id]

    def get_support_factors_for_tutorial(self, tutorial):
        return SupportFactor.get_factors_for_experiment_group(self.groups[tutorial.id])

    def get_all_support_factors(self):
        return SupportFactor.get_all_factors()
