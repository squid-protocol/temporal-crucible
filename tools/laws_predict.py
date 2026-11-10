#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAW-8, network metrics in defect prediction, forward in time and effort-aware (methods review M8).

For each test year with at least MIN_TRAIN_YEARS training years and MIN_TEST_POS positive file-years:
  training rows   file-years of earlier snapshots whose 365-day outcome window closed by the test snapshot;
  models          (a) size and process: log(1 + loc, functions, churn, prior_fixes, authors, coupled);
                  (b) = (a) + network: k_mean, k_max, callers, callees (log(1 + .)), in_cycle, giant.
                  L2-penalised logistic regression; the penalty is chosen among LAMBDAS by cross-validated log loss
                  over time-blocked folds of the training years; features are standardised on the training rows;
  ranking         by predicted risk density p / loc, ties by smaller loc first;
  gain            recall at 20% of the test year's LOC, (b) - (a). AUC and Popt are reported beside it.
Effect = the mean gain over test years; SE = SD of the yearly gains / sqrt(years), inflated by
sqrt((1 + r) / (1 - r)) for their lag-1 autocorrelation r (0 when r is not positive). Margin 0.02; equivalence
margin +-0.02 (M2).

Not here: the rewiring feature of the original (b) (the panel does not carry it yet), ranking by p, and the
random-forest sensitivity.
"""
from __future__ import annotations

import math

import numpy as np

DAY = 86400
LAMBDAS = (0.01, 0.1, 1.0, 10.0, 100.0)
FOLDS = 5
MIN_TRAIN_YEARS = 3
MIN_TEST_POS = 10
MIN_TEST_YEARS = 3
BASE = ("loc", "functions", "churn", "prior_fixes", "authors", "coupled")
NETWORK = ("k_mean", "k_max", "callers", "callees")
FLAGS = ("in_cycle", "giant")


def design(rows: list[dict], network: bool) -> np.ndarray:
    cols = [np.log1p([r[c] for r in rows]) for c in BASE]
    if network:
        cols += [np.log1p([r[c] for r in rows]) for c in NETWORK] + [np.array([r[c] for r in rows], dtype=float) for c in FLAGS]
    return np.column_stack(cols).astype(float)


def ridge_logit(x: np.ndarray, y: np.ndarray, lam: float, max_iter: int = 100) -> np.ndarray:
    """L2-penalised logistic regression by Newton steps; x has a constant first column, which is not penalised."""
    n, k = x.shape
    pen = np.eye(k) * lam
    pen[0, 0] = 0.0
    b = np.zeros(k)
    for _ in range(max_iter):
        p = 1 / (1 + np.exp(-np.clip(x @ b, -35, 35)))
        g = x.T @ (y - p) - pen @ b
        h = (x * (p * (1 - p))[:, None]).T @ x + pen + 1e-9 * np.eye(k)
        step = np.linalg.solve(h, g)
        b = b + step
        if np.max(np.abs(step)) < 1e-8:
            break
    return b


def _standardise(train: np.ndarray, *others: np.ndarray):
    mu, sd = train.mean(axis=0), train.std(axis=0)
    sd[sd == 0] = 1.0
    add = lambda m: np.column_stack([np.ones(len(m)), (m - mu) / sd])  # noqa: E731
    return (add(train), *(add(o) for o in others))


def _logloss(y, p):
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def choose_lambda(x: np.ndarray, y: np.ndarray, years: np.ndarray) -> float:
    """The penalty with the lowest log loss over time-blocked folds (contiguous blocks of training years)."""
    ys = np.unique(years)
    blocks = [b for b in np.array_split(ys, min(FOLDS, len(ys))) if len(b)]
    if len(blocks) < 2:
        return 1.0
    best, best_loss = 1.0, math.inf
    for lam in LAMBDAS:
        loss = 0.0
        for b in blocks:
            val = np.isin(years, b)
            if val.all() or not val.any() or len(np.unique(y[~val])) < 2:
                continue
            xt, xv = _standardise(x[~val], x[val])
            p = 1 / (1 + np.exp(-np.clip(xv @ ridge_logit(xt, y[~val], lam), -35, 35)))
            loss += _logloss(y[val], p) * val.sum()
        if loss < best_loss:
            best, best_loss = lam, loss
    return best


def effort_curve(score: np.ndarray, loc: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Cumulative share of LOC and of positives when files are inspected by descending score, smaller LOC first."""
    order = np.lexsort((loc, -score))
    eff = np.cumsum(loc[order]) / loc.sum()
    rec = np.cumsum(y[order]) / max(1.0, y.sum())
    return eff, rec


def recall_at(score, loc, y, share: float = 0.2) -> float:
    eff, rec = effort_curve(score, loc, y)
    inside = eff <= share + 1e-12
    return float(rec[inside][-1]) if inside.any() else 0.0


def popt(score, loc, y) -> float:
    """Popt (Mende & Koschke): 1 - (area between the optimal and the model's effort curves) / (area between the
    optimal and the worst)."""
    area = lambda s: float(np.trapezoid(np.r_[0.0, effort_curve(s, loc, y)[1]], np.r_[0.0, effort_curve(s, loc, y)[0]]))  # noqa: E731
    dens = y / np.maximum(loc, 1)
    opt, worst, model = area(dens), area(-dens), area(score)
    return 1 - (opt - model) / (opt - worst) if opt > worst else float("nan")


def auc(score, y) -> float:
    pos, neg = score[y == 1], score[y == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    ranks = np.argsort(np.argsort(np.r_[pos, neg], kind="mergesort"), kind="mergesort") + 1.0
    return float((ranks[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def fit(rows: list[dict], window_days: int = 365) -> dict:
    """The LAW-8 record of one repo from its file-years (tools/laws_panel.py)."""
    years = np.array([r["year"] for r in rows])
    t = np.array([r["t"] for r in rows])
    y = np.array([r["outcome"] for r in rows], dtype=float)
    loc = np.maximum(1.0, np.array([r["loc"] for r in rows], dtype=float))
    xa, xb = design(rows, False), design(rows, True)
    by_year = []
    for test in sorted(set(years.tolist())):
        te = years == test
        t_test = t[te].min()
        tr = (years < test) & (t + window_days * DAY <= t_test)
        if len(np.unique(years[tr])) < MIN_TRAIN_YEARS or y[te].sum() < MIN_TEST_POS or len(np.unique(y[tr])) < 2:
            continue
        rec = {"year": int(test), "train_rows": int(tr.sum()), "test_rows": int(te.sum()), "test_positives": int(y[te].sum())}
        for name, x in (("a", xa), ("b", xb)):
            lam = choose_lambda(x[tr], y[tr], years[tr])
            xt, xs = _standardise(x[tr], x[te])
            p = 1 / (1 + np.exp(-np.clip(xs @ ridge_logit(xt, y[tr], lam), -35, 35)))
            dens = p / loc[te]
            rec[name] = {"lambda": lam, "recall20": recall_at(dens, loc[te], y[te]), "popt": popt(dens, loc[te], y[te]),
                         "auc": auc(p, y[te])}
        rec["gain"] = rec["b"]["recall20"] - rec["a"]["recall20"]
        by_year.append(rec)
    out = {"evaluable": False, "test_years": len(by_year), "by_year": by_year}
    if len(by_year) < MIN_TEST_YEARS:
        return {**out, "why": f"fewer than {MIN_TEST_YEARS} test years with {MIN_TRAIN_YEARS} training years and {MIN_TEST_POS} positives"}
    g = np.array([r["gain"] for r in by_year])
    r1 = float(np.corrcoef(g[:-1], g[1:])[0, 1]) if len(g) > 2 and np.std(g[:-1]) > 0 and np.std(g[1:]) > 0 else 0.0
    infl = math.sqrt((1 + r1) / (1 - r1)) if 0 < r1 < 1 else 1.0
    mean = lambda k, m: float(np.mean([r[m][k] for r in by_year]))  # noqa: E731
    return {**out, "evaluable": True, "effect": float(g.mean()), "se": float(g.std(ddof=1) / math.sqrt(len(g)) * infl),
            "lag1": r1, "recall20_a": mean("recall20", "a"), "recall20_b": mean("recall20", "b"),
            "popt_a": mean("popt", "a"), "popt_b": mean("popt", "b"), "auc_a": mean("auc", "a"), "auc_b": mean("auc", "b")}
