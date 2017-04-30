""" Utilities to work with LaTeX files. """

import re
import requests
import unicodedata
import sys


def read_tex_file(tex_file, encoding="utf-8"):
    with open(tex_file, 'r', encoding=encoding) as data:
        tex_source = data.read()
    return tex_source


def write_tex_file(tex_file, tex_source):
    with open(tex_file, 'w') as open_file:
        open_file.write(tex_source)


def get_relevant_warnings(log_file):
    """Extract relevant warnings from a LaTeX log file."""
    overfull_lines = re.findall(r"Overfull \\hbox .*", log_file)
    undefined_references = re.findall(r"LaTeX Warning: Citation `.*?' on page .*", log_file)
    return overfull_lines + undefined_references


def remove_accented_characters(string):
    return unicodedata.normalize('NFD', string).encode('ascii', 'ignore').decode('utf-8')


def open_webpage(address):
    """Return the request server response for a webpage."""
    try:
        server_response = requests.get(address, timeout=10)
        server_response.raise_for_status()
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
        sys.exit(e)
    else:
        return server_response
