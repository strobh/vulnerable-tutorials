{{ "Dear " ~ tutorial_author if tutorial_author and contact_author else "Hello" }},

We recently informed you about {{ "a security vulnerability" if count_vulnerabilities == 1 else "several security vulnerabilities" }} in your tutorial at {{ tutorial_url }}. This notification was part of an experiment in which you participated.

The experiment aims to determine how authors of tutorials with security vulnerabilities can be effectively notified so that the vulnerabilities are fixed. The knowledge gained from this experiment will help to provide better notifications in the future and improve programming tutorials on the web.

To better understand how the participants reacted to the notification, we would appreciate it if you participated in a 5-minute survey at {{ survey_url }}

The survey covers how you perceived the notification, whether you knew about the vulnerability beforehand, and your background on software security in general. Participation is anonymous and voluntary, of course.


Description of the Experiment

In the course of the experiment, we have sent out different notification texts and reports that informed the participants in varying detail about the vulnerabilities and the reasons for fixing them. Afterwards, we observed how the participants reacted to the different messages and whether they adapted their tutorials.

For the study, we have collected information about the tutorials and their authors. We collected the URLs of relevant tutorials for the experiment and examined them for security vulnerabilities. Furthermore, we collected the name and contact details of the authors from the website to send the notification.

We make every effort to ensure that you do not suffer any harm as a result of the study (equal opportunities and data protection). The project was reviewed by the Ethics Committee of the University of Bamberg, Germany, and approval was granted. We only use the collected data for scientific purposes. The data is only stored on access-restricted systems, not passed on to third parties and only published in anonymized form.

You can find detailed information about the experiment as well as information on data protection at {{ privacy_policy_url }}
You may choose not to participate in this study, i.e., to withdraw from the study. Your data will then be deleted and not evaluated for the study.


{% if not support_individual %}
Full Report with More Details than in the Previous Notifications

In the previous notifications, you only received a shortened version of the vulnerability report which did not contain all the available information. You are now receiving the full report in order to ensure equal opportunities for all participants: {{ full_report_url }}
The full report contains a detailed, individual and illustrated explanation of how the {{ "vulnerability works" if count_vulnerabilities == 1 else "vulnerabilities work" }} and how you can fix it.


{% endif %}
If you have any feedback or questions about the experiment and the survey, please do not hesitate to {{ "respond to this email" if is_email else "contact me at research.psi@uni-bamberg.de" }}.

Best regards,
Tobias Heckel, Master's student at University of Bamberg
-- 
Privacy and Security in Information Systems Group
https://www.uni-bamberg.de/psi
University of Bamberg, Germany
