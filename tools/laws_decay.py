#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAW-5, decay (docs/laws_hypotheses.md; methods review should-fix 3). Descriptive in LAWS (Amendment 0 item 2).

Per yearly snapshot:
  Q excess    directed modularity of the function network over the DIRECTORY partition at a fixed depth (the first
              two directory levels below the source root), minus its mean over REWIRES degree-preserving rewirings.
              Also Q / Q_max, and the excess with same-file edges removed (sensitivity).
  PC excess   propagation cost (MacCormack: the share of ordered function pairs joined by a directed path),
              estimated from PC_SOURCES sampled sources, minus its mean over the same rewirings.
Per repo: Sen's slope per year of each excess over the yearly points, with a block bootstrap (blocks of 2 yearly
points, BOOT resamples, seed 2982) for its SE. The law predicts slope(Q excess) < 0 AND slope(PC excess) > 0.
"""
from __future__ import annotations

import os
from pathlib import PurePosixPath

import numpy as np
from scipy import sparse
from scipy.sparse import csgraph

SEED = 2982
BOOT = 1000
REWIRES = 20
PC_SOURCES = 200
DEPTH = 2
MIN_YEARS = 8
MIN_EDGES = 50


def partition(paths: list[str], depth: int = DEPTH) -> list[str]:
    """The directory group of each path: its first `depth` directory levels below the common source root."""
    dirs = [PurePosixPath(p).parent.parts for p in paths]
    root = os.path.commonprefix(dirs) if dirs else ()
    return ["/".join(d[len(root):len(root) + depth]) or "." for d in dirs]


def modularity(src: np.ndarray, dst: np.ndarray, group: np.ndarray, n_groups: int) -> tuple[float, float]:
    """(Q, Q_max) of a directed graph for a node partition: Q = sum_c [e_cc / m - out_c * in_c / m^2]."""
    m = len(src)
    if m == 0:
        return 0.0, 0.0
    out_c = np.bincount(group[src], minlength=n_groups).astype(float)
    in_c = np.bincount(group[dst], minlength=n_groups).astype(float)
    e_cc = np.bincount(group[src][group[src] == group[dst]], minlength=n_groups).astype(float)
    expected = float((out_c * in_c).sum()) / m ** 2
    return float(e_cc.sum()) / m - expected, 1.0 - expected


def rewire(src: np.ndarray, dst: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """New targets for the edges with every in- and out-degree kept: the targets are permuted, and a permutation that
    makes a self-loop or repeats an edge is repaired by swapping targets with other edges (a few passes)."""
    d = rng.permutation(dst)
    for _ in range(20):
        key = src.astype(np.int64) * (int(d.max()) + 1) + d
        _, first = np.unique(key, return_index=True)
        bad = np.ones(len(d), dtype=bool)
        bad[first] = False
        bad |= src == d
        idx = np.flatnonzero(bad)
        if not len(idx):
            break
        other = rng.integers(0, len(d), len(idx))
        d[idx], d[other] = d[other].copy(), d[idx].copy()
    return d


def propagation_cost(src: np.ndarray, dst: np.ndarray, n: int, sources: np.ndarray) -> float:
    """The mean share of the other functions reachable from each sampled source."""
    if n < 2:
        return 0.0
    g = sparse.csr_matrix((np.ones(len(src), dtype=np.int8), (src, dst)), shape=(n, n))
    reach = [len(csgraph.breadth_first_order(g, int(s), directed=True, return_predecessors=False)) - 1 for s in sources]
    return float(np.mean(reach)) / (n - 1)


def snapshot(net, rng: np.random.Generator) -> dict | None:
    """The Q and PC excesses of one tools/laws_net.Net; None with fewer than MIN_EDGES edges."""
    nodes = sorted(net.nodes)
    idx = {x: i for i, x in enumerate(nodes)}
    if len(net.edges) < MIN_EDGES:
        return None
    e = np.array(sorted((idx[u], idx[v]) for u, v in net.edges), dtype=np.int64)
    src, dst = e[:, 0], e[:, 1]
    names = partition([x[0] for x in nodes])
    groups = {g: i for i, g in enumerate(sorted(set(names)))}
    group = np.array([groups[g] for g in names])
    n = len(nodes)
    q, qmax = modularity(src, dst, group, len(groups))
    files = {f: i for i, f in enumerate(sorted({x[0] for x in nodes}))}
    file_of = np.array([files[x[0]] for x in nodes])
    cross = file_of[src] != file_of[dst]
    q_x, _ = modularity(src[cross], dst[cross], group, len(groups))
    sources = rng.choice(n, min(PC_SOURCES, n), replace=False)
    pc = propagation_cost(src, dst, n, sources)
    q0, qx0, pc0 = [], [], []
    for _ in range(REWIRES):
        d = rewire(src, dst, rng)
        q0.append(modularity(src, d, group, len(groups))[0])
        c = file_of[src] != file_of[d]
        qx0.append(modularity(src[c], d[c], group, len(groups))[0])
        pc0.append(propagation_cost(src, d, n, sources))
    return {"date": net.date[:10], "nodes": n, "edges": len(src), "groups": len(groups), "Q": q, "Q_over_Qmax": q / qmax if qmax else None,
            "Q_null": float(np.mean(q0)), "Q_excess": q - float(np.mean(q0)),
            "Q_excess_cross_file": q_x - float(np.mean(qx0)), "PC": pc, "PC_null": float(np.mean(pc0)),
            "PC_excess": pc - float(np.mean(pc0))}


def sen_slope(t: np.ndarray, y: np.ndarray) -> float:
    """The median of the pairwise slopes."""
    i, j = np.triu_indices(len(t), 1)
    ok = t[j] != t[i]
    return float(np.median((y[j][ok] - y[i][ok]) / (t[j][ok] - t[i][ok])))


def trend(t: np.ndarray, y: np.ndarray, rng: np.random.Generator, boot: int = BOOT) -> dict:
    """Sen's slope and its block-bootstrap SE (blocks of 2 consecutive points, resampled with replacement)."""
    slope = sen_slope(t, y)
    blocks = [np.arange(i, min(i + 2, len(t))) for i in range(0, len(t), 2)]
    reps = []
    for _ in range(boot):
        pick = np.concatenate([blocks[b] for b in rng.integers(0, len(blocks), len(blocks))])
        if len(np.unique(t[pick])) > 2:
            reps.append(sen_slope(t[pick], y[pick]))
    return {"slope": slope, "se": float(np.std(reps, ddof=1)) if len(reps) > 1 else float("nan")}


def fit(yearly_nets: list, seed: int = SEED, boot: int = BOOT) -> dict:
    """The LAW-5 record of one repo, from its yearly networks, oldest first."""
    rng = np.random.default_rng(seed)
    rows = [r for net in yearly_nets if (r := snapshot(net, rng)) is not None]
    out = {"years": len(rows), "evaluable": False, "by_year": rows}
    if len(rows) < MIN_YEARS:
        return {**out, "why": f"fewer than {MIN_YEARS} yearly snapshots with {MIN_EDGES} edges"}
    t = np.array([float(r["date"][:4]) for r in rows])
    q = trend(t, np.array([r["Q_excess"] for r in rows]), rng, boot)
    pc = trend(t, np.array([r["PC_excess"] for r in rows]), rng, boot)
    qx = trend(t, np.array([r["Q_excess_cross_file"] for r in rows]), rng, boot)
    return {**out, "evaluable": True, "q_slope": q["slope"], "q_se": q["se"], "pc_slope": pc["slope"], "pc_se": pc["se"],
            "q_cross_file_slope": qx["slope"], "q_cross_file_se": qx["se"],
            "predicted_direction": bool(q["slope"] < 0 and pc["slope"] > 0)}
