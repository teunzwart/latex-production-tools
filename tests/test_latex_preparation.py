import os
import unittest
import tempfile

from latex_preparation import LatexPreparer


class TestLatexPreparer(unittest.TestCase):
    def test_submission_scipost_metadata_retrieval(self):
        latex_preparer = LatexPreparer("https://scipost.org/submissions/1611.08225v2/")
        latex_preparer.retrieve_scipost_submission_data()
        self.assertEqual(latex_preparer.arxiv_id, "1611.08225v2")
        self.assertEqual(latex_preparer.submission_date, "31-01-2017")

    def test_error_if_not_current_version(self):
        """Test that the program exits when the link does not point to the current version."""
        latex_preparer = LatexPreparer("https://scipost.org/submissions/1611.08225v1/")
        with self.assertRaises(SystemExit) as error:
            latex_preparer.retrieve_scipost_submission_data()
        self.assertEqual(error.exception.code, "Not the current version.")

    def test_arxiv_metadata_retrieval(self):
        latex_preparer = LatexPreparer("https://scipost.org/submissions/1611.08225v2/")
        latex_preparer.retrieve_scipost_submission_data()
        latex_preparer.retrieve_arxiv_metadata()
        self.assertEqual(latex_preparer.title, "A note on generalized hydrodynamics: inhomogeneous fields and other concepts")
        self.assertEqual(latex_preparer.full_authors, ['Benjamin Doyon', 'Takato Yoshimura'])
        self.assertEqual(latex_preparer.abbreviated_authors, ['B. Doyon', 'T. Yoshimura'])
        self.assertEqual(latex_preparer.first_author_last_name, "Doyon")
        # Remove the newlines for the comparison (we keep them in the program to make the final LaTeX file look nicer).
        self.assertEqual(latex_preparer.abstract.replace("\n", " "),
                         ("Generalized hydrodynamics (GHD) was proposed recently as a formulation of "
                          "hydrodynamics for integrable systems, taking into account infinitely-many "
                          "conservation laws. In this note we further develop the theory in various "
                          "directions. By extending GHD to all commuting flows of the integrable model, we "
                          "provide a full description of how to take into account weakly varying force "
                          "fields, temperature fields and other inhomogeneous external fields within GHD. "
                          "We expect this can be used, for instance, to characterize the non-equilibrium "
                          "dynamics of one-dimensional Bose gases in trap potentials. We further show how "
                          "the equations of state at the core of GHD follow from the continuity relation "
                          "for entropy, and we show how to recover Euler-like equations and discuss "
                          "possible viscosity terms."))

    def test_production_folder_preparation(self):
        """
        Test for the correct preparation of the submission production folder.

        This submission's source consists of a single tex file. This also tests that these are handled properly.
        """
        latex_preparer = LatexPreparer("https://scipost.org/submissions/1611.08225v2/")
        latex_preparer.retrieve_scipost_submission_data()
        latex_preparer.retrieve_arxiv_metadata()
        with tempfile.TemporaryDirectory() as temp_dir:
            latex_preparer.prepare_production_folder(production_path=temp_dir)
            self.assertEqual(latex_preparer.publication_tex_filename, "SciPost_Phys_1611_08225v2_Doyon.tex")
            latex_preparer.download_arxiv_source()
            self.assertEqual(os.listdir(latex_preparer.publication_production_folder),
                             ["1611.08225v2.tar.gz",
                              "1611.08225v2.tex",
                              'by.eps',
                              'logo_scipost_with_bgd.pdf',
                              'SciPost.cls',
                              'SciPost_bibstyle.bst',
                              'SciPost_Phys_1611_08225v2_Doyon.tex',
                              'SciPost_Phys_Skeleton.tex'])
            # Check that trying to create the same folder twice fails.
            with self.assertRaises(SystemExit) as error:
                latex_preparer.prepare_production_folder(production_path=temp_dir)
            self.assertEqual(error.exception.code, "Folder already exists! Aborting...")

    def test_arxiv_latex_source_retrieval(self):
        """Test that source retrieval and extraction went correctly."""
        latex_preparer = LatexPreparer("https://scipost.org/submissions/1610.02036v3/")
        latex_preparer.retrieve_scipost_submission_data()
        latex_preparer.retrieve_arxiv_metadata()
        with tempfile.TemporaryDirectory() as temp_dir:
            latex_preparer.prepare_production_folder(production_path=temp_dir)
            latex_preparer.download_arxiv_source()
            # Check that the source file was correctly untarred.
            self.assertEqual(os.listdir(os.path.join(latex_preparer.publication_production_folder, latex_preparer.arxiv_id)),
                             ['Dets.pdf',
                              'Matrixblocks.pdf',
                              'MlhPlot.pdf',
                              'NEB_PulseOverlap.tex',
                              'Particle_Mixing.pdf',
                              'SciPost.cls',
                              'SciPost_bibstyle.bst',
                              'Set_Dis_SN.pdf',
                              'setup.pdf',
                              'Setup_basic.pdf',
                              'windowfunction.pdf'])
            # Check that all required files are copied up one level.
            self.assertEqual(os.listdir(latex_preparer.publication_production_folder),
                             ['1610.02036v3',
                              '1610.02036v3.tar.gz',
                              'by.eps', 'Dets.pdf',
                              'logo_scipost_with_bgd.pdf',
                              'Matrixblocks.pdf',
                              'MlhPlot.pdf',
                              'NEB_PulseOverlap.tex',
                              'Particle_Mixing.pdf',
                              'SciPost.cls',
                              'SciPost_bibstyle.bst',
                              'SciPost_Phys_1610_02036v3_Schneider.tex',
                              'SciPost_Phys_Skeleton.tex',
                              'Set_Dis_SN.pdf',
                              'setup.pdf',
                              'Setup_basic.pdf',
                              'windowfunction.pdf'])


if __name__ == "__main__":
    unittest.main(buffer=True, verbosity=2)
