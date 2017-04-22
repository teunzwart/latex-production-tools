import os
import os.path
import shutil
import sys
import tarfile
import tempfile

import requests
from bs4 import BeautifulSoup

from latex_utils import cli_parser
from reference_utils import Reference


class LatexPreparer:
    def __init__(self, submission):
        self.submission = submission
        self.scipost_page = self.get_page(self.submission)
        self.arxiv_link = None
        self.submission_date = None
        self.arxiv_id = None
        self.title = None
        self.authors = None
        self.abstract = None
        self.tex_source_zip = None

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
        reference.extract_arxiv_reference_data()
        reference.arxiv_format_authors()
        self.arxiv_id = reference.arxiv_id
        self.title = reference.title
        self.authors = reference.full_authors
        self.abstract = reference.abstract

    def open_arxiv_source(self, tar_file):

        print(tar_file)
        current_dir = os.path.dirname(os.path.realpath(tar_file))
        if tarfile.is_tarfile(tar_file):
            new_tar_file = f"{tar_file}.tar.gz"
            print(new_tar_file)
            os.rename(tar_file, new_tar_file)
            os.mkdir(tar_file)
            with tarfile.open(new_tar_file) as data:
                data.extractall(path=os.path.join(current_dir, tar_file))
                print("done")
        else:
            new_tar_file = f"{tar_file}.tex"
            print(new_tar_file)
            os.rename(tar_file, new_tar_file)
        
    def download_arxiv_source(self):
        print("Downloading tex source from arXiv...")
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                tex_source_zip = requests.get(f"https://arxiv.org/e-print/{self.arxiv_id}", timeout=10, stream=True)
            except requests.exceptions.Timeout:
                sys.exit("Could not contact arXiv: the connection timed out.")
            except requests.exceptions.ConnectionError as e:
                sys.exit(f"Could not contact arXiv: {e}")
            with open(self.arxiv_id, "wb") as zip_file:
                for chunk in tex_source_zip:
                    zip_file.write(chunk)
            print(os.listdir(temp_dir))
            self.open_arxiv_source(self.arxiv_id)
            print(os.listdir(temp_dir))
            print(os.listdir(os.path.join(temp_dir, self.arxiv_id)))
            arxiv_source_folder = os.path.join(temp_dir, self.arxiv_id)
            for file_name in os.listdir(arxiv_source_folder):
                if not os.path.splitext(file_name)[-1] in [".bst", ".cls"]:
                    print(os.path.splitext(file_name)[-1])
                    shutil.copy(os.path.join(arxiv_source_folder, file_name), os.getcwd())
            print(os.listdir(os.path.join(temp_dir, self.arxiv_id)))
            print(os.listdir(temp_dir))

            


if __name__ == "__main__":
    args = cli_parser()
    latex_preparer = LatexPreparer(args.tex_file)
    latex_preparer.extract_scipost_meta_data()
    latex_preparer.get_arxiv_meta_data()
    latex_preparer.download_arxiv_source()
