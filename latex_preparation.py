import calendar
import datetime
import math
import os
import os.path
import shutil
import sys
import tarfile
import subprocess
import tempfile
import re

import requests
from bs4 import BeautifulSoup

from latex_utils import cli_parser, remove_accented_characters, read_tex_file, write_tex_file, get_relevant_warnings
from reference_utils import Reference
from reference_formatter import ReferenceFormatter
from paths import LATEX_SKELETON_PATH, PRODUCTION_PATH


class LatexPreparer:
    def __init__(self, submission):
        self.submission = submission
        self.scipost_page = self.get_page(self.submission)
        self.arxiv_link = None
        self.submission_date = None
        self.arxiv_id = None
        self.arxiv_id_with_version = None
        self.title = None
        self.authors = None
        self.first_author_last_name = None
        self.abstract = None
        self.tex_source_zip = None
        self.production_folder = None
        now = datetime.datetime.now()
        self.issue = math.floor((now.month-0.1)/2) + 1  # Slight offset so even months are correctly converted.
        self.volume = now.year - 2015
        self.year = now.year
        self.original_tex_text = None
        self.references = None

    def get_page(self, address, check_version=True):
        try:
            page = requests.get(address, timeout=10).text
        except requests.exceptions.Timeout:
            sys.exit("Could not contact SciPost: the connection timed out.")
        except requests.exceptions.ConnectionError as e:
            sys.exit(f"Could not contact SciPost: {e}")
        page = BeautifulSoup(page, "html5lib")
        version = page.find(text="SciPost Submission Page").parent.find_next("h3").text
        if check_version and version == "This is not the current version.":
            sys.exit("Link is not of current article version.")
        return page

    def extract_scipost_meta_data(self):
        self.arxiv_link = self.scipost_page.find(text="arxiv Link:").parent.find_next("td").text.strip()
        print(self.arxiv_link)
        # Extract submission date.
        if self.scipost_page.find(text="Other versions of this Submission (with Reports) exist:"):
            oldest_version = self.scipost_page.find(class_="pubtitleli")["href"]
            oldest_version_page = self.get_page(f"https://www.scipost.org{oldest_version}", check_version=False)
            submission_date = oldest_version_page.find(text="Date submitted:").parent.find_next("td").text.strip()
        else:
            submission_date = self.scipost_page.find(text="Date submitted:").parent.find_next("td").text.strip()
        self.submission_date = "-".join(submission_date.split("-")[::-1])
        print(self.submission_date)

    def get_arxiv_meta_data(self):
        reference = Reference(self.arxiv_link, extract_bibitem_identifier=False)
        reference.extract_arxiv_id()
        reference.get_arxiv_data()
        reference.extract_arxiv_reference_data(get_doi_if_available=False)
        reference.arxiv_format_authors()
        self.arxiv_id = reference.arxiv_id
        self.arxiv_id_with_version = reference.arxiv_id_with_version
        print(self.arxiv_id)
        print(self.arxiv_id_with_version)
        self.title = reference.title
        self.authors = reference.full_authors
        self.first_author_last_name = reference.first_author_last_name.replace(" ", "_")
        self.abstract = reference.abstract

    def open_arxiv_source(self, tar_file):
        current_dir = os.path.dirname(os.path.realpath(tar_file))
        if tarfile.is_tarfile(tar_file):
            new_tar_file = f"{tar_file}.tar.gz"
            os.rename(tar_file, new_tar_file)
            os.mkdir(tar_file)
            with tarfile.open(new_tar_file) as data:
                data.extractall(path=os.path.join(current_dir, tar_file))
                print("done")
            return "is_tar"
        else:
            sys.exit("Can not currently handle single file submissions")
            return "is_tex"
    
    def prepare_production_folder(self):
        print("Downloading tex source from arXiv...", end="")
        name_without_special_chars = remove_accented_characters(self.first_author_last_name)
        self.production_folder = os.path.join(PRODUCTION_PATH, f"SciPost_Phys_{self.arxiv_id_with_version}_{name_without_special_chars}")
        if not os.path.exists(self.production_folder):
            os.makedirs(self.production_folder)
        else:
            sys.exit("Folder already exists! Aborting...")
        os.chdir(self.production_folder)
        try:
            tex_source_zip = requests.get(f"https://arxiv.org/e-print/{self.arxiv_id_with_version}", timeout=10)
        except requests.exceptions.Timeout:
            sys.exit("Could not contact arXiv: the connection timed out.")
        except requests.exceptions.ConnectionError as e:
            sys.exit(f"Could not contact arXiv: {e}")
        with open(self.arxiv_id_with_version, "wb") as zip_file:
            for chunk in tex_source_zip:
                zip_file.write(chunk)
        print("done.")
        print("Copying production file... ", end="")
        for file_name in os.listdir(LATEX_SKELETON_PATH):
            shutil.copy2(os.path.join(LATEX_SKELETON_PATH, file_name), self.production_folder)
        print("done.")
        file_type = self.open_arxiv_source(self.arxiv_id_with_version)
        if file_type == "is_tar":
            arxiv_source_folder = os.path.join(self.production_folder, self.arxiv_id_with_version)
            for file_name in os.listdir(arxiv_source_folder):
                print(file_name)
                if not os.path.splitext(file_name)[-1] in [".bst", ".cls"]:
                    print(os.path.splitext(file_name)[-1])
                    if os.path.isdir(os.path.join(arxiv_source_folder, file_name)):
                        print("ISDIR", os.path.join(arxiv_source_folder, file_name))
                        shutil.copytree(os.path.join(arxiv_source_folder, file_name,), os.path.join(self.production_folder, file_name))
                    else:
                        shutil.copy2(os.path.join(arxiv_source_folder, file_name), self.production_folder)
        print(os.listdir(self.production_folder))

    def edit_tex_file(self):
        os.chdir(self.production_folder)
        arxiv_id_without_dots = self.arxiv_id_with_version.replace(".", "_")
        self.publication_tex = f"SciPost_Phys_{arxiv_id_without_dots}_{self.first_author_last_name}.tex"
        shutil.copy("SciPost_Phys_Skeleton.tex", self.publication_tex)
        print(self.current_issue)
        print(self.current_volume)
        print(self.authors.replace(" and ", ",").split(","))
        for file_name in os.listdir(self.production_folder):
            no_of_bbl_files = 0
            bbl_file = None
            if os.path.splitext(file_name)[-1] == ".bbl":
                no_of_bbl_files += 1
                bbl_file = file_name
                references = read_tex_file(os.path.join(self.production_folder, file_name))
                print(references)
                self.references = re.search(r"(\\bibitem.*)(?=\\end{thebibliography})", references, re.DOTALL).group(1)
                print(os.path.splitext(file_name)[-1])
            # TODO: CHOKES ON MULTIPLE TEX FILES!
            if os.path.splitext(file_name)[-1] == ".tex" and file_name != "SciPost_Phys_Skeleton.tex" and file_name != self.publication_tex:
                self.original_tex_source = read_tex_file(os.path.join(self.production_folder, file_name))
                print("FOUND TEX")
        self.tex_source = read_tex_file(self.publication_tex)
        print(repr(self.tex_source))
        

        # try:
        # print(repr(self.original_tex_source))
        pattern = re.compile(r"(\\section{.*?}.*)(?=\\bibliography|\\begin{thebibliography})", re.DOTALL)
        print(pattern)
        print(self.original_tex_source)
        self.original_tex_text = re.search(r"(\\section{.*?}.*)(?=\\bibliography|\\begin{thebibliography})", self.original_tex_source, re.DOTALL).group(0)
        # print(self.original_tex_text)
        # sys.exit()
        # except AttributeError:
        #     pass
        self.packages = "".join([m + "\n" for m in re.findall(r"\\usepackage{.*?}.*", self.original_tex_source)])
        self.new_commands = "".join([m + "\n" for m in re.findall(r"\\newcommand{.*?}.*", self.original_tex_source)])

        if self.references:
            self.tex_source = selfelf.tex_source.replace("TODO: BBL IF BiBTeX was used: paste the contenst of the .bbl file here", f"TODO: BBL IF BiBTeX was used: paste the contenst of the .bbl file here\n\n{self.references}")
        self.tex_source = self.tex_source.replace("%%%%%%%%%% TODO: PAPER CITATION 1\n\\rhead{\\small \\href{https://scipost.org/SciPostPhys.?.?.???}{SciPost Phys. ?, ??? (20??)}}\n%%%%%%%%%% END TODO: PAPER CITATION 1", f"%%%%%%%%%% TODO: PAPER CITATION 1\n\\rhead{{\\small \\href{{https://scipost.org/SciPostPhys.{self.current_volume}.{self.current_issue}.???}}{{SciPost Phys. {self.current_volume}, ??? ({self.year})}}}}\n%%%%%%%%%% END TODO: PAPER CITATION 1")
        self.tex_source = self.tex_source.replace("%%%%%%%%%% TODO: PAPER CITATION 2\n\\rhead{\\small \\href{https://scipost.org/SciPostPhys.?.?.???}{SciPost Phys. ?, ??? (20??)}}\n%%%%%%%%%% END TODO: PAPER CITATION 2", f"%%%%%%%%%% TODO: PAPER CITATION 2\n\\rhead{{\\small \\href{{https://scipost.org/SciPostPhys.{self.current_volume}.{self.current_issue}.???}}{{SciPost Phys. {self.current_volume}, ??? ({self.year})}}}}\n%%%%%%%%%% END TODO: PAPER CITATION 2")


        self.tex_source = self.tex_source.replace("% multiline titles: end with a \\\\ to regularize line spacing", f"% multiline titles: end with a \\\\ to regularize line spacing\n{self.title}\\\\")
        self.tex_source = self.tex_source.replace("\\small Received ??-??-20??", f"\\small Received {self.submission_date}")

        self.tex_source = self.tex_source.replace("%%%%%%%%%% TODO: ABSTRACT Paste abstract here\n%%%%%%%%%% END TODO: ABSTRACT", f"%%%%%%%%%% TODO: ABSTRACT Paste abstract here\n{self.abstract}\n%%%%%%%%%% END TODO: ABSTRACT")

        self.tex_source = self.tex_source.replace("\\href{https://doi.org/10.21468/SciPostPhys.?.?.???}{doi:10.21468/SciPostPhys.?.?.???}", f"\\href{{https://doi.org/10.21468/SciPostPhys.{self.current_volume}.{self.current_issue}.???}}{{doi:10.21468/SciPostPhys.{self.current_volume}.{self.current_issue}.???}}")

        self.tex_source = self.tex_source.replace("A. Bee\\textsuperscript{1,2},\nC. Dee \\textsuperscript{1} and\nE. Eff \\textsuperscript{3*}", self.authors)

        self.tex_source = self.tex_source.replace("%%%%%%%%% TODO: CONTENTS Contents come here, starting from first \\section\n\n\n\n%%%%%%%%% END TODO: CONTENTS", f"%%%%%%%%% TODO: CONTENTS Contents come here, starting from first \\section\n\n{self.original_tex_text}\n\n%%%%%%%%% END TODO: CONTENTS")

        self.tex_source = self.tex_source.replace("%%%%%%%%%% TODO: PACKAGES include extra packages used by authors:\n\n% ADDED IN PRODUCTION", f"%%%%%%%%%% TODO: PACKAGES include extra packages used by authors:\n\n{self.packages}\n\n% ADDED IN PRODUCTION")

        self.tex_source = self.tex_source.replace("%%%%%%%%%% TODO: COMMANDS\n\n%%%%%%%%%% END TODO: COMMANDS", f"%%%%%%%%%% TODO: COMMANDS\n\n{self.new_commands}\n%%%%%%%%%% END TODO: COMMANDS")

        self.tex_source = self.tex_source.replace("%%%%%%%%%% TODO: LINENO Activate linenumbers during proofs stage\n%\\linenumbers", "%%%%%%%%%% TODO: LINENO Activate linenumbers during proofs stage\n\\linenumbers")

        reference_formatter = ReferenceFormatter(self.tex_source, None, False)
        self.tex_source = reference_formatter.main()

        # self.tex_source = convert_equations(self.tex_source)
        
        write_tex_file(self.publication_tex, self.tex_source)

    def run_pdflatex(self):
        subprocess.run(["latexmk", "-pdf", f"{self.publication_tex}"])
        print((re.sub(r".tex$", ".log", self.publication_tex)))
        print(get_relevant_warnings(read_tex_file(re.sub(r".tex$", ".log", self.publication_tex), encoding='latin-1')))


if __name__ == "__main__":
    args = cli_parser()
    latex_preparer = LatexPreparer(args.tex_file)
    latex_preparer.extract_scipost_meta_data()
    latex_preparer.get_arxiv_meta_data()
    latex_preparer.download_arxiv_source()
    latex_preparer.edit_tex_file()
    latex_preparer.run_pdflatex()
