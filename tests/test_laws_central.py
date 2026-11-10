"""LAW-4: a network grown by a known kernel shows no centralisation beyond that kernel, and clear centralisation
beyond uniform attachment."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import laws_attach as A  # noqa: E402
import laws_central as C  # noqa: E402
from test_laws_attach import grow  # noqa: E402


def test_gini_of_known_sequences():
    assert C.gini([1, 1, 1, 1]) == pytest.approx(0) and C.gini([0, 0, 0, 10]) == pytest.approx(0.75)
    assert C.gini([1, 2, 3, 4]) == pytest.approx(0.25) and C.gini([]) == 0 and C.gini([0, 0]) == 0


def test_the_history_replays_itself_when_nothing_is_redrawn():
    nets = grow(alpha=1.0, local=1.0, quarters=10)
    h = C.History(nets)
    last = nets[-1]
    assert h.q == 10 and int(h.present[-1].sum()) == len(last.nodes) and len(h.alive[-1]) == len(last.edges)
    assert sorted(h.observed()[h.present[-1]]) == sorted(float(last.in_degree().get(x, 0)) for x in last.nodes)
    assert sum(len(a) for a in h.added) == len({e for net in nets[1:] for e in net.edges} - nets[0].edges)


def test_growth_by_its_own_kernel_shows_no_extra_centralisation_but_beats_uniform():
    nets = grow(alpha=1.0, local=1.0)
    law2 = A.fit(nets)
    r = C.fit(nets, law2, sims=60)
    assert r["evaluable"] and r["gini_observed"] > 0.3
    assert abs(r["effect"]) < 4 * r["se"] + 0.02  # explained by the repo's own attachment process
    assert r["uniform"]["effect"] > 0.05 and r["uniform"]["effect"] > 5 * r["uniform"]["se"]  # not by uniform attachment
    assert r["negative_locality_replayed_as_zero"] == [] or set(r["negative_locality_replayed_as_zero"]) <= {"same_file", "same_dir"}


def test_uniform_growth_shows_no_centralisation_either_way():
    nets = grow(alpha=0.0, local=0.0, seed=8)
    r = C.fit(nets, A.fit(nets), sims=60)
    assert r["evaluable"] and abs(r["effect"]) < 4 * r["se"] + 0.02 and abs(r["uniform"]["effect"]) < 4 * r["uniform"]["se"] + 0.02


def test_a_replay_keeps_sources_edge_counts_and_presence():
    nets = grow(alpha=1.0, local=1.0, quarters=10)
    h = C.History(nets)
    k = h.replay({"log_k": 1.0, "same_file": 1.0}, np.random.default_rng(0))
    assert k[~h.present[-1]].sum() == 0  # no edge lands on a function that is gone
    assert k.sum() <= len(h.alive[-1]) and k.sum() > 0.9 * len(h.alive[-1])  # a few replayed pairs coincide


def test_no_kernel_no_law_4():
    assert not C.fit(grow(alpha=1.0, quarters=4), {"evaluable": False})["evaluable"]
