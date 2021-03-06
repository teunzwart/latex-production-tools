"""Automatically get author names of references in a tex file."""

import argparse
import re
import webbrowser
from multiprocessing import Pool

from reference_utils import Reference, extract_bibtex_items, abbreviate_authors
from latex_utils import read_latex_file, remove_accented_characters


def get_unique_names(names):
    """Get unique names from a list of names."""
    name_dict = {}
    for name in list(set(names)):
        full_name = re.sub("\s\s+", " ", name.replace('.', ''))  # Remove any dots and extraneous whitespace.
        # Create a normalized name that can be used to compare names with different levels of abbrevation.
        abbrv_name = abbreviate_authors([full_name])[0].replace(" ", "")
        abbrv_name = remove_accented_characters(abbrv_name.lower())  # Remove accents to improve comparison.
        if abbrv_name not in name_dict or len(name_dict[abbrv_name].encode("utf-8")) < len(full_name.encode("utf-8")):
            name_dict[abbrv_name] = full_name  # Always store the longest available name, to improve the odds of finding someone.
    unique_names = sorted(list(name_dict.values()), key=lambda x: x.split(' ')[-1])
    return unique_names


def get_reference(bibtex_entry):
    """Wrapper function for parallelization."""
    reference = Reference(bibtex_entry.rstrip())
    reference.main()
    return reference.year, reference.full_authors, reference.bibitem_data


class ReferenceScraper:
    def __init__(self, tex_source, debug=False):
        self.tex_source = tex_source
        self.names = []
        self.unique_names = None
        self.check_manually = []
        self.debug = debug

    def main(self):
        print("Processing references...")
        bibtex_entries = extract_bibtex_items(self.tex_source)
        with Pool(15) as pool:
            results = pool.map(get_reference, bibtex_entries)
        for year, authors, bibentry in results:
            if year and int(year) >= 2000 and authors and len(authors) < 15:
                for a in authors:
                    self.names.append(a)
            elif year and int(year) < 2000:
                pass
            else:
                self.check_manually.append(bibentry)
        self.unique_names = get_unique_names(self.names)
        print(f"The timely references were written by {len(self.names)} authors, of which {len(self.unique_names)} are unique.")
        if not self.debug:
            self.open_google_pages()
        else:
            print(self.unique_names)
        if len(self.check_manually) == 0:
            print("There are no reference to check manually.")
        else:
            print("The following references have to be checked by hand:")
            for reference in self.check_manually:
                print(reference, '\n')
        return self.unique_names, self.check_manually

    def open_google_pages(self):
        print("Opening Google search pages (in batches of 10):")
        for i, name in enumerate(sorted(list(self.unique_names), key=lambda x: x.split(' ')[-1])):
            webbrowser.open(f"https://www.google.com/search?q={name.replace(' ', '+')}+physics")
            if (i + 1) % 10 == 0:
                input(f"Opening {i+1}/{len(self.unique_names)}. Press enter to open next 10...")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('latex_file')
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    latex_source = read_latex_file(args.latex_file)
    reference_scraper = ReferenceScraper(latex_source, debug=args.debug)
    reference_scraper.main()
