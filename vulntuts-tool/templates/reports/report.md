---
title: Explanation of the Vulnerabilities in the Programming Tutorial
header-includes: <link href="static/prism.css" rel="stylesheet" type="text/css"><script src="static/prism.js"></script>
---

This page provides a detailed and illustrated explanation of the security {{ "vulnerability" if count_vulnerabilities == 1 else "vulnerabilities" }} found in the programming tutorial at <{{ tutorial_url }}>.

The programming tutorial contains code that is susceptible to the following security {{ "vulnerability" if count_weaknesses == 1 else "vulnerabilities" }}:

{% for weakness_summary in weakness_summaries %}
- **{{ weakness_summary.name }}**
{% endfor %}


{% for vulnerability in vulnerabilities %}
## {{ vulnerability.name }}

{{ vulnerability.summary }}

### Where Is the Problem?

{% if support_individual %}
<div class="individual-explanation">

{{ vulnerability.description }}

</div>
{% endif %}

The following code from the tutorial {{ "(at time " ~ vulnerability.video_timestamp ~ ") " if vulnerability.video_timestamp else "" }}is susceptible to the attack:

<pre class="language-{{ vulnerability.language }} line-numbers" data-line="{{ vulnerability.line_numbers }}"><code>{{ vulnerability.code }}</code></pre>

*Note*: This issue may exist multiple times in the tutorial, but we only list one example to keep this report short and concise.


{% if support_explanation %}
### How Can an Attacker Exploit the Vulnerability?

{{ vulnerability.exploit }}


### How Can You Fix the Vulnerability?

{{ vulnerability.fix }}
{% endif %}

{% endfor %}


{% if support_reason %}
## Why Should You Fix the {{ "Vulnerability" if count_vulnerabilities == 1 else "Vulnerabilities" }}?

Beginners who learn to program with tutorials containing vulnerable code are generally not aware of security issues. They may write and publish software that is susceptible to various attacks. Even advanced and professional programmers often copy vulnerable code from tutorials into their software projects. Studies have shown that up to 15% of all Android apps contain code snippets with security vulnerabilities that were copied from StackOverflow (<https://arxiv.org/pdf/1710.03135.pdf>). Therefore, it is critical that programmers are educated about the security aspects of programming and that tutorials do not contain vulnerable code.
{% endif %}


## Further Information on This Report

Only people who know the URL of this page have access to this report. It is not publicly available and we have not shared and will not share the report with anyone else. Also, we will not disclose the above-mentioned {{ "vulnerability" if count_vulnerabilities == 1 else "vulnerabilities" }} publicly. This message is intended exclusively for you personally to inform you about the security {{ "vulnerability" if count_vulnerabilities == 1 else "vulnerabilities" }}.

Please also note that, as a public university, we are not interested in and cannot accept financial benefits for this notification. 
