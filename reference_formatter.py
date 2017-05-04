"""Automatically format references in a LaTeX file."""

import argparse

from reference_utils import Reference, extract_bibtex_items
from latex_utils import read_latex_file, write_latex_file


def format_references(latex_source):
    bibtex_entries = extract_bibtex_items(latex_source)
    for i, bibtex_entry in enumerate(bibtex_entries):
        print(f"Processing reference {i+1:>{len(str(len(bibtex_entries)))}} of {len(bibtex_entries)}...")
        reference = Reference(bibtex_entry.rstrip())
        reference.main()
        latex_source = latex_source.replace(reference.bibitem_data, f"\\bibitem{{{reference.bibitem_identifier}}} TODO\n{reference.reformatted_original_reference}\n\n%{reference.formatted_reference}\n\n\n")
    return latex_source


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('latex_file')
    args = parser.parse_args()
    latex_source = read_latex_file(args.latex_file)
    latex_source = format_references(latex_source)
    write_latex_file(args.latex_file, latex_source)
