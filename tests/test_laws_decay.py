"""LAW-5: modularity and propagation cost against a rewired null, and the trend, on simulated networks."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import laws_decay as D  # noqa: E402
import laws_net as N  # noqa: E402


def planted(inside: float, n_dirs: int = 8, per_dir: int = 120, edges: int = 4000, seed: int = 1, year: int = 2015):
    """A network whose edges stay inside the source's directory with probability `inside`."""
    rng = np.random.default_rng(seed)
    nodes = [(f"src/pkg{d}/sub/f{i % 6}.c", "", f"fn{d}_{i}") for d in range(n_dirs) for i in range(per_dir)]
    net = N.Net(f"s{year}", f"{year}-09-30")
    net.nodes = {x: {"loc": 9, "n": 1, "file": x[0], "test": False} for x in nodes}
    es = set()
    while len(es) < edges:
        a = int(rng.integers(0, len(nodes)))
        d = a // per_dir if rng.random() < inside else int(rng.integers(0, n_dirs))
        b = d * per_dir + int(rng.integers(0, per_dir))
        if a != b:
            es.add((nodes[a], nodes[b]))
    net.edges = es
    return net


def test_the_partition_is_two_levels_below_the_common_root():
    assert D.partition(["a/b/src/x/y/z/f.c", "a/b/src/x/w/g.c", "a/b/src/h.c", "a/b/src/q/i.c"]) == ["x/y", "x/w", ".", "q"]


def test_modularity_matches_a_hand_count():
    # two groups of two nodes; 3 edges inside group 0, 1 edge from group 0 to group 1
    src, dst, group = np.array([0, 1, 0, 1]), np.array([1, 0, 1, 2]), np.array([0, 0, 1, 1])
    q, qmax = D.modularity(src[[0, 1, 3]], dst[[0, 1, 3]], group, 2)  # edges 0->1, 1->0 (inside), 1->2 (across)
    assert q == pytest.approx(2 / 3 - (3 * 2 + 0 * 1) / 9) and qmax == pytest.approx(1 - 6 / 9)


def test_rewiring_keeps_every_degree_and_makes_no_self_loop():
    net = planted(0.9)
    idx = {x: i for i, x in enumerate(sorted(net.nodes))}
    e = np.array(sorted((idx[u], idx[v]) for u, v in net.edges))
    d = D.rewire(e[:, 0], e[:, 1], np.random.default_rng(0))
    assert sorted(d) == sorted(e[:, 1]) and not (d == e[:, 0]).any()
    assert len(set(zip(e[:, 0].tolist(), d.tolist()))) == len(e)  # no repeated edge


def test_a_modular_network_has_excess_modularity_and_a_random_one_has_none():
    rng = np.random.default_rng(0)
    mod, flat = D.snapshot(planted(0.9), rng), D.snapshot(planted(0.0), rng)
    assert mod["Q_excess"] > 0.6 and abs(mod["Q_null"]) < 0.02 and mod["groups"] == 8
    assert abs(flat["Q_excess"]) < 0.03
    assert mod["PC_excess"] < 0.02  # edges kept inside directories never reach further than the rewired ones


def test_falling_modularity_is_read_as_a_negative_slope():
    nets = [planted(0.95 - 0.07 * y, seed=y, year=2010 + y) for y in range(10)]
    r = D.fit(nets, boot=200)
    assert r["evaluable"] and r["years"] == 10 and r["q_slope"] < -0.03 and r["q_slope"] < -5 * r["q_se"]


def test_constant_structure_has_no_trend_and_short_histories_are_not_evaluable():
    flat = D.fit([planted(0.7, seed=y, year=2010 + y) for y in range(10)], boot=200)
    assert abs(flat["q_slope"]) < 3 * flat["q_se"] + 0.005
    assert not D.fit([planted(0.7, seed=y, year=2010 + y) for y in range(5)], boot=50)["evaluable"]


def test_sens_slope_is_the_median_pairwise_slope():
    t = np.array([0.0, 1, 2, 3, 4])
    assert D.sen_slope(t, 2 * t + 1) == pytest.approx(2.0)
    assert D.sen_slope(t, np.array([0.0, 1, 2, 3, 100])) == pytest.approx(1.0)  # one outlier does not move it
