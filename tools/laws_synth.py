#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAWS synthesis (docs/laws_hypotheses.md; methods review M1 and M2, Amendments 0, 2 and 3). No data is read here:
these are the pooling and testing rules the scorer applies to per-repo effects.

  pool(y, v)                 random effects within one language: tau^2 by REML (Paule-Mandel if REML does not
                             converge), Hartung-Knapp-Sidik-Jonkman CI with the ad-hoc correction and never narrower
                             than the DerSimonian-Laird CI, 95% prediction interval; DL reported for sensitivity
  one_sided_p(...)           p of the pooled effect against a law's margin, in the predicted direction
  tost_p(...)                the equivalence test an absence claim needs (M2)
  partial_conjunction(p, r)  Benjamini-Heller p for "at least r of n" (Bonferroni combining)
  holm(ps, alpha)            which of the laws' p-values survive Holm
  universal(...)             the primary (>= 3 of C, Java, Go, Python) and extended (>= r of n) calls for every law
"""
from __future__ import annotations

import math

from scipy import optimize, stats

ALPHA_FAMILY = 0.01  # family-wise, across the nine laws (M2)
ALPHA_LANGUAGE = 0.005  # one-sided, per language ("holds"): the registered 99% CI
PRIMARY = ("c", "java", "go", "python")
PRIMARY_R = 3


def _wmean(y, w):
    sw = sum(w)
    return sum(a * b for a, b in zip(w, y)) / sw, sw


def tau2_dl(y, v):
    k = len(y)
    w = [1 / x for x in v]
    mu, sw = _wmean(y, w)
    q = sum(wi * (yi - mu) ** 2 for wi, yi in zip(w, y))
    c = sw - sum(wi * wi for wi in w) / sw
    return max(0.0, (q - (k - 1)) / c) if c > 0 else 0.0


def tau2_reml(y, v, tol=1e-10, max_iter=500):
    """Fisher scoring from the DL start; None when it does not converge."""
    t2 = tau2_dl(y, v)
    for _ in range(max_iter):
        w = [1 / (x + t2) for x in v]
        mu, sw = _wmean(y, w)
        new = max(0.0, sum(wi * wi * ((yi - mu) ** 2 - vi) for wi, yi, vi in zip(w, y, v)) / sum(wi * wi for wi in w) + 1 / sw)
        if abs(new - t2) < tol:
            return new
        t2 = new
    return None


def tau2_pm(y, v):
    """Paule-Mandel: the tau^2 at which the generalised Q equals k - 1 (0 when Q(0) is already below it)."""
    k = len(y)

    def excess(t2):
        w = [1 / (x + t2) for x in v]
        mu, _ = _wmean(y, w)
        return sum(wi * (yi - mu) ** 2 for wi, yi in zip(w, y)) - (k - 1)

    if excess(0.0) <= 0:
        return 0.0
    hi = 1.0
    while excess(hi) > 0:
        hi *= 10
        if hi > 1e12:
            return hi
    return float(optimize.brentq(excess, 0.0, hi))


def pool(y: list[float], v: list[float]) -> dict:
    """Pooled effect of k >= 2 repo effects y with sampling variances v (all finite, v > 0)."""
    k = len(y)
    if k < 2 or len(v) != k or any(not math.isfinite(a) for a in (*y, *v)) or any(a <= 0 for a in v):
        raise ValueError("pool needs k >= 2 finite effects with positive variances")
    t2 = tau2_reml(y, v)
    method = "REML"
    if t2 is None:
        t2, method = tau2_pm(y, v), "Paule-Mandel"
    w = [1 / (x + t2) for x in v]
    mu, sw = _wmean(y, w)
    q = sum(wi * (yi - mu) ** 2 for wi, yi in zip(w, y)) / (k - 1)
    se_hk = math.sqrt(max(1.0, q) / sw)  # ad-hoc correction: never below the model-based variance
    d2 = tau2_dl(y, v)
    wd = [1 / (x + d2) for x in v]
    mud, swd = _wmean(y, wd)
    se_dl = math.sqrt(1 / swd)
    tcrit, zcrit = stats.t.ppf(1 - ALPHA_LANGUAGE, k - 1), stats.norm.ppf(1 - ALPHA_LANGUAGE)
    se = max(se_hk, se_dl * zcrit / tcrit)  # no HKSJ interval narrower than the DL interval, at the 99% bar
    pi = stats.t.ppf(0.975, k - 2) * math.sqrt(t2 + se * se) if k > 2 else float("nan")
    i2 = max(0.0, (q * (k - 1) - (k - 1)) / (q * (k - 1))) if q > 0 else 0.0
    return {"k": k, "mu": mu, "se": se, "df": k - 1, "tau2": t2, "tau2_method": method, "I2_at_tau2": i2,
            "ci99": [mu - tcrit * se, mu + tcrit * se], "pi95": [mu - pi, mu + pi],
            "dl": {"mu": mud, "se": se_dl, "tau2": d2, "ci99": [mud - zcrit * se_dl, mud + zcrit * se_dl]}}


def one_sided_p(pooled: dict, margin: float = 0.0, direction: int = 1) -> float:
    """p of H0: direction * (mu - margin) <= 0, on t with k - 1 degrees of freedom."""
    return float(stats.t.sf(direction * (pooled["mu"] - margin) / pooled["se"], pooled["df"]))


def tost_p(pooled: dict, margin: float, centre: float = 0.0) -> float:
    """Two one-sided tests: p for |mu - centre| < margin (the larger of the two one-sided p-values)."""
    lo = stats.t.sf((pooled["mu"] - (centre - margin)) / pooled["se"], pooled["df"])
    hi = stats.t.sf(((centre + margin) - pooled["mu"]) / pooled["se"], pooled["df"])
    return float(max(lo, hi))


def partial_conjunction(ps: list[float], r: int) -> float:
    """Benjamini-Heller (2008) with Bonferroni combining: (n - r + 1) * p_(r), valid under any dependence."""
    n = len(ps)
    if not 1 <= r <= n:
        raise ValueError("r must be between 1 and n")
    return min(1.0, (n - r + 1) * sorted(ps)[r - 1])


def holm(ps: dict[str, float], alpha: float = ALPHA_FAMILY) -> dict[str, bool]:
    """Which hypotheses Holm rejects at family-wise alpha."""
    out, m, stopped = {}, len(ps), False
    for i, (name, p) in enumerate(sorted(ps.items(), key=lambda kv: kv[1])):
        stopped = stopped or p > alpha / (m - i)
        out[name] = not stopped
    return out


def extended_r(n: int) -> int:
    return math.ceil(2 * n / 3)  # Amendment 2 item 3


def universal(law_ps: dict[str, dict[str, float]], opposite_ps: dict[str, dict[str, float]], languages: list[str]) -> dict:
    """law_ps[law][language]: the one-sided p in the predicted direction (1.0 for a language that is ACC-failed or
    not evaluable for the law: it counts against, the test is not re-scaled). opposite_ps: the same in the opposite
    direction. `languages`: every language that entered ACC-P (the extended test's n). Returns, per law, the primary
    and extended partial-conjunction p-values and whether each survives Holm with no language opposite at p < 0.01."""
    n, r = len(languages), extended_r(len(languages))
    prim = {law: partial_conjunction([ps.get(lang, 1.0) for lang in PRIMARY], PRIMARY_R) for law, ps in law_ps.items()}
    ext = {law: partial_conjunction([ps.get(lang, 1.0) for lang in languages], r) for law, ps in law_ps.items()}
    hp, he = holm(prim), holm(ext)
    out = {}
    for law in law_ps:
        opp = sorted(lang for lang, p in (opposite_ps.get(law) or {}).items() if p < 0.01)
        out[law] = {"primary_p": prim[law], "primary_universal": hp[law] and not [x for x in opp if x in PRIMARY],
                    "extended_p": ext[law], "extended_r_of_n": [r, n], "extended_universal": he[law] and not opp,
                    "opposite_languages": opp}
    return out
