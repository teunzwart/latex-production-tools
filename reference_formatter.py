"""
Automatically format references in a tex file.
"""

from reference_utils import Reference, ReferenceUtils
from latex_utils import read_tex_file, write_tex_file, cli_parser

class ReferenceFormatter(ReferenceUtils):
    def __init__(self, tex_file, debug):
        self.tex_file = tex_file
        self.debug = debug
        self.tex_source = read_tex_file(self.tex_file)

    def main(self):
        bibtex_entries = self.extract_bibtex_items(self.tex_source)
        for i, bibtex_entry in enumerate(bibtex_entries):
            print(f"Processing reference {i+1:>{len(str(len(bibtex_entries)))}} of {len(bibtex_entries)}... ", end='')
            reference = Reference(bibtex_entry.rstrip())
            print(reference.get_crossref_data())
            reference.extract_reference_data()
            reference.reformat_original_reference()
            reference.format_reference()
            self.tex_source = self.tex_source.replace(reference.bibitem_data, f"\\bibitem{{{reference.bibitem_identifier}}} TODO\n{reference.reformatted_original_reference}\n\n%{reference.formatted_reference}\n\n\n")
        if not self.debug:
            write_tex_file(self.tex_file, self.tex_source)


if __name__ == '__main__':
    args = cli_parser()
    reference_formatter = ReferenceFormatter(args.tex_file, args.debug)
    reference_formatter.main()
