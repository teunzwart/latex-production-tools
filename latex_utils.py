"""
Utilities to work with LaTeX files.
"""

import argparse
import re

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


