"""Tests for reference_scraper.py"""

import unittest

from reference_scraper import get_unique_names

class TestReferenceScraper(unittest.TestCase):
    def test_unique_names_extractions(self):
        """Test that unique names are correctly extracted from a list of names."""
        self.assertEqual(get_unique_names(["Jean-Sébastien Caux", "Jean-Sebastien Caux"]), ["Jean-Sébastien Caux"])
        # Check that order does not matter.
        self.assertEqual(get_unique_names(["Jean-Sebastien Caux", "Jean-Sébastien Caux"]), ["Jean-Sébastien Caux"])
        
