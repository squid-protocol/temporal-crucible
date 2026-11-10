#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAW-3, hubs persist (docs/laws_hypotheses.md; methods review M5).

For each pair of yearly snapshots 5 years apart, on the functions present in both and the edges between them:

  hubs       the top 1% by in-degree at t (at least MIN_HUBS of them, else the pair is not evaluable). A tie at the
             cut is included whole, each tied function weighted (slots left) / (tie size), so the weights sum to
             the top-1% count.
  observed   the weighted share of hubs whose in-degree at t + 5 is in the top 5% (ties at that cut count as in).
  null       the same share when every edge ADDED between t and t + 5 keeps its source and takes a target drawn
             uniformly among the persisting functions (the source excluded); removed edges stay removed.
             NULL_REPS replicates.
  pair effect   observed - mean null.

The per-repo effect is the mean over pairs; its SE is a bootstrap over pairs (BOOT resamples, seed 2982). Margin 0.
Descriptive, reported beside it: the same persistence for the top 1% by LOC, and hub survival (still present).

Two things the pilot (the CGR development repos) settled, to be listed at the scorer freeze:
  - Callers. The followed functions are those present at both snapshots, but their in-degree counts every caller,
    also functions born or gone in between (callers="all"). Counting only edges between two persisting functions
    left 53 to 589 added edges per pair, and observed = null to three decimals in every pilot repo.
  - Ceiling. Where the null does not move (the mean over pairs of the null's SD across replicates is below
    CEILING_SD), who is in the top 5% is fixed by the edges that are kept and removed, whatever the added edges
    do: redis, even with 3,779 added edges per pair, has observed = null to six decimals in every pair. Such a repo
    carries no information on the law; it is "not evaluable (ceiling)" and counted, never pooled as a 0 (its
    near-zero variance would outweigh every other repo).
"""
from __future__ import annotations

import math

import numpy as np

SEED = 2982
BOOT = 1000
NULL_REPS = 200
YEARS_APART = 5
TOP_HUB, TOP_LATER = 0.01, 0.05
MIN_HUBS = 10
MIN_PAIRS = 3
CEILING_SD = 0.005


def top_weights(values: np.ndarray, share: float) -> np.ndarray:
    """Weights of the top `share` by value: 1 above the cut, (slots left) / (tie size) on the cut, 0 below. Functions
    with value 0 are never in the top."""
    n = len(values)
    h = max(1, math.ceil(share * n))
    cut = np.sort(values)[::-1][h - 1]
    w = np.zeros(n)
    if cut <= 0:
        pos = values > 0
        w[pos] = 1.0
        return w
    above = values > cut
    tied = values == cut
    w[above] = 1.0
    w[tied] = (h - above.sum()) / tied.sum()
    return w


def in_top(values: np.ndarray, share: float) -> np.ndarray:
    """Membership of the top `share`: value at or above the cut value (ties count as in), and above 0."""
    h = max(1, math.ceil(share * len(values)))
    cut = np.sort(values)[::-1][h - 1]
    return (values >= cut) & (values > 0)


def pair(a, b, rng: np.random.Generator, reps: int = NULL_REPS, callers: str = "all") -> dict | None:
    """One (t, t + 5) pair of tools/laws_net.Net; None when it has fewer than MIN_HUBS hubs. The functions whose hub
    status is followed are those present at both. callers="all": their in-degree counts every caller of the
    snapshot, also functions that exist at only one of the two; callers="persisting": only edges between two
    persisting functions (the literal reading of M5, which the pilot showed leaves the null almost nothing to move)."""
    persist = [n for n in a.nodes if n in b.nodes]
    n = len(persist)
    if math.ceil(TOP_HUB * n) < MIN_HUBS:
        return None
    idx = {x: i for i, x in enumerate(persist)}
    if callers == "persisting":
        ea = {(idx[u], idx[v]) for u, v in a.edges if u in idx and v in idx}
        eb = {(idx[u], idx[v]) for u, v in b.edges if u in idx and v in idx}
    else:  # sources keep their identity (an index for a persisting one, the node itself otherwise)
        ea = {(idx.get(u, u), idx[v]) for u, v in a.edges if v in idx}
        eb = {(idx.get(u, u), idx[v]) for u, v in b.edges if v in idx}
    k_a = np.bincount([v for _, v in ea], minlength=n).astype(float)
    k_b = np.bincount([v for _, v in eb], minlength=n).astype(float)
    w = top_weights(k_a, TOP_HUB)
    if w.sum() <= 0:
        return None
    obs = float((w * in_top(k_b, TOP_LATER)).sum() / w.sum())
    kept = ea & eb
    added = sorted(eb - ea, key=str)
    src = np.array([u if isinstance(u, int) else -1 for u, _ in added], dtype=int)  # -1: a caller that is not a candidate
    base = np.bincount([v for _, v in kept], minlength=n).astype(float)
    null = np.empty(reps)
    for r in range(reps):
        if len(added):
            t = rng.integers(0, n - 1, len(added))
            t = np.where(src >= 0, t + (t >= src), rng.integers(0, n, len(added)))  # uniform; a persisting source excluded
            k = base + np.bincount(t, minlength=n)
        else:
            k = base
        null[r] = (w * in_top(k, TOP_LATER)).sum() / w.sum()
    loc_a = np.array([a.nodes[x]["loc"] for x in persist], dtype=float)
    loc_b = np.array([b.nodes[x]["loc"] for x in persist], dtype=float)
    wl = top_weights(loc_a, TOP_HUB)
    hubs_all = top_weights(np.array([a.in_degree().get(x, 0) for x in a.nodes], dtype=float), TOP_HUB)
    alive = np.array([x in b.nodes for x in a.nodes], dtype=float)
    return {"t": a.date[:10], "t5": b.date[:10], "persisting": n, "hubs": float(w.sum()), "observed": obs,
            "null_mean": float(null.mean()), "null_sd": float(null.std(ddof=1)), "effect": obs - float(null.mean()),
            "edges_added": int(len(added)), "edges_removed": int(len(ea - eb)),
            "loc_persistence": float((wl * in_top(loc_b, TOP_LATER)).sum() / wl.sum()) if wl.sum() else None,
            "hub_survival": float((hubs_all * alive).sum() / hubs_all.sum()) if hubs_all.sum() else None,
            "all_survival": float(alive.mean())}


def fit(yearly_nets: list, seed: int = SEED, boot: int = BOOT, callers: str = "all") -> dict:
    """The LAW-3 record of one repo, from its yearly networks, oldest first (one per year, tools/laws_net.yearly)."""
    rng = np.random.default_rng(seed)
    year = lambda net: int(str(net.date)[:4])  # noqa: E731
    by_year = {year(net): net for net in yearly_nets}
    pairs = [p for y in sorted(by_year) if y + YEARS_APART in by_year
             and (p := pair(by_year[y], by_year[y + YEARS_APART], rng, callers=callers)) is not None]
    out = {"pairs": len(pairs), "evaluable": False, "callers": callers, "by_pair": pairs}
    if len(pairs) < MIN_PAIRS:
        return {**out, "why": f"fewer than {MIN_PAIRS} five-year pairs with {MIN_HUBS} hubs"}
    eff = np.array([p["effect"] for p in pairs])
    reps = rng.choice(eff, (boot, len(eff))).mean(axis=1)
    null_sd = float(np.mean([p["null_sd"] for p in pairs]))
    if null_sd < CEILING_SD or float(reps.std(ddof=1)) == 0.0:
        return {**out, "why": f"ceiling: the null does not move (mean SD {null_sd:.4f} < {CEILING_SD})", "ceiling": True,
                "null_sd_mean": null_sd,
                "observed_mean": float(np.mean([p["observed"] for p in pairs])),
                "null_mean": float(np.mean([p["null_mean"] for p in pairs]))}
    return {**out, "evaluable": True, "effect": float(eff.mean()), "se": float(reps.std(ddof=1)),
            "observed_mean": float(np.mean([p["observed"] for p in pairs])),
            "null_mean": float(np.mean([p["null_mean"] for p in pairs])),
            "loc_persistence_mean": float(np.mean([p["loc_persistence"] for p in pairs if p["loc_persistence"] is not None]))}
