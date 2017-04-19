### LaTeX reference scraper

Automatically extract the names of authors from references in a tex file given a DOI or arXiv identifier, and open a Google search page for that name.
Also makes sure to only extract references from 2000 or later and get only one instance of an author name.
Any references that could not be processed are shown at the end of the program to be checked manually.

#### Usage
    
```
python reference_scraper.py [texfile]    
```

Because names may include non-ASCII characters and f-strings are used, this only works with Python 3.6 and up, which handles unicode natively.
