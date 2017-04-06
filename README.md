### SciPost reference scraper

Automatically extract the names of authors from references given a DOI or arXiv identifier, and open a Google search page for that name.
Any references that could not be processed are shown at the end of the program to be checked manually.

#### Usage
    
```
python reference_scraper.py [texfile]    
```

You need the `requests` package for the program to run.
Also, because names may include non-ASCII characters, for the moment this only works with Python 3, which handles unicode natively.