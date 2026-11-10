"""LAW-2: the conditional logit recovers a known attachment exponent, and reads uniform attachment as zero."""
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
