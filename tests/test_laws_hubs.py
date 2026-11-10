"""LAW-3: persistence of hubs against the target-randomised null, on simulated networks."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import laws_hubs as H  # noqa: E402
import laws_net as N  # noqa: E402


def yearly(mode: str, years: int = 9, n: int = 1500, seed: int = 4) -> list:
    """`n` functions; every year four fifths of the edges fall away and 3,000 are added: mode "sticky" sends the new ones to
    the same few favoured targets every year (hubs stay hubs), "random" to uniform targets, "churn" to a fresh set of
    favourites each year (hubs are replaced). Without the turnover an old hub keeps its old edges, stays a hub under
    the null too, and the effect is 0 whatever the attachment (the null only moves ADDED edges)."""
    rng = np.random.default_rng(seed)
    nodes = [(f"d/f{i % 60}.c", "", f"fn{i}") for i in range(n)]
    weight = np.ones(n)
    fav = rng.choice(n, 30, replace=False)
    weight[fav] = 60
    edges: set = set()
    nets = []
    for y in range(years):
        if mode == "churn":
            weight = np.ones(n)
            weight[rng.choice(n, 30, replace=False)] = 60
        p = weight / weight.sum() if mode != "random" else np.ones(n) / n
        src, dst = rng.integers(0, n, 3000), rng.choice(n, 3000, p=p)
        old = sorted(edges)
        edges = {old[i] for i in rng.choice(len(old), len(old) // 5, replace=False)} if old else set()
        edges |= {(nodes[a], nodes[b]) for a, b in zip(src, dst) if a != b}
        net = N.Net(f"s{y}", f"{2010 + y}-09-30")
        net.nodes = {x: {"loc": 5 + (i % 90), "n": 1, "file": x[0], "test": False} for i, x in enumerate(nodes)}
        net.edges = set(edges)
        nets.append(net)
    return nets


def test_top_weights_share_a_tie_at_the_cut():
    v = np.array([9, 7, 7, 7, 3, 1, 0, 0, 0, 0] * 30, dtype=float)  # n = 300: top 1% = 3 slots, all on the 30 nines
    w = H.top_weights(v, 0.01)
    assert w.sum() == pytest.approx(3) and set(np.round(w[v == 9], 6)) == {0.1} and w[v < 9].sum() == 0
    w = H.top_weights(np.array([5, 4, 4, 0] * 50, dtype=float), 0.3)  # 60 slots: 50 fives whole, 10 slots over 100 fours
    assert w[::4].tolist() == [1.0] * 50 and w[1] == pytest.approx(0.1) and w.sum() == pytest.approx(60)
    assert H.top_weights(np.zeros(200), 0.01).sum() == 0  # a function nobody calls is never a hub
    assert H.in_top(np.array([3, 2, 2, 1, 0, 0, 0, 0, 0, 0], dtype=float), 0.2).tolist() == [True, True, True] + [False] * 7


def test_hubs_that_keep_attracting_calls_persist_beyond_the_null():
    r = H.fit(yearly("sticky"), boot=200)
    assert r["evaluable"] and r["pairs"] == 4
    assert r["observed_mean"] > 0.9 and r["effect"] > 0.2 and r["effect"] > 5 * r["se"]


def test_uniform_attachment_shows_no_persistence_beyond_the_null():
    r = H.fit(yearly("random"), boot=200)
    assert r["evaluable"] and abs(r["effect"]) < 0.15


def test_hubs_that_are_replaced_do_not_persist():
    r = H.fit(yearly("churn"), boot=200)
    assert r["evaluable"] and r["observed_mean"] < 0.3 and r["effect"] < 0.1  # few old hubs are still on top, as the null expects


def test_small_or_short_histories_are_not_evaluable():
    assert not H.fit(yearly("sticky", n=600), boot=50)["evaluable"]  # 6 hubs
    r = H.fit(yearly("sticky", years=7), boot=50)  # two five-year pairs
    assert not r["evaluable"] and r["pairs"] == 2 and "pairs" in r["why"]


def test_the_record_is_reproducible():
    nets = yearly("sticky")
    assert H.fit(nets, boot=100) == H.fit(nets, boot=100)


def test_without_turnover_an_old_hub_persists_under_the_null_too():
    """A property of the registered null, kept as a test so it is not forgotten when reading LAW-3: where edges only
    accumulate, observed and null persistence are both high and the effect is near 0."""
    rng = np.random.default_rng(1)
    n = 1500
    nodes = [(f"d/f{i % 60}.c", "", f"fn{i}") for i in range(n)]
    w = np.ones(n)
    w[:30] = 60
    edges: set = set()
    nets = []
    for y in range(8):
        edges |= {(nodes[a], nodes[b]) for a, b in zip(rng.integers(0, n, 3000), rng.choice(n, 3000, p=w / w.sum())) if a != b}
        net = N.Net(f"s{y}", f"{2010 + y}-09-30")
        net.nodes = {x: {"loc": 9, "n": 1, "file": x[0], "test": False} for x in nodes}
        net.edges = set(edges)
        nets.append(net)
    r = H.fit(nets, boot=100)
    assert r["observed_mean"] > 0.95 and r["null_mean"] > 0.9
    assert not r["evaluable"] and r["ceiling"] if "effect" not in r else abs(r["effect"]) < 0.1


def test_callers_born_later_count_toward_a_persisting_hub():
    """The pilot's finding: most new calls come from functions born after t. They count (callers="all")."""
    old = [(f"d/f{i % 30}.c", "", f"fn{i}") for i in range(1200)]
    nets = []
    rng = np.random.default_rng(2)
    edges = {(old[a], old[b]) for a, b in zip(rng.integers(0, 1200, 4000), rng.integers(0, 40, 4000)) if a != b}
    for y in range(8):
        born = [(f"new/y{y}.c", "", f"n{y}_{i}") for i in range(300)] if y else []
        new_edges = {(u, old[int(rng.integers(0, 12))]) for u in born}  # newcomers call the first twelve hubs
        net = N.Net(f"s{y}", f"{2010 + y}-09-30")
        net.nodes = {x: {"loc": 9, "n": 1, "file": x[0], "test": False} for x in [*old, *born]}
        net.edges = edges | new_edges
        nets.append(net)
    only_persisting = H.pair(nets[0], nets[5], np.random.default_rng(0), callers="persisting")
    everyone = H.pair(nets[0], nets[5], np.random.default_rng(0), callers="all")
    assert only_persisting["edges_added"] == 0 and everyone["edges_added"] == 300
