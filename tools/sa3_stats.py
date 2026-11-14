#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The statistics of SA3 and SA3-CH, as registered and amended. Pure functions on arrays; no repo is read here.

    python tools/sa3_stats.py --selftest      # null centring and power on synthetic data

  bands        equal-count LOC bands (10 if >= 300 files, else 5), ties broken by path
  Design       the eligible (positive, negative) pairs of one repo and outcome: same band, LOC ratio within the
               caliper, and any further calipers (SA3-CH: prior commits, lines changed). Built once; it does not
               depend on the predictor.
  bAUC         size-balanced caliper concordance (SA3 registration, "Statistic"): concordance scored
               separately on pairs where the positive is the larger file and where it is the smaller, weighted
               equally, plus the equal-LOC pairs by their share. effect = bAUC - 0.5.
  residual     the co-reported statistic (SA3 Amendment 1 rule 1): within a band, the predictor's rank fraction
               with its least-squares fit on the covariates removed, then within-band AUC - 0.5.
  sauc_minus   the statistic first registered and withdrawn, kept as sensitivity S6.
"""
from __future__ import annotations

import sys
import numpy as np
from scipy.stats import rankdata

CALIPER = 1.5


def bands(loc: np.ndarray, paths: list[str], k: int | None = None) -> tuple[np.ndarray, int]:
    n = len(loc)
    if k is None:
        k = 10 if n >= 300 else 5
    order = sorted(range(n), key=lambda i: (loc[i], paths[i]))
    b = np.empty(n, int)
    b[order] = (np.arange(n) * k) // n
    return b, k


class Design:
    """Eligible pairs for one (repo, outcome). `extra` = [(values, max ratio)] for further calipers on 1 + value."""

    def __init__(self, loc, y, band, k, caliper: float = CALIPER, extra=()):
        self.parts = []          # per band: (pos idx, neg idx, mask_gt, mask_lt, mask_eq) as float32
        self.n_gt = self.n_lt = self.n_eq = 0
        loc = np.asarray(loc, float)
        for j in range(k):
            idx = np.flatnonzero(band == j)
            p, q = idx[y[idx] == 1], idx[y[idx] == 0]
            if not len(p) or not len(q):
                continue
            ratio = loc[p][:, None] / loc[q][None, :]
            ok = (ratio <= caliper) & (ratio >= 1 / caliper)
            for v, mx in extra:
                r2 = (1.0 + v[p])[:, None] / (1.0 + v[q])[None, :]
                ok &= (r2 <= mx) & (r2 >= 1 / mx)
            gt, lt, eq = ok & (ratio > 1), ok & (ratio < 1), ok & (ratio == 1)
            if not ok.any():
                continue
            self.parts.append((p, q, gt.astype(np.float32), lt.astype(np.float32), eq.astype(np.float32)))
            self.n_gt += int(gt.sum()); self.n_lt += int(lt.sum()); self.n_eq += int(eq.sum())
        self.n = self.n_gt + self.n_lt + self.n_eq

    def clears_pair_floor(self) -> bool:
        return self.n >= 100 and self.n_gt >= 25 and self.n_lt >= 25

    def informative_pairs(self, x) -> int:
        """eligible pairs in which the two values differ (SA3-CH Amendment 1 rule 2)"""
        return int(sum(((x[p][:, None] != x[q][None, :]) * (gt + lt + eq)).sum() for p, q, gt, lt, eq in self.parts))

    def effect(self, x, wp=None, wn=None) -> float:
        """bAUC(x) - 0.5. wp / wn: optional bootstrap weights per file index (stratified resampling)."""
        s = {"gt": 0.0, "lt": 0.0, "eq": 0.0}
        t = {"gt": 0.0, "lt": 0.0, "eq": 0.0}
        for p, q, gt, lt, eq in self.parts:
            xp, xq = x[p][:, None], x[q][None, :]
            conc = (xp > xq).astype(np.float32) + 0.5 * (xp == xq)
            w = None if wp is None else np.outer(wp[p], wn[q]).astype(np.float32)
            for name, m in (("gt", gt), ("lt", lt), ("eq", eq)):
                mm = m if w is None else m * w
                s[name] += float((conc * mm).sum()); t[name] += float(mm.sum())
        tot = t["gt"] + t["lt"] + t["eq"]
        if t["gt"] <= 0 or t["lt"] <= 0:
            return float("nan")
        we = t["eq"] / tot
        ce = s["eq"] / t["eq"] if t["eq"] > 0 else 0.5
        return (1 - we) * 0.5 * (s["gt"] / t["gt"] + s["lt"] / t["lt"]) + we * ce - 0.5


def sauc(x, y, band, k) -> float:
    num = den = 0.0
    for j in range(k):
        m = band == j
        yy = y[m]
        p = int(yy.sum()); n = len(yy) - p
        if p == 0 or n == 0:
            continue
        r = rankdata(x[m])
        num += r[yy == 1].sum() - p * (p + 1) / 2
        den += p * n
    return num / den if den else float("nan")


def residual_effect(x, y, band, k, covariates) -> float:
    """within-band rank fraction of x, minus its least-squares fit on the covariates; then sAUC - 0.5"""
    r = np.zeros(len(x))
    for j in range(k):
        m = np.flatnonzero(band == j)
        if len(m) < 3:
            continue
        u = rankdata(x[m]) / len(m)
        cols = [c[m] - c[m].mean() for c in covariates]
        cols = [c for c in cols if np.ptp(c) > 0]
        if np.ptp(u) == 0 or not cols:
            r[m] = u - u.mean()
            continue
        A = np.column_stack([np.ones(len(m))] + cols)
        beta, *_ = np.linalg.lstsq(A, u, rcond=None)
        r[m] = u - A @ beta
    return sauc(r, y, band, k) - 0.5


def sauc_minus_loc(x, loc, y, band, k) -> float:
    return sauc(x, y, band, k) - sauc(loc, y, band, k)


def auc_plain(x, y) -> float:
    p = int(y.sum()); n = len(y) - p
    if not p or not n:
        return float("nan")
    r = rankdata(x)
    return (r[y == 1].sum() - p * (p + 1) / 2) / (p * n)


def logistic_z(x, lg, y, band, k, count: bool) -> float:
    """S9: y ~ band dummies + ln LOC + standardised x (log1p for counts); the Wald z of x"""
    g = np.log1p(np.maximum(x, 0)) if count else x
    if np.ptp(g) == 0:
        return float("nan")
    z = (g - g.mean()) / g.std()
    keep = [j for j in range(k) if 0 < y[band == j].sum() < (band == j).sum()]
    rows = np.isin(band, keep)
    X = np.zeros((int(rows.sum()), len(keep) + 2))
    bb = band[rows]
    for c, j in enumerate(keep):
        X[bb == j, c] = 1
    X[:, -2] = lg[rows] - lg[rows].mean(); X[:, -1] = z[rows]
    yy = y[rows].astype(float)
    w = np.zeros(X.shape[1])
    H = np.eye(X.shape[1])
    for _ in range(40):
        p = 1 / (1 + np.exp(-np.clip(X @ w, -30, 30)))
        W = p * (1 - p) + 1e-9
        H = X.T @ (X * W[:, None]) + 1e-6 * np.eye(X.shape[1])
        step = np.linalg.solve(H, X.T @ (yy - p))
        w += step
        if np.abs(step).max() < 1e-7:
            break
    return float(w[-1] / np.sqrt(np.linalg.inv(H)[-1, -1]))


def block_permute(x, loc, paths, rng, block: int = 4, groups=None):
    """the real predictor, permuted within blocks of `block` LOC-adjacent files (optionally within groups)"""
    out = x.copy()
    order = sorted(range(len(x)), key=lambda i: ((groups[i] if groups is not None else 0), loc[i], paths[i]))
    order = np.asarray(order)
    key = np.asarray([groups[i] for i in order]) if groups is not None else np.zeros(len(order), int)
    start = 0
    for g in np.unique(key):
        idx = order[key == g]
        for s in range(0, len(idx), block):
            blk = idx[s:s + block]
            out[blk] = x[rng.permutation(blk)]
        start += len(idx)
    return out


def boot_ci(design: Design, x, band, k, y, reps: int = 600, seed: int = 2982, level: float = 0.95):
    """stratified bootstrap over files within (band, outcome): resampling weights, not copies"""
    rng = np.random.default_rng(seed)
    n = len(x)
    strata = [np.flatnonzero((band == j) & (y == v)) for j in range(k) for v in (0, 1)]
    strata = [s for s in strata if len(s)]
    vals = []
    for _ in range(reps):
        w = np.zeros(n)
        for s in strata:
            np.add.at(w, rng.choice(s, len(s)), 1.0)
        e = design.effect(x, w, w)
        if e == e:
            vals.append(e)
    if len(vals) < reps // 4:
        return [None, None]
    a = (1 - level) / 2
    return [float(np.quantile(vals, a)), float(np.quantile(vals, 1 - a))]


def _selftest() -> int:
    rng = np.random.default_rng(11)
    rows = []
    for kind, c in (("noise", 0.0), ("size_proxy", 0.0), ("count", 0.0), ("score", 0.0), ("count", 0.3), ("score", 0.3)):
        e1, e2 = [], []
        for _ in range(60):
            n = 800
            lg = rng.normal(5, 1.2, n); loc = np.exp(lg); trait = rng.normal(0, 1, n)
            if kind == "noise":
                x = rng.normal(0, 1, n)
            elif kind == "size_proxy":
                x = lg + rng.normal(0, 0.5, n)
            elif kind == "count":
                x = rng.poisson(loc * 0.12 * np.exp(0.6 * trait)).astype(float)
            else:
                hits = rng.poisson(loc * 0.01 * np.exp(0.6 * trait))
                x = np.where(hits > 0, 100 / (1 + np.exp(-4 * (0.05 * trait + rng.normal(0, 0.02, n)))), 0.0)
            lin = 0.9 * (lg - 5) + c * trait
            y = (rng.random(n) < 1 / (1 + np.exp(-(lin - 2.0)))).astype(int)
            paths = [f"f{i}" for i in range(n)]
            b, k = bands(loc, paths)
            d = Design(loc, y, b, k)
            e1.append(d.effect(x)); e2.append(residual_effect(x, y, b, k, [lg]))
        rows.append((kind, c, np.nanmean(e1), np.nanmean(e2)))
        print(f"{kind:<11} true effect {c:<4} bAUC-0.5 {np.nanmean(e1):+.4f}   residual {np.nanmean(e2):+.4f}")
    bad = [r for r in rows if r[1] == 0 and (abs(r[2]) > 0.01 or abs(r[3]) > 0.01)]
    bad += [r for r in rows if r[1] > 0 and (r[2] < 0.03 or r[3] < 0.03)]
    print("selftest", "FAILED" if bad else "ok: null centred within 0.01, a real effect detected by both")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(_selftest() if "--selftest" in sys.argv else 0)
