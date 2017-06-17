import argparse
import datetime
import math
import os
import shutil
import sys
import tarfile
import subprocess
import re

from bs4 import BeautifulSoup

from latex_utils import remove_accented_characters, read_latex_file, write_latex_file, get_relevant_warnings, open_webpage
from reference_utils import Reference, concatenate_authors, extract_bibtex_items, remove_arxiv_id_version
from reference_formatter import format_references
from paths import LATEX_SKELETON_PATH, PRODUCTION_PATH


def extract_submission_content(latex_source):
    """Extract the submission content from a LaTeX source."""
    content = re.search(r"(\\section{.*?}.*)(?=\\bibliography|\\begin{thebibliography})", latex_source, re.DOTALL).group(0)
    return content


def extract_packages(latex_source):
    """Extract packages and package options from a LaTeX source."""
    production_packages = []
    usepackages = re.findall(r"(?<!%)\\usepackage.*?{.*?}", latex_source)
    for package in usepackages:
        print(package)
        package_name = re.search(r"{(.*?)}", package).group(1).split(",")[0]
        print(package_name)
        if package_name in ["amssymb", "a4wide"]:
            production_packages.append("% REMOVED IN PROD " + package)
        elif package_name in ["amsmath", "doi", "fancyhdr", "geometry", "graphicx", "hyperref", "inputenc", "lineno", "titlesec", "tocloft", "nottoc", "notlot", "notlof", "xcolor"]:
            pass
        else:
            production_packages.append(package)
    production_packages.append("\\usepackage{amsfonts}")
    production_packages = "".join([m + "\n" for m in production_packages])
    return production_packages


def extract_commands(latex_source):
    commands = []
    commands += re.findall(r"(?<=\n)\\newcommand.*", latex_source)
    commands += re.findall(r"(?<=\n)\\def.*", latex_source)
    commands += re.findall(r"(?<=\n)\\DeclareMathOperator.*", latex_source)
    return "\n".join(commands)


class LatexPreparer:
    def __init__(self, submission_address):
        self.submission_address = submission_address
        now = datetime.datetime.now()
        self.issue = math.floor((now.month-0.1)/2) + 1  # Slight offset so even months are correctly converted.
        self.volume = now.year - 2015
        self.arxiv_id = None
        self.submission_date = None
        self.title = None
        self.full_authors = None
        self.abbreviated_authors = None
        self.first_author_last_name = None
        self.abstract = None
        self.tex_source_zip = None
        self.original_tex_text = None
        self.publication_production_folder = None
        self.publication_tex_filename = None
        self.year = now.year
        self.references = None
        self.content = None
        self.packages = None
        self.commands = None

    def main(self):
        self.retrieve_scipost_submission_data()
        self.retrieve_arxiv_metadata()
        self.prepare_production_folder()
        self.download_arxiv_source()
        self.prepare_paper_data()
        self.edit_tex_file()
        self.run_pdflatex()

    def retrieve_scipost_submission_data(self):
        """Retrieve a submission's webpage and extract metadata."""
        print("Retrieving SciPost submission data...")
        submission_page = open_webpage(self.submission_address)
        submission_page = BeautifulSoup(submission_page.text, "html5lib")
        # Check that the latest version for the submission is retrieved.
        submission_version = submission_page.find(text="SciPost Submission Page").parent.find_next("h3").text
        if submission_version == "This is not the current version.":
            sys.exit("Not the current version.")
        self.arxiv_id = submission_page.find(text="arxiv Link:").parent.find_next("td").text.strip().strip("http://arxiv.org/abs/")
        # Extract submission date (date that first version was submitted).
        if submission_page.find(text="Other versions of this Submission (with Reports) exist:"):
            oldest_version = submission_page.find(class_="pubtitleli")["href"]  # First instance is first version.
            oldest_version_page = open_webpage(f"https://www.scipost.org{oldest_version}")
            oldest_version_page = BeautifulSoup(oldest_version_page.text, "html5lib")
            submission_date = oldest_version_page.find(text="Date submitted:").parent.find_next("td").text.strip()
        else:
            submission_date = submission_page.find(text="Date submitted:").parent.find_next("td").text.strip()
        # Change from YYYY-MM-DD to DD-MM-YYYY.
        self.submission_date = "-".join(submission_date.split("-")[::-1])

    def retrieve_arxiv_metadata(self):
        """Retrieve the arXiv data (title, authors, abstract) for a submission."""
        reference = Reference(f"arXiv:{self.arxiv_id}")
        reference.main()
        self.title = re.sub(r"[ ]{2,}", " ", reference.title)  # Remove occurences of more than one space.
        self.full_authors = reference.full_authors
        self.abbreviated_authors = reference.abbreviated_authors
        self.first_author_last_name = remove_accented_characters(reference.first_author_last_name.replace(" ", "_"))
        self.abstract = reference.abstract

    def prepare_production_folder(self, production_path=PRODUCTION_PATH):
        """
        Prepare the production folder for the submission.

        production_path: top level folder in which the submission folder should be placed
        """
        print("Preparing production folder...")
        self.publication_production_folder = os.path.join(production_path, f"SciPost_Phys_{self.arxiv_id}_{self.first_author_last_name}")
        if not os.path.exists(self.publication_production_folder):
            os.makedirs(self.publication_production_folder)
        else:
            sys.exit("Folder already exists! Aborting...")  # Better save than sorry, so no overwriting.
        for file_name in os.listdir(LATEX_SKELETON_PATH):
            shutil.copy2(os.path.join(LATEX_SKELETON_PATH, file_name), self.publication_production_folder)
        arxiv_id_without_dots = self.arxiv_id.replace(".", "_")
        self.publication_tex_filename = f"SciPost_Phys_{arxiv_id_without_dots}_{self.first_author_last_name}.tex"
        shutil.copy(os.path.join(self.publication_production_folder, "SciPost_Phys_Skeleton.tex"), os.path.join(self.publication_production_folder, self.publication_tex_filename))

    def download_arxiv_source(self):
        """Download the LaTeX source for a submission from arXiv."""
        print("Downloading LaTeX source from arXiv...")
        # Note that we use src/ID instead of e-print/ID, since then the source is always returned as a tarfile, even if it's a single file.
        tex_source_zip = open_webpage(f"https://arxiv.org/src/{self.arxiv_id}")
        # Save the tar file.
        with open(os.path.join(self.publication_production_folder, f"{self.arxiv_id}.tar.gz"), "wb") as zip_file:
            for chunk in tex_source_zip:
                zip_file.write(chunk)
        # Extract the tar file.
        with tarfile.open(os.path.join(self.publication_production_folder, f"{self.arxiv_id}.tar.gz")) as tar_file:
            # Single file submission.
            if len(tar_file.getmembers()) == 1:
                tar_file.extractall(path=self.publication_production_folder)
                arxiv_id_without_version = remove_arxiv_id_version(self.arxiv_id)
                os.rename(os.path.join(self.publication_production_folder, arxiv_id_without_version), os.path.join(self.publication_production_folder, f"{self.arxiv_id}.tex"))
            else:
                tar_file.extractall(path=os.path.join(self.publication_production_folder, self.arxiv_id))
                # Copy the files and directories one level up.
                for file_name in os.listdir(os.path.join(self.publication_production_folder, self.arxiv_id)):
                    # Exclude any class files the authors may have bundled.
                    if not os.path.splitext(file_name)[-1] in [".bst", ".cls"]:
                        # Copy directories and their contents.
                        if os.path.isdir(os.path.join(self.publication_production_folder, self.arxiv_id, file_name)):
                            shutil.copytree(os.path.join(self.publication_production_folder, self.arxiv_id, file_name), os.path.join(self.publication_production_folder, file_name))
                            # Copy individual files.
                        else:
                            shutil.copy2(os.path.join(self.publication_production_folder, self.arxiv_id, file_name), self.publication_production_folder)

    def prepare_paper_data(self):
        """Prepare and extract data from the LaTeX source file of a submission."""
        for file_name in os.listdir(self.publication_production_folder):
            print(file_name)
            if os.path.splitext(file_name)[-1] == ".bbl":
                print("Found bbl")
                references = read_latex_file(os.path.join(self.publication_production_folder, file_name))
                print(references)
                self.references = "\n\n".join(extract_bibtex_items(references))
            # TODO: Handle multiple tex files in a submission.
            elif os.path.splitext(file_name)[-1] == ".tex" and file_name not in ["SciPost_Phys_Skeleton.tex", self.publication_tex_filename]:
                self.original_tex_source = read_latex_file(os.path.join(self.publication_production_folder, file_name))

        self.content = extract_submission_content(self.original_tex_source)
        self.packages = extract_packages(self.original_tex_source)
        self.commands = extract_commands(self.original_tex_source)

        if not self.references:
            self.references = "\n\n".join(extract_bibtex_items(self.original_tex_source))

    def edit_tex_file(self):
        """Edit a tex file."""
        self.production_tex_source = read_latex_file(os.path.join(self.publication_production_folder, self.publication_tex_filename))

        old_citation = "%%%%%%%%%% TODO: PAPER CITATION\n\\rhead{\\small \\href{https://scipost.org/SciPostPhys.?.?.???}{SciPost Phys. ?, ??? (20??)}}\n%%%%%%%%%% END TODO: PAPER CITATION"
        new_citation = f"%%%%%%%%%% TODO: PAPER CITATION\n\\rhead{{\\small \\href{{https://scipost.org/SciPostPhys.{self.volume}.{self.issue}.???}}{{SciPost Phys. {self.volume}, ??? ({self.year})}}}}\n%%%%%%%%%% END TODO: PAPER CITATION"
        self.production_tex_source = self.production_tex_source.replace(old_citation, new_citation)

        old_packages = "%%%%%%%%%% TODO: PACKAGES include extra packages used by authors:\n\n% ADDED IN PRODUCTION"
        new_packages = f"%%%%%%%%%% TODO: PACKAGES include extra packages used by authors:\n\n{self.packages}\n\n% ADDED IN PRODUCTION"
        self.production_tex_source = self.production_tex_source.replace(old_packages, new_packages)

        old_commands = "%%%%%%%%%% TODO: COMMANDS\n\n%%%%%%%%%% END TODO: COMMANDS"
        new_commands = f"%%%%%%%%%% TODO: COMMANDS\n\n{self.commands}\n%%%%%%%%%% END TODO: COMMANDS"
        self.production_tex_source = self.production_tex_source.replace(old_commands, new_commands)

        old_title = "% multiline titles: end with a \\\\ to regularize line spacing"
        new_title = f"% multiline titles: end with a \\\\ to regularize line spacing\n{self.title}\\\\"
        self.production_tex_source = self.production_tex_source.replace(old_title, new_title)

        old_authors = "A. Bee\\textsuperscript{1,2},\nC. Dee\\textsuperscript{1} and\nE. Eff\\textsuperscript{3$\star$}"
        new_authors = concatenate_authors(self.full_authors)
        self.production_tex_source = self.production_tex_source.replace(old_authors, new_authors)

        old_abstract = "%%%%%%%%%% TODO: ABSTRACT Paste abstract here\n%%%%%%%%%% END TODO: ABSTRACT"
        new_abstract = f"%%%%%%%%%% TODO: ABSTRACT Paste abstract here\n{self.abstract}\n%%%%%%%%%% END TODO: ABSTRACT"
        self.production_tex_source = self.production_tex_source.replace(old_abstract, new_abstract)

        old_copyright = "{\\small Copyright A. Bee {\\it et al}."
        new_copyright = "{\\small Copyright DA COPY SQUAD."
        self.production_tex_source = self.production_tex_source.replace(old_copyright, new_copyright)

        old_received_date = "\\small Received ??-??-20??"
        new_received_date = f"\\small Received {self.submission_date}"
        self.production_tex_source = self.production_tex_source.replace(old_received_date, new_received_date)

        old_doi = "\\doi{10.21468/SciPostPhys.?.?.???}"
        new_doi = f"\\doi{{10.21468/SciPostPhys.{self.volume}.{self.issue}.???}}"
        self.production_tex_source = self.production_tex_source.replace(old_doi, new_doi)

        old_contents = "%%%%%%%%% TODO: CONTENTS Contents come here, starting from first \\section\n\n\n\n%%%%%%%%% END TODO: CONTENTS"
        new_contents = f"%%%%%%%%% TODO: CONTENTS Contents come here, starting from first \\section\n\n{self.content}\n\n%%%%%%%%% END TODO: CONTENTS"
        self.production_tex_source = self.production_tex_source.replace(old_contents, new_contents)

        if self.references:
            old_references = "TODO: BBL IF BiBTeX was used: paste the contenst of the .bbl file here"
            new_references = f"TODO: BBL IF BiBTeX was used: paste the contenst of the .bbl file here\n\n{self.references}"
            self.production_tex_source = self.production_tex_source.replace(old_references, new_references)

        print("Processing references...")
        self.production_tex_source = format_references(self.production_tex_source)

        write_latex_file(os.path.join(self.publication_production_folder, self.publication_tex_filename), self.production_tex_source)

    def run_pdflatex(self):
        os.chdir(self.publication_production_folder)
        subprocess.check_output(["latexmk", "-pdf", os.path.join(self.publication_production_folder, self.publication_tex_filename)])
        print("The following warning were generated:")
        for warning in get_relevant_warnings(read_latex_file(re.sub(r".tex$", ".log", self.publication_tex_filename))):
            print(warning)
        subprocess.run(["open", os.path.join(self.publication_production_folder, self.publication_tex_filename.replace(".tex", ".pdf"))])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('submission_address')
    args = parser.parse_args()
    latex_preparer = LatexPreparer(args.submission_address)
    latex_preparer.main()
