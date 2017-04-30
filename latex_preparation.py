import argparse
import calendar
import datetime
import math
import os
import shutil
import sys
import tarfile
import subprocess
import tempfile
import re

import requests
from bs4 import BeautifulSoup

from latex_utils import remove_accented_characters, read_tex_file, write_tex_file, get_relevant_warnings, open_webpage
from reference_utils import Reference
from reference_formatter import ReferenceFormatter
from paths import LATEX_SKELETON_PATH, PRODUCTION_PATH


class LatexPreparer:
    def __init__(self, submission_address):
        self.submission_address = submission_address
        now = datetime.datetime.now()
        self.issue = math.floor((now.month-0.1)/2) + 1  # Slight offset so even months are correctly converted.
        self.volume = now.year - 2015
        self.arxiv_id = None
        self.submission_date = None
        self.title = None
        self.authors = None
        self.first_author_last_name = None
        self.abstract = None
        self.tex_source_zip = None
        self.original_tex_text = None
        self.publication_production_folder = None
        self.year = now.year
        self.references = None
        self.content = None
        self.packages = None
        self.commands = None

    def main(self):
        self.retrieve_scipost_submission_data()
        self.retrieve_arxiv_metadata()
        print(self.authors)
        self.prepare_production_folder()
        self.download_arxiv_source()
        sys.exit()
        latex_preparer.extract_paper_data()
        latex_preparer.edit_tex_file()
        latex_preparer.run_pdflatex()

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
        reference = Reference(f"http://arxiv.org/abs/{self.arxiv_id}", extract_bibitem_identifier=False)
        reference.extract_arxiv_id()
        reference.get_arxiv_data()
        reference.extract_arxiv_reference_data(get_doi_if_available=False)
        reference.arxiv_format_authors()
        self.title = reference.title
        self.authors = reference.raw_full_authors
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
        tex_source_zip = open_webpage(f"https://arxiv.org/e-print/{self.arxiv_id}")
        if tex_source_zip.headers["Content-Type"] == "application/x-eprint-tar":
            # Save the tar file.
            with open(os.path.join(self.publication_production_folder, f"{self.arxiv_id}.tar.gz"), "wb") as zip_file:
                for chunk in tex_source_zip:
                    zip_file.write(chunk)
            # Extract the tar file.
            with tarfile.open(os.path.join(self.publication_production_folder, f"{self.arxiv_id}.tar.gz")) as tar_file:
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
        else:
            # FIXME: seems to be a problem with decompression which does happen in a browser but not in Python.
            sys.exit("Can not currently handle single file submissions. Aborting...")

    def extract_paper_data(self):
        os.chdir(self.production_folder)
        for file_name in os.listdir(self.production_folder):
            if os.path.splitext(file_name)[-1] == ".bbl":
                references = read_tex_file(os.path.join(self.production_folder, file_name))
                self.references = re.search(r"(\\bibitem.*)(?=\\end{thebibliography})", references, re.DOTALL).group(1)
                print(os.path.splitext(file_name)[-1])
            # TODO: Can't handle multiple tex files in the submission!
            elif os.path.splitext(file_name)[-1] == ".tex" and file_name not in  ["SciPost_Phys_Skeleton.tex", self.publication_tex]:
                self.original_tex_source = read_tex_file(os.path.join(self.production_folder, file_name))
        self.paper_content = re.search(r"(\\section{.*?}.*)(?=\\bibliography|\\begin{thebibliography})", self.original_tex_source, re.DOTALL).group(0)
        all_packages = re.findall(r"(?<=\n)\\usepackage.*", self.original_tex_source)
        print(all_packages)

        if not self.references:
            self.references = re.search(r"(\\bibitem.*)(?=\\end{thebibliography})", self.original_tex_source, re.DOTALL).group(1)
        self.packages = []
        for i, package in enumerate(all_packages):
            package_name = re.search(r"{(.*?)}", package).group(1)
            print(package_name)
            if package_name in ["amssymb", "a4wide"]:
                print("REMOVED")
                self.packages.append("% REMOVED IN PROD" + package)
            elif package_name in ["doi", "amsmath", "graphicx", "hyperref"]:
                print("ALREADY")
                pass
            else:
                self.packages.append(package)
                print("ADDED")

        

        
        self.packages = "".join([m + "\n" for m in self.packages])

        self.new_commands = "".join([m + "\n" for m in re.findall(r"(?<=\n)\\newcommand.*", self.original_tex_source)])
        self.new_commands += "".join([m + "\n" for m in re.findall(r"(?<=\n)\\def.*", self.original_tex_source)])

        print(self.packages)

    def edit_tex_file(self):
        os.chdir(self.production_folder)
        self.production_tex_source = read_tex_file(os.path.join(self.production_folder, self.publication_tex))
        self.tex_source = self.production_tex_source

        self.tex_source = self.tex_source.replace("%%%%%%%%%% TODO: PAPER CITATION 1\n\\rhead{\\small \\href{https://scipost.org/SciPostPhys.?.?.???}{SciPost Phys. ?, ??? (20??)}}\n%%%%%%%%%% END TODO: PAPER CITATION 1", f"%%%%%%%%%% TODO: PAPER CITATION 1\n\\rhead{{\\small \\href{{https://scipost.org/SciPostPhys.{self.volume}.{self.issue}.???}}{{SciPost Phys. {self.volume}, ??? ({self.year})}}}}\n%%%%%%%%%% END TODO: PAPER CITATION 1")
        self.tex_source = self.tex_source.replace("%%%%%%%%%% TODO: PAPER CITATION 2\n\\rhead{\\small \\href{https://scipost.org/SciPostPhys.?.?.???}{SciPost Phys. ?, ??? (20??)}}\n%%%%%%%%%% END TODO: PAPER CITATION 2", f"%%%%%%%%%% TODO: PAPER CITATION 2\n\\rhead{{\\small \\href{{https://scipost.org/SciPostPhys.{self.volume}.{self.issue}.???}}{{SciPost Phys. {self.volume}, ??? ({self.year})}}}}\n%%%%%%%%%% END TODO: PAPER CITATION 2")

        self.tex_source = self.tex_source.replace("%%%%%%%%%% TODO: PACKAGES include extra packages used by authors:\n\n% ADDED IN PRODUCTION", f"%%%%%%%%%% TODO: PACKAGES include extra packages used by authors:\n\n{self.packages}\n\n% ADDED IN PRODUCTION")

        self.tex_source = self.tex_source.replace("%%%%%%%%%% TODO: COMMANDS\n\n%%%%%%%%%% END TODO: COMMANDS", f"%%%%%%%%%% TODO: COMMANDS\n\n{self.new_commands}\n%%%%%%%%%% END TODO: COMMANDS")

        self.tex_source = self.tex_source.replace("% multiline titles: end with a \\\\ to regularize line spacing", f"% multiline titles: end with a \\\\ to regularize line spacing\n{self.title}\\\\")
                 
        self.tex_source = self.tex_source.replace("A. Bee\\textsuperscript{1,2},\nC. Dee \\textsuperscript{1} and\nE. Eff \\textsuperscript{3*}", self.authors)
                 
        self.tex_source = self.tex_source.replace("%%%%%%%%%% TODO: ABSTRACT Paste abstract here\n%%%%%%%%%% END TODO: ABSTRACT", f"%%%%%%%%%% TODO: ABSTRACT Paste abstract here\n{self.abstract}\n%%%%%%%%%% END TODO: ABSTRACT")

        self.tex_source = self.tex_source.replace("{\\small Copyright A. Bee {\\it et al}.", "{\\small Copyright DA COPY SQUAD.")
                 
        self.tex_source = self.tex_source.replace("\\small Received ??-??-20??", f"\\small Received {self.submission_date}")

        self.tex_source = self.tex_source.replace("\\href{https://doi.org/10.21468/SciPostPhys.?.?.???}{doi:10.21468/SciPostPhys.?.?.???}", f"\\href{{https://doi.org/10.21468/SciPostPhys.{self.volume}.{self.issue}.???}}{{doi:10.21468/SciPostPhys.{self.volume}.{self.issue}.???}}")

        self.tex_source = self.tex_source.replace("%%%%%%%%%% TODO: LINENO Activate linenumbers during proofs stage\n%\\linenumbers", "%%%%%%%%%% TODO: LINENO Activate linenumbers during proofs stage\n\\linenumbers")

        self.tex_source = self.tex_source.replace("%%%%%%%%% TODO: CONTENTS Contents come here, starting from first \\section\n\n\n\n%%%%%%%%% END TODO: CONTENTS", f"%%%%%%%%% TODO: CONTENTS Contents come here, starting from first \\section\n\n{self.paper_content}\n\n%%%%%%%%% END TODO: CONTENTS")

        if self.references:
            self.tex_source = self.tex_source.replace("TODO: BBL IF BiBTeX was used: paste the contenst of the .bbl file here", f"TODO: BBL IF BiBTeX was used: paste the contenst of the .bbl file here\n\n{self.references}")
        reference_formatter = ReferenceFormatter(self.tex_source)
        # self.tex_source = reference_formatter.main()

        
        write_tex_file(self.publication_tex, self.tex_source)

    def run_pdflatex(self):
        subprocess.run(["latexmk", "-pdf", f"{self.publication_tex}"])
        print((re.sub(r".tex$", ".log", self.publication_tex)))
        print(get_relevant_warnings(read_tex_file(re.sub(r".tex$", ".log", self.publication_tex), encoding='latin-1')))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('submission_address')
    args = parser.parse_args()
    latex_preparer = LatexPreparer(args.submission_address)
    latex_preparer.main()
