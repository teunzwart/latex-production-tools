"""Test cases for the file reference_utils.py"""

import unittest

from reference_utils import (abbreviate_authors,
                             get_first_author_last_name,
                             extract_bibtex_items,
                             extract_bibitem_identifier,
                             extract_doi,
                             extract_arxiv_id,
                             reformat_original_reference,
                             concatenate_authors,
                             remove_arxiv_id_version,
                             Reference)


class TestReferenceUtils(unittest.TestCase):
    """Test single funcions from reference_utils.py"""
    def test_author_abbreviation(self):
        """Test that author names are correctly abbreviated and that the operation is idempotent."""
        self.assertEqual(abbreviate_authors(["Jean-Sébastien Caux"]), ["J.-S. Caux"])
        self.assertEqual(abbreviate_authors(["J.-S. Caux"]), ["J.-S. Caux"])
        self.assertEqual(abbreviate_authors(["Jean-Sébastien Caux", "Andrew S. Campbell"]), ["J.-S. Caux", "A. S. Campbell"])
        self.assertEqual(abbreviate_authors(["J.-S. Caux", "Andrew S. Campbell"]), ["J.-S. Caux", "A. S. Campbell"])
        self.assertEqual(abbreviate_authors(["J.-S. Caux", "A. S. Campbell"]), ["J.-S. Caux", "A. S. Campbell"])
        self.assertEqual(abbreviate_authors(["Cristiane Morais Smith"]), ["C. Morais Smith"])  # Test multiple last names.
        self.assertEqual(abbreviate_authors(["Al.B. Zamolodchikov"]), ["Al. B. Zamolodchikov"])
        self.assertEqual(abbreviate_authors(["Jasper van Wezel"]), ["J. van Wezel"])  # Test Dutch last names.

    def test_get_first_author_last_name(self):
        """Test that the last name of the first author is correctly returned."""
        self.assertEqual(get_first_author_last_name(["Cristiane Morais Smith"]), "Morais Smith")
        self.assertEqual(get_first_author_last_name(["Jean-Sébastien Caux"]), "Caux")
        self.assertEqual(get_first_author_last_name(["Andrew S. Campbell"]), "Campbell")

    def test_bibtex_item_extraction(self):
        """Test that bibtex items are correctly extracted from a string."""
        # Test until end of bibliography.
        self.assertEqual(extract_bibtex_items("\\bibitem{KWW} T. Kinoshita, T. Wenger, D.S. Weiss, ``A quantum Newton\'s cradle\'\', "
                                              "Nature {\\bf 440}, 900  (2006). \\\\ DOI: 10.1038/nature04693\n\n\\bibitem{JDprivate} "
                                              "J. Dubail, private communications.\n\n\\bibitem{Frietrans} D. Friedan, ``Entropy flow "
                                              "in near-critical quantum circuits\'\', J Stat Phys (2017) \\\\ DOI: "
                                              "10.1007/s10955-017-1751-9\n\n\\end{thebibliography}"),
                         ["\\bibitem{KWW} T. Kinoshita, T. Wenger, D.S. Weiss, ``A quantum Newton's cradle'', "
                          "Nature {\\bf 440}, 900  (2006). \\\\ DOI: 10.1038/nature04693\n\n",
                          '\\bibitem{JDprivate} J. Dubail, private communications.\n\n',
                          "\\bibitem{Frietrans} D. Friedan, ``Entropy flow in near-critical quantum "
                          "circuits'', J Stat Phys (2017) \\\\ DOI: 10.1007/s10955-017-1751-9\n\n"])
        # Just match until final item.
        self.assertEqual(extract_bibtex_items("\\bibitem{KWW} T. Kinoshita, T. Wenger, D.S. Weiss, ``A quantum Newton\'s cradle\'\', "
                                              "Nature {\\bf 440}, 900  (2006). \\\\ DOI: 10.1038/nature04693\n\n\\bibitem{JDprivate} "
                                              "J. Dubail, private communications.\n\n\\bibitem{Frietrans} D. Friedan, ``Entropy flow "
                                              "in near-critical quantum circuits\'\', J Stat Phys (2017) \\\\ DOI: "
                                              "10.1007/s10955-017-1751-9\n\n"),
                         ["\\bibitem{KWW} T. Kinoshita, T. Wenger, D.S. Weiss, ``A quantum Newton's cradle'', "
                          "Nature {\\bf 440}, 900  (2006). \\\\ DOI: 10.1038/nature04693\n\n",
                          '\\bibitem{JDprivate} J. Dubail, private communications.\n\n',
                          "\\bibitem{Frietrans} D. Friedan, ``Entropy flow in near-critical quantum "
                          "circuits'', J Stat Phys (2017) \\\\ DOI: 10.1007/s10955-017-1751-9\n"])
        # Don't match commented out bibtex items.
        self.assertEqual(extract_bibtex_items("\\bibitem{KWW} T. Kinoshita, T. Wenger, D.S. Weiss, ``A quantum Newton\'s cradle\'\', "
                                              "Nature {\\bf 440}, 900  (2006). \\\\ DOI: 10.1038/nature04693\n\n%\\bibitem{JDprivate} "
                                              "J. Dubail, private communications.\n\n\\bibitem{Frietrans} D. Friedan, ``Entropy flow "
                                              "in near-critical quantum circuits\'\', J Stat Phys (2017) \\\\ DOI: "
                                              "10.1007/s10955-017-1751-9\n\n\\end{thebibliography}"),
                         ["\\bibitem{KWW} T. Kinoshita, T. Wenger, D.S. Weiss, ``A quantum Newton's cradle'', "
                          "Nature {\\bf 440}, 900  (2006). \\\\ DOI: 10.1038/nature04693\n\n%",
                          "\\bibitem{Frietrans} D. Friedan, ``Entropy flow in near-critical quantum circuits'', "
                          "J Stat Phys (2017) \\\\ DOI: 10.1007/s10955-017-1751-9\n\n"])

    def test_doi_extraction(self):
        """Test that DOI's are correctly extracted from a string."""
        self.assertEqual(extract_doi("Hello"), None)
        self.assertEqual(extract_doi("doi: 10.21468/SciPostPhys.2.2.015"), "10.21468/SciPostPhys.2.2.015")
        self.assertEqual(extract_doi("\doi{10.21468/SciPostPhys.2.2.015}"), "10.21468/SciPostPhys.2.2.015")
        self.assertEqual(extract_doi("doi: 10.21468/SciPostPhys.2.2.015 and something else"), "10.21468/SciPostPhys.2.2.015")
        self.assertEqual(extract_doi("doi: 10.21468/SciPostPhys.2.2.015\nand something else"), "10.21468/SciPostPhys.2.2.015")

    def test_arxiv_extraction(self):
        """Test that arXiv id's are correctly extracted from a string."""
        self.assertEqual(extract_arxiv_id("Hello"), None)
        self.assertEqual(extract_arxiv_id("https://arxiv.org/abs/1608.02869"), "1608.02869")
        self.assertEqual(extract_arxiv_id("https://arxiv.org/abs/1608.02869 "), "1608.02869")
        self.assertEqual(extract_arxiv_id("https://arxiv.org/abs/1608.02869}"), "1608.02869")
        self.assertEqual(extract_arxiv_id("arXiv:1608.02869"), "1608.02869")
        self.assertEqual(extract_arxiv_id("arXiv:1608.02869 "), "1608.02869")
        self.assertEqual(extract_arxiv_id("arXiv:1608.02869}"), "1608.02869")
        self.assertEqual(extract_arxiv_id("arXiv:1608.02869]"), "1608.02869")
        self.assertEqual(extract_arxiv_id("\eprint{1608.02869}"), "1608.02869")

    def test_original_reference_reformatting(self):
        """Test reformatting of original references."""
        self.assertEqual(reformat_original_reference("\\bibitem{tba1} A.~Zamolodchikov, \\newblock "
                                                     "{``Thermodynamic Bethe ansatz in relativistic models. "
                                                     "Scaling   three state Potts and Lee-Yang models''}, "
                                                     "\\newblock Nucl. Phys. B {\\bf 342}, 695--720 (1990)."
                                                     "\\\\ DOI: 10.1016/0550-3213(90)90333-9"),
                         "A.~Zamolodchikov, {``Thermodynamic Bethe ansatz in relativistic models. "
                         "Scaling three state Potts and Lee-Yang models''}, Nucl. Phys. B {\\bf 342}, "
                         "695--720 (1990).\\\\ DOI: 10.1016/0550-3213(90)90333-9")
        # Test that eprint commands are properly commented out.
        self.assertEqual(reformat_original_reference("\\bibitem{Hunyadi2004} \nV.~Hunyadi, Z.~Racz and L.~Sasvari,\n"
                                                     "\\newblock \emph{{Dynamic scaling of fronts in the quantum XX "
                                                     "chain}}, \\newblock Physical Review E \textbf{69}(6), "
                                                     "066103 (2004), \\newblock \doi{10.1103/PhysRevE.69.066103},"
                                                     "\\newblock \eprint{cond-mat/0312250}."),
                         "V.~Hunyadi, Z.~Racz and L.~Sasvari, \\emph{{Dynamic scaling of fronts in "
                         "the quantum XX chain}}, Physical Review E \textbf{69}(6), 066103 (2004), "
                         "\\doi{10.1103/PhysRevE.69.066103}, \n%\\eprint{cond-mat/0312250}\n.")

    def test_bibitem_identifier_extraction(self):
        """Test extraction of bibitem identifier."""
        self.assertEqual(extract_bibitem_identifier("\\bibitem{tba1} A.~Zamolodchikov, \\newblock "
                                                    "{``Thermodynamic Bethe ansatz in relativistic models. "
                                                    "Scaling   three state Potts and Lee-Yang models''}, "
                                                    "\\newblock Nucl. Phys. B {\\bf 342}, 695--720 (1990)."
                                                    "\\\\ DOI: 10.1016/0550-3213(90)90333-9"), "tba1")
        self.assertEqual(extract_bibitem_identifier("A.~Zamolodchikov, \\newblock "
                                                    "{``Thermodynamic Bethe ansatz in relativistic models. "
                                                    "Scaling   three state Potts and Lee-Yang models''}, "
                                                    "\\newblock Nucl. Phys. B {\\bf 342}, 695--720 (1990)."
                                                    "\\\\ DOI: 10.1016/0550-3213(90)90333-9"), None)

    def test_author_concatenation(self):
        self.maxDiff = None
        """Test that a list of authors is correctly concatenated."""
        self.assertEqual(concatenate_authors(["Jean-Sébastien Caux"]), "Jean-Sébastien Caux")
        self.assertEqual(concatenate_authors(["Jean-Sébastien Caux", "Andrew S. Campbell"]), "Jean-Sébastien Caux and Andrew S. Campbell")
        self.assertEqual(concatenate_authors(["Jean-Sébastien Caux", "Andrew S. Campbell", "Jasper van Wezel"]),
                         "Jean-Sébastien Caux, Andrew S. Campbell and Jasper van Wezel")
        self.assertEqual(concatenate_authors([]), None)
        self.assertEqual(concatenate_authors(None), None)
        self.assertEqual(concatenate_authors("Hello"), None)

    def test_arxiv_version_removal(self):
        """Test that the version of an arXiv id is correctly removed."""
        self.assertEqual(remove_arxiv_id_version("1606.04401v2"), "1606.04401")
        self.assertEqual(remove_arxiv_id_version("1606.04401"), "1606.04401")


class TestReferenceClass(unittest.TestCase):
    """Test the Reference class from reference_utils.py"""
    def test_reference_class(self):
        """Test the extraction and formating of reference data."""
        reference = Reference("\\bibitem{tba1} A.~Zamolodchikov, \\newblock "
                              "{``Thermodynamic Bethe ansatz in relativistic models. "
                              "Scaling   three state Potts and Lee-Yang models''}, "
                              "\\newblock Nucl. Phys. B {\\bf 342}, 695--720 (1990)."
                              "\\\\ DOI: 10.1016/0550-3213(90)90333-9")
        reference.main()
        self.assertEqual(reference.bibitem_identifier, "tba1")
        self.assertEqual(reference.doi, "10.1016/0550-3213(90)90333-9")
        self.assertEqual(reference.item_type, "journal-article")
        self.assertEqual(reference.full_authors, ['Al.B. Zamolodchikov'])
        self.assertEqual(reference.abbreviated_authors, ['Al. B. Zamolodchikov'])
        self.assertEqual(reference.title, "Thermodynamic Bethe ansatz in relativistic models: Scaling 3-state potts and Lee-Yang models")
        self.assertEqual(reference.year, 1990)
        self.assertEqual(reference.journal, "Nuclear Physics B")
        self.assertEqual(reference.short_journal, "Nucl. Phys. B")
        self.assertEqual(reference.volume, "342")
        self.assertEqual(reference.issue, "3")
        self.assertEqual(reference.page, "695-720")
        self.assertEqual(reference.article_number, None)
        self.assertEqual(reference.publisher, "Elsevier BV")
        self.assertEqual(reference.reformatted_original_reference,
                         "A.~Zamolodchikov, {``Thermodynamic Bethe ansatz in relativistic models. "
                         "Scaling three state Potts and Lee-Yang models''}, Nucl. Phys. B {\\bf 342}, "
                         "695--720 (1990).\\\\ DOI: 10.1016/0550-3213(90)90333-9")
        self.assertEqual(reference.formatted_reference,
                         "Al. B. Zamolodchikov, \\textit{Thermodynamic Bethe ansatz in relativistic "
                         "models: Scaling 3-state potts and Lee-Yang models}, Nucl. Phys. B \\textbf{342}, "
                         "695-720 (1990), \\doi{10.1016/0550-3213(90)90333-9}.")
        # Test that a reference without a valid DOI does not return anything.
        reference = Reference("\\bibitem{tba1} A.~Zamolodchikov, \\newblock "
                              "{``Thermodynamic Bethe ansatz in relativistic models. "
                              "Scaling   three state Potts and Lee-Yang models''}, "
                              "\\newblock Nucl. Phys. B {\\bf 342}, 695--720 (1990)."
                              "\\\\ DOI: 10.1016/zzzzzzzzzzzzzzzzzzzzzz")
        reference.main()
        self.assertEqual(reference.crossref_data, None)
        self.assertEqual(reference.formatted_reference,
                         "AUTHORS, \\textit{{TITLE}}, JOURNAL \\textbf{{VOLUME}}, "
                         "PAGE/ARTICLE NUMBER (YEAR), \\doi{{DOI}}.")
        # Test that a reference with an arXiv id which has been published is correctly cited.
        reference = Reference("\\bibitem{Dubail}, Dubail et. al. \emph{Conformal Field Theory for "
                              "Inhomogeneous One-dimensional Quantum Systems: the Example of "
                              "Non-Interacting Fermi Gases}, arXiv:1606.04401v2")
        reference.main()
        # Check that the DOI of this arXiv entry was picked up correctly.
        self.assertEqual(reference.doi, "10.21468/SciPostPhys.2.1.002")
        self.assertEqual(reference.formatted_reference, "J. Dubail, P. Calabrese, J.-M. Stéphan and J. Viti, "
                         "\\textit{Conformal field theory for inhomogeneous one-dimensional quantum  systems: "
                         "the example of non-interacting Fermi gases}, SciPost Phys. \\textbf{2}, None (2017), "
                         "\\doi{10.21468/SciPostPhys.2.1.002}.")
        # Test a reference which only appears on the arXiv.
        reference = Reference("\\bibitem{Mehendale}, \emph{On Hadwiger Conjecture}, https://arxiv.org/abs/0705.0100v5")
        reference.main()
        self.assertEqual(reference.arxiv_id, "0705.0100v5")
        self.assertEqual(reference.formatted_reference, "D. P. Mehendale, \\textit{On Hadwiger Conjecture}, "
                         "\href{https://arxiv.org/abs/0705.0100v5}{arXiv:0705.0100v5}. % Has this been published somewhere?")


if __name__ == "__main__":
    unittest.main(buffer=True, verbosity=2, catchbreak=True)
