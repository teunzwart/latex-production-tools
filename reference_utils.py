import re

from bs4 import BeautifulSoup

from journal_abbreviations import JOURNAL_ABBRVS
from latex_utils import open_webpage


def abbreviate_authors(list_of_authors):
    """Given a list of author names, abbreviate their first names, taking into account dashes. Operation is idempotent."""
    abbreviated_authors = []
    for author in list_of_authors:
        first_name = author.split()[0]
        middle_and_last_names = " ".join(author.split()[1:])
        if "-" in first_name:
            first_name = first_name.split("-")
            first_name = "-".join(g[:1] + "." for g in first_name)
        elif "." in first_name:
            # If dots are present, the name is probably already an abbreviation, just without spacing.
            first_name = first_name.split(".")
            first_name = " ".join(g + "." for g in first_name if g != "")
        else:
            first_name = first_name[:1] + "."
        full_name = f"{first_name} {middle_and_last_names}"
        # Make sure any initials after the first one also have a dot appended if not present.
        name_with_all_dots = []
        for name in full_name.split():
            if len(name) == 1:
                name = name + "."
            name_with_all_dots.append(name)
        abbreviated_authors.append(" ".join(name_with_all_dots))
    return abbreviated_authors


def get_first_author_last_name(list_of_authors):
    """Given a list of authors, return the last name of the first author, stripped of initials."""
    abbreviated_first_author = abbreviate_authors(list_of_authors)[0]
    last_name = ""
    for name in abbreviated_first_author.replace("-", " ").split():
        if len(name.replace(".", "")) > 1:
            last_name += f"{name} "
    return last_name.strip()


def extract_bibtex_items(latex_source):
    """Extract all bibtex items in a LaTeX file which are not commented out."""
    bibtex_item_regex = re.compile(r"""(?<!%)  # Lookbehind to check that the bibtex item is not commented out.
                                (\\bibitem{.*?}.+?)  # Match the entire bibtex item.
                                (?=\\bibitem{|\\end{thebibliography}|$)  # Match only until the next bibtex item, end of bibliography or end of line.
                                """, re.DOTALL | re.VERBOSE)
    return bibtex_item_regex.findall(latex_source)


def extract_bibitem_identifier(bibtex_entry):
    """Extract the bibitem identifier for a bibtex item."""
    try:
        return re.search(r"\\bibitem{(.*?)}", bibtex_entry).group(1)
    except AttributeError:
        return None


def extract_doi(bibtex_item):
    """Extract the DOI (singular) from a bibtex item."""
    # TODO: Gracefully handle multiple DOI's in a given piece of text.
    try:
        doi_regex = re.compile(r"""
        (10\.\d{4,}\/[^} \n]*)
        """, re.VERBOSE)
        doi = doi_regex.search(bibtex_item)
        doi =  doi.group(1).rstrip()
        return doi.rstrip(";%%")
    except AttributeError:
        return None


def extract_arxiv_id(bibtex_item):
    """Extract the arXiv id for a bibtex item."""
    try:
        arxiv_id_regex = re.compile(r"""abs\/(.*?)(?=\ |}|$)  # Match in a url.
                                    |arxiv:(.*?)(?=\ |}|$|])  # Match in a arXiv tag.
                                    |\\eprint{(.*?)}          # Match in an eprint tag.
                                    """, re.IGNORECASE | re.VERBOSE)
        arxiv_id = arxiv_id_regex.search(bibtex_item)
        # Find the group which has a match.
        return list(filter(lambda x: x is not None, arxiv_id.groups()))[0].rstrip()
    except AttributeError:
        return None


def reformat_original_reference(original_reference):
    """Remove newlines, newblocks and extraneous whitespace from the original refere."""
    text = re.sub(r"\\bibitem{(.*?)}|\\newblock", " ", original_reference)
    text = re.sub(r"\n", " ", text)
    text = re.sub(r" +", " ", text.strip())
    text = re.sub(r"(\\eprint{.*?})", r"\n%\1\n", text)  # Comment out \eprint, since it's not provided by the bibstyle and makes LaTeX choke during compilation.
    return text


def concatenate_authors(list_of_authors):
    """Concatenate a list of authors into a string seperated by commas, and with the last author preceded by 'and'."""
    if not isinstance(list_of_authors, list) or len(list_of_authors) == 0:
        return None
    elif len(list_of_authors) == 1:
        return list_of_authors[0]
    elif len(list_of_authors) < 10:
        author_string = ", ".join(list_of_authors[:-1])
        return f"{author_string} and {list_of_authors[-1]}"
    # Only cite the first author (especially important for particle physics publications with 100+ authors).
    else:
        return f"{list_of_authors[0]} et al."


def remove_arxiv_id_version(arxiv_id):
    """Remove the version from an arXiv id."""
    return re.sub("v\d$", "", arxiv_id)


class Reference:
    """Extract data for a bibtex entry, and reformat it for use in publications."""
    def __init__(self, bibitem_data):
        self.bibitem_data = bibitem_data
        self.bibitem_identifier = None
        self.item_type = None
        self.doi = None
        self.crossref_data = None
        self.arxiv_id = None
        self.arxiv_data = None
        self.full_authors = None
        self.abbreviated_authors = None
        self.title = None
        self.abstract = None
        self.year = None
        self.journal = None
        self.short_journal = None
        self.volume = None
        self.issue = None
        self.page = None
        self.article_number = None
        self.publisher = None
        self.publisher_location = None
        self.isbn = None
        self.formatted_reference = None
        self.reformatted_original_reference = None

    def main(self):
        """Extract DOI's and arXiv id's from a reference, and retrieve data, giving preference to Crossref data."""
        self.bibitem_identifier = extract_bibitem_identifier(self.bibitem_data)
        split_bibdata = self.bibitem_data.split(";")
        print(split_bibdata)
        self.doi = extract_doi(self.bibitem_data)
        self.arxiv_id = extract_arxiv_id(self.bibitem_data)
        self.reformatted_original_reference = reformat_original_reference(self.bibitem_data)
        if self.doi:
            succes, crossref_data = open_webpage(f"https://api.crossref.org/works/{self.doi}", exit_on_error=False)
            if succes:
                self.crossref_data = crossref_data.json()["message"]
                self.extract_crossref_reference_data()
        elif self.arxiv_id:
            succes, arxiv_data = open_webpage(f"https://export.arxiv.org/api/query?id_list={remove_arxiv_id_version(self.arxiv_id)}", exit_on_error=False)
            if succes:
                self.arxiv_data = arxiv_data.text
                self.extract_arxiv_reference_data()
        self.format_reference()

    def extract_arxiv_reference_data(self):
        """Extract arXiv data for a reference, and the DOI information, if a DOI is available."""
        soup = BeautifulSoup(self.arxiv_data, "html5lib")
        self.title = re.sub(" +", " ", re.sub("\n", "", soup.entry.title.string.strip()))
        self.full_authors = [a.string for a in soup.find_all("name")]
        self.abbreviated_authors = abbreviate_authors(self.full_authors)
        self.first_author_last_name = " ".join([a for a in self.abbreviated_authors[0].replace(".", "").split() if len(a) > 1])
        self.year = soup.published.string.split("-")[0]
        self.abstract = soup.find("summary").string.strip()
        # Prefer DOI data if it is available.
        try:
            self.doi = soup.find_all("link", title='doi')[0]["href"].lstrip("http://dx.doi.org/")
            succes, crossref_data = open_webpage(f"https://api.crossref.org/works/{self.doi}", exit_on_error=False)
            if succes:
                self.crossref_data = crossref_data.json()["message"]
                self.extract_crossref_reference_data()
        except IndexError:
            pass

    def extract_crossref_reference_data(self):
        """Extract a reference's metadata from a Crossref api response."""
        self.item_type = self.crossref_data['type']
        try:
            authors = self.crossref_data['author']
            self.full_authors = []
            for i, author in enumerate(authors):
                self.full_authors.append(f"{author['given']} {author['family']}")
            self.abbreviated_authors = abbreviate_authors(self.full_authors)
        except KeyError:
            pass
        try:
            journal = self.crossref_data["container-title"]
            if len(journal) != 0:
                self.journal = journal[0]
            else:
                self.journal = None
        except KeyError:
            pass
        try:
            short_journal = self.crossref_data["short-container-title"]
            if len(short_journal) != 0:
                self.short_journal = short_journal[0]
            else:
                self.short_journal = None
            if self.journal in JOURNAL_ABBRVS.keys():
                self.short_journal = JOURNAL_ABBRVS[self.journal]
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

    def format_reference(self):
        """Format the reference correctly."""
        authors_and_title = f"{concatenate_authors(self.abbreviated_authors)}, \\textit{{{self.title}}}"
        volume = f"\\textbf{{{self.volume}}}"
        if self.crossref_data:
            if self.item_type == "journal-article":
                # J. Stat. Mech. has a different citation style.
                if "Journal of Statistical Mechanics" in self.journal:
                    reference = f"{authors_and_title}, {self.short_journal} {self.page} ({self.year}), \doi{{{self.doi}}}."
                elif self.page:
                    reference = f"{authors_and_title}, {self.short_journal} {volume}, {self.page} ({self.year}), \doi{{{self.doi}}}."
                elif self.article_number:
                    reference = f"{authors_and_title}, {self.short_journal} {volume}, {self.article_number} ({self.year}), \doi{{{self.doi}}}."
                else:
                    reference = f"{authors_and_title}, {self.short_journal} {volume}, None ({self.year}), \doi{{{self.doi}}}."
            elif self.item_type in ["book", "monograph"]:
                reference = f"{authors_and_title}, {self.publisher}, {self.publisher_location}, ISBN {self.isbn} ({self.year}), \doi{{{self.doi}}}."
            elif self.item_type == "book-chapter":
                reference = f"{authors_and_title}, in {self.journal}, {self.publisher}, {self.publisher_location}, ISBN {self.isbn} ({self.year}), \doi{{{self.doi}}}."
        elif self.arxiv_data:
            reference = f"{authors_and_title}, \href{{https://arxiv.org/abs/{self.arxiv_id}}}{{arXiv:{self.arxiv_id}}}. % Has this been published somewhere?"
        else:
            reference = "AUTHORS, \\textit{TITLE}, JOURNAL \\textbf{VOLUME}, PAGE/ARTICLE NUMBER (YEAR), \doi{DOI}."

        # Remove any newlines which are included in the formatted reference.
        self.formatted_reference = re.sub(r"\n", "", reference)
