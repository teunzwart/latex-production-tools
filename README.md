# LaTeX production tools

Tools to work with LaTeX files. Tools include automatic publication preparation, reference formatting and reference extraction.

At least Python 3.6 is required for [format strings](https://www.python.org/dev/peps/pep-0498/) and to easily handle unicode strings.
External dependencies are `bs4`, `requests` and `html5lib`.

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

## LaTeX reference formatter

Automatically format references correctly. The system relies on DOIs and arXiv identifiers to extract information from the correct databases.
If a paper has been published and the arXiv page updated with the DOI, the scraper will prefer the DOI data over the arXiv data.

### Usage
    
```
python reference_formatter.py latex_file
```


There is also an option `--add_arxiv`, if you want to add arXiv references as well.


## TODO

- Handle references with collaboration names (such as [[http://api.crossref.org/works/10.1007%252FJHEP11%25282015%2529206]])
- Handle multiple references in the same bibitem
