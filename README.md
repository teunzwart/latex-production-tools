# LaTeX production tools

Tools to work with LaTeX files. Tools include automatic publication preparation, reference formatting and reference extraction.

At least Python 3.6 is required for [format strings](https://www.python.org/dev/peps/pep-0498/) and to easily handle unicode strings.
External dependencies are `bs4`, `requests` and `html5lib`.

## Setup
1. Clone the repository
2. Set the relevant paths in `paths_template.py` and rename it to `paths.py`

### Tests

Run unittests with 
```
python -m unittest discover tests/ -b -v -c
```

## LaTeX reference scraper

Automatically extract the names of authors from references in a tex file given a DOI or arXiv identifier, and open a Google search page for that name.
Also makes sure to only extract references from 2000 or later and get only one instance of an author name.
Any references that could not be processed are shown at the end of the program to be checked manually.

### Usage
    
```
python reference_scraper.py latex_file
```


