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
                  "Nature Physics": "Nat. Phys.",
                  "Journal of Statistical Physics": "J. Stat. Phys.",
                  "Physics Letters A": "Phys. Lett. A",
                  "American Journal of Mathematics": "Am. J. Math.",
                  "Annals of Physics": "Ann. Phys.",
                  "Journal of Mathematical Physics": "J. Math. Phys."}

class Reference:
    """Hold (meta)data for a reference, and ways to format the data."""
    def __init__(self, bibitem_data, bibitem_identifier):
        self.bibitem_data = bibitem_data
        self.bibitem_identifier = bibitem_identifier
        self.doi = None
        self.item_type = None
        self.crossref_data = None
        self.authors = None
        self.title = None
        self.publisher = None
        self.publisher_location = None
        self.journal = None
        self.volume = None
        self.year = None
        self.issue = None
        self.short_journal = None
        self.formatted_reference = None
        self.page = None
        self.article_number = None
        self.isbn = None
        self.reformatted_original_reference = None

    def format_authors(self):
        for i, auth in enumerate(self.authors):
            if "-" in auth['given']:
                given_name = auth['given'].split("-")
                given_name = "-".join(g[:1] + "." for g in given_name)
            else:
                given_name = auth['given'].split()
                given_name = " ".join(a[:1] + "." for a in given_name)
            self.authors[i] = given_name + " " + auth['family']
        if len(self.authors) == 1:
            self.authors = self.authors[0]
        else:
            self.authors = ", ".join(self.authors[:-1]) + " and " + self.authors[-1]

    def format_short_journal(self):
        if len(self.short_journal) != 0:
            self.short_journal = self.short_journal[0]
        else:
            self.short_journal = None
        if self.journal in JOURNAL_ABBRVS.keys():
            self.short_journal = JOURNAL_ABBRVS[self.journal]

    def format_journal(self):
        if len(self.journal) != 0:
            self.journal = self.journal[0]
        else:
            self.journal = None

class ReferenceFormatter:
    def __init__(self, tex_file, debug=False):
        self.references = []
        self.tex_file = tex_file

    def get_bibtex_items(self):
        with open(self.tex_file, 'r') as f:
            tex_source = f.read()
        bibitem_regex = re.compile(r"(\\bibitem{.*?}.+?)(?=\\bibitem{|\\end{thebibliography})", re.DOTALL)
        references = bibitem_regex.findall(tex_source)
        for ref in references:
            bibitem_identifier = re.search(r"\\bibitem{(.*?)}", ref).group(1)
            ref_data = Reference(ref.rstrip(), bibitem_identifier)
            self.references.append(ref_data)

    def get_dois(self):
        for ref in self.references:
            try:
                # print(ref.bibitem_data)
                # doi = re.search(r"(10\.\d{4,}\/\S+[^}])", ref.bibitem_data)
                doi = re.search(r"(10\.\d{4,}\/[^} \n]*)", ref.bibitem_data)
                # print(doi.group(1))
                ref.doi = doi.group(1).rstrip()
            except AttributeError:
               pass

    def get_crossref_data(self):
        """Extract reference data through the Crossref api."""
        for i, ref in enumerate(self.references):
            print(f"Processing reference {i+1:>{len(str(len(self.references)))}} of {len(self.references)}... ", end='')
            if not ref.doi:
                print("failed (no DOI)")
                continue
            try:
                with urllib.request.urlopen(f"https://api.crossref.org/works/{ref.doi}", timeout=10) as data:
                    ref.crossref_data = json.loads(data.read().decode('utf-8'))
                    print(f"succes ({ref.doi})")
            except socket.timeout:
                print(f"failed (connection timeout: {ref.doi})")
            except urllib.error.HTTPError as e:
                print(f"failed ({e}, the DOI may be malformed: {ref.doi})")

    def get_ref_data(self):
        """Extract all data for a given reference."""
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
                    ref.format_journal()
                except KeyError:
                    pass
                try:
                    ref.short_journal = ref.crossref_data['message']["short-container-title"]
                    ref.format_short_journal()
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
                try:
                    ref.isbn = ref.crossref_data['message']['ISBN'][0].split("/")[-1]
                except KeyError:
                    pass
                try:
                    ref.publisher_location = ref.crossref_data['message']['publisher-location']
                except KeyError:
                    pass

    def reformat_original_references(self):
        for ref in self.references:
            text = re.sub(r"\\bibitem{(.*?)}|\\newblock", " ", ref.bibitem_data)
            text = re.sub(r"\n", " ", text)
            text = re.sub(r" +", " ", text.strip())
            ref.reformatted_original_reference = text
            
            
                
    def format_references(self):
        for ref in self.references:
            if ref.doi and ref.crossref_data:
                # print(ref.item_type, ref.doi)
                if ref.item_type == "journal-article":
                    # J. Stat. Mech. has a different scitation style.
                    if "Journal of Statistical Mechanics" in ref.journal:
                        ref.formatted_reference = f"{ref.authors}, \\textit{{{ref.title}}}, {ref.short_journal} {ref.page} ({ref.year}), \doi{{{ref.doi}}}."
                    elif ref.page and ref.volume:
                        ref.formatted_reference = f"{ref.authors}, \\textit{{{ref.title}}}, {ref.short_journal} \\textbf{{{ref.volume}}}, {ref.page} ({ref.year}), \doi{{{ref.doi}}}."
                    elif ref.article_number and ref.volume:
                        ref.formatted_reference = f"{ref.authors}, \\textit{{{ref.title}}}, {ref.short_journal} \\textbf{{{ref.volume}}}, {ref.article_number} ({ref.year}), \doi{{{ref.doi}}}."
                    elif ref.issue and ref.volume:
                        ref.formatted_reference = f"{ref.authors}, \\textit{{{ref.title}}}, {ref.short_journal} \\textbf{{{ref.volume}}}, {ref.issue} ({ref.year}), \doi{{{ref.doi}}}."
                    else:
                        ref.formatted_reference = f"{ref.authors}, \\textit{{{ref.title}}}, {ref.short_journal} \\textbf{{{ref.volume}}}, {(ref.year)}, \doi{{{ref.doi}}}"
                elif ref.item_type == "book":
                    ref.formatted_reference = f"{ref.authors}, \\textit{{{ref.title}}}, {ref.publisher}, {ref.publisher_location} ({ref.year}), \doi{{{ref.doi}}}"
                elif ref.item_type == "book-chapter":
                    ref.formatted_reference = f"{ref.authors}, \\textit{{{ref.title}}}, in {ref.journal}, {ref.publisher}, {ref.publisher_location} ({ref.year}), \doi{{{ref.doi}}}"
            elif "arxiv" in ref.bibitem_data:
                ref.formatted_reference = f"[AUTHORS], \\textit{{[TITLE]}}, \href{{https://arxiv.org/abs/####.#####}}{{arXiv:####.#####}}. % Has this been published somewhere?"
            else:
                ref.formatted_reference = f"[AUTHORS], \\textit{{[TITLE]}}, [JOURNAL] \\textbf{{[]VOLUME]}}, [PAGE/ARTICLE NUMBER] ([YEAR]), \doi{{[DOI]}}."
            
    def rewrite_tex_file(self):
        tex_data = None
        with open(self.tex_file, 'r') as data:
            tex_data = data.read()
        for ref in self.references:
            if ref.formatted_reference:
                tex_data = tex_data.replace(ref.bibitem_data, f"\\bibitem{{{ref.bibitem_identifier}}} TODO\n{ref.reformatted_original_reference}\n\n%{ref.formatted_reference}\n\n\n")
            else:
                tex_data = tex_data.replace(ref.bibitem_data, f"\\bibitem{{{ref.bibitem_identifier}}} TODO\n{ref.reformatted_original_reference}\n\n")
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
    scitation_scraper.get_bibtex_items()
    scitation_scraper.get_dois()
    scitation_scraper.get_crossref_data()
    scitation_scraper.get_ref_data()
    scitation_scraper.format_references()
    scitation_scraper.reformat_original_references()
    scitation_scraper.rewrite_tex_file()
