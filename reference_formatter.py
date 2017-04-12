"""
Automatically format references in a tex file.
"""

import sys
if sys.version_info < (3, 6):
    sys.exit("Can't execute script. At least Python 3.6 is required.")

import argparse
import json
import re
import urllib.request
import socket


# Some additional abbreviations which are not provided by Crossref.
JOURNAL_ABBRVS = {"Nuclear Physics B":"Nucl. Phys. B",
                  "American Journal of Physics": "Am. J. Phys",
                  "Communications in Mathematical Physics": "Commun. Math. Phys.",
                  "J Stat Phys": "J. Stat. Phys."}

class Reference:
    def __init__(self, bibitem_data, bibitem_identifier):
        self.bibitem_data = bibitem_data
        self.bibitem_identifier = bibitem_identifier
        self.has_doi = False
        self.doi = None
        self.item_type = None
        self.crossref_data = None
        self.authors = None
        self.title = None
        self.publisher = None
        self.journal = None
        self.volume = None
        self.year = None
        self.issue = None
        self.short_journal = None
        self.formatted_reference = None
        self.page = None
        self.article_number = None

    def format_authors(self):
        for i, auth in enumerate(self.authors):
            if "-" in auth['given']:
                given_name = auth['given'].split("-")
                given_name = "-".join([g[:1] + "." for g in given_name])
            else:
                given_name = auth['given'][:1] + "."
                self.authors[i] = given_name + " " + auth['family']
        if len(self.authors) == 1:
            self.authors = self.authors[0]
        else:
            self.authors = ", ".join(self.authors[:-1]) + " and " + self.authors[-1]

    def format_short_journal(self):
        pass

    def format_journal(self):
        pass

class ReferenceFormatter:
    def __init__(self, tex_file, debug=False):
        self.check_manually = []
        self.references = []
        self.tex_file = tex_file
        self.get_bibtex_items()
        self.get_dois()
        self.get_crossref_data()
        self.get_ref_data()
        self.format_references()
        self.rewrite_tex_file()

    def get_bibtex_items(self):
        with open(self.tex_file, 'r') as f:
            tex_source = f.read()
        bibitem_regex = re.compile(r"(\\bibitem{.*?}.+?)(?=\\bibitem{|\\end{thebibliography})", re.DOTALL)
        references = bibitem_regex.findall(tex_source)
        for ref in references:
            bibitem_identifier = re.search(r"\\bibitem{(.*?)}", ref).group(1)
            ref_data = Reference(ref, bibitem_identifier)
            self.references.append(ref_data)

    def get_dois(self):
        for ref in self.references:
            try:
                # print(ref.bibitem_data)
                doi = re.search(r"(10\.\d{4,}\/\S+[^}])", ref.bibitem_data)
                # print(doi.group(1))
                ref.doi = doi.group(1)
                ref.has_doi = True
            except AttributeError:
               print("NO DOI")

    def get_crossref_data(self):
        """Extract author names associated with DOI's using the Crossref api."""
        for i, ref in enumerate(self.references):
            print(f"Processing reference {i+1:>{len(str(len(self.references)))}} of {len(self.references)}...", end='')
            if not ref.has_doi:
                continue
            try:
                print(ref.doi)
                with urllib.request.urlopen(f"https://api.crossref.org/works/{ref.doi}", timeout=10) as data:
                    ref.crossref_data = json.loads(data.read().decode('utf-8'))
            except socket.timeout:
                self.check_manually.append(ref)
                print(f"failed (connection timeout: {ref.doi})")
            except urllib.error.HTTPError as e:
                self.check_manually.append(ref)
                print(f"failed ({e}, the DOI may be malformed: {ref.doi})")

    def get_ref_data(self):
        for ref in self.references:
            if ref.crossref_data:
                ref.item_type = ref.crossref_data['message']['type']
                try:
                    ref.authors = ref.crossref_data['message']['author']
                    ref.format_authors()
                except KeyError:
                    pass
                try:
                    ref.title = ref.crossref_data['message']['title'][0]
                except KeyError:
                    pass
                try:
                    ref.publisher = ref.crossref_data['message']['publisher']
                except KeyError:
                    pass
                try:
                    ref.issue = ref.crossref_data['message']['issue']
                except KeyError:
                    pass
                try:
                    ref.journal = ref.crossref_data['message']["container-title"]
                    print(ref.journal)
                    if len(ref.journal) != 0:
                        ref.journal = ref.journal[0]
                    else:
                        ref.journal = None
                except KeyError:
                    pass
                try:
                    ref.short_journal = ref.crossref_data['message']["short-container-title"]
                    if len(ref.short_journal) != 0:
                        ref.short_journal = ref.short_journal[0]
                    else:
                        ref.short_journal = None
                    if ref.short_journal in JOURNAL_ABBRVS.keys():
                        print("PROBLEM", ref.journal)
                        ref.short_journal = JOURNAL_ABBRVS[ref.short_journal]
                        print("Succesfully shortened")
                except KeyError:
                    pass
                try:
                    ref.volume = ref.crossref_data['message']['volume']
                except KeyError:
                    pass
                try:
                    ref.year = ref.crossref_data['message']['issued']['date-parts'][0][0]
                except KeyError:
                    pass
                try:
                    ref.page = ref.crossref_data['message']['page']
                except KeyError:
                    pass
                try:
                    ref.article_number = ref.crossref_data['message']["article-number"]
                except KeyError:
                    pass

    def format_references(self):
        for ref in self.references:
            if ref.has_doi:
                if ref.item_type == "journal-article":
                    if "Journal of Statistical Mechanics" in ref.journal:
                        ref.formatted_reference = f"{ref.authors}, {ref.title}, {ref.short_journal} {ref.page} ({ref.year}), {ref.doi}."
                    elif ref.page and ref.issue and ref.volume:
                        ref.formatted_reference = f"{ref.authors}, {ref.title}, {ref.short_journal} {ref.volume}({ref.issue}), {ref.page} ({ref.year}), {ref.doi}."
                    elif ref.issue and ref.volume:
                        ref.formatted_reference = f"{ref.authors}, {ref.title}, {ref.short_journal} {ref.volume}, {ref.issue} ({ref.year}), {ref.doi}."
                    print(ref.formatted_reference)

    def rewrite_tex_file(self):
        tex_data = None
        with open(self.tex_file, 'r') as data:
            tex_data = data.read()
        for ref in self.references:
            if ref.formatted_reference:
                tex_data = tex_data.replace(ref.bibitem_data, f"{ref.bibitem_data}\n\n#{ref.formatted_reference}")
                # re.sub(ref.bibitem_data, f"{ref.bibitem_data}\n#{ref.formatted_reference}\n\n", tex_data)
        with open(self.tex_file, 'w') as tex_file:
            tex_file.write(tex_data)
        

    @staticmethod
    def cli_parsing():
        parser = argparse.ArgumentParser()
        parser.add_argument('tex_file')
        parser.add_argument('--debug', action="store_true")
        args = parser.parse_args()
        return args


if __name__ == '__main__':
    args = ReferenceFormatter.cli_parsing()
    scitation_scraper = ReferenceFormatter(args.tex_file, args.debug)
