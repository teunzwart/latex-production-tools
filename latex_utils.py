""" Utilities to work with LaTeX files. """

import re
import requests
import unicodedata
import sys


def read_latex_file(latex_file):
    try:
        with open(latex_file, 'r', encoding="utf-8") as data:
            latex_source = data.read()
    except UnicodeDecodeError:
        with open(latex_file, 'r', encoding="latin-1") as data:
            latex_source = data.read()
    return latex_source


def write_latex_file(latex_file, latex_source):
    with open(latex_file, 'w') as open_file:
        open_file.write(latex_source)


def get_relevant_warnings(log_file):
    """Extract relevant warnings from a LaTeX log file."""
    overfull_lines = re.findall(r"Overfull \\hbox .*", log_file)
    undefined_references = re.findall(r"LaTeX Warning: Citation `.*?' on page .*", log_file)
    return overfull_lines + undefined_references


def remove_accented_characters(string):
    """Change accented characters to their ASCII equivalents."""
    return unicodedata.normalize('NFD', string).encode('ascii', 'ignore').decode('utf-8')


def open_webpage(address, exit_on_error=True):
    """Return succes/failure and the request server response for a webpage."""
    try:
        server_response = requests.get(address, timeout=20)
        server_response.raise_for_status()
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
        if exit_on_error:
            sys.exit(e)
        else:
            return False, e
    else:
        return True, server_response
