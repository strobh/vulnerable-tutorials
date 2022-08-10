# Master's Thesis: Vulnerable Tutorials

This repository contains the code, data and supplementary material for my master's thesis on security vulnerabilities in online programming tutorials.

Brief summary of the material:

- `vulntuts-tool` contains the tool supporting the study. It creates a list of search queries, searches for tutorials via Google, YouTube and Twitter, supports the researcher while inspecting search results, manages the study (e.g., assigning to groups, creating notifications and reports), scans tutorials to check for changes, and evaluates the results of the study.
- `vulntuts-tool/templates` contains the templates for the notifcation messages and the detailed reports sent to the tutorial authors.
- `vulntuts-tool/config` contains the config files, including the queries used to search for tutorials.
- `reports` contains the parts of the reports explaining the type of vulnerability and how the vulnerability can be fixed.

The `vulntuts-tool` directory contains a detailed `README` file explaining the tool.