"""Tests for LaTeX utilities."""

import unittest

from latex_utils import (get_relevant_warnings,
                         remove_accented_characters,
                         open_webpage)


class TestLaTeXUtils(unittest.TestCase):
    def test_get_relevant_warnings(self):
        """Test that relevant warnings are extracted from a LaTeX log file."""
        test_log = """
                   Overfull \hbox (24.00002pt too wide) in paragraph at lines 245--268
                   LaTeX Warning: Citation `Qhydo4' on page 2 undefined on input line 304.
                   Underfull \hbox (badness 1132) in paragraph at lines 1347--1348
                   """
        expected_warnings = ["Overfull \hbox (24.00002pt too wide) in paragraph at lines 245--268",
                             "LaTeX Warning: Citation `Qhydo4' on page 2 undefined on input line 304."]
        self.assertEqual(get_relevant_warnings(test_log), expected_warnings)

    def test_accented_character_removal(self):
        """Test that accented strings are correctly normalized."""
        self.assertEqual(remove_accented_characters("Jean-Sébastien Caux"), "Jean-Sebastien Caux")
        self.assertEqual(remove_accented_characters("Caux"), "Caux")
        self.assertEqual(remove_accented_characters("Jérôme"), "Jerome")

    def test_webpage_access(self):
        """Test that webpages are retrieved and errors handled correctly."""
        # Test 404 error catching.
        with self.assertRaises(SystemExit):
            open_webpage("http://example.com/404")
        # Test no system exit on error.
        self.assertFalse(open_webpage("http://example.com/404", exit_on_error=False)[0])
        # Test succesfull connection to site.
        self.assertEqual(open_webpage("http://example.com/")[1].status_code, 200)
