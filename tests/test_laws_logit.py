"""Firth logistic regression, cluster-robust covariance and marginal effects, against statsmodels and by simulation."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import laws_logit as L  # noqa: E402


def data(n=4000, seed=0, beta=(-1.0, 0.8, -0.5)):
    rng = np.random.default_rng(seed)
    x = np.column_stack([np.ones(n), rng.normal(size=n), rng.integers(0, 2, n)])
    y = (rng.random(n) < L._p(x @ np.array(beta))).astype(float)
    return x, y


def test_firth_agrees_with_maximum_likelihood_on_a_large_sample():
    import statsmodels.api as sm
    x, y = data()
    f = L.firth(x, y)
    ml = sm.Logit(y, x).fit(disp=0)
    assert f["converged"] and np.allclose(f["beta"], ml.params, atol=0.01)  # the penalty is O(1/n)
    assert np.allclose(np.sqrt(np.diag(f["cov"])), ml.bse, rtol=0.02)


def test_firth_stays_finite_under_complete_separation():
    x = np.column_stack([np.ones(40), np.r_[np.zeros(20), np.ones(20)]])
    y = np.r_[np.zeros(20), np.ones(20)]  # the column predicts the outcome perfectly: ML has no finite estimate
    f = L.firth(x, y)
    assert f["converged"] and np.all(np.isfinite(f["beta"])) and 3 < f["beta"][1] < 12


def test_one_way_cluster_covariance_matches_statsmodels():
    import statsmodels.api as sm
    x, y = data(seed=3)
    groups = np.repeat(np.arange(400), 10)
    f = L.firth(x, y)
    mine = np.sqrt(np.diag(L.cov_cluster(x, y, f, groups)["cov"]))
    ref = sm.Logit(y, x).fit(disp=0, cov_type="cluster", cov_kwds={"groups": groups, "use_correction": True}).bse
    assert np.allclose(mine, ref, rtol=0.03)


def test_clustered_errors_grow_when_rows_of_a_cluster_share_a_shock():
    rng = np.random.default_rng(1)
    g = np.repeat(np.arange(200), 20)
    shock = rng.normal(size=200)[g]
    x = np.column_stack([np.ones(4000), shock + 0.1 * rng.normal(size=4000)])  # the covariate is nearly constant in a cluster
    y = (rng.random(4000) < L._p(-0.5 + 0.7 * shock + rng.normal(size=200)[g])).astype(float)  # and so is an unseen shock
    f = L.firth(x, y)
    naive, robust = np.sqrt(np.diag(f["cov"]))[1], np.sqrt(np.diag(L.cov_cluster(x, y, f, g)["cov"]))[1]
    assert robust > 1.5 * naive


def test_two_way_covariance_is_the_sum_minus_the_intersection():
    x, y = data(seed=5)
    a, b = np.repeat(np.arange(400), 10), np.tile(np.arange(100), 40)
    f = L.firth(x, y)
    va, vb = L.cov_cluster(x, y, f, a)["cov"], L.cov_cluster(x, y, f, b)["cov"]
    vab = L.cov_cluster(x, y, f, a * 1000 + b)["cov"]
    two = L.cov_cluster(x, y, f, a, b)
    assert np.allclose(two["cov"], va + vb - vab) and two["ok"] and two["clusters_a"] == 400 and two["clusters_b"] == 100


def test_average_marginal_effects():
    x, y = data(n=20000, seed=2)
    f = L.firth(x, y)
    p = f["p"]
    assert L.ame(x, f, 1) == pytest.approx(float(np.mean(p * (1 - p))) * f["beta"][1])
    x1, x0 = x.copy(), x.copy()
    x1[:, 2], x0[:, 2] = 1, 0
    assert L.ame(x, f, 2, binary=True) == pytest.approx(float(np.mean(L._p(x1 @ f["beta"]) - L._p(x0 @ f["beta"]))))
    assert L.ame(x, f, 2, binary=True) < 0 < L.ame(x, f, 1)


def test_vif_flags_collinear_columns():
    rng = np.random.default_rng(0)
    a = rng.normal(size=2000)
    x = np.column_stack([np.ones(2000), a, a + 0.1 * rng.normal(size=2000), rng.normal(size=2000)])
    v = L.vif(x)
    assert np.isnan(v[0]) and v[1] > 50 and v[2] > 50 and v[3] < 1.1
