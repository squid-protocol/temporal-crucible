#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAW-6 and LAW-7 (docs/laws_hypotheses.md; methods review M7), from the file-years of tools/laws_panel.py.

LAW-6, cycles go with later fixes. Firth logistic of the outcome on in_cycle with the controls
  log(1 + loc), log(1 + functions), log(1 + churn), log(1 + prior_fixes), log(1 + authors), log(1 + coupled),
  log(1 + callers), log(1 + callees) (static fan-in and fan-out), giant (its own category), calendar-year effects.
  Effect = the log odds ratio of in_cycle; SE two-way cluster-robust by file and by fix commit (a file-year with no
  fix is its own cluster on that side); where that is not positive, a cluster bootstrap by file. Margin 0.
  Not evaluable: fewer than MIN_CLASS positive or negative file-years, in_cycle share below 5% or above 80%, or a
  fit that does not converge.

LAW-7, the size confound. For each of three size-neutral metrics (k_mean, coupling = callers + callees, in_cycle):
  the average marginal effect on the probability of a fix, per SD of the metric (per 0 -> 1 for in_cycle),
  unadjusted (metric + calendar year) and adjusted for size (+ log(1 + loc), log(1 + functions)).
  Effect = 1 - AME_adjusted / AME_unadjusted, computed only where the unadjusted AME is positive at one-sided
  p < 0.05 (file-clustered); SE by a paired cluster bootstrap over files. Margin 0.5, for all three (M2).
"""
from __future__ import annotations

import numpy as np

import laws_logit as L

SEED = 2982
BOOT = 1000
MIN_CLASS = 50
CYCLE_SHARE = (0.05, 0.80)
CONTROLS = ("loc", "functions", "churn", "prior_fixes", "authors", "coupled")
METRICS = {"k_mean": False, "coupling": False, "in_cycle": True}


def _col(rows, name):
    if name == "coupling":
        return np.array([r["callers"] + r["callees"] for r in rows], dtype=float)
    return np.array([r[name] for r in rows], dtype=float)


def _years(rows) -> np.ndarray:
    """Calendar-year indicator columns, the first year left out (it is the constant's)."""
    ys = sorted({r["year"] for r in rows})
    y = np.array([r["year"] for r in rows])
    return np.column_stack([(y == v).astype(float) for v in ys[1:]]) if len(ys) > 1 else np.empty((len(rows), 0))


def _ids(values) -> np.ndarray:
    return np.unique(np.array(values, dtype=object).astype(str), return_inverse=True)[1]


def evaluable(rows) -> str | None:
    pos = sum(r["outcome"] for r in rows)
    if pos < MIN_CLASS or len(rows) - pos < MIN_CLASS:
        return f"fewer than {MIN_CLASS} positive or negative file-years ({pos} of {len(rows)})"
    return None


def law6(rows: list[dict], seed: int = SEED, boot: int = BOOT) -> dict:
    out = {"evaluable": False, "rows": len(rows), "positives": sum(r["outcome"] for r in rows)}
    if why := evaluable(rows):
        return {**out, "why": why}
    share = float(np.mean([r["in_cycle"] for r in rows]))
    out["in_cycle_share"], out["giant_share"] = share, float(np.mean([r["giant"] for r in rows]))
    if not CYCLE_SHARE[0] <= share <= CYCLE_SHARE[1]:
        return {**out, "why": f"in-cycle share {share:.3f} outside {CYCLE_SHARE[0]}-{CYCLE_SHARE[1]}"}
    y = _col(rows, "outcome")
    names = ["const", "in_cycle", *CONTROLS, "callers", "callees", "giant"]
    cols = [np.ones(len(rows)), _col(rows, "in_cycle"), *(np.log1p(_col(rows, c)) for c in CONTROLS),
            np.log1p(_col(rows, "callers")), np.log1p(_col(rows, "callees")), _col(rows, "giant")]
    keep = [i for i, c in enumerate(cols) if i == 0 or np.ptp(c) > 0]  # a column that never varies has no coefficient
    x = np.column_stack([cols[i] for i in keep] + [_years(rows)])
    names = [names[i] for i in keep]
    fit = L.firth(x, y)
    if not fit["converged"] or "in_cycle" not in names:
        return {**out, "why": "the model did not converge"}
    j = names.index("in_cycle")
    files = _ids([r["file"] for r in rows])
    fixes = _ids([r["fix_commit"] or f"none:{i}" for i, r in enumerate(rows)])
    cov = L.cov_cluster(x, y, fit, files, fixes)
    if cov["ok"]:
        se, how = float(np.sqrt(cov["cov"][j, j])), "two-way (file, fix commit)"
    else:
        rng = np.random.default_rng(seed)
        groups = [np.flatnonzero(files == g) for g in np.unique(files)]
        reps = []
        for _ in range(boot):
            idx = np.concatenate([groups[g] for g in rng.integers(0, len(groups), len(groups))])
            f = L.firth(x[idx], y[idx])
            if f["converged"]:
                reps.append(f["beta"][j])
        se, how = float(np.std(reps, ddof=1)), f"cluster bootstrap by file ({len(reps)})"
    v = dict(zip(names[1:], L.vif(x[:, :len(names)])[1:]))
    return {**out, "evaluable": True, "effect": float(fit["beta"][j]), "se": se, "se_method": how,
            "se_naive": float(np.sqrt(fit["cov"][j, j])), "coefficients": {n: float(b) for n, b in zip(names, fit["beta"])},
            "vif": {k: float(x_) for k, x_ in v.items()}, "files": int(files.max()) + 1}


def _ame_pair(rows, metric: str, binary: bool, idx: np.ndarray | None = None) -> tuple[float, float, dict, np.ndarray, np.ndarray]:
    sub = rows if idx is None else [rows[i] for i in idx]
    y = _col(sub, "outcome")
    m = _col(sub, metric)
    if not binary:
        sd = m.std()
        m = (m - m.mean()) / sd if sd > 0 else m * 0
    yrs = _years(sub)
    xu = np.column_stack([np.ones(len(sub)), m, yrs])
    xa = np.column_stack([np.ones(len(sub)), m, np.log1p(_col(sub, "loc")), np.log1p(_col(sub, "functions")), yrs])
    fu, fa = L.firth(xu, y), L.firth(xa, y)
    return L.ame(xu, fu, 1, binary), L.ame(xa, fa, 1, binary), fu, xu, y


def law7(rows: list[dict], seed: int = SEED, boot: int = BOOT) -> dict:
    out = {"evaluable": False, "rows": len(rows), "positives": sum(r["outcome"] for r in rows), "metrics": {}}
    if why := evaluable(rows):
        return {**out, "why": why}
    rng = np.random.default_rng(seed)
    files = _ids([r["file"] for r in rows])
    groups = [np.flatnonzero(files == g) for g in np.unique(files)]
    for metric, binary in METRICS.items():
        rec = {"evaluable": False}
        if np.ptp(_col(rows, metric)) == 0:
            out["metrics"][metric] = {**rec, "why": "the metric never varies"}
            continue
        un, ad, fu, xu, y = _ame_pair(rows, metric, binary)
        se_b = float(np.sqrt(L.cov_cluster(xu, y, fu, files)["cov"][1, 1]))
        z = fu["beta"][1] / se_b if se_b > 0 else 0.0
        rec.update(ame_unadjusted=un, ame_adjusted=ad, unadjusted_z=float(z))
        if not (un > 0 and z > 1.645):
            out["metrics"][metric] = {**rec, "why": "the unadjusted effect is not positive at one-sided p < 0.05"}
            continue
        reps = []
        for _ in range(boot):
            idx = np.concatenate([groups[g] for g in rng.integers(0, len(groups), len(groups))])
            u, a, *_ = _ame_pair(rows, metric, binary, idx)
            if u > 0:
                reps.append(1 - a / u)
        out["metrics"][metric] = {**rec, "evaluable": True, "effect": 1 - ad / un, "se": float(np.std(reps, ddof=1)),
                                  "boot": len(reps)}
    out["evaluable"] = any(m["evaluable"] for m in out["metrics"].values())
    return out
