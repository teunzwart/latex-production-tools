"""Automatically format references in a LaTeX file."""

import argparse
from multiprocessing import Pool

from reference_utils import Reference, extract_bibtex_items
from latex_utils import read_latex_file, write_latex_file


class ReferenceFormatter:
    def __init__(self, add_arxiv):
        self.add_arxiv = add_arxiv

    def get_reference(self, bibtex_entry):
        """Wrapper for multithreading."""
        reference = Reference(bibtex_entry.rstrip(), self.add_arxiv)
        reference.main()
        return reference.bibitem_data, reference.bibitem_identifier, reference.reformatted_original_reference, reference.formatted_reference

    def format_references(self, latex_source):
        """Format all references in the given LaTeX source."""
        bibtex_entries = extract_bibtex_items(latex_source)
        # Parallelising the reference lookup gives a 15x speedup.
        # Values larger than 15 for the poolsize do not give a further speedup.
        with Pool(15) as pool:
            res = pool.map(self.get_reference, bibtex_entries)
        for r in res:
            bibitem_data, bibitem_identifier, reformatted_original_reference, formatted_reference = r
            latex_source = latex_source.replace(bibitem_data, f"\\bibitem{{{bibitem_identifier}}} \\textcolor{{red}}{{TODO}}\n{reformatted_original_reference}\n\n%{formatted_reference}\n\n\n")
        return latex_source


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('latex_file')
    parser.add_argument('--add_arxiv', action="store_true")
    args = parser.parse_args()
    latex_source = read_latex_file(args.latex_file)
    print("Processing references...")
    reference_formatter = ReferenceFormatter(args.add_arxiv)
    latex_source = reference_formatter.format_references(latex_source)
    write_latex_file(args.latex_file, latex_source)
