"""LAW-6 and LAW-7 on simulated file-years with a known cycle effect and a known size confound."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import laws_defects as D  # noqa: E402


def panel(cycle_or: float = 0.0, confound: float = 1.0, n_files: int = 500, years: int = 8, seed: int = 0) -> list[dict]:
    """File-years where the log odds of a fix are -1.5 + 0.9 * z(size) + cycle_or * in_cycle + a file effect, and the
    network metrics k_mean and coupling follow size with strength `confound` (0: independent of size)."""
    rng = np.random.default_rng(seed)
    size = rng.normal(size=n_files)
    file_fx = 0.4 * rng.normal(size=n_files)
    in_cycle = (rng.random(n_files) < 0.3).astype(int)
    rows = []
    for f in range(n_files):
        for y in range(years):
            p = 1 / (1 + np.exp(-(-1.5 + 0.9 * size[f] + cycle_or * in_cycle[f] + file_fx[f])))
            out = int(rng.random() < p)
            noise = rng.normal(size=2)
            rows.append({"file": f, "year": 2010 + y, "outcome": out, "fix_commit": f"c{f}_{y}" if out else None,
                         "loc": int(np.exp(4 + size[f])), "functions": int(np.exp(1.5 + 0.8 * size[f])) + 1,
                         "churn": int(rng.poisson(2)), "prior_fixes": int(rng.poisson(0.5)), "authors": int(rng.poisson(1)) + 1,
                         "coupled": int(rng.poisson(1)), "k_mean": float(np.exp(confound * size[f] + 0.7 * noise[0])),
                         "callers": int(np.exp(1 + confound * size[f] + 0.7 * noise[1])), "callees": 2,
                         "in_cycle": int(in_cycle[f]), "giant": 0, "scc": 3 if in_cycle[f] else 1})
    return rows


def test_law6_recovers_a_cycle_effect_beside_the_controls():
    r = D.law6(panel(cycle_or=0.7), boot=50)
    assert r["evaluable"] and r["effect"] == pytest.approx(0.7, abs=0.2) and r["effect"] > 4 * r["se"]
    assert r["se"] > r["se_naive"]  # eight years of one file are not eight independent rows
    assert r["se_method"].startswith("two-way") and 0.25 < r["in_cycle_share"] < 0.35 and r["files"] == 500


def test_law6_reads_no_cycle_effect_as_zero():
    r = D.law6(panel(cycle_or=0.0, seed=4), boot=50)
    assert r["evaluable"] and abs(r["effect"]) < 3 * r["se"]


def test_law6_is_not_evaluable_without_cycles_or_without_outcomes():
    rows = panel()
    for row in rows:
        row["in_cycle"] = 0
    assert "in-cycle share" in D.law6(rows)["why"]
    assert "fewer than" in D.law6(panel(n_files=20, years=2))["why"]


def test_law7_a_metric_that_only_tracks_size_loses_most_of_its_effect():
    r = D.law7(panel(confound=1.0), boot=60)
    for metric in ("k_mean", "coupling"):
        m = r["metrics"][metric]
        assert m["evaluable"] and m["ame_unadjusted"] > 0.03 and m["effect"] > 0.6  # the association was size
    assert not r["metrics"]["in_cycle"]["evaluable"]  # no unadjusted effect: attenuation is undefined there


def test_law7_a_metric_with_its_own_effect_keeps_it():
    rows = panel(cycle_or=1.0, confound=0.0, seed=2)
    m = D.law7(rows, boot=60)["metrics"]["in_cycle"]
    assert m["evaluable"] and abs(m["effect"]) < 0.3  # independent of size: adjusting for size changes little
