import os, sys, json, tempfile, unittest
from datetime import datetime, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("FINAL_OUT", tempfile.mkdtemp(prefix="final_test_out_"))
import analysis as A

D0 = datetime(2026, 1, 1)
def sha(i): return "%040x" % (i + 1)
def mk_tm(levels, step=1):
    """levels: list of cpu per timed commit; index = position*step, one date per day"""
    return [(i * step, v, (D0 + timedelta(days=i * step)).strftime("%Y-%m-%d")) for i, v in enumerate(levels)]
def step(corpus, i, down=False, rel=0.5): return {"corpus": corpus, "sha": sha(i), "index": i, "down": down, "boundary_rel": rel, "boundary": [1, 1 + rel]}
T = {"a": 0.10, "b": 0.10}
SD = {sha(i): (D0 + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(200)}
def run(levels, steps, T=T):
    return A.persistence_analyze(steps, {"a": mk_tm(levels)}, T, SD)


class Persistence(unittest.TestCase):
    def test_planted_up_with_true_revert(self):
        lv = [10] * 10 + [15] * 10 + [10] * 10
        up, down, sk = run(lv, [step("a", 10)])
        self.assertEqual(len(up), 1); x = up[0]
        self.assertTrue(x["reversed"]); self.assertEqual(x["commits_to_reversal"], 9); self.assertEqual(x["days_to_reversal"], 9); self.assertFalse(x["elevated_at_tip"])

    def test_overshoot_counts_as_reversed(self):
        lv = [10] * 10 + [15] * 10 + [5] * 10
        up, _, _ = run(lv, [step("a", 10)])
        self.assertTrue(up[0]["reversed"]); self.assertTrue(up[0]["overshoot"])

    def test_up_then_unrelated_drop_named_down(self):
        lv = [10] * 10 + [15] * 15 + [10] * 10
        up, _, _ = run(lv, [step("a", 10), step("a", 25, down=True, rel=-0.33)])
        self.assertEqual(up[0]["removed_by_named_down"], sha(25)[:10])
        up2, _, _ = run(lv, [step("a", 10)])
        self.assertIsNone(up2[0]["removed_by_named_down"])

    def test_reversed_then_growth_tip_elevated_independent(self):
        lv = [10] * 10 + [15] * 8 + [10] * 6 + [30] * 6
        up, _, _ = run(lv, [step("a", 10)])
        self.assertTrue(up[0]["reversed"]); self.assertTrue(up[0]["elevated_at_tip"])

    def test_exactly_three_after_excluded(self):
        lv = [10] * 10 + [15] * 3
        up, _, sk = run(lv, [step("a", 10)])
        self.assertEqual(up, []); self.assertIn("fewer than 6", sk[0]["reason"])

    def test_not_visible_at_median_excluded(self):
        lv = [10] * 10 + [10.5] * 10
        up, _, sk = run(lv, [step("a", 10)])
        self.assertEqual(up, []); self.assertIn("within T", sk[0]["reason"])

    def test_down_uses_boundary_not_medians(self):
        # DOWN -30% at 10 followed by a +186% UP at 12 would give a positive median-level size; the DOWN row must carry boundary_rel
        lv = [10] * 10 + [7, 7] + [20] * 12
        up, down, sk = run(lv, [step("a", 10, down=True, rel=-0.3), step("a", 12, rel=1.86)])
        self.assertEqual(down[0]["boundary_rel"], -0.3); self.assertNotIn("size", down[0])

    def test_down_with_few_commits_after_still_reported(self):
        lv = [10] * 10 + [7] * 2
        _, down, _ = run(lv, [step("a", 10, down=True, rel=-0.3)])
        self.assertEqual(len(down), 1)

    def test_overlapping_flagged(self):
        lv = [10] * 10 + [15] * 4 + [30] * 12
        up, _, _ = run(lv, [step("a", 10), step("a", 12)])
        self.assertTrue(up[0]["overlap"])
        S = A.persistence_summary(up)
        self.assertEqual(S["n_overlapping_excluded"], len([x for x in up if x["overlap"]]))

    def test_same_commit_two_corpora_counted_once_per_commit(self):
        lv = [10] * 10 + [15] * 10 + [10] * 10
        tm = {"a": mk_tm(lv), "b": mk_tm(lv)}
        up, _, _ = A.persistence_analyze([step("a", 10), step("b", 10)], tm, T, SD)
        S = A.persistence_summary(up)
        self.assertEqual(S["pooled_corpus_commit_pairs"]["n"], 2); self.assertEqual(S["pooled_per_commit"]["n_commits"], 1)

    def test_eastern_vs_utc_day_count(self):
        from common import EAST
        utc = datetime.fromisoformat("2026-05-05T02:00:00+00:00")
        self.assertEqual(utc.astimezone(EAST).strftime("%Y-%m-%d"), "2026-05-04")
        rows = [{"target": "a", "fp_index": 1, "sha": "s1", "date": "2026-05-05", "exit": 0, "cpu_s": 1.0, "files_mapped": 1}]
        self.assertEqual(A.build_series(rows, {"s1": "2026-05-04"})["a"][1]["date"], "2026-05-04")
        lv = [10] * 10 + [15] * 10 + [10] * 10
        tm = mk_tm(lv)                                            # dates are one base (Eastern) for both step and series
        up, _, _ = A.persistence_analyze([step("a", 10)], {"a": tm}, T, SD)
        self.assertEqual(up[0]["days_to_reversal"], up[0]["commits_to_reversal"])

    def test_km_censoring(self):
        share, med = A.km_reversed([5, 10, 20], [True, False, False])
        self.assertAlmostEqual(share, 1 / 3)


class Events(unittest.TestCase):
    def R(self, corpus, found, metric, rel, down, cls="LOCALISED", i=1):
        return {"corpus": corpus, "from_sha": sha(i - 1), "to_sha": sha(i + 5), "from_date": "", "to_date": "", "dcpu": rel, "dfiles": 0, "metric": metric, "down": down, "found": found, "boundary": [10, 10 * (1 + rel)], "boundary_rel": rel, "class": cls}

    def test_same_commit_two_corpora_one_event(self):
        ev = A.make_events([self.R("a", sha(3), "cpu_s", .3, False), self.R("b", sha(3), "cpu_s", .5, False)], {sha(3): 3})
        self.assertEqual(len(ev), 1); self.assertEqual(set(ev[0]["corpora"]), {"a", "b"}); self.assertAlmostEqual(ev[0]["size_cpu"], .5)

    def test_duplicate_corpus_found_prefers_cpu_and_keeps_sizes_apart(self):
        ev = A.make_events([self.R("a", sha(3), "files_mapped", .05, False), self.R("a", sha(3), "cpu_s", .3, False)], {sha(3): 3})
        e = ev[0]; self.assertEqual(len(ev), 1); self.assertEqual(e["corpora"]["a"]["metric"], "cpu_s")
        self.assertAlmostEqual(e["size_cpu"], .3); self.assertAlmostEqual(e["size_files"], .05)

    def test_cpu_up_files_down_both_kept(self):
        ev = A.make_events([self.R("a", sha(3), "cpu_s", .15, False), self.R("a", sha(3), "files_mapped", -.40, True)], {sha(3): 3})[0]
        self.assertAlmostEqual(ev["size_cpu"], .15); self.assertAlmostEqual(ev["size_files"], .40); self.assertEqual(ev["direction"], "up")
        self.assertAlmostEqual(ev["corpora"]["a"]["files_rel"], -.40)

    def test_files_only_event_has_no_cpu_size(self):
        ev = A.make_events([self.R("a", sha(3), "files_mapped", .05, False)], {sha(3): 3})[0]
        self.assertIsNone(ev["size_cpu"]); self.assertAlmostEqual(ev["size_files"], .05)

    def test_mixed_direction(self):
        ev = A.make_events([self.R("a", sha(3), "cpu_s", .3, False), self.R("b", sha(3), "cpu_s", -.2, True)], {sha(3): 3})[0]
        self.assertEqual(ev["direction"], "mixed")

    def test_unconfirmed_not_an_event(self):
        self.assertEqual(A.make_events([self.R("a", sha(3), "cpu_s", .3, False, cls="UNCONFIRMED")], {sha(3): 3}), [])

    def test_merge_passes(self):
        p1 = [self.R("a", sha(3), "cpu_s", .0, False, cls="UNCONFIRMED"), self.R("b", sha(4), "cpu_s", .3, False, i=2)]
        p2 = [{**p1[0], "class": "LOCALISED", "dcpu_raw": .1004, "pass1_class": "UNCONFIRMED"}]
        rows, info = A.merge_passes(p1, p2 + p2)       # duplicate pass-2 line deduped
        self.assertEqual(len(rows), 2); self.assertEqual(info["n_changed_class"], 1)
        self.assertEqual([r for r in rows if r["corpus"] == "a"][0]["class"], "LOCALISED")
        rows1, info1 = A.merge_passes(p1 + p1, [])
        self.assertEqual(len(rows1), 2); self.assertEqual(info1["n_changed_class"], 0)

    def test_loader_with_and_without_pass2(self):
        import common
        d = Path(tempfile.mkdtemp())
        p1 = [self.R("a", sha(3), "cpu_s", .0, False, cls="UNCONFIRMED")]
        (d / "refined.jsonl").write_text(json.dumps(p1[0]) + "\n")
        common._snap = d; self.assertEqual(common.load_refined()[0]["class"], "UNCONFIRMED")
        (d / "refined_pass2.jsonl").write_text(json.dumps({**p1[0], "class": "LOCALISED", "pass1_class": "UNCONFIRMED"}) + "\n")
        r, info = common.load_refined_info(); self.assertEqual(r[0]["class"], "LOCALISED"); self.assertEqual(info["n_changed_class"], 1)
        common._snap = None


class Detection(unittest.TestCase):
    def test_rounding_raw_dcpu(self):
        c = {"cpu": [10.0, 11.004], "dcpu": round(0.1004, 3)}
        self.assertGreater(A.raw_dcpu(c), 0.10); self.assertFalse(abs(c["dcpu"]) > 0.10)

    def test_crash_gap_pair_listed(self):
        rows = [{"target": "a", "fp_index": i, "sha": sha(i), "date": "2026-01-0%d" % (i + 1), "exit": 1 if i in (2, 3) else 0, "cpu_s": None if i in (2, 3) else (10 if i < 2 else 12), "files_mapped": 5} for i in range(6)]
        s = A.build_series(rows)
        g = A.crash_gap_pairs(s, "a")
        self.assertEqual(len(g), 1); self.assertEqual((g[0]["from"], g[0]["to"]), (1, 4)); self.assertAlmostEqual(g[0]["dcpu"], 0.2)

    def test_anchor_runs_excluded(self):
        rows = [{"target": "a", "fp_index": 1, "sha": "x", "date": "d", "exit": 0, "cpu_s": 5, "anchor_n": 1}]
        self.assertEqual(dict(A.build_series(rows)), {})


class Stats(unittest.TestCase):
    def test_fisher_zero_zero_is_nan(self):
        o, p = A.fisher_exact(0, 5, 0, 10); self.assertTrue(o != o)
        o, p = A.fisher_exact(3, 0, 0, 5); self.assertEqual(o, float("inf"))

    def test_fisher_known_value(self):
        o, p = A.fisher_exact(3, 1, 1, 3); self.assertAlmostEqual(p, 0.4857142857, places=6)

    def test_cp_large_n(self):
        lo, hi = A.clopper_pearson(800, 1634); self.assertTrue(0.46 < lo < 0.47 and 0.51 < hi < 0.52)
        lo, hi = A.clopper_pearson(0, 1634); self.assertEqual(lo, 0.0)
        lo, hi = A.clopper_pearson(1634, 1634); self.assertEqual(hi, 1.0)

    def test_cp_small(self):
        lo, hi = A.clopper_pearson(3, 10); self.assertAlmostEqual(lo, 0.0667, places=3); self.assertAlmostEqual(hi, 0.6525, places=3)

    def test_mh_single_stratum_close_to_fisher_or(self):
        o, p, used = A.mantel_haenszel([(10, 5, 5, 10)]); self.assertAlmostEqual(o, 4.0); self.assertEqual(used, 1)

    def test_quiet_test_populations(self):
        mk = lambda q, era: {"q": q, "era": era}
        group = [mk(True, "fleet"), mk(False, "fleet"), mk(False, "claude")]
        others = [mk(True, "fleet")] * 6 + [mk(False, "claude")] * 4
        r = A.quiet_test(group, others, "q")
        self.assertEqual((r["n_events"], r["quiet_events"], r["n_others"], r["quiet_others"]), (3, 1, 10, 6))
        self.assertEqual(sum(s["events"] for s in r["strata"].values()), 3)

    def test_eras(self):
        self.assertEqual([A.era_of_date(d) for d in ("2026-07-05", "2026-07-06", "2026-07-21", "2026-07-22", "2026-09-26", "2026-09-27")], ["gemini", "transition", "transition", "claude", "claude", "fleet"])


class Text(unittest.TestCase):
    def test_perf_regex(self):
        for bad in ("COBOL: PERFORM x TIMES", "FastAPI()", "ruff PERF401", "fasten the belt", "caches"[:0] + "cachet"):
            self.assertIsNone(A.PERF.search(bad), bad)
        for good in ("perf(detector): skip lines", "make it faster", "add a cache", "O(n^2) scan", "slow down", "lookup table", "memoize results"):
            self.assertIsNotNone(A.PERF.search(good), good)
        self.assertIsNotNone(A.PERF_OLD.search("COBOL: PERFORM x TIMES"))        # the inherited regex over-matches

    def test_pr_number(self):
        self.assertEqual(A.pr_number('Revert "fix x (#992)"'), 992)
        self.assertEqual(A.pr_number("docs: x (#1475) trailing words"), 1475)
        self.assertEqual(A.pr_number("fix (#3211-followup, epic #3122) (#3847)"), 3847)
        self.assertIsNone(A.pr_number("no number here"))

    def test_buckets(self):
        self.assertEqual(A.bucket([], 0), "e"); self.assertEqual(A.bucket(["tests/x.py"], 0), "d")
        self.assertEqual(A.bucket(["gitgalaxy/standards/x.py"], 0), "a"); self.assertEqual(A.bucket(["gitgalaxy/core/x.py"], 3), "b")
        self.assertEqual(A.bucket(["gitgalaxy/core/x.py"], 4), "c"); self.assertEqual(A.bucket(["gitgalaxy/core/x.py"], 4, cutoff=5), "b")
        self.assertEqual(A.bucket(["gitgalaxy/core/x.py"], 0, gap=True), "gap")


class Git(unittest.TestCase):
    def test_numstat_merge_commit(self):
        import common
        if not common.MIRROR.exists(): self.skipTest("no mirror")
        merges = common.git("rev-list", "--first-parent", "--merges", "-n", "1", common.TIP).split()
        if not merges: self.skipTest("no merge")
        a, d = common.numstat(merges[0]); self.assertGreater(a + d, 0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
