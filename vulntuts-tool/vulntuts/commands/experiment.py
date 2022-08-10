import csv
import os
import pprint
import random
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone

import pypandoc
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from vulntuts import models, storage, terminal_ui
from vulntuts.commands import BaseCommand
from vulntuts.errors import InvalidArgumentError

TEMPLATES_DIR = "templates"

MESSAGE_TEMPLATES_DIR = "messages"
NOTIFICATION_TEMPLATE_FILE = os.path.join(
    MESSAGE_TEMPLATES_DIR, "notification-pandoc.md"
)
REMINDER_TEMPLATE_FILE = os.path.join(MESSAGE_TEMPLATES_DIR, "reminder-pandoc.md")
DEBRIEFING_TEMPLATE_FILE = os.path.join(MESSAGE_TEMPLATES_DIR, "debriefing-pandoc.md")

REPORT_TEMPLATES_DIR = "reports"
HTML_STATIC_RELATIVE_DIR = "static"
HTML_STATIC_DIR = os.path.join(REPORT_TEMPLATES_DIR, HTML_STATIC_RELATIVE_DIR)
PANDOC_TEMPLATE_FILE = os.path.join(REPORT_TEMPLATES_DIR, "pandoc-template.html")
REPORT_TEMPLATE_FILE = os.path.join(REPORT_TEMPLATES_DIR, "report.md")

WEAKNESS_TEMPLATES_DIR = "weaknesses"
WEAKNESS_INFO_FILE = os.path.join(WEAKNESS_TEMPLATES_DIR, "weaknesses.yaml")

NGINX_LOGS_DIR = "nginx-logs"
NGINX_ACCESS_LOG_FILE = "access.log"


class ExperimentCommand(BaseCommand):
    def get_name(self):
        return "experiment"

    def get_help(self):
        return "Manage experiment (assign to groups, create emails and reports)"

    def setup_arguments(self, parser):
        parser.add_argument(
            "--initialize",
            help=(
                "Initialize experiment by extracting vulnerable tutorials and assigning"
                " them to the experiment groups"
            ),
            action="store_true",
        )
        parser.add_argument(
            "--print-groups",
            help="Print experiment groups and list the vulnerable tutorials",
            action="store_true",
        )
        parser.add_argument(
            "--create-reports",
            help="Create reports to be uploaded to webserver",
            action="store_true",
        )
        parser.add_argument(
            "--create-contacts",
            help="Create list of contacts for the notification",
            action="store_true",
        )
        parser.add_argument(
            "--remove-contact",
            metavar="CONTACT_DETAILS",
            help="Remove a contact from list of contacts",
        )
        parser.add_argument(
            "--remove-contacts",
            metavar="CONTACT_FILE",
            help="Remove contacts loaded from file from list of contacts",
        )
        parser.add_argument(
            "--create-messages",
            help=(
                "Create notification and reminder messages and csv data file for"
                " Thunderbird's MailMerge plugin"
            ),
            action="store_true",
        )
        parser.add_argument(
            "--contact",
            help="Go through all the tutorials that need to be contacted manually",
            action="store_true",
        )
        parser.add_argument(
            "--parse-nginx-logs",
            help="Parse the nginx access logs to determine if reports were read or not",
            action="store_true",
        )
        parser.add_argument(
            "--create-results",
            help="Create the results file",
            action="store_true",
        )
        parser.add_argument(
            "--start",
            metavar="START_DATE",
            help=(
                "For `--create-results`: Start date of the experiment (format:"
                " `YYYY-mm-dd HH:MM:SS`)"
            ),
        )
        parser.add_argument(
            "--undelivered",
            metavar="UNDELIVERED_FILE",
            help=(
                "For `--create-results`: File with tutorial ids of undelivered"
                " notifications"
            ),
        )
        parser.add_argument(
            "--replies",
            metavar="REPLIES_FILE",
            help="For `--create-results`: File with csv data of replies [optional]",
        )

    def main(self, args):
        # initialize storage
        data_dir = args.get("data_dir")
        tutorial_storage = storage.TutorialStorage(data_dir)
        scan_storage = storage.ScanStorage(data_dir)
        experiment_storage = storage.ExperimentStorage(data_dir)
        result_storage = storage.ResultStorage(data_dir)
        contact_storage = storage.ContactStorage(data_dir)
        report_storage = storage.ReportStorage(data_dir)
        message_storage = storage.MessageStorage(data_dir)
        templates_path = os.path.join(data_dir, TEMPLATES_DIR)
        nginx_logs_path = os.path.join(data_dir, NGINX_LOGS_DIR)

        experiment_manager = ExperimentManager(
            tutorial_storage,
            scan_storage,
            experiment_storage,
            result_storage,
            contact_storage,
            report_storage,
            message_storage,
            templates_path,
        )

        if args.get("initialize"):
            experiment_manager.initialize_experiment()
        elif args.get("print_groups"):
            experiment_manager.print_groups()
        elif args.get("create_reports"):
            experiment_manager.create_reports()
        elif args.get("create_contacts"):
            experiment_manager.create_contacts()
        elif args.get("remove_contact"):
            experiment_manager.remove_contact(args.get("remove_contact"))
        elif args.get("remove_contacts"):
            experiment_manager.remove_contacts(args.get("remove_contacts"))
        elif args.get("create_messages"):
            experiment_manager.create_messages()
        elif args.get("contact"):
            experiment_manager.contact()
        elif args.get("parse_nginx_logs"):
            experiment_manager.parse_nginx_logs(nginx_logs_path)
        elif args.get("create_results"):
            if not args.get("start") or not args.get("undelivered"):
                raise InvalidArgumentError(
                    "Please specify the start date of the experiment and the file with"
                    " undelivered notifications"
                )
            experiment_manager.create_results(
                args.get("start"),
                args.get("undelivered"),
                args.get("replies"),
                nginx_logs_path,
            )


class ExperimentManager(object):
    def __init__(
        self,
        tutorial_storage,
        scan_storage,
        experiment_storage,
        result_storage,
        contact_storage,
        report_storage,
        message_storage,
        templates_path,
    ):
        self.tutorial_storage = tutorial_storage
        self.scan_storage = scan_storage
        self.experiment_storage = experiment_storage
        self.result_storage = result_storage
        self.contact_storage = contact_storage
        self.report_storage = report_storage
        self.message_storage = message_storage
        self.templates_path = templates_path

    def initialize_experiment(self):
        # find vulnerable tutorials
        vulnerable_tutorials = self._find_vulntuts()

        # create experiment
        experiment = models.Experiment(vulnerable_tutorials=vulnerable_tutorials)

        # divide tutorials into groups of equal size (same domain in same group)
        tutorial_groups = self._divide_tutorials_to_n_groups(
            vulnerable_tutorials, len(models.ExperimentGroup)
        )

        # assign tutorials to experiment groups
        for experiment_group, tutorials in zip(models.ExperimentGroup, tutorial_groups):
            for tutorial in tutorials:
                experiment.assign_tutorial_to_group(tutorial, experiment_group)

        # create backup of old experiment and save
        self.experiment_storage.create_backup()
        self.experiment_storage.save(experiment)

    def _find_vulntuts(self):
        # create result list
        vulnerable_tutorials = []

        # find vulnerable tutorials
        tutorials = self.tutorial_storage.load_all()
        for tutorial in tutorials:
            if tutorial.has_vulnerabilities():
                vulnerable_tutorials.append(tutorial)

        # sort by id/domain
        return sorted(vulnerable_tutorials, key=lambda x: x.id)

    def _divide_tutorials_to_n_groups(self, vulnerable_tutorials, num_groups):
        # assign tutorials to contact groups
        contact_groups = defaultdict(list)
        for tutorial in vulnerable_tutorials:
            group_with_same_contact = self._find_group_with_same_contact(
                contact_groups, tutorial
            )

            # if a contact for the tutorial is already present in another group
            # (e.g., same email), we must ensure that all tutorials from the same
            # contact are in the same experiment group
            if group_with_same_contact:
                group_with_same_contact.append(tutorial)
            # if tutorial is a webpage, we must ensure that all tutorials from the
            # same domain are in the same experiment group
            elif tutorial.type == models.TutorialType.WEBPAGE:
                domain = models.extract_first_level_domain(tutorial.url)
                contact_groups[domain].append(tutorial)
            # if tutorial is a video (i.e., from youtube), the tutorial can be in
            # different experiment groups (use unique tutorial id instead of domain)
            else:
                contact_groups[tutorial.id].append(tutorial)

        # create groups for tutorials
        tutorial_groups = self._create_groups(num_groups)

        contact_groups = list(contact_groups.values())
        while len(contact_groups) > 0:
            # choose random contact group and remove it from the list
            contact_group = random.choice(contact_groups)
            contact_groups.remove(contact_group)

            # function to get the next group to assign a tutorial to,
            # i.e., the group with the smallest number of tutorials
            tutorial_group = self._get_smallest_group(tutorial_groups)

            # assign tutorials in the contact group to the experiment group
            for tutorial in contact_group:
                tutorial_group.append(tutorial)

        return tutorial_groups

    def _find_group_with_same_contact(self, contact_groups, tutorial):
        for group_key, tutorials_in_group in contact_groups.items():
            for tutorial_in_group in tutorials_in_group:
                if self._does_one_contact_match(tutorial, tutorial_in_group):
                    return contact_groups[group_key]
        return None

    def _does_one_contact_match(self, tutorial1, tutorial2):
        for contact1 in tutorial1.contact:
            for contact2 in tutorial2.contact:
                if (
                    contact1.type == contact2.type
                    and contact1.details == contact2.details
                ):
                    return True
        return False

    def _create_groups(self, num_groups):
        return [[] for x in range(num_groups)]

    def _get_smallest_group(self, groups):
        min_group_len = min([len(group) for group in groups])
        for group in groups:
            if len(group) == min_group_len:
                return group

    def print_groups(self):
        # load experiment
        experiment = self.experiment_storage.load_experiment()

        # create dict (group -> list of tutorials)
        groups = defaultdict(list)
        domains = defaultdict(lambda: defaultdict(int))
        contacts = defaultdict(lambda: defaultdict(int))

        for tutorial in experiment.vulnerable_tutorials:
            # get experiment group
            experiment_group = experiment.get_group_for_tutorial(tutorial)

            # add tutorial to group
            groups[experiment_group].append(tutorial)

            # count first-level domain
            fld = models.extract_first_level_domain(tutorial.url)
            if fld == "youtube.com":
                domains[experiment_group][tutorial.id] += 1
            else:
                domains[experiment_group][fld] += 1

            # count contacts
            if len(tutorial.contact) > 0:
                contact_details = tutorial.contact[0].details
                contacts[experiment_group][contact_details] += 1
            else:
                contacts[experiment_group][fld] += 1

        # print groups
        for group, tutorials_in_group in groups.items():
            print(
                f"{group} ({len(tutorials_in_group)} tutorials,"
                f" {len(domains[group])} domains,"
                f" {len(contacts[group])} contacts)"
            )
            print("-" * len(group))
            for tutorial in tutorials_in_group:
                if len(tutorial.contact) > 0:
                    contact = (
                        f"{tutorial.contact[0].type}: {tutorial.contact[0].details}"
                    )
                else:
                    contact = "-"
                print(f"{tutorial.id: <34} {contact[:50]}")
            print("")

    def create_reports(self):
        # create backup of reports
        self.report_storage.create_backup()

        # load experiment
        experiment = self.experiment_storage.load_experiment()

        # load information about weaknesses
        weaknesses_info = self._load_weaknesses_info()

        for tutorial in experiment.vulnerable_tutorials:
            # create report id
            report_id = models.create_report_id(tutorial.id)

            # get experiment group
            experiment_group = experiment.get_group_for_tutorial(tutorial)

            # create notification report (if not control group)
            if experiment_group != models.ExperimentGroup.CONTROL_GROUP:
                notification_report = self._create_report(
                    tutorial,
                    experiment.get_support_factors_for_tutorial(tutorial),
                    weaknesses_info,
                )
                self.report_storage.save_notification_report(
                    report_id, notification_report
                )

            # create full report (always)
            full_report = self._create_report(
                tutorial,
                experiment.get_all_support_factors(),
                weaknesses_info,
            )
            self.report_storage.save_full_report(report_id, full_report)

        # copy static files for html to reports directory
        self.report_storage.copy_to_reports_dir(
            os.path.join(self.templates_path, HTML_STATIC_DIR)
        )

    def _create_report(self, tutorial, support_factors, weaknesses_info):
        # create jinja2 environment
        template_env = Environment(
            loader=FileSystemLoader(self.templates_path),
            autoescape=select_autoescape(),
            trim_blocks=True,
        )

        # create summary of weaknesses
        weakness_summaries = self._create_summary_of_weaknesses(
            tutorial.vulnerabilities, weaknesses_info, is_markdown=True
        )

        # determine support factors
        support_reason = models.SupportFactor.SUPPORT_REASON in support_factors
        support_explanation = (
            models.SupportFactor.SUPPORT_EXPLANATION in support_factors
        )
        support_individual = models.SupportFactor.SUPPORT_INDIVIDUAL in support_factors

        # load vulnerabilitites for report
        vulnerabilities = []
        for vulnerability in tutorial.vulnerabilities:
            weakness_summary = self._create_summary_of_weakness(
                vulnerability, weaknesses_info, is_markdown=True
            )
            vuln_data = {
                "name": weaknesses_info[vulnerability.type]["name"],
                "summary": weakness_summary["description"],
                "description": vulnerability.details,
                "language": vulnerability.language,
                "code": vulnerability.code.replace("<", "&lt;"),
                "line_numbers": vulnerability.line_numbers,
                "video_timestamp": vulnerability.video_timestamp,
            }

            if models.SupportFactor.SUPPORT_EXPLANATION in support_factors:
                vuln_data["fix"] = self._load_vulnerability_fix(
                    vulnerability.type,
                    vulnerability.language,
                )
                vuln_data["exploit"] = self._load_vulnerability_exploit(
                    vulnerability.type,
                    vulnerability.language,
                )

            vulnerabilities.append(vuln_data)

        # load template and render it
        template = template_env.get_template(REPORT_TEMPLATE_FILE)
        report = template.render(
            {
                "tutorial_url": tutorial.url,
                "weakness_summaries": weakness_summaries,
                "count_weaknesses": len(weakness_summaries),
                "vulnerabilities": vulnerabilities,
                "count_vulnerabilities": len(vulnerabilities),
                "support_reason": support_reason,
                "support_explanation": support_explanation,
                "support_individual": support_individual,
            }
        )

        # convert report to HTML
        return self._convert_report(report)

    def _convert_report(self, report):
        pandoc_template = os.path.join(self.templates_path, PANDOC_TEMPLATE_FILE)
        return pypandoc.convert_text(
            report,
            "html5",
            format="markdown",
            extra_args=[
                "--standalone",
                f"--css={HTML_STATIC_RELATIVE_DIR}/pandoc-theme.css",
                f"--template={pandoc_template}",
                "--toc",
                "--variable=toc-title:Contents",
            ],
        )

        # subprocess.run(
        #     "pandoc --standalone --from markdown --to html5"
        #     f" --css {HTML_STATIC_DIR}/pandoc-theme.css"
        #     f" --template {pandoc_template}"
        #     " --toc --variable toc-title=Contents"
        #     f" -o {html_report_path} {md_report_path}",
        #     shell=True,
        #     check=True,
        # )

    def create_contacts(self):
        # create backup of contacts
        self.contact_storage.create_backup()

        # load experiment
        experiment = self.experiment_storage.load_experiment()

        # dict for contacts
        contacts = dict()

        for tutorial in experiment.vulnerable_tutorials:
            # get experiment group
            experiment_group = experiment.get_group_for_tutorial(tutorial)

            # skip the tutorial if it is in the control group (no notification)
            if experiment_group == models.ExperimentGroup.CONTROL_GROUP:
                continue

            first_level_domain = models.extract_first_level_domain(tutorial.url)

            # if we have no contacts, use default emails
            if len(tutorial.contact) == 0:
                contacts[tutorial.id] = self._get_default_contacts(first_level_domain)
            # otherwise, use the contacts we have
            else:
                # retrieve first contact
                contact = tutorial.contact[0]

                # if contact is email contact, use it
                if contact.type == models.ContactType.EMAIL:
                    email = contact.details
                    if email.startswith("@"):
                        contacts[tutorial.id] = self._get_default_contacts(email[1:])
                    else:
                        contacts[tutorial.id] = [contact]
                # if contact is contact form or onsite contact form, use it
                elif (
                    contact.type == models.ContactType.CONTACT_FORM
                    or contact.type == models.ContactType.ON_SITE
                ):
                    contacts[tutorial.id] = [contact]
                # otherwise (social media):
                else:
                    contacts[tutorial.id] = [contact]

                    # if not a popular platform, also include default emails
                    if (
                        first_level_domain != "youtube.com"
                        and first_level_domain != "wordpress.com"
                        and first_level_domain != "medium.com"
                    ):
                        contacts[tutorial.id].extend(
                            self._get_default_contacts(first_level_domain)
                        )

        # save contacts
        self.contact_storage.save(contacts)

    def _get_default_contacts(self, domain):
        mailboxes = ["info", "webmaster", "abuse", "security"]

        # generate emails
        emails = [f"{mailbox}@{domain}" for mailbox in mailboxes]

        # generate contacts
        return [
            models.Contact(
                type=models.ContactType.EMAIL,
                party=models.ContactParty.WEBSITE,
                details=email,
            )
            for email in emails
        ]

    def remove_contact(self, remove_contact):
        # load contacts
        contacts = self.contact_storage.load_contacts()

        # create backup of contacts
        self.contact_storage.create_backup()

        # remove contact
        contacts = self._remove_contact(remove_contact, contacts)

        # save contacts
        self.contact_storage.save(contacts)

    def remove_contacts(self, remove_contacts_file):
        # load contacts
        contacts = self.contact_storage.load_contacts()

        # create backup of contacts
        self.contact_storage.create_backup()

        # load contacts to be removed
        remove_contacts = storage.BaseStorage()._load_list(remove_contacts_file)

        # remove contact
        for remove_contact in remove_contacts:
            contacts = self._remove_contact(remove_contact, contacts)

        # save contacts
        self.contact_storage.save(contacts)

    def _remove_contact(self, remove_contact, contacts):
        return {
            tutorial_id: [
                contact
                for contact in contacts_for_tutorial
                if contact.details != remove_contact
            ]
            for tutorial_id, contacts_for_tutorial in contacts.items()
        }

    def create_messages(self):
        # create backup of notifications
        self.message_storage.create_backup()

        # load experiment
        experiment = self.experiment_storage.load_experiment()

        # load contacts
        contacts = self.contact_storage.load_contacts()

        # create jinja2 environment
        template_env = Environment(
            loader=FileSystemLoader(self.templates_path),
            autoescape=select_autoescape(),
            trim_blocks=True,
        )

        mailmerge_notification_data = []
        mailmerge_debriefing_data = []

        for tutorial in experiment.vulnerable_tutorials:
            # get experiment group
            experiment_group = experiment.get_group_for_tutorial(tutorial)

            # skip the tutorial if it is in the control group (no notification)
            if experiment_group == models.ExperimentGroup.CONTROL_GROUP:
                continue

            # create template data
            template_data = self._create_template_data(tutorial, experiment)

            # notification: render template and save
            template = template_env.get_template(NOTIFICATION_TEMPLATE_FILE)
            notification = template.render(template_data)
            self.message_storage.save_message(
                tutorial.id, notification, storage.MessageType.NOTIFICATION
            )
            # reminder: render template and save
            template = template_env.get_template(REMINDER_TEMPLATE_FILE)
            reminder = template.render(template_data)
            self.message_storage.save_message(
                tutorial.id, reminder, storage.MessageType.REMINDER
            )
            # debriefing: render template and save
            template = template_env.get_template(DEBRIEFING_TEMPLATE_FILE)
            debriefing = template.render(template_data)
            self.message_storage.save_message(
                tutorial.id, debriefing, storage.MessageType.DEBRIEFING
            )

            # if tutorial has no contacts (e.g., deleted after 1st notification bounced)
            if tutorial.id not in contacts:
                continue

            for contact in contacts[tutorial.id]:
                # skip contacts other than email
                if contact.type != models.ContactType.EMAIL:
                    continue

                email = contact.details
                contact_author = contact.party == models.ContactParty.AUTHOR

                domain = models.extract_domain(tutorial.url)
                if domain.startswith("www."):
                    domain = domain[len("www.") :]

                list_of_vulnerabilitites = []
                for vuln_summary in template_data.get("vuln_summaries"):
                    list_of_vulnerabilitites.append(
                        f"- {vuln_summary['name']}: {vuln_summary['description']}"
                    )

                # create mailmerge data for notification
                mailmerge_data = dict(template_data)
                mailmerge_data.update(
                    {
                        "email": email,
                        "subject": (
                            "Security Vulnerability in Your Programming Tutorial"
                            f" on {domain}"
                        ),
                        "contact_author": contact_author,
                        "vuln_summaries": "<br><br>".join(list_of_vulnerabilitites),
                    }
                )
                mailmerge_data = self._convert_data_for_mailmerge(mailmerge_data)
                mailmerge_notification_data.append(mailmerge_data)

                # create mailmerge data for debriefing
                mailmerge_data = dict(template_data)
                mailmerge_data.update(
                    {
                        "email": email,
                        "subject": (
                            "Debriefing on Experiment About Vulnerabilities in"
                            " Programming Tutorials"
                        ),
                        "contact_author": contact_author,
                        "vuln_summaries": "<br><br>".join(list_of_vulnerabilitites),
                        "receives_full_report": not template_data.get(
                            "support_individual"
                        ),
                    }
                )
                mailmerge_data = self._convert_data_for_mailmerge(mailmerge_data)
                mailmerge_debriefing_data.append(mailmerge_data)

        # save mailmerge data for notification
        self.message_storage.save_mailmerge(
            mailmerge_notification_data, storage.MessageType.NOTIFICATION
        )

        # save mailmerge data for debriefing
        self.message_storage.save_mailmerge(
            mailmerge_debriefing_data, storage.MessageType.DEBRIEFING
        )

    def _create_template_data(self, tutorial, experiment):
        # load information about weaknesses
        weaknesses_info = self._load_weaknesses_info()

        # create summary of weaknesses
        weakness_summaries = self._create_summary_of_weaknesses(
            tutorial.vulnerabilities, weaknesses_info, is_markdown=False
        )

        # determine support factors
        support_factors = experiment.get_support_factors_for_tutorial(tutorial)
        support_reason = models.SupportFactor.SUPPORT_REASON in support_factors
        support_explanation = (
            models.SupportFactor.SUPPORT_EXPLANATION in support_factors
        )
        support_individual = models.SupportFactor.SUPPORT_INDIVIDUAL in support_factors
        support_explanation_or_individual = support_explanation or support_individual

        report_id = models.create_report_id(tutorial.id)
        base_url = "https://research.psi.uni-bamberg.de"
        report_url = f"{base_url}/reports/{report_id}.html"
        full_report_url = f"{base_url}/full-reports/{report_id}.html"
        privacy_policy_url = f"{base_url}/debriefing-privacy-policy.html"

        experiment_group = experiment.get_group_for_tutorial(tutorial)
        if experiment_group == models.ExperimentGroup.SUPPORT_NONE:
            survey_url = f"{base_url}/vulnerable-tutorials-survey"
        elif experiment_group == models.ExperimentGroup.SUPPORT_REASON:
            survey_url = f"{base_url}/vulnerable-tutorials-questionnaire"
        elif experiment_group == models.ExperimentGroup.SUPPORT_EXPLANATION:
            survey_url = f"{base_url}/vulnerability-tutorials-survey"
        elif experiment_group == models.ExperimentGroup.SUPPORT_INDIVIDUAL:
            survey_url = f"{base_url}/vulnerability-tutorials-questionnaire"
        else:
            survey_url = None

        if len(tutorial.contact) > 0:
            contact_author = tutorial.contact[0].party == models.ContactParty.AUTHOR
            is_email = tutorial.contact[0].type == models.ContactType.EMAIL
        else:
            contact_author = False
            is_email = False

        return {
            "is_email": is_email,
            "contact_author": contact_author,
            "has_author": tutorial.author is not None,
            "tutorial_author": tutorial.author,
            "tutorial_url": tutorial.url,
            "vuln_summaries": weakness_summaries,
            "count_vulnerabilities": len(weakness_summaries),
            "report_url": report_url,
            "full_report_url": full_report_url,
            "survey_url": survey_url,
            "privacy_policy_url": privacy_policy_url,
            "support_reason": support_reason,
            "support_explanation": support_explanation,
            "support_individual": support_individual,
            "support_explanation_or_individual": support_explanation_or_individual,
        }

    def _convert_data_for_mailmerge(self, template_data):
        mailmerge_data = dict(template_data)
        for key, value in mailmerge_data.items():
            if isinstance(value, bool):
                mailmerge_data[key] = "x" if value else ""
        return mailmerge_data

    def _load_weaknesses_info(self):
        file_path = os.path.join(self.templates_path, WEAKNESS_INFO_FILE)
        if os.path.isfile(file_path):
            with open(file_path, "r") as file:
                data = yaml.safe_load(file)
                return {
                    models.VulnerabilityType(type_): item
                    for type_, item in data.items()
                }
        else:
            raise ValueError(f"File '{file_path}' does not exist")

    def _create_summary_of_weaknesses(
        self, vulnerabilities, weaknesses_info, is_markdown
    ):
        vuln_summaries = []
        vuln_types = set()

        for vulnerability in vulnerabilities:
            # ensure that each weakness is only mentioned once
            if vulnerability.type in vuln_types:
                continue
            vuln_types.add(vulnerability.type)

            # add summary
            vuln_summaries.append(
                self._create_summary_of_weakness(
                    vulnerability, weaknesses_info, is_markdown
                )
            )

        return vuln_summaries

    def _create_summary_of_weakness(self, vulnerability, weaknesses_info, is_markdown):
        # retrieve data about weakness
        weakness_info = weaknesses_info[vulnerability.type]
        weakness_name = weakness_info["name"]
        weakness_description = weakness_info["description"]
        cwe = weakness_info["cwe"]

        # check if description exists
        if weakness_description is None:
            weakness_description = ""
            print(
                "Warning: No description for weakness"
                f" '{vulnerability.type.name}/{vulnerability.type.value}'"
            )

        # check if CWE exists
        if cwe:
            # append CWE to description (as markdown or plaintext)
            if is_markdown:
                weakness_description = (
                    f"{weakness_description} "
                    f"([CWE-{cwe}](https://cwe.mitre.org/data/definitions/{cwe}.html))"
                )
            else:
                weakness_description = f"{weakness_description} (CWE-{cwe})"
        else:
            print(
                "Warning: No CWE for weakness"
                f" '{vulnerability.type.name}/{vulnerability.type.value}'"
            )

        # return summary
        return {
            "name": weakness_name,
            "description": weakness_description,
            "cwe": cwe,
        }

    def _load_vulnerability_fix(self, vuln_type, language):
        file_path_generic = os.path.join(
            self.templates_path,
            WEAKNESS_TEMPLATES_DIR,
            "generic",
            f"{vuln_type.value}-fix.md",
        )
        file_path_language_specific = os.path.join(
            self.templates_path,
            WEAKNESS_TEMPLATES_DIR,
            language,
            f"{vuln_type.value}-fix.md",
        )

        if os.path.isfile(file_path_generic):
            with open(file_path_generic, "r") as file:
                return file.read()
        elif os.path.isfile(file_path_language_specific):
            with open(file_path_language_specific, "r") as file:
                return file.read()
        else:
            print(
                "Warning: No fix for vulnerability"
                f" '{language}/{vuln_type.name}/{vuln_type.value}'"
            )
            return None

    def _load_vulnerability_exploit(self, vuln_type, language):
        file_path_generic = os.path.join(
            self.templates_path,
            WEAKNESS_TEMPLATES_DIR,
            "generic",
            f"{vuln_type.value}-exploit.md",
        )
        file_path_language_specific = os.path.join(
            self.templates_path,
            WEAKNESS_TEMPLATES_DIR,
            language,
            f"{vuln_type.value}-exploit.md",
        )

        if os.path.isfile(file_path_generic):
            with open(file_path_generic, "r") as file:
                return file.read()
        elif os.path.isfile(file_path_language_specific):
            with open(file_path_language_specific, "r") as file:
                return file.read()
        else:
            print(
                "Warning: No exploit for vulnerability"
                f" '{language}/{vuln_type.name}/{vuln_type.value}'"
            )
            return None

    def contact(self):
        # load experiment
        experiment = self.experiment_storage.load_experiment()

        for tutorial in experiment.vulnerable_tutorials:
            # get experiment group
            experiment_group = experiment.get_group_for_tutorial(tutorial)

            # skip the tutorial if it is in the control group (no notification)
            if experiment_group == models.ExperimentGroup.CONTROL_GROUP:
                continue

            if (
                len(tutorial.contact) > 0
                and tutorial.contact[0].type != models.ContactType.EMAIL
            ):
                contact = tutorial.contact[0]
                domain = models.extract_first_level_domain(tutorial.url)
                social_media = (
                    "I am an IT security researcher at the University of Bamberg,"
                    " Germany, studying programming tutorials. I have feedback on your"
                    f" tutorial on {domain} that I don't want to discuss publicly."
                    " Could you please contact me at research.psi@uni-bamberg.de?"
                )
                social_media_reminder = (
                    "I am an IT security researcher studying programming tutorials and"
                    " recently tried to contact you. I have feedback on your tutorial"
                    f" on {domain} that I don't want to discuss publicly. Could you"
                    " please answer me or contact me at research.psi@uni-bamberg.de?"
                )
                subject = (
                    f"Security Vulnerability in Your Programming Tutorial on {domain}"
                )

                # load notification
                notification = self.message_storage.load_message(
                    tutorial.id, storage.MessageType.NOTIFICATION
                )
                reminder = self.message_storage.load_message(
                    tutorial.id, storage.MessageType.REMINDER
                )

                # print notifications
                print("------------------------------------------------------------")
                print("")
                print(social_media)
                print("")
                print("")
                print(notification)
                print("")
                print("")

                # print other details
                print(f"ID: {tutorial.id}")
                print(f"URL: {tutorial.url}")
                print(f"Type: {contact.type}")
                print(f"Details: {contact.details}")
                print(f"Subject: {subject}")

                ui = terminal_ui.TerminalUI()

                self._write_to_clipboard(contact.details)
                ui._ask_for_boolean("Copy short notification?")
                self._write_to_clipboard(social_media)
                ui._ask_for_boolean("Copy full notification?")
                self._write_to_clipboard(notification)
                ui._ask_for_boolean("Copy short reminder?")
                self._write_to_clipboard(social_media_reminder)
                ui._ask_for_boolean("Copy full reminder?")
                self._write_to_clipboard(reminder)
                ui._ask_for_boolean("Copy subject?")
                self._write_to_clipboard(subject)
                ui._ask_for_boolean("Next?")

    def _write_to_clipboard(self, output):
        process = subprocess.Popen(
            "pbcopy", env={"LANG": "en_US.UTF-8"}, stdin=subprocess.PIPE
        )
        process.communicate(output.encode("utf-8"))

    def create_results(
        self, start_date, undelivered_file, replies_file, nginx_logs_path
    ):
        # create backup of results
        self.result_storage.create_backup()

        # load experiment and scan results
        experiment = self.experiment_storage.load_experiment()
        scan_results = list(self.scan_storage.load_all())

        # create dict for results
        experiment_results = {}

        # load and parse access logs
        local_timezone = datetime.now(timezone.utc).astimezone().tzinfo
        start_date = datetime.fromisoformat(start_date).replace(tzinfo=local_timezone)
        log_lines = self._load_access_logs(nginx_logs_path)
        report_access_logs = self._parse_access_logs(log_lines)
        report_access_logs = self._process_report_access_logs(
            report_access_logs, start_date
        )

        # load undelivered notifications
        undelivered_notifications = storage.BaseStorage()._load_list(undelivered_file)

        # load replies csv
        replies = self._load_replies(replies_file)

        # create result for each tutorial
        for tutorial in experiment.vulnerable_tutorials:
            report_id = models.create_report_id(tutorial.id)

            # filter scan results for tutorial
            scan_results_for_tutorial = [
                scan_result
                for scan_result in scan_results
                if tutorial.id == scan_result.tutorial_id
            ]
            # sort scan results by datetime
            scan_results_for_tutorial = sorted(
                scan_results_for_tutorial, key=lambda x: x.get_datetime(), reverse=True
            )
            # get final scan result
            final_scan_result = self._get_final_scan_result(scan_results_for_tutorial)

            # create result
            result = models.ExperimentResult(
                tutorial_id=tutorial.id,
                tutorial_type=tutorial.type,
                tutorial_language=tutorial.language,
                tutorial_subject=tutorial.subject,
                tutorial_contact=tutorial.contact[0].type
                if tutorial.contact
                else "NONE",
                tutorial_vulnerabilities="|".join(
                    sorted([vuln.type.value for vuln in tutorial.vulnerabilities])
                ),
                group=experiment.get_group_for_tutorial(tutorial),
            )

            # check if report was watched and when
            result.has_watched_report = report_id in report_access_logs
            if result.has_watched_report:
                after_days = report_access_logs.get(report_id).get("days_after_start")
                result.has_watched_report_after_days = after_days
                result.has_watched_report_after_initial = after_days < 14
                result.has_watched_report_after_reminder = after_days >= 14

            # check if at least one vulnerability was fixed
            result.has_fixed = final_scan_result.is_at_least_one_vulnerability_fixed()

            if result.has_fixed:
                print("---")
                print(tutorial.id)
                print("")
                self._print_scan_results(scan_results_for_tutorial, tutorial)
                ui = terminal_ui.TerminalUI()
                fix_date = ui._ask_for_string("Fix Date (YYYY-mm-dd)")
                fix_date = datetime.strptime(fix_date, "%Y-%m-%d").replace(
                    tzinfo=local_timezone
                )
                after_days = (fix_date - start_date).days
                result.has_fixed_after_days = after_days
                result.has_fixed_after_initial = after_days < 14
                result.has_fixed_after_reminder = after_days >= 14

                print("")
                self._print_remedations(final_scan_result)
                result.remediation = ui._ask_for_enum(
                    "Remediation",
                    models.RemediationType,
                    default=self._obtain_remediation_type(final_scan_result),
                )

            if tutorial.id in undelivered_notifications:
                result.notification_undeliverable = True

            reply = replies.get(tutorial.id, {"has_replied": False})
            result.has_replied = reply.get("has_replied")
            if result.has_replied:
                result.reply_type = reply.get("reply_type")
                result.reply_grateful = reply.get("grateful")
                result.reply_annoyed = reply.get("annoyed")

            experiment_results[tutorial.id] = result

        self.result_storage.save(experiment_results)

    def _load_replies(self, replies_file):
        if not replies_file:
            return {}

        replies = {}
        with open(replies_file, "r") as file:
            csv_file = csv.DictReader(file)
            for row in csv_file:
                row = dict(row)

                tutorial_id = row.get("tutorial")
                has_replied = row.get("answer") == "x"
                reply_type = None

                ignored_keys = ["tutorial", "answer", "grateful", "annoyed", "notes"]
                for key, value in row.items():
                    if key not in ignored_keys and value:
                        reply_type = key
                        break

                replies[tutorial_id] = {
                    "has_replied": has_replied,
                    "reply_type": reply_type,
                    "grateful": row.get("grateful") == "x",
                    "annoyed": row.get("annoyed") == "x",
                    "notes": row.get("notes"),
                }

        return replies

    def _get_final_scan_result(self, scan_results):
        return next(
            scan_result for scan_result in scan_results if scan_result.type == "final"
        )

    def _print_scan_results(self, scan_results, tutorial):
        for scan_result in scan_results:
            self._print_scan_result(scan_result, tutorial)

    def _print_scan_result(self, scan_result, tutorial):
        if scan_result.failed:
            print(f"{scan_result.id}: failed ({scan_result.failed_reason})")
        else:
            if tutorial.type == models.TutorialType.WEBPAGE:
                result_str = (
                    "any/all fixed"
                    if scan_result.is_at_least_one_vulnerability_fixed()
                    else "not fixed"
                )
                print(f"{scan_result.id}: {result_str}")
            elif tutorial.type == models.TutorialType.VIDEO:
                result_str = (
                    "video has changed"
                    if scan_result.has_video_changed()
                    else "video has not changed"
                )
                print(f"{scan_result.id}: {result_str}")

    def _print_remedations(self, final_scan_result):
        for vuln_result in final_scan_result.vulnerabilities.values():
            print(vuln_result.get("remediation"))

    def _obtain_remediation_type(self, final_scan_result):
        has_incorrect_fix = any(
            models.RemediationType(vuln_result.get("remediation"))
            == models.RemediationType.FIXED_INCORRECTLY
            or models.RemediationType(vuln_result.get("remediation"))
            == models.RemediationType.FIXED_PARTIALLY
            for vuln_result in final_scan_result.vulnerabilities.values()
        )
        has_correct_fix = any(
            models.RemediationType(vuln_result.get("remediation"))
            == models.RemediationType.FIXED_CORRECTLY
            for vuln_result in final_scan_result.vulnerabilities.values()
        )
        if has_incorrect_fix and has_correct_fix:
            return models.RemediationType.FIXED_PARTIALLY
        else:
            # get remediation of first vulnerability
            return models.RemediationType(
                list(final_scan_result.vulnerabilities.values())[0].get("remediation")
            )

    def parse_nginx_logs(self, nginx_logs_path):
        log_lines = self._load_access_logs(nginx_logs_path)
        report_access_logs = self._parse_access_logs(log_lines)

        unique_reports = set()
        for report_access_log in report_access_logs:
            unique_reports.add(report_access_log.get("report_id"))

        report_count = defaultdict(int)
        for report_access_log in report_access_logs:
            report_count[report_access_log.get("report_id")] += 1
        pprint.pprint(dict(report_count))

        print(f"Number of accessed reports: {len(unique_reports)}")

    def _load_access_logs(self, nginx_logs_path):
        file_path = os.path.join(nginx_logs_path, NGINX_ACCESS_LOG_FILE)
        if os.path.isfile(file_path):
            with open(file_path, "r") as file:
                log_lines = file.readlines()
                log_lines = [line.rstrip() for line in log_lines]
                return log_lines
        else:
            raise ValueError(f"File '{file_path}' does not exist")

    def _parse_access_logs(self, log_lines):
        # regex for nginx log
        # https://gist.github.com/hreeder/f1ffe1408d296ce0591d
        line_format = re.compile(
            r"""(?P<ipaddress>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"""
            r""" - (?P<remoteuser>.+)"""
            r""" \[(?P<time>\d{2}\/[a-z]{3}\/\d{4}:\d{2}:\d{2}:\d{2} (\+|\-)\d{4})\]"""
            r""" (["](?P<method>.+) (?P<url>.+) (http\/[1-2]\.[0-9])["])"""
            r""" (?P<statuscode>\d{3}) (?P<bytessent>\d+)"""
            r""" (["](?P<refferer>(\-)|(.+))["]) (["](?P<useragent>.+)["])""",
            re.IGNORECASE,
        )

        # strptime format for nginx datetime
        # Example: 09/May/2022:17:50:43 +0200
        time_format = "%d/%b/%Y:%H:%M:%S %z"

        # regex for report URL
        report_url_format = re.compile(
            r"\/reports\/(?P<report_id>[a-z0-9-]+)\.html",
            re.IGNORECASE,
        )

        report_access_log = []

        # iterate over each line in the log
        for log_line in log_lines:
            log_matches = re.search(line_format, log_line)

            # if line format does not match, continue with next line
            if not log_matches:
                continue

            # extract data
            log_data = log_matches.groupdict()
            ip = log_data["ipaddress"]
            time_str = log_data["time"]
            url = log_data["url"]
            status = int(log_data["statuscode"])

            # parse time
            time = datetime.strptime(time_str, time_format)

            # check if report was requested
            report_matches = report_url_format.match(url)
            if not report_matches or status != 200:
                continue

            report_id = report_matches.groupdict()["report_id"]
            report_access_log.append(
                {
                    "ip": ip,
                    "datetime": time,
                    "report_id": report_id,
                }
            )

        return report_access_log

    def _process_report_access_logs(self, report_access_logs, start_date):
        report_access_logs = sorted(report_access_logs, key=lambda x: x.get("datetime"))

        result = {}
        for log in report_access_logs:
            report_id = log.get("report_id")
            if report_id not in result:
                # calculate days between start of experiment and first report access
                time_delta = log.get("datetime") - start_date
                days_after_start = time_delta.days

                # reminders were sent out two days late
                if days_after_start > 14:
                    days_after_start -= 2

                result[report_id] = {
                    "first_access": log.get("datetime"),
                    "days_after_start": days_after_start,
                    "access_count": 0,
                    "access_logs": [],
                }

            # increase access count by one
            result[report_id]["access_count"] += 1
            result[report_id]["access_logs"].append(log)

        return result
