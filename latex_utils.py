"""
Utilities to work with LaTeX files.
"""

import argparse
import re
import unicodedata

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


def convert_equations(tex_source):
    """
    Automatically insert math atoms in a tex file ($[]$ -> ${[]}$).

    Inpsired by http://stackoverflow.com/questions/14182879/regex-to-match-latex-equations
    """
    regex = r"""
    (?<!\\)    # negative look-behind to make sure start is not escaped
    (?:        # start non-capture group for all possible match starts
        # group 1, match dollar signs only
        # single or double dollar sign enforced by look-arounds
        ((?<!\$)\${1}(?!\$))|
        # group 2, match escaped parenthesis
        (\\\()
    )
    (.*?(.*?)?.*?)  # match everything in between
    (?<!\\)  # negative look-behind to make sure end is not escaped
        # if group 1 was start, match \1
        (?(1)(?<!\$)\1(?!\$)|
        # if group 2 was start, escaped parenthesis is end
    (?(2)\\\)))
    """
    regex = re.compile(regex, re.MULTILINE | re.VERBOSE)
    tex_source = re.sub(regex, "${\\3}$", tex_source)
    return tex_source


def remove_accented_characters(string):
    return unicodedata.normalize('NFD', string).encode('ascii', 'ignore').decode('utf-8')

        
def cli_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('tex_file')
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = cli_parser()
    log_file = read_tex_file(args.tex_file, encoding="latin-1")
    relevant_warnings = get_relevant_warnings(log_file)
    for warning in relevant_warnings:
        print(warning)


