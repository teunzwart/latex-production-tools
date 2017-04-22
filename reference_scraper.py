"""
Automatically get author names of references in a tex file.
"""


import argparse
import json
import re
import urllib.request
import socket
import webbrowser
import xml.etree.ElementTree as et

from reference_utils import Reference, ReferenceUtils
from latex_utils import read_tex_file, write_tex_file, cli_parser


class ReferenceScraper(ReferenceUtils):
    def __init__(self, tex_source. debug=False):
        self.tex_source = tex_source
        self.names = []
        self.unique_names = None
        self.check_manually = []

    def main(self):
        bibtex_entries = self.extract_bibtex_items(self.tex_source)
        for i, bibtex_entry in enumerate(bibtex_entries):
            print(f"Processing reference {i+1:>{len(str(len(bibtex_entries)))}} of {len(bibtex_entries)}... ", end='')
            reference = Reference(bibtex_entry.rstrip())
            data_status = reference.get_crossref_data()
            print(data_status)
            if "failed" in data_status:
                self.check_manually.append(reference.reformatted_original_reference)
            reference.extract_crossref_reference_data(format=False)
            if not reference.year:
                print("\tNo year specified in api response")
                self.check_manually.append(reference.reformatted_original_reference)
            elif reference.year >= 2000:
                if reference.authors:
                    for a in reference.authors:
                        self.names.append(f"{a['given']} {a['family']}")
                    print(f"\tSucces (result from 2000 or later)")
                else:
                    print(f"\tFailed (no authors specified in api response)")
                    self.check_manually.append(reference.reformatted_original_reference)
            else:
                print("\tSucces (but result too old)")
        self.get_unique_names()
        if not self.debug:
            self.open_google_pages()
        if len(self.check_manually) == 0:
            print("There are no reference to check manually.")
        else:
            print("The following references have to be checked by hand:")
            for reference in self.check_manually:
                print(reference, '\n')


    def get_unique_names(self):
        """Get unique names from a list of names."""
        name_dict = {}
        for name in list(set(self.names)):
            full_name = re.sub("\s\s+", " ", name.replace('.', ' '))  # Remove any dots and extraneous whitespace.
            abbrv_name = full_name
            # Create a normalized name that can be used to compare names with different levels of abbrevation.
            # TODO: Remove any accents and special characters from names to improve comparison.
            abbrv_name = ' '.join([n[:1] for n in abbrv_name.split(' ')[:-1]] + [abbrv_name.split(' ')[-1]])
            abbrv_name = abbrv_name.lower()
            if abbrv_name not in name_dict or len(name_dict[abbrv_name]) < len(full_name):
                name_dict[abbrv_name] = full_name
        self.unique_names = list(name_dict.values())
        print(f"The timely references were written by {len(self.names)} authors, of which {len(self.unique_names)} are unique.")
        print(sorted(self.unique_names, key=lambda x: x.split(' ')[-1]))

    def open_google_pages(self):
        print("Opening Google search pages (in batches of 10):")
        for i, name in enumerate(sorted(list(self.unique_names), key=lambda x: x.split(' ')[-1])):
            webbrowser.open(f"https://www.google.com/search?q={name.replace(' ', '+')}+physics")
            if (i + 1) % 10 == 0:
                input(f"Opening {i+1}/{len(self.unique_names)}. Press enter to open next 10...")


if __name__ == '__main__':
    args = cli_parser()
    tex_source = read_tex_file(args.tex_file)
    reference_scraper = ReferenceScraper(tex_source)
    reference_scraper.main()
    if not args.debug:
        reference_scraper.open_google_pages()
