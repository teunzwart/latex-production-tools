import argparse
import copy
import json
import re
from abc import ABCMeta

import requests
from bs4 import BeautifulSoup

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
    def __init__(self, bibitem_data, extract_bibitem_identifier=True):
        self.bibitem_data = bibitem_data
        if extract_bibitem_identifier:
            self.bibitem_identifier = re.search(r"\\bibitem{(.*?)}", self.bibitem_data).group(1)
        self.item_type = None
        self.doi = None
        self.arxiv_id = None
        self.arxiv_data = None
        self.crossref_data = None
        self.authors = None
        self.full_authors = None
        self.title = None
        self.abstract = None
        self.journal = None
        self.short_journal = None
        self.volume = None
        self.issue = None
        self.page = None
        self.article_number = None
        self.publisher = None
        self.publisher_location = None
        self.isbn = None
        self.year = None
        self.formatted_reference = None
        self.reformatted_original_reference = None  # Newlines and newblocks removed.
        self.extract_doi()
        self.reformat_original_reference()

    def extract_doi(self):
        """Extract the DOI (singular) from a bibitem entry."""
        # TODO: Gracefully handle multiple DOI's in a given piece of text.
        try:
            doi = re.search(r"(10\.\d{4,}\/[^} \n]*)", self.bibitem_data)
            self.doi = doi.group(1).rstrip()
        except AttributeError:
            pass

    def extract_arxiv_id(self):
        """Extract the arXiv id for a bibitem entry."""
        try:
            arxiv_id = re.search(r"abs\/(.*?)(?=\ |}|$)|arxiv:(.*?)(?=\ |}|$)", self.bibitem_data)
            self.arxiv_id = re.sub("v\d{1,2}$", "", arxiv_id.group(1).rstrip())
        except AttributeError:
            pass
        
    def crossref_format_authors(self):
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

    def arxiv_format_authors(self):
        self.full_authors = copy.copy(self.authors)
        for i, author in enumerate(self.authors):
            author = author.split()
            given_name = author[0]
            family_name = " ".join(author[1:])
            if "-" in given_name:
                given_name = given_name.split("-")
                given_name = "-".join(g[:1] + "." for g in given_name)
            else:
                given_name = given_name[:1] + "."
            self.authors[i] = given_name + " " + family_name
        if len(self.authors) == 1:
            self.authors = self.authors[0]
            self.full_authors = self.full_authors[0]
        else:
            self.authors = ", ".join(self.authors[:-1]) + " and " + self.authors[-1]
            self.full_authors = ", ".join(self.full_authors[:-1]) + " and " + self.full_authors[-1]

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

    def reformat_original_reference(self):
        """Remove newlines, newblocks and extraneous whitespace from the original refere."""
        text = re.sub(r"\\bibitem{(.*?)}|\\newblock", " ", self.bibitem_data)
        text = re.sub(r"\n", " ", text)
        text = re.sub(r" +", " ", text.strip())
        self.reformatted_original_reference = text


    def get_crossref_data(self):
        """Get the Crossref data for a reference which has a DOI."""
        if not self.doi:
            return "failed (no DOI)"
        try:
            crossref_data = requests.get(f"https://api.crossref.org/works/{self.doi}", timeout=10).text
            self.crossref_data = json.loads(crossref_data)["message"]
            return f"succes ({self.doi})"
        except requests.exceptions.Timeout:
            return f"failed (connection timeout: {self.doi})"
        except requests.exceptions.HTTPError as e:
            return f"failed ({e}, the DOI may be malformed: {self.doi})"

    def get_arxiv_data(self):
        """Get arXiv api data."""
        try:
            self.arxiv_data = requests.get(f"https://export.arxiv.org/api/query?search_query={self.arxiv_id}", timeout=10).text
            return f"succes ({self.arxiv_id})"
        except requests.exceptions.Timeout:
            return f"failed (connection timeout: {self.arxiv_id})"
        except requests.exceptions.HTTPError as e:
            return f"failed ({e})"        
        
    def extract_arxiv_reference_data(self):
        soup = BeautifulSoup(self.arxiv_data, "html5lib")
        self.title = re.sub(" +", " ", re.sub("\n", "", soup.entry.title.string.strip()))
        self.authors = [a.string for a in soup.find_all("name")]
        self.year = soup.published.string.split("-")[0]
        self.abstract = soup.find("summary").string.strip()
        try:
            self.doi = soup.find_all("link", title='doi')[0]["href"].lstrip("http://dx.doi.org/")
        except IndexError:
            pass
        
    def extract_crossref_reference_data(self, format=True):
        """Extract a reference's metadata from a Crossref api response."""
        if self.crossref_data:
            self.item_type = self.crossref_data['type']
            try:
                self.authors = self.crossref_data['author']
            except KeyError:
                pass
            try:
                self.title = self.crossref_data['title'][0]
            except (KeyError, IndexError):
                pass
            try:
                self.publisher = self.crossref_data['publisher']
            except KeyError:
                pass
            try:
                self.issue = self.crossref_data['issue']
            except KeyError:
                pass
            try:
                self.journal = self.crossref_data["container-title"]
            except KeyError:
                pass
            try:
                self.short_journal = self.crossref_data["short-container-title"]
            except KeyError:
                pass
            try:
                self.volume = self.crossref_data['volume']
            except KeyError:
                pass
            try:
                self.year = self.crossref_data['issued']['date-parts'][0][0]
            except (KeyError, IndexError):
                pass
            try:
                self.page = self.crossref_data['page']
            except KeyError:
                pass
            try:
                self.article_number = self.crossref_data["article-number"]
            except KeyError:
                pass
            try:
                self.isbn = self.crossref_data['ISBN'][0].split("/")[-1]
            except (KeyError, IndexError):
                pass
            try:
                self.publisher_location = self.crossref_data['publisher-location']
            except KeyError:
                pass
            if format:
                self.crossref_format_authors()
                self.format_journal()
                self.format_short_journal()        

    def format_reference(self):
        if self.crossref_data:
            if self.item_type == "journal-article":
                # J. Stat. Mech. has a different scitation style.
                if "Journal of Statistical Mechanics" in self.journal:
                    self.formatted_reference = f"{self.authors}, \\textit{{{self.title}}}, {self.short_journal} {self.page} ({self.year}), \doi{{{self.doi}}}."
                elif self.page and self.volume:
                    self.formatted_reference = f"{self.authors}, \\textit{{{self.title}}}, {self.short_journal} \\textbf{{{self.volume}}}, {self.page} ({self.year}), \doi{{{self.doi}}}."
                elif self.article_number and self.volume:
                    self.formatted_reference = f"{self.authors}, \\textit{{{self.title}}}, {self.short_journal} \\textbf{{{self.volume}}}, {self.article_number} ({self.year}), \doi{{{self.doi}}}."
                elif self.issue and self.volume:
                    self.formatted_reference = f"{self.authors}, \\textit{{{self.title}}}, {self.short_journal} \\textbf{{{self.volume}}}, {self.issue} ({self.year}), \doi{{{self.doi}}}."
                else:
                    self.formatted_reference = f"{self.authors}, \\textit{{{self.title}}}, {self.short_journal} \\textbf{{{self.volume}}}, {(self.year)}, \doi{{{self.doi}}}"
            elif self.item_type == "book":
                self.formatted_reference = f"{self.authors}, \\textit{{{self.title}}}, {self.publisher}, {self.publisher_location} ({self.year}), \doi{{{self.doi}}}"
            elif self.item_type == "book-chapter":
                self.formatted_reference = f"{self.authors}, \\textit{{{self.title}}}, in {self.journal}, {self.publisher}, {self.publisher_location} ({self.year}), \doi{{{self.doi}}}"
        elif "arxiv" in self.bibitem_data:
            self.formatted_reference = f"[AUTHORS], \\textit{{[TITLE]}}, \href{{https://arxiv.org/abs/####.#####}}{{arXiv:####.#####}}. % Has this been published somewhere?"
        else:
            self.formatted_reference = f"[AUTHORS], \\textit{{[TITLE]}}, [JOURNAL] \\textbf{{[]VOLUME]}}, [PAGE/ARTICLE NUMBER] ([YEAR]), \doi{{[DOI]}}."
                
                
class ReferenceUtils(metaclass=ABCMeta):
    def extract_bibtex_items(self, tex_source):
        bibitem_regex = re.compile(r"(\\bibitem{.*?}.+?)(?=\\bibitem{|\\end{thebibliography})", re.DOTALL)
        return bibitem_regex.findall(tex_source)
    
