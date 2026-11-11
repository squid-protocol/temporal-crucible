"""LAW-2: the conditional logit recovers a known attachment exponent, and reads uniform attachment as zero."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import laws_attach as A  # noqa: E402
import laws_net as N  # noqa: E402


def grow(alpha: float, local: float = 0.0, quarters: int = 14, n0: int = 400, new_nodes: int = 15, new_edges: int = 260,
         seed: int = 3) -> list:
    """Networks that grow by `new_edges` a quarter, each new edge's target drawn with weight
    (k + 1)^alpha * exp(local * same_file)."""
    rng = np.random.default_rng(seed)
    name = lambda i: (f"d{i % 40 % 7}/f{i % 40}.c", "", f"fn{i}")  # noqa: E731  40 files in 7 directories
    nodes = [name(i) for i in range(n0)]
    edges: set = set()
    nets = []
    for q in range(quarters):
        k = {n: 0 for n in nodes}
        for _, d in edges:
            k[d] += 1
        net = N.Net(f"sha{q}", f"2020-{q:02d}")
        net.nodes = {n: {"loc": 10 + (hash(n) % 50), "n": 1, "file": n[0], "test": False} for n in nodes}
        net.edges = set(edges)
        nets.append(net)
        kv = np.array([k[n] for n in nodes], dtype=float)
        files = np.array([n[0] for n in nodes])
        for _ in range(new_edges):
            u = nodes[rng.integers(len(nodes))]
            w = np.power(kv + 1, alpha) * np.exp(local * (files == u[0]))
            w[nodes.index(u)] = 0  # never itself
            edges.add((u, nodes[rng.choice(len(nodes), p=w / w.sum())]))
        nodes = nodes + [name(i) for i in range(len(nodes), len(nodes) + new_nodes)]
    return nets


def test_a_known_exponent_is_recovered_beside_locality():
    r = A.fit(grow(alpha=1.0, local=1.5))
    assert r["evaluable"] and r["choices"] > 2500
    assert r["effect"] == pytest.approx(1.0, abs=0.12) and r["effect"] > 5 * r["se"]
    assert r["coefficients"]["same_file"]["b"] == pytest.approx(1.5, abs=0.35)


def test_uniform_attachment_reads_as_zero():
    r = A.fit(grow(alpha=0.0, local=1.0, seed=5))
    assert r["evaluable"] and abs(r["effect"]) < 3 * r["se"] + 0.05


def test_the_clustered_se_is_no_smaller_than_nothing_and_the_fit_is_reproducible():
    nets = grow(alpha=0.6)
    a, b = A.fit(nets), A.fit(nets)
    assert a["effect"] == b["effect"] and a["se"] == b["se"] and a["se"] > 0  # seed 2982 samples the alternatives
    assert a["coefficients"]["log_k"]["se_model"] > 0 and a["quarters_with_new_edges"] == 13


def test_too_little_growth_is_not_evaluable():
    r = A.fit(grow(alpha=1.0, quarters=4))
    assert not r["evaluable"] and "quarters" in r["why"]


def test_a_quarter_with_no_commit_adds_no_choices():
    nets = grow(alpha=1.0, quarters=10)
    same = N.Net(nets[4].sha, nets[4].date)
    same.nodes, same.edges = nets[4].nodes, nets[4].edges
    x, cl, _ = A.choices([*nets[:5], same, *nets[5:]])
    x0, cl0, _ = A.choices(nets)
    assert len(x) == len(x0)


def grow_fitness(spread: float = 1.0, quarters: int = 14, n0: int = 400, new_nodes: int = 15,
                 new_edges: int = 260, seed: int = 11) -> list:
    """Networks where a target's chance of being called depends ONLY on a fixed intrinsic fitness, never on its
    degree. Degree still correlates with being chosen, because a fit function accumulates callers -- which is
    exactly the confound the fixed-effects sensitivity exists to remove."""
    rng = np.random.default_rng(seed)
    name = lambda i: (f"d{i % 40 % 7}/f{i % 40}.c", "", f"fn{i}")  # noqa: E731
    nodes = [name(i) for i in range(n0)]
    fitness = {n: float(np.exp(spread * rng.normal())) for n in nodes}
    edges: set = set()
    nets = []
    for q in range(quarters):
        net = N.Net(f"sha{q}", f"2020-{q:02d}")
        net.nodes = {n: {"loc": 10 + (hash(n) % 50), "n": 1, "file": n[0], "test": False} for n in nodes}
        net.edges = set(edges)
        nets.append(net)
        w0 = np.array([fitness[n] for n in nodes])
        for _ in range(new_edges):
            u = nodes[rng.integers(len(nodes))]
            w = w0.copy()
            w[nodes.index(u)] = 0
            edges.add((u, nodes[rng.choice(len(nodes), p=w / w.sum())]))
        for i in range(len(nodes), len(nodes) + new_nodes):
            n = name(i)
            fitness[n] = float(np.exp(spread * rng.normal()))
            nodes = nodes + [n]
    return nets


def test_the_plain_estimator_is_unbiased_but_fitness_alone_can_fake_an_exponent():
    """alpha_plain recovers a known exponent well -- and pure fitness, with no attachment at all, produces an
    alpha as large as a true exponent of 1.0. That is why a null model is needed and a test against zero is
    not enough."""
    for true, tol in ((0.0, 0.12), (1.0, 0.15)):
        r = A.fit(grow(alpha=true, local=0.0, seed=4))
        assert r["effect"] == pytest.approx(true, abs=tol), true
    fake = A.fit(grow_fitness(spread=1.2))
    assert fake["evaluable"] and fake["effect"] > 0.9 and fake["effect"] > 4 * fake["se"]


def test_the_fixed_effect_estimator_is_biased_and_cannot_discriminate_at_this_size():
    """The registered "beyond fitness" sensitivity, implemented and shown not to work here. With roughly seven
    choices per fixed effect the conditional-logit FE estimator carries a large negative bias (the incidental-
    parameters problem), and -- decisively -- pure fitness and a true exponent of 1.0 give the SAME alpha_fe.
    It is kept because the registration asks for it, and it must not be read as an exponent.

    Calibration measured on this generator (alpha_plain -> alpha_fe):
        true 0.0  -0.03 -> -0.84      true 1.0  +0.93 -> +0.25
        true 0.5  +0.44 -> -0.21      true 1.5  +1.46 -> +0.86
        pure fitness (true 0.0)  +1.09 -> +0.23
    """
    real = A.fit_fixed_effects(grow(alpha=1.0, local=0.0, seed=4), boot=0)
    fake = A.fit_fixed_effects(grow_fitness(spread=1.2), boot=0)
    assert real["evaluable"] and fake["evaluable"]
    assert real["alpha_fe"] < real["alpha_plain"] - 0.5          # a bias far larger than the effect tested
    assert abs(real["alpha_fe"] - fake["alpha_fe"]) < 0.15       # true attachment and pure fitness: the same
    null_true = A.fit_fixed_effects(grow(alpha=0.0, local=0.0, seed=4), boot=0)
    assert null_true["alpha_fe"] < -0.4                          # and no attachment reads well below zero
    assert real["targets_with_own_effect"] > 50 and real["min_appear"] == A.MIN_FE_APPEAR
    for lam, rec in real["by_ridge"].items():                    # the penalty is not what drives it
        assert rec["alpha"] < real["alpha_plain"], lam


def test_the_fixed_effect_slots_pool_the_rarely_chosen():
    _, _, _, ids = A.choices(grow(alpha=1.0, quarters=10), with_ids=True)
    fe_of, n_fe, n_own = A._fe_slots(ids, min_appear=2)
    assert n_fe == n_own + 1 and fe_of[fe_of > 0].min() == 1  # slot 0 is the pooled baseline
    chosen = np.bincount(ids[:, 0], minlength=len(fe_of))
    assert all(fe_of[t] > 0 for t in np.flatnonzero(chosen >= 2))
    assert all(fe_of[t] == 0 for t in np.flatnonzero(chosen < 2))
    strict = A._fe_slots(ids, min_appear=100)[2]
    assert strict < n_own                                     # a higher cut keeps fewer own effects


def test_the_nonparametric_kernel_recovers_the_exponent_and_reads_a_flat_one_as_zero():
    pa = A.kernel(grow(alpha=1.0, local=0.0, seed=4))
    assert pa["evaluable"] and pa["degrees"] >= 4
    assert pa["slope"] == pytest.approx(1.0, abs=0.45)        # uncontrolled, so only roughly
    assert pa["r2_loglinear"] > 0.5
    flat = A.kernel(grow(alpha=0.0, local=0.0, seed=5))
    assert flat["evaluable"] and abs(flat["slope"]) < 0.5     # a flat kernel reads near zero
    assert pa["slope"] > flat["slope"]


def test_the_kernel_reports_curvature_so_a_misspecified_form_shows():
    r = A.kernel(grow(alpha=1.0, local=0.0, seed=4))
    assert "curvature" in r and math.isfinite(r["curvature"])
    assert abs(r["curvature"]) < 1.0                          # a power-law kernel is near straight in log-log
    assert r["note"].startswith("confounded")                 # never read as a rival alpha


def test_the_fitness_null_separates_real_attachment_from_fitness():
    """The sensitivity that works. Under a fitness-only null each target keeps its observed total intake but
    loses the timing, so an alpha that only reflects "popular functions are popular" is reproduced by the null,
    while one that reflects attachment is not."""
    real = A.fitness_null(grow(alpha=1.0, local=0.0, seed=4), reps=25)
    assert real["evaluable"] and real["reps"] >= 13
    assert real["alpha_observed"] > real["alpha_null_mean"]      # the timing carries signal the null cannot
    assert real["excess"] > 0 and real["p"] < 0.05 and real["beyond_fitness"] is True

    fake = A.fitness_null(grow_fitness(spread=1.2), reps=25)
    assert fake["evaluable"]
    assert fake["alpha_observed"] > 0.5                          # a confidently positive alpha ...
    assert fake["p"] > 0.05 and fake["beyond_fitness"] is False   # ... that pure fitness fully explains
    assert abs(fake["excess"]) < abs(real["excess"])


def test_the_fitness_null_needs_enough_events():
    r = A.fitness_null(grow(alpha=1.0, quarters=3), reps=5)
    assert not r["evaluable"] and ("new edges" in r["why"] or "not evaluable" in r["why"])
