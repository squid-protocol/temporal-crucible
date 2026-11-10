#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAW-4, centralisation beyond the repo's own attachment process (docs/laws_hypotheses.md; methods review M5).

    effect = Gini of in-degree (k >= 1) at the last snapshot  -  mean of the same Gini over SIMS replays

A replay starts from the first snapshot and follows the repo's quarters. It keeps what was observed: which
functions exist at each quarter, which edges are removed and when, and the source and the quarter of every added
edge. Only the TARGET of an added edge is drawn again, and only where LAW-2 models it: an edge whose observed
target already existed the quarter before is redrawn among the functions present at both quarters; an edge to a
function born that quarter keeps its observed target (the kernel says nothing about newborn functions, and the
pilot showed that sending those edges to old functions overstates the replay's inequality). The weights are those
of the repo's fitted LAW-2 kernel (tools/laws_attach.py):

    exp(alpha * log(k + 1) + b1 * same_file + b2 * same_directory + b3 * log(LOC) + b4 * log(1 + age))

with k the replay's own in-degree at the start of the quarter. An edge whose replayed target has left the code is
not counted. SE = the SD of the replayed Gini. Margin 0. Reported beside it: the Gini over k >= 0, and the same
effect under uniform attachment (every coefficient 0), which LAW-2 already implies and is descriptive.

A negative same-file or same-directory coefficient cannot be drawn by the additive mixture used here and is
replayed as 0; the record says when that happened.
"""
from __future__ import annotations

import math
from pathlib import PurePosixPath

import numpy as np

SEED = 2982
SIMS = 200
MIN_QUARTERS = 8


def gini(k: np.ndarray) -> float:
    """The Gini coefficient of a non-negative sequence (0 for an empty or all-zero one)."""
    k = np.sort(np.asarray(k, dtype=float))
    n, tot = len(k), k.sum()
    if n == 0 or tot == 0:
        return 0.0
    return float((2 * np.arange(1, n + 1) - n - 1) @ k / (n * tot))


class History:
    """A repo's quarterly networks as arrays, built once and shared by every replay."""

    def __init__(self, nets: list):
        nets = [net for i, net in enumerate(nets) if i == 0 or net.sha != nets[i - 1].sha]  # a quiet quarter adds nothing
        self.q = len(nets)
        ids: dict = {}
        for net in nets:
            for node in net.nodes:
                ids.setdefault(node, len(ids))
        self.n = len(ids)
        self.present = np.zeros((self.q, self.n), dtype=bool)
        self.loc = np.ones((self.q, self.n))
        born = np.full(self.n, -1)
        for qi, net in enumerate(nets):
            for node, meta in net.nodes.items():
                i = ids[node]
                self.present[qi, i] = True
                self.loc[qi, i] = max(1, meta["loc"])
                if born[i] < 0:
                    born[i] = qi
        self.born = born
        files, dirs = {}, {}
        self.file_of = np.array([files.setdefault(node[0], len(files)) for node in ids])
        self.dir_of = np.array([dirs.setdefault(str(PurePosixPath(node[0]).parent), len(dirs)) for node in ids])
        # candidate order: by (directory, file), so a file and a directory are contiguous ranges of it
        self.order = np.lexsort((self.file_of, self.dir_of))
        eids: dict = {}
        self.alive = []  # per quarter: the edge ids present
        for net in nets:
            self.alive.append(np.array(sorted(eids.setdefault((ids[u], ids[v]), len(eids)) for u, v in net.edges), dtype=np.int64))
        pairs = np.array(list(eids), dtype=np.int64).reshape(-1, 2)
        self.src, self.dst = pairs[:, 0], pairs[:, 1]
        self.added = [np.setdiff1d(self.alive[qi + 1], self.alive[qi], assume_unique=True) for qi in range(self.q - 1)]

    def degree(self, edges: np.ndarray, dst: np.ndarray, qi: int) -> np.ndarray:
        """In-degree at quarter qi of the distinct (source, target) pairs among `edges`, targets present at qi only."""
        d = dst[edges]
        ok = self.present[qi, d]
        key = np.unique(self.src[edges][ok].astype(np.int64) * self.n + d[ok])
        return np.bincount(key % self.n, minlength=self.n).astype(float)

    def replay(self, coef: dict, rng: np.random.Generator) -> np.ndarray:
        """The in-degree at the last quarter of one replay with the kernel `coef` ({feature: coefficient})."""
        a, b3, b4 = coef.get("log_k", 0.0), coef.get("log_loc", 0.0), coef.get("log_age", 0.0)
        b1, b2 = coef.get("same_file", 0.0), coef.get("same_dir", 0.0)
        c_dir = max(0.0, math.exp(b2) - 1.0)
        c_file = max(0.0, math.exp(b1 + b2) - math.exp(b2))
        dst = self.dst.copy()
        for qi in range(self.q - 1):
            add = self.added[qi]
            add = add[self.present[qi, self.dst[add]]]  # only edges whose observed target already existed at qi
            if not len(add):
                continue
            both = self.present[qi] & self.present[qi + 1]
            cand = self.order[both[self.order]]  # the persisting functions, in (dir, file) order
            if not len(cand):
                continue
            k = self.degree(self.alive[qi], dst, qi)[cand]
            base = np.exp(a * np.log(k + 1) + b3 * np.log(self.loc[qi + 1, cand]) + b4 * np.log1p(qi + 1 - self.born[cand]))
            cum = np.concatenate(([0.0], np.cumsum(base)))
            cd, cf = self.dir_of[cand], self.file_of[cand]
            s = self.src[add]
            dlo, dhi = np.searchsorted(cd, self.dir_of[s], "left"), np.searchsorted(cd, self.dir_of[s], "right")
            # within one directory range the files are sorted: locate the file's range by a combined key
            key = cd.astype(np.int64) * (self.file_of.max() + 1) + cf
            skey = self.dir_of[s].astype(np.int64) * (self.file_of.max() + 1) + self.file_of[s]
            flo, fhi = np.searchsorted(key, skey, "left"), np.searchsorted(key, skey, "right")
            m_all = cum[-1]
            m_dir = c_dir * (cum[dhi] - cum[dlo])
            m_file = c_file * (cum[fhi] - cum[flo])
            u = rng.random(len(add)) * (m_all + m_dir + m_file)
            in_all, in_dir = u < m_all, (u >= m_all) & (u < m_all + m_dir)
            lo = np.where(in_all, 0, np.where(in_dir, dlo, flo))
            hi = np.where(in_all, len(cand), np.where(in_dir, dhi, fhi))
            frac = np.where(in_all, u / m_all, np.where(in_dir, (u - m_all) / np.maximum(m_dir, 1e-300),
                                                         (u - m_all - m_dir) / np.maximum(m_file, 1e-300)))
            pos = np.searchsorted(cum, cum[lo] + frac * (cum[hi] - cum[lo]), "right") - 1
            dst[add] = cand[np.clip(pos, lo, np.maximum(hi - 1, lo))]
        return self.degree(self.alive[-1], dst, self.q - 1)

    def observed(self) -> np.ndarray:
        return self.degree(self.alive[-1], self.dst, self.q - 1)


def fit(nets: list, law2: dict, seed: int = SEED, sims: int = SIMS) -> dict:
    """The LAW-4 record of one repo: `nets` its quarterly networks, `law2` its tools/laws_attach.fit record."""
    out = {"evaluable": False}
    if not law2.get("evaluable"):
        return {**out, "why": "LAW-2 is not evaluable for this repo, so it has no kernel to replay"}
    h = History(nets)
    if h.q < MIN_QUARTERS:
        return {**out, "why": f"fewer than {MIN_QUARTERS} quarters with a commit"}
    coef = {k: v["b"] for k, v in law2["coefficients"].items()}
    rng = np.random.default_rng(seed)
    here = h.present[-1]
    k_obs = h.observed()[here]
    g1 = lambda k: gini(k[k >= 1])  # noqa: E731
    own = [h.replay(coef, rng)[here] for _ in range(sims)]
    uni = [h.replay({}, rng)[here] for _ in range(sims)]
    own1, uni1 = np.array([g1(k) for k in own]), np.array([g1(k) for k in uni])
    return {**out, "evaluable": True, "quarters": h.q, "functions_last": int(here.sum()), "edges_last": int(len(h.alive[-1])),
            "gini_observed": g1(k_obs), "gini_replayed_mean": float(own1.mean()),
            "effect": g1(k_obs) - float(own1.mean()), "se": float(own1.std(ddof=1)),
            "gini0_observed": gini(k_obs), "gini0_replayed_mean": float(np.mean([gini(k) for k in own])),
            "uniform": {"gini_replayed_mean": float(uni1.mean()), "effect": g1(k_obs) - float(uni1.mean()),
                        "se": float(uni1.std(ddof=1))},
            "kernel": coef, "negative_locality_replayed_as_zero": [f for f in ("same_file", "same_dir") if coef.get(f, 0) < 0],
            "sims": sims}
