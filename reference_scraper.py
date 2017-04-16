"""
Automatically get author names of references in a tex file.
"""

import sys
if sys.version_info < (3, 6):
    sys.exit("Can't execute script. At least Python 3.6 is required.")

import argparse
import json
import re
import urllib.request
import socket
import webbrowser
import xml.etree.ElementTree as et


class ReferenceScraper:
    def __init__(self, tex_file):
        self.tex_file = tex_file
        self.names = []
        self.check_manually = []
        self.all_dois = []
        self.no_dois = []
        self.references = None
        self.arxiv_ids = []

    def parse_manually_checked_references(self):
        if len(self.check_manually) == 0:
            print("There are no reference to check manually.")
        else:
            print("The following references have to be checked by hand:")
            for ref in self.check_manually:
                print(ref, '\n')

    def get_bibtex_items(self):
        with open(self.tex_file, 'r') as f:
            tex_source = f.read()
        bibitem_regex = re.compile(r"\\bibitem{.*?}(.+?)(?=\\bibitem{|\\end{thebibliography})", re.DOTALL)
        self.references = bibitem_regex.findall(tex_source)
        self.references = [re.sub("\s\s+|\\\\newblock|\n", " ", r) for r in self.references]

    def get_doi(self):
        for ref in self.references:
            try:
                doi = re.search(r"\\doi{(.*?)}", ref).group(1)
                self.all_dois.append(doi)
            except AttributeError:
                self.no_dois.append(ref)

    def parse_no_doi_refs(self):
        """Parse references without DOI's."""
        for ref in self.no_dois:
            if "arxiv" in ref:
                arxiv_id = re.search(r"\\href{.*?}{arXiv:(.*?)}", ref).group(1)
                self.arxiv_ids.append(arxiv_id)
            else:
                if re.search(r"\(20\d{2}\)", ref) or re.search(r"\(20\d{2}--\)", ref):
                    self.check_manually.append(ref)

    def get_names_doi_refs(self):
        """Extract author names associated with DOI's using the Crossref api."""
        for i, ref in enumerate(self.all_dois):
            print(f"Processing DOI {i+1:>{len(str(len(self.all_dois)))}} of {len(self.all_dois)}... ", end='')
            try:
                with urllib.request.urlopen(f"https://api.crossref.org/works/{ref}", timeout=10) as data:
                    data = json.loads(data.read().decode('utf-8'))
                    year = data['message']['issued']['date-parts'][0][0]
                    if year is None:
                        self.check_manually.append(ref)
                        print(f"failed (no year specified in api response, {ref})")
                        continue
                    try:
                        if year >= 2000:
                            authors = data['message']['author']
                            for a in authors:
                                self.names.append(f"{a['given']} {a['family']}")
                            print(f"succes (result from 2000 or later: {ref})")
                        else:
                            print(f"succes (but result too old: {ref})")
                    except KeyError:
                        self.check_manually.append(ref)
                        print(f"failed (no authors specified in api response: {ref})")
            except socket.timeout:
                self.check_manually.append(ref)
                print(f"failed (connection timeout: {ref})")
                continue
            except urllib.error.HTTPError as e:
                self.check_manually.append(ref)
                print(f"failed ({e}, the DOI may be malformed: {ref})")
                continue

    def get_names_arxiv_refs(self):
        """Get names of authors of arXiv entries using the arXiv api."""
        for i, ref in enumerate(self.arxiv_ids):
            print(f"Processing arXiv entry {i+1:>{len(str(len(self.arxiv_ids)))}} of {len(self.arxiv_ids)}...", end='')
            try:
                with urllib.request.urlopen(f"http://export.arxiv.org/api/query?search_query={ref}", timeout=10) as data:
                    # TODO: Improve XML parsing.
                    data = et.fromstring(data.read())
                    found_author = False
                    for z in data.find('.')[-1]:
                        try:
                            author = z.find('{http://www.w3.org/2005/Atom}name').text
                            self.names.append(author)
                            found_author = True
                        except AttributeError:
                            pass
                    if found_author:
                        print(f"succes ({ref})")
            except socket.timeout:
                self.check_manually.append(ref)
                print(f"failed (connection timeout: {ref})")
                continue
            except urllib.error.HTTPError as e:
                self.check_manually.append(ref)
                print(f"failed ({e}, the arXiv identifier may be malformed: {ref})")
                continue

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

    @staticmethod
    def cli_parsing():
        parser = argparse.ArgumentParser()
        parser.add_argument('tex_file')
        parser.add_argument('--debug', action="store_true")
        args = parser.parse_args()
        return args


if __name__ == '__main__':
    args = ReferenceScraper.cli_parsing()
    reference_scraper = ReferenceScraper(args.tex_file)
    reference_scraper.get_bibtex_items()
    reference_scraper.get_doi()
    reference_scraper.parse_no_doi_refs()
    reference_scraper.get_names_arxiv_refs()
    if not args.debug:
        reference_scraper.get_names_doi_refs()
    reference_scraper.get_unique_names()
    if not args.debug:
        reference_scraper.open_google_pages()
    reference_scraper.parse_manually_checked_references()
