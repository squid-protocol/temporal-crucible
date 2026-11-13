"""Unit tests for tools/etyp_label.py (ETYP-LABEL). Stdlib unittest; skipped without numpy.

Run: python -m unittest tests.test_etyp_label -v
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

try:
    import numpy as np
    import etyp_label as el
    HAVE = True
except ImportError:
    HAVE = False


@unittest.skipUnless(HAVE, "numpy not installed")
class Model(unittest.TestCase):
    def test_auc_handles_ties_and_extremes(self):
        y = np.array([0, 0, 1, 1.0])
        self.assertEqual(el.auc(np.array([1, 2, 3, 4.0]), y), 1.0)
        self.assertEqual(el.auc(np.array([4, 3, 2, 1.0]), y), 0.0)
        self.assertEqual(el.auc(np.array([1, 1, 1, 1.0]), y), 0.5)

    def test_logit_recovers_the_informative_feature(self):
        rng = np.random.default_rng(0)
        Z = rng.normal(size=(2000, 3))
        y = (rng.random(2000) < 1 / (1 + np.exp(-2 * Z[:, 1]))).astype(float)
        w = el.fit_logit(Z, y)
        self.assertGreater(w[2], 1.5)
        self.assertLess(abs(w[1]), 0.3)
        self.assertLess(abs(w[3]), 0.3)

    def test_labelled_steps_are_limited_to_the_burned_repos_and_score_reads_no_label(self):
        src = pathlib.Path(el.__file__).read_text()
        self.assertIn('ap.add_argument("--repo", choices=("curl", "libarchive"))', src)
        body = src.split("def cmd_score", 1)[1].split("def main", 1)[0]
        self.assertNotIn("labelled(", body)
        self.assertNotIn("load_events", body)


if __name__ == "__main__":
    unittest.main()
