from __future__ import print_function

import re

import requests

import scitation_scraper


class DOITester(scitation_scraper.ScitationScraper):
    def __init__(self, tex_file, debug=False):
        self.debug = debug
        self.tex_file = tex_file
        print(self.tex_file)
        self.bibitem_regex = re.compile(r"(\\bibitem{.*?}.+?)(?=\\bibitem{|\\end{thebibliography})", re.DOTALL)
        self.get_tex_source()
        self.references = self.bibitem_regex.findall(self.tex_source)
        self.get_dois()
        self.validate_dois()

    def get_dois(self):
        self.all_dois = []
        for ref in self.references:
            try:
                bibtex_label = re.search(r"\\bibitem{(.*?)}", ref).group(1)
                doi = re.search(r"\\doi{(.*?)}", ref).group(1)
                self.all_dois.append((bibtex_label, doi))
            except AttributeError:
                continue

    def validate_dois(self):
        self.non_valid_dois = []
        print("Validating doi's. This may take some time...")
        for index, doi in enumerate(self.all_dois):
            print("Validating {0} of {1}".format(index+1, len(self.all_dois)))
            if doi[1].endswith("/meta"):
                self.non_valid_dois.append((doi[0], doi[1]))
            try:
                site = requests.get("https://dx.doi.org/{0}".format(doi[1]), timeout=15)
                if site.status_code == 404:
                    self.non_valid_dois.append((doi[0], doi[1]))
            except requests.exceptions.Timeout:
                self.non_valid_dois.append((doi[0], doi[1]))
        if not self.non_valid_dois:
            print("There are no non-valid doi's in the .tex file.")
        else:
            print("The following bibitems may have non-valid doi's:")
            for k in self.non_valid_dois:
                print("{0}: https://dx.doi.org/{1}".format(k[0], k[1]))


if __name__ == '__main__':
    args = DOITester.cli_parsing()
    doi_tester = DOITester(args.tex_file)
