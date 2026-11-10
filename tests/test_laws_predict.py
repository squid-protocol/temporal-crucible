"""LAW-8: forward, effort-aware prediction on simulated file-years where the network metrics do or do not carry signal."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import laws_predict as P  # noqa: E402

DAY = 86400


def panel(signal: float, n_files: int = 400, years: int = 9, seed: int = 0) -> list[dict]:
    """The log odds of a fix are -1.2 + 0.3 * z(churn) + signal * z(callers); the other columns are noise."""
    rng = np.random.default_rng(seed)
    rows = []
    for f in range(n_files):
        size = rng.normal()
        call = rng.normal()
        for y in range(years):
            churn = rng.normal()
            p = 1 / (1 + np.exp(-(-1.2 + 0.3 * churn + signal * call)))
            rows.append({"file": f, "year": 2010 + y, "t": 1_300_000_000 + y * 365 * DAY, "outcome": int(rng.random() < p),
                         "loc": int(np.exp(5 + 0.5 * size)), "functions": int(np.exp(2 + 0.4 * size)) + 1,
                         "churn": int(np.exp(1 + 0.6 * churn)), "prior_fixes": int(rng.poisson(0.5)), "authors": int(rng.poisson(1)) + 1,
                         "coupled": int(rng.poisson(1)), "k_mean": float(np.exp(0.3 * rng.normal())), "k_max": int(rng.poisson(3)),
                         "callers": int(np.exp(1.5 + 0.8 * call)), "callees": int(rng.poisson(3)), "in_cycle": int(rng.random() < 0.2),
                         "giant": 0})
    return rows


def test_network_metrics_that_carry_signal_raise_recall():
    r = P.fit(panel(signal=1.2))
    assert r["evaluable"] and r["test_years"] == 6  # three training years first
    assert r["effect"] > 0.05 and r["effect"] > 3 * r["se"] and r["auc_b"] > r["auc_a"] + 0.05 and r["popt_b"] > r["popt_a"]


def test_network_metrics_without_signal_add_nothing():
    r = P.fit(panel(signal=0.0, seed=3))
    assert r["evaluable"] and abs(r["effect"]) < 0.04 and abs(r["auc_b"] - r["auc_a"]) < 0.03


def test_training_rows_end_before_the_test_snapshot():
    rows = panel(signal=0.5, years=6)
    first = P.fit(rows)["by_year"][0]
    assert first["year"] == 2013 and first["train_rows"] == 3 * 400 and first["test_rows"] == 400
    late = [{**r, "t": r["t"] + 40 * DAY} if r["year"] == 2012 else r for r in rows]  # 2012's window now closes after 2013's snapshot
    assert P.fit(late)["by_year"][0]["year"] == 2014


def test_effort_aware_metrics_on_a_hand_example():
    loc, y = np.array([10.0, 10, 40, 40]), np.array([1.0, 0, 1, 0])
    good, bad = np.array([0.9, 0.1, 0.8, 0.2]) / loc, np.array([0.1, 0.9, 0.2, 0.8]) / loc
    # 20% of the 100 LOC: `good` inspects the fixed 10-line file, then the clean one; `bad` the clean 10-line file,
    # then a 40-line file that no longer fits
    assert P.recall_at(good, loc, y, 0.2) == 0.5 and P.recall_at(bad, loc, y, 0.2) == 0.0
    assert P.recall_at(good, loc, y, 0.1) == 0.5 and P.recall_at(good, loc, y, 0.05) == 0.0
    assert P.popt(y / loc, loc, y) == pytest.approx(1.0) and P.popt(-(y / loc), loc, y) == pytest.approx(0.0)
    assert P.auc(np.array([0.9, 0.1, 0.8, 0.2]), y) == 1.0 and P.auc(np.array([0.1, 0.9, 0.2, 0.8]), y) == 0.0


def test_ridge_shrinks_and_the_intercept_is_free():
    rng = np.random.default_rng(0)
    x = np.column_stack([np.ones(3000), rng.normal(size=3000)])
    y = (rng.random(3000) < 1 / (1 + np.exp(-(1.0 + 1.5 * x[:, 1])))).astype(float)
    weak, strong = P.ridge_logit(x, y, 0.01), P.ridge_logit(x, y, 1000.0)
    assert weak[1] == pytest.approx(1.5, abs=0.15) and 0 < strong[1] < 0.6 * weak[1] and strong[0] > 0.5


def test_short_histories_are_not_evaluable():
    assert not P.fit(panel(signal=1.0, years=4))["evaluable"]
