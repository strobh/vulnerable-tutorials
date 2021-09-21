import itertools
import os

from pathlib import Path


def construct_q(*terms):
    queries = list(itertools.product(*terms))
    return [' '.join(q) for q in queries]


def save_queries(queries, filename):
    with open(filename, 'w') as file:
        for q in queries:
            file.write("%s\n" % q)


langs = ["php"]
tutorial = [
    "tutorial", "example", "how to",
    "learn", "course",
    "for beginners", "for dummies"]
subjects_normal = [
    "database", "mysql", "sql",
    "login", "login page", "password login", 
    "registration", "password", "password protected", "user management",
    "contact page", "contact form",
    "comment section", "comment form",
    "forum",
    "social media",
    "search form",
    "form",
    "random number"]
subjects_technical = [
    "authentication", "authentication system", "password hashing",
    "session", "session management",
    "random number seed"]
secure = ["secure", "best practice"]

q_normal = construct_q(langs, subjects_normal, tutorial)
q_normal_sec = construct_q(langs, subjects_normal, tutorial, secure)
q_technical = construct_q(langs, subjects_technical, tutorial)
q_technical_sec = construct_q(langs, subjects_technical, tutorial, secure)

queries_dir = os.path.join('data', 'search-queries')
q_normal_file = os.path.join(queries_dir, 'web-normal.txt')
q_normal_sec_file = os.path.join(queries_dir, 'web-normal-sec.txt')
q_technical_file = os.path.join(queries_dir, 'web-technical.txt')
q_technical_sec_file = os.path.join(queries_dir, 'web-technical-sec.txt')

Path(queries_dir).mkdir(parents=True, exist_ok=True)
save_queries(q_normal, q_normal_file)
save_queries(q_normal_sec, q_normal_sec_file)
save_queries(q_technical, q_technical_file)
save_queries(q_technical_sec, q_technical_sec_file)
