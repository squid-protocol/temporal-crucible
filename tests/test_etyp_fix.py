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

DAY = 86400


def row(sha, func, labels, ct=10, tadd=5, path="a.c"):
    return {"sha": sha, "ct": ct, "au": "x", "path": path, "func": func, "labels": labels,
            "primary": ef.et.primary(labels), "ntok": 50, "tadd": tadd, "tdel": 0, "err": False}


@unittest.skipUnless(HAVE, "numpy not installed")
class Lifts(unittest.TestCase):
    def test_a_commit_is_a_vector_of_fractions_and_sweeps_are_dropped(self):
        rows = [row("c1", "f", ["BRANCH_ADD"]), row("c1", "g", ["COMMENT"], tadd=0),
                row("c2", "f", ["COND_EDIT", "OPERATOR"], tadd=200)]
        rows += [row("sweep", f"h{i}", ["FORMAT"]) for i in range(ef.et.SWEEP + 1)]
        shas, X, n, _ct, mag = ef.commit_matrix(rows)
        self.assertNotIn("sweep", shas)
        i, col = shas.index("c1"), ef.COLS.index
        self.assertEqual((n[i], mag[i]), (2, 5))
        self.assertEqual(X[i, col("BRANCH_ADD")], 0.5)
        self.assertEqual(X[i, col("P:STRUCTURE")] + X[i, col("P:COSMETIC")], 1.0)

    def test_size_alone_gives_no_lift(self):
        """Two groups that differ only in commit size show lift 1 once standardised."""
        rng = np.random.default_rng(1)
        bins = np.array([0] * 200 + [5] * 200)
        X = np.zeros((400, len(ef.COLS)))
        X[bins == 5, 0] = 1.0
        g = np.zeros(400, dtype=bool)
        g[:20] = True
        g[200:380] = True
        res = ef.std_lift(X, bins, g, ~g, rng)[ef.COLS[0]]
        self.assertAlmostEqual(res["lift"], 1.0)
        self.assertFalse(res["marked"])

    def test_a_cell_the_reference_does_not_occupy_is_renormalised_not_dropped(self):
        """Every commit has share 0.5; half the group sits where the reference has nobody. Lift must be 1."""
        rng = np.random.default_rng(1)
        bins = np.array([0] * 100 + [1] * 100 + [0] * 200)
        X = np.full((400, len(ef.COLS)), 0.5)
        g = np.zeros(400, dtype=bool)
        g[:200] = True                                # group: cells 0 and 1; reference: cell 0 only
        res = ef.std_lift(X, bins, g, ~g, rng)
        self.assertAlmostEqual(res[ef.COLS[0]]["lift"], 1.0)
        self.assertAlmostEqual(res["_lost_weight"], 0.5)

    def test_zero_occurrences_never_earn_a_mark(self):
        rng = np.random.default_rng(1)
        bins = np.zeros(300, dtype=int)
        X = np.zeros((300, len(ef.COLS)))
        X[30:, 0] = 1.0                               # the reference always has it, the group never
        g = np.zeros(300, dtype=bool)
        g[:30] = True
        res = ef.std_lift(X, bins, g, ~g, rng)[ef.COLS[0]]
        self.assertEqual((res["lift"], res["k_group"]), (0.0, 0))
        self.assertFalse(res["marked"])

    def test_the_reference_never_contains_the_group_and_inducing_groups_hold_no_fixes(self):
        n = 6
        z = np.zeros(n, dtype=bool)
        m = {"fix": np.array([1, 1, 0, 0, 0, 0], bool), "dropped": np.array([0, 0, 1, 0, 0, 0], bool),
             "nonfix": np.array([0, 0, 0, 1, 1, 1], bool), "window": ~z, "platform": z, "reported": z,
             "cls": np.array(["other-fix", "regression", "", "", "", ""]), "cve_fix": z, "control": z,
             "cve_intro": np.array([1, 0, 1, 1, 0, 0], bool), "reg_inducing": z}
        for name, g, ref, _sec in ef.contrasts(m):
            self.assertFalse((g & ref).any(), name)
        intro = dict((c[0], c[1]) for c in ef.contrasts(m))["CVE-introducing"]
        self.assertEqual(intro.tolist(), [False, False, False, True, False, False])

    def test_the_only_repos_offered_are_the_burned_ones(self):
        src = pathlib.Path(ef.__file__).read_text()
        self.assertIn('choices=("curl", "libarchive")', src)


@unittest.skipUnless(HAVE, "numpy not installed")
class FollowUp(unittest.TestCase):
    EVS = {"since": 0, "head_ct": 10 ** 10, "dropped": {"drop"}}

    def run_fu(self, rows, fixes):
        evs = dict(self.EVS, **{"class": {s: "other-fix" for s in fixes}})
        return ef.follow_up(rows, evs, np.random.default_rng(3))

    def test_each_type_is_compared_with_the_others_in_its_stratum(self):
        """BRANCH_ADD edits are fixed 60% of the time, OPERATOR edits 30%: relative rates 2.0 and 0.5."""
        rows, fixes = [], set()
        for i in range(200):
            lab = ["BRANCH_ADD"] if i < 100 else ["OPERATOR"]
            rows.append(row(f"e{i}", f"fn{i}", lab, ct=1000))
            if (i % 10) < (6 if i < 100 else 3):
                rows.append(row(f"x{i}", f"fn{i}", ["COND_EDIT"], ct=1000 + 30 * DAY))
                fixes.add(f"x{i}")
        fu = self.run_fu(rows, fixes)
        self.assertEqual(fu["eligible_edits"], 200)
        self.assertAlmostEqual(fu["by"]["BRANCH_ADD"]["fix"]["rel"], 2.0)
        self.assertAlmostEqual(fu["by"]["OPERATOR"]["fix"]["rel"], 0.5)

    def test_what_counts_as_an_exposure_and_as_an_outcome(self):
        rows = [row("e1", "f", ["BRANCH_ADD"], ct=1000),
                row("fx", "f", ["COND_EDIT"], ct=1000 + 366 * DAY),      # a fix, but a day too late
                row("drop", "g", ["BRANCH_ADD"], ct=1000),              # v3c-dropped: not an exposure
                row("fx2", "h", ["BRANCH_ADD"], ct=1000),               # a fix: not an exposure
                row("e2", "k", ["BRANCH_ADD"], ct=1000),
                row("late", "k", ["OPERATOR"], ct=10 ** 10 - 5)]        # less than a year of follow-up
        rows += [row("sweep", f"s{i}", ["BRANCH_ADD"], ct=1000) for i in range(ef.et.SWEEP + 1)]
        fu = self.run_fu(rows, {"fx", "fx2"})
        self.assertEqual(fu["eligible_edits"], 2)                       # e1 and e2 only
        self.assertEqual(fu["base_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
