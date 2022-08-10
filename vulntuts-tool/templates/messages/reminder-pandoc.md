{{ "Dear " ~ tutorial_author if tutorial_author and contact_author else "Hello" }},

{% if contact_author %}
We recently contacted you because the programming tutorial at {{ tutorial_url }} contains code that is susceptible to {{ "a security vulnerability" if count_vulnerabilities == 1 else "several security vulnerabilities" }} (see the original message attached below and the report provided by as at {{ report_url }} ).
{% else %}
We recently contacted you because the programming tutorial at {{ tutorial_url }}{% if tutorial_author %} written by {{ tutorial_author }}{% endif %} contains code that is susceptible to {{ "a security vulnerability" if count_vulnerabilities == 1 else "several security vulnerabilities" }} (see the original message attached below and the report provided by us at {{ report_url }} ).
{% endif %}

We have not yet heard back from you. Have you found time to fix the vulnerability? If fixing the tutorial is too time-consuming, please consider adding a clearly visible warning to the tutorial notifying users of the vulnerability or deleting the tutorial if it is not relevant anymore.

If you did not understand the vulnerability or if you need further assistance or information, you may simply respond to this email.

Best regards,
Tobias Heckel


---

We are IT security researchers from the University of Bamberg, Germany. As part of our research, we have studied the prevalence of vulnerabilities in programming tutorials (i.e., how often tutorials contain code snippets that could be hacked by attackers). For reasons of research ethics, we would like to inform you that your tutorial contains code that is susceptible to the following security {{ "vulnerability" if count_vulnerabilities == 1 else "vulnerabilities" }}:

{% for vuln_summary in vuln_summaries %}
- {{ vuln_summary.name }}: {{ vuln_summary.description }}

{% endfor %}
Please consider fixing the {{ "vulnerability" if count_vulnerabilities == 1 else "vulnerabilities" }} in your tutorial.


How {{ "does the vulnerability" if count_vulnerabilities == 1 else "do the vulnerabilities" }} work?

{% if support_explanation or support_individual %}
We have provided a detailed and illustrated explanation of the {{ "vulnerability" if count_vulnerabilities == 1 else "vulnerabilities" }} with the vulnerable code from your tutorial at the following private URL: {{ report_url }}
The report also contains an explanation of how to fix the {{ "vulnerability" if count_vulnerabilities == 1 else "vulnerabilities" }}. The vulnerable code is not included in this email to prevent this email from being rejected by spam filters.
{% else %}
We have provided a short explanation of the {{ "vulnerability" if count_vulnerabilities == 1 else "vulnerabilities" }} with the vulnerable code from your tutorial at the following private URL: {{ report_url }}
The vulnerable code is not included in this email to prevent this email from being rejected by spam filters.
{% endif %}
Only people who know the URL have access to the report. It is not publicly available and we have not shared and will not share the URL with anyone else.


{% if support_reason %}
Why should you fix the {{ "vulnerability" if count_vulnerabilities == 1 else "vulnerabilities" }}?

Beginners who learn to program with tutorials containing vulnerable code are generally not aware of security issues. They may write and publish software that is susceptible to various attacks. Even advanced and professional programmers often copy vulnerable code from tutorials into their software projects. Studies have shown that up to 15% of all Android apps contain code snippets with security vulnerabilities that were copied from StackOverflow (https://arxiv.org/pdf/1710.03135.pdf). Therefore, it is critical that programmers are educated about the security aspects of programming and that tutorials do not contain vulnerable code.


{% endif %}
Please note that, as a public university, we are not interested in and cannot accept financial benefits for this notification. Also, we will not disclose the above-mentioned {{ "vulnerability" if count_vulnerabilities == 1 else "vulnerabilities" }} publicly. This message is intended exclusively for you personally to inform you about the security {{ "vulnerability" if count_vulnerabilities == 1 else "vulnerabilities" }}.

{% if support_explanation or support_individual %}
Should you need further information or have any other questions or feedback, please do not hesitate to {{ "respond to this email." if is_email else "contact me at research.psi@uni-bamberg.de"}}
{% else %}
Should you have any feedback, please do not hesitate to {{ "respond to this email." if is_email else "contact me at research.psi@uni-bamberg.de"}}
{% endif %}

Best regards,
Tobias Heckel, Master's student at University of Bamberg
-- 
Privacy and Security in Information Systems Group
https://www.uni-bamberg.de/en/psi/
University of Bamberg, Germany
