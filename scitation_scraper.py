from __future__ import print_function

import argparse
import collections
import re
import webbrowser


class ScitationScraper:
    def __init__(self, tex_file, debug=False):
        self.debug = debug
        self.tex_file = tex_file
        print(self.tex_file)
        self.bibitem_regex = re.compile(r"\\bibitem{.*?}(.+?)(?=\\bibitem{|\\end{thebibliography})", re.DOTALL)
        self.get_tex_source()
        self.references = self.bibitem_regex.findall(self.tex_source)
        self.get_recent_references()
        self.get_names()
        if not self.debug:
            self.open_google_pages()

    def flatten(self, non_flat_list):
        """
        Flatten an irregularly nested list.

        As seen at:
        http://stackoverflow.com/questions/2158395/flatten-an-irregular-list-of-lists-in-python
        """
        for item in non_flat_list:
            if isinstance(item, collections.Iterable) and not isinstance(item, (str, bytes)):
                yield from self.flatten(item)
            else:
                yield item

    def get_tex_source(self):
        with open(self.tex_file, 'r') as f:
            self.tex_source = f.read()

    def get_recent_references(self):
        """Retain only thos references that are more recent than 2000."""
        self.timely_references = []
        for ref in self.references:
            if re.search(r"\(20\d{2}\)", ref):
                self.timely_references.append(ref.replace('\n', ' '))

        print("Of {0} references, {1} are from 2000 or later.".format(len(self.references), len(self.timely_references)))

    def get_names(self):
        all_names = []
        for ref in self.timely_references:
            try:
                names = re.search(r"(?:(?!({\\it|\\textsl{|\\textit{)).)*", ref, re.DOTALL).group()
            except AttributeError:
                continue
            seperate_names = [p for p in names.split(",") if p != ' ']
            seperate_names[-1] = seperate_names[-1].split(" and ")
            seperate_names = [a.replace(',', '').replace('~', ' ').strip() for a in list(self.flatten(seperate_names))]
            for n in seperate_names:
                if len(n) < 30 and n != '':
                    all_names.append(n)
        print("These were written by {0} authors, of which {1} are unique.".format(len(all_names), len(set(all_names))))

        self.names = set(all_names)
        if self.debug:
            print(sorted(self.names))

    def open_google_pages(self):
        for index, name in enumerate(sorted(list(self.names))[:3]):
            webbrowser.open("https://www.google.nl/search?q={0}+physics".format(name.replace(' ', '+')))
            if index + 1 % 10 == 0:
                input("Press enter to continue...")

    @staticmethod
    def cli_parsing():
        parser = argparse.ArgumentParser()
        parser.add_argument('tex_file')
        args = parser.parse_args()
        return args

if __name__ == '__main__':
    args = ScitationScraper.cli_parsing()
    scitation_scraper = ScitationScraper(args.tex_file, debug=True)
