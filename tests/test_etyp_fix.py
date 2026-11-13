"""Unit tests for tools/etyp_fix.py (ETYP-FIX). Stdlib unittest; skipped without numpy.

Run: python -m unittest tests.test_etyp_fix -v
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

try:
    import numpy as np
    import etyp_fix as ef
    HAVE = True
except ImportError:
    HAVE = False


@unittest.skipUnless(HAVE, "numpy not installed")
class Join(unittest.TestCase):
    def rows(self):
        mk = lambda sha, func, labels, tadd: {"sha": sha, "ct": 10, "path": "a.c", "func": func,
                                              "labels": labels, "primary": ef.et.primary(labels),
                                              "ntok": 50, "tadd": tadd, "tdel": 0, "err": False}
        return [mk("c1", "f", ["BRANCH_ADD"], 5), mk("c1", "g", ["COMMENT"], 0),
                mk("c2", "f", ["COND_EDIT", "OPERATOR"], 200)]

    def test_a_commit_is_a_vector_of_fractions(self):
        shas, X, n, _ct, mag = ef.commit_matrix(self.rows())
        i, col = shas.index("c1"), ef.COLS.index
        self.assertEqual((n[i], mag[i]), (2, 5))
        self.assertEqual(X[i, col("BRANCH_ADD")], 0.5)
        self.assertEqual(X[i, col("P:STRUCTURE")] + X[i, col("P:COSMETIC")], 1.0)

    def test_the_only_repos_offered_are_the_burned_ones(self):
        src = pathlib.Path(ef.__file__).read_text()
        self.assertIn('choices=("curl", "libarchive")', src)

    def test_size_alone_gives_no_lift(self):
        """Two groups that differ only in commit size show lift 1 once standardised."""
        rng = np.random.default_rng(1)
        bins = np.array([0] * 200 + [5] * 200)
        X = np.zeros((400, len(ef.COLS)))
        X[bins == 5, 0] = 1.0                       # the label depends on the size cell and nothing else
        g = np.zeros(400, dtype=bool)
        g[:20] = True
        g[200:380] = True                           # the group is mostly big commits
        res = ef.std_lift(X, bins, g, ~g, rng)[ef.COLS[0]]
        self.assertAlmostEqual(res["lift"], 1.0)
        self.assertGreater(res["share"], 0.8)


if __name__ == "__main__":
    unittest.main()
