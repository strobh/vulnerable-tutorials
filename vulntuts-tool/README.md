# Vulntuts: Collection, Inspection and Scanning of Online Programming Tutorials with Security Vulnerabilities

The tool *vulntuts* is used to collect, inspect and scan for security vulnerabilities in online programming tutorials. The tool searches for online programming tutorials on Google, YouTube, and Twitter using a list of queries. The tutorials can then be manually inspected for security vulnerabilities and automatically re-scanned in the future to determine whether the vulnerabilities have been fixed.

## Installation

Build *vulntuts* from the source:

```
python3 -m pip install --upgrade build
python3 -m build
```

Install *vulntuts* from the source:

```
python3 -m pip install .
```

Or install *vulntuts* from the source while allowing changes to the code (editable):

```
python3 -m pip install -e .
```

## Usage

Run *vulntuts*:

```
vulntuts {COMMAND} [OPTIONS]
```

You can run *vulntuts* as a package if running it as a script doesn't work:

```
python3 -m vulntuts {COMMAND} [OPTIONS]
```

### Commands

```
suggest-terms       Retrieve term suggestions for search queries used to search
                    for tutorials
generate-queries    Generate queries used to search for tutorials
search              Execute search queries on different search engines and
                    collect the results
sample              Randomly sample search results to be inspected manually
inspect             Inspect search results manually to identify vulnerable
                    tutorials
experiment          Manage experiment (assign to groups, create emails and
                    reports)
scan                Scan vulnerable tutorials automatically and try to determine
                    whether the vulnerabilities that were previously identified
                    during the inspection were fixed
data                Manage and print data and calculate statistics
open-browser        Open browser with vulntuts' browser profile, e.g., to
                    install extensions
```

```
vulntuts suggest-terms [-h] [--source {google-suggest,stack-overflow}]
vulntuts generate-queries [-h] [-q QUERIES]
vulntuts search [-h] [-c CONFIG] --engine {google,youtube,twitter}
vulntuts sample [-h] [-c CONFIG] [-n SAMPLE_SIZE] [--weighted] [--keep-previous]
vulntuts inspect [-h] [-c CONFIG] [--type {all,webpage,video}] [--language LANGUAGE]
                      [--reinspect [{search-results,tutorials}]]
vulntuts experiment [-h] [--initialize] [--print-groups] [--create-reports] [--create-contacts]
                         [--remove-contact CONTACT_DETAILS] [--remove-contacts CONTACT_FILE] [--create-messages]
                         [--contact] [--parse-nginx-logs] [--create-results] [--start START_DATE]
                         [--undelivered UNDELIVERED_FILE] [--replies REPLIES_FILE]
vulntuts scan [-h] [-c CONFIG] [--manu] [--final]
vulntuts data [-h] [--info URL_OR_ID] [--stats] [--full-stats]
vulntuts open-browser [-h] [--tutorial URL_OR_ID]
```

## Setup / Config

### Data Directory and Template/Config Files

*vulntuts* reads and stores its data in the current working directory. Therefore, create a new directory where the data will be stored and cd into it:

```
mkdir data && cd data
```

Create a directory named `config` inside of your data directory for the config files:

```
mkdir config
```

#### Templates for notifications and reports

*vulntuts* generates its notifications and reports based on template files that must be located in a directory named `templates`. Copy the `templates` directory from the repository into your data directory:

```
mkdir templates
cp PATH_TO_PROJECT/templates/ templates
```

#### Config file `queries.yaml`

*vulntuts* generates its search queries (`vulntuts generate-queries`) based on a set of query templates defined in the file `queries.yaml`. Copy the file `queries.example.yaml` to the `config` directory inside your data directory, rename it to `queries.yaml` and adjust the templates if needed:

```
cp PATH_TO_PROJECT/config/queries.example.yaml config/queries.yaml
```

Example for `queries.yaml`:

```yaml
templates:
    php-tutorials:
        - php
        - tutorial
    php-subjects:
        - php
        - subjects
        - tutorial

terms:
    php:
        - php
    subjects:
        - encryption
        - database
    tutorial:
        - tutorial
        - example
        - how to
```

Config options in `queries.yaml`:

- `templates`: The templates describe how the queries are constructed:
    - The key is the name of the template (i.e., the query category's name).

      **Example**: `php-tutorials`

    - The value defines the template and consists of a list (indicated by dashes) of term groups.
      The queries are constructed by looking up the terms in the term groups (e.g., `tutorial`, `example` and `how to` for the term group `tutorial`) and generating each possible combination of these terms (cartesian product). Each combination of terms is a separate query.
      The order of the term groups is preserved when constructing the query.

      **Examples**:

      For the template `php-subjects` above the resulting queries are: `php encryption tutorial`, `php encryption example`, `php encryption how to`, `php database tutorial`, `php database example`, and `php database how to`.

      Assuming a template with the term groups `group1` (with the terms `a1` and `a2`) and `group2` (with the terms `b1` and `b2`). The resuling queries would be `a1 b1`, `a1 b2`, `a2 b1`, and `a2 b2`.

- `terms`: A term groups consists of a list of terms to be used when constructing queries. See `templates` above for more details.
    - The key is the name of the term group.

      **Example**: `tutorial`

    - The value defines the list (indicated by dashes) of terms.

      **Example**: The term group `tutorial` contains the terms `tutorial`, `example` and `how to`.

#### Config file `config.yaml`

Copy the file `config.example.yaml` to the `config` directory inside your data directory and rename it to `config.yaml`:

```
cp PATH_TO_PROJECT/config/config.example.yaml config/config.yaml
```

Example for `config.yaml`:

```yaml
apis:
    google:
        search_engine_id: YOUR_SEARCH_ENGINE_ID
        api_key: YOUR_API_KEY
    youtube:
        api_key: YOUR_API_KEY
    twitter:
        bearer_token: YOUR_BEARER_TOKEN

search:
    google:
        language: en
        num_results: 30
    youtube:
        language: en
        num_results: 50
    twitter:
        language: en
        num_results: 500

sampling:
    max_rank:
        google: 30
        youtube: 50
        twitter: 50
    proportion:
        type:
            video: 0.5
            webpage: 0.5
        engine:
            video: null
            webpage:
                google: 0.8
                twitter: 0.2
    excluded_domains:
        # Q&A platforms
        - stackoverflow.com
        - stackexchange.com
        - quora.com
        - ...
```

Config options in `config.yaml`:

- `apis`: The parameters and credentials for the search APIs of Google (Custom Search API), YouTube (YouTube Data API) and Twitter (Twitter API). The YouTube Data API is also used to retrieve metadata about tutorial videos during inspection and scanning. Follow the instructions below to set up the APIs.

- `search`: The configuration for searching tutorials (`vulntuts search`):
    - `language` defines the language of the tutorials to be searched and is passed to the search engines.

      **Default**: en

    - `num_results` defines the number of results to fetch from the search engines.

      The highest rank up to which search results should then actually be used for the manual inspection (can be a subset of the search results) is defined under `sampling`.

      **Default**: 30 results for Google (3 pages) and the maximum number of results that are allowed to be retrieved in one request for YouTube (50) and Twitter (500).

- `sampling`: The configuration for sampling search results for the manual inspection (`vulntuts sample`):
    - `max_rank` defines the highest rank up to which search results should be included in the sample.

      **Default**:

      ```
      google: 30
      youtube: 50
      twitter: 50
      ```

      **Example**: If you set the max rank for Google to 10, only the first result page is considered.

    - `proportion`: The proportion of inspection types and engine results in the final sample.

      First, the search results are filtered by type (video or webpage). Second, the search results are filtered by their source engine (Google, YouTube or Twitter). Then the sample is drawn from each subset of search results (filtered by inspection type and search engine) according to the defined proportion. Finally, the samples are combined into one final sample.

      The proportion for the different inspection type is required (config option `sampling.proportion.type`). The proportion for the search engines (config option `sampling.proportion.engine`) can be left empty (value `null`) resulting in drawing the sample from all search engines without considering their proportion in the final sample. This means that a search engine with a large number of results will also be represented more often in the sample than a search engine with few results.

      Duplicate inspections are prevented. The sample size itself is specified in the sample command.

      **Default**: Videos and websites each account for 50% of inspections. Videos are sampled from all search engines without considering their proportion. Webpages are sampled such that 80% of the sample are results from Google and 20% of the sample are results from Twitter.

    - `excluded_domains`: The list of first-level domains that should be excluded from the sample.

      **Default**: By default the list is empty. In the example config, this list contains Q&A platforms, commercial programming tutorials, and the official documentations of programming languages.

### Search Engines / APIs

In order to execute the search command (`vulntuts search`) or the inspection and scanning of YouTube videos (`vulntuts inspect` and `vulntuts scan`), you must first set up access to the APIs you want to use:

#### Google

To set up a Google *Custom Search Engine*, follow the instructions below (see <https://stackoverflow.com/a/11206266>):

1. Go to <https://programmablesearchengine.google.com/cse/all>.
2. Start creating a new Custom Search Engine (CSE) by clicking on **New search engine** or **Add**.
2. Enter a valid URL under **Sites to search**, e.g., `example.org`. This URL will be removed later, so any valid URL can be used.
3. Enter a name and complete any other necessary steps to create the CSE.
4. Navigate to the **Control Panel** to edit the CSE.
5. Copy the **Search engine ID** and enter it in the config file.
5. Enable **Search the entire web**.
6. Under **Sites to search**, select and delete the URL you entered during the initial setup.

To set up access to the *Custom Search API*, visit the *Google Cloud Console* (<https://console.cloud.google.com>):

1. Create a new project.
2. Navigate to **APIs and services**, e.g., by searching for it.
3. Click on the button **Enable APIs and services**.
4. Search for **Custom Search API** and select it.
5. Enable the API by clicking on **Enable**; you will be forwarded to the dashboard for the API.
6. Navigate back to **APIs and services** and its subpage **Credentials** to view all credentials. (Do not confuse this with the **Credentials** page for the **Custom Search API** itself!).
8. Click on the button **Create credentials** and select **API key** from the dropdown menu.
9. Copy the API key and enter it in the config file.
10. You might want to restrict the usage of the API key to the Custom Search API by editing it.

Please note: Google's Custom Search API only allows 100 search requests per day and project for free. If you need more, you may sign up for billing in the Google Cloud API Console (see [Custom Search API pricing](https://developers.google.com/custom-search/v1/overview?hl=en_GB#pricing), currently 5 \$ per 1000 queries, up to 10k queries per day).

#### YouTube

Follow the steps in the Google Cloud Console described above for the Google search engine. However, enable the *YouTube Data API* instead of (or in addition to) the Custom Search API.

Similar to the Google's Custom Search API, the YouTube Data API only allows 100 search requests per day and project for free. If you need more, you can request additional quota (see [YouTube Data API quota](https://developers.google.com/youtube/v3/getting-started#quota)).

#### Twitter

To use the Twitter search in *vulntuts*, you need access to Twitter's *full-archive search*, i.e., the Twitter API for academic research. You can apply for it via Twitter's *Developer Portal* (<https://developer.twitter.com>). After you gained access to the API, create a new project and copy the *Bearer Token* to the config file.

#### Quota for Google and YouTube

Alternatively, you can create multiple projects in the Google Cloud Console with access to the Custom Search API or the YouTube Data API. *vulntuts* accepts a list of API keys in the configuration file and tries them one by one. *Caution*: This violates Google's API usage policy and may result in your account being suspended. I **strongly advise against** using this feature.
