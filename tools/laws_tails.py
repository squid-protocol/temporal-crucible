#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAW-1, heavy tails (docs/laws_hypotheses.md; methods review M5): discrete tail fits of a degree sequence.

    fit(degrees)  ->  the per-repo LAW-1 record for the in-degrees k >= 1 of one network

  - discrete power law by Clauset-Shalizi-Newman: alpha by maximum likelihood, x_min by the smallest KS distance,
    among x_min that leave n_tail >= MIN_TAIL (else not evaluable);
  - goodness of fit by the CSN semi-parametric bootstrap (BOOT replicates, seed 2982);
  - Vuong likelihood-ratio tests of the power law against exponential, log-normal, stretched exponential and power
    law with exponential cutoff, all fitted to the same tail;
  - the confirmatory effect: the per-node log-likelihood ratio of the better of {power law, log-normal, truncated
    power law} against a negative binomial truncated below x_min (zero-truncated when x_min = 1), with its
    bootstrap SE (tail resampled, every model refitted, x_min held); margin 0; needs tail fraction >= 0.05;
  - descriptive: the same ratio against the exponential, and the Broido-Clauset strength class.

Continuous families (log-normal, stretched exponential) are discretised on [x - 1/2, x + 1/2) and renormalised on
x >= x_min. All likelihoods are computed on the distinct values with their counts.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import optimize, special, stats

SEED = 2982
BOOT = 1000
MIN_TAIL = 50
MIN_TAIL_FRACTION = 0.05
XMAX_SUM = 200_000  # where the truncated power law's normalising sum stops (terms are below 1e-12 long before)


def _counts(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    v, c = np.unique(x, return_counts=True)
    return v.astype(float), c.astype(float)


def _nll(c, logp) -> float:
    """The negative log-likelihood, or a large penalty where the likelihood is not finite."""
    val = -float((c * logp).sum())
    return val if math.isfinite(val) else 1e18


# ---- each family: fit(v, c, xmin) -> params; logpmf(params, v, xmin) -> log p(v) on the tail -------------------
def pl_logpmf(p, v, xmin):
    return -p[0] * np.log(v) - math.log(special.zeta(p[0], xmin))


def pl_fit(v, c, xmin, start=None):
    n, s = c.sum(), (c * np.log(v)).sum()
    r = optimize.minimize_scalar(lambda a: a * s + n * math.log(special.zeta(a, xmin)), bounds=(1.01, 12.0), method="bounded")
    return (float(r.x),)


def exp_logpmf(p, v, xmin):
    return math.log1p(-math.exp(-p[0])) - p[0] * (v - xmin)


def exp_fit(v, c, xmin, start=None):
    m = (c * (v - xmin)).sum() / c.sum()
    return (math.log1p(1 / m) if m > 0 else 50.0,)


def _disc(logsf, v, xmin):
    """log pmf of a continuous family, given its LOG survival function, discretised on [x - 1/2, x + 1/2) and
    renormalised on x >= xmin. Worked in logs: a parameter corner where the survival function underflows gives
    -inf (the fit rejects it), never a clamped value that reads as a perfect fit."""
    la, lb = logsf(v - 0.5), logsf(v + 0.5)
    lc = logsf(np.array([xmin - 0.5]))[0]
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        out = la + np.log1p(-np.exp(lb - la)) - lc
    return np.where(np.isfinite(out), out, -np.inf)


def ln_logpmf(p, v, xmin):
    mu, sig = p
    return _disc(lambda t: stats.norm.logsf((np.log(np.maximum(t, 1e-12)) - mu) / sig), v, xmin)


def ln_fit(v, c, xmin, start=None):
    lv = np.log(v)
    m0 = (c * lv).sum() / c.sum()
    s0 = max(0.3, math.sqrt((c * (lv - m0) ** 2).sum() / c.sum()))
    f = lambda q: _nll(c, ln_logpmf((q[0], math.exp(min(q[1], 50.0))), v, xmin))  # noqa: E731
    best = min((optimize.minimize(f, x0, method="Nelder-Mead", options={"xatol": 1e-6, "fatol": 1e-8, "maxiter": 4000})
                for x0 in (((start[0], math.log(start[1])),) if start else
                           ((m0, math.log(s0)), (m0 - 2.0, math.log(s0 * 2)), (0.0, math.log(2.0))))), key=lambda r: r.fun)
    return (float(best.x[0]), float(math.exp(min(best.x[1], 50.0))))


def se_logpmf(p, v, xmin):
    lam, beta = p
    with np.errstate(over="ignore"):  # log S(t) = -(lam t)^beta, formed in logs
        return _disc(lambda t: -np.exp(beta * (math.log(lam) + np.log(np.maximum(t, 1e-12)))), v, xmin)


def se_fit(v, c, xmin, start=None):
    f = lambda q: _nll(c, se_logpmf((math.exp(min(q[0], 600.0)), math.exp(min(q[1], 50.0))), v, xmin))  # noqa: E731
    m = (c * v).sum() / c.sum()
    best = min((optimize.minimize(f, x0, method="Nelder-Mead", options={"xatol": 1e-6, "fatol": 1e-8, "maxiter": 4000})
                for x0 in (((math.log(start[0]), math.log(start[1])),) if start else
                           ((math.log(1 / m), 0.0), (math.log(1 / m), math.log(0.5)), (math.log(10 / m), math.log(0.3))))),
               key=lambda r: r.fun)
    return (float(math.exp(min(best.x[0], 600.0))), float(math.exp(min(best.x[1], 50.0))))


def _tpl_norm(alpha, lam, xmin):
    if lam <= 1e-7:
        return math.log(special.zeta(alpha, xmin))
    k = np.arange(xmin, min(XMAX_SUM, xmin + 45.0 / lam + 2), dtype=float)  # e^{-45} is below 1e-19 of the first term
    return math.log(np.sum(np.power(k, -alpha) * np.exp(-lam * k)))


def tpl_logpmf(p, v, xmin):
    alpha, lam = p
    return -alpha * np.log(v) - lam * v - _tpl_norm(alpha, lam, xmin)


def tpl_fit(v, c, xmin, start=None):
    a0 = pl_fit(v, c, xmin)[0]
    f = lambda q: _nll(c, tpl_logpmf((q[0], math.exp(min(q[1], 50.0))), v, xmin)) if 0.2 < q[0] < 12 else 1e18  # noqa: E731
    best = min((optimize.minimize(f, x0, method="Nelder-Mead", options={"xatol": 1e-6, "fatol": 1e-8, "maxiter": 4000})
                for x0 in (((start[0], math.log(max(start[1], 1e-9))),) if start else
                           ((a0, math.log(1e-3)), (max(1.0, a0 - 0.5), math.log(1e-2))))), key=lambda r: r.fun)
    return (float(best.x[0]), float(math.exp(best.x[1])))


def nb_logpmf(p, v, xmin):
    r, q = p
    return stats.nbinom.logpmf(v, r, q) - stats.nbinom.logsf(xmin - 1, r, q)


NB_R_MIN = 1e-6  # r -> 0 is the logarithmic-series limit of the negative binomial; the fit stops there


def nb_fit(v, c, xmin, start=None):
    f = lambda t: _nll(c, nb_logpmf((max(NB_R_MIN, math.exp(min(t[0], 50.0))), special.expit(t[1])), v, xmin))  # noqa: E731
    m = (c * v).sum() / c.sum()
    starts = ((0.0, special.logit(1 / (1 + m))), (math.log(0.2), special.logit(0.2 / (0.2 + m))), (math.log(5.0), special.logit(5 / (5 + m))))
    if start:
        starts = ((math.log(max(start[0], NB_R_MIN)), special.logit(min(max(start[1], 1e-9), 1 - 1e-9))),)
    best = min((optimize.minimize(f, x0, method="Nelder-Mead", options={"xatol": 1e-6, "fatol": 1e-8, "maxiter": 4000})
                for x0 in starts), key=lambda r: r.fun)
    return (float(max(NB_R_MIN, math.exp(min(best.x[0], 50.0)))), float(special.expit(best.x[1])))


FAMILIES = {"power_law": (pl_fit, pl_logpmf), "exponential": (exp_fit, exp_logpmf), "lognormal": (ln_fit, ln_logpmf),
            "stretched_exponential": (se_fit, se_logpmf), "truncated_power_law": (tpl_fit, tpl_logpmf),
            "negative_binomial": (nb_fit, nb_logpmf)}
HEAVY = ("power_law", "lognormal", "truncated_power_law")


def _ks(v, c, alpha, xmin):
    emp = np.cumsum(c) / c.sum()
    z = special.zeta(alpha, xmin)
    model = 1 - special.zeta(alpha, v + 1) / z
    return float(np.max(np.abs(emp - model)))


def csn(x: np.ndarray) -> dict | None:
    """alpha, x_min and the KS distance of the discrete power law; None when no x_min leaves MIN_TAIL points."""
    x = np.sort(x[x >= 1])
    best = None
    for xmin in np.unique(x):
        tail = x[x >= xmin]
        if len(tail) < MIN_TAIL:
            break
        v, c = _counts(tail)
        if len(v) < 2:
            continue
        a = pl_fit(v, c, float(xmin))[0]
        d = _ks(v, c, a, float(xmin))
        if best is None or d < best["ks"]:
            best = {"xmin": int(xmin), "alpha": a, "ks": d, "n_tail": int(len(tail))}
    return best


def _pl_sample(rng, n, alpha, xmin):
    """n draws from the discrete power law on x >= xmin (CSN appendix D: inverse transform by doubling and bisection)."""
    u = rng.random(n)
    lo = np.full(n, float(xmin))
    hi = lo * 2
    z = special.zeta(alpha, xmin)
    surv = lambda k: special.zeta(alpha, k) / z  # noqa: E731  P(X >= k)
    grow = surv(hi) > 1 - u
    while grow.any():
        lo[grow], hi[grow] = hi[grow], hi[grow] * 2
        grow = surv(hi) > 1 - u
    while ((hi - lo) > 1).any():
        mid = np.floor((lo + hi) / 2)
        up = surv(mid) > 1 - u
        lo, hi = np.where(up, mid, lo), np.where(up, hi, mid)
    return lo


def gof_p(x: np.ndarray, best: dict, boot: int = BOOT, seed: int = SEED) -> float:
    """CSN goodness of fit: the share of synthetic datasets whose own best-fit KS is at least the observed one."""
    rng = np.random.default_rng(seed)
    x = x[x >= 1]
    body, n = x[x < best["xmin"]], len(x)
    p_tail = best["n_tail"] / n
    worse = done = 0
    for _ in range(boot):
        k = rng.binomial(n, p_tail)
        syn = np.concatenate([_pl_sample(rng, k, best["alpha"], best["xmin"]),
                              rng.choice(body, n - k) if len(body) and n - k else np.empty(0)])
        b = csn(syn)
        if b is not None:
            done += 1
            worse += b["ks"] >= best["ks"]
    return worse / done if done else float("nan")


def _loglik(name, v, c, xmin, start=None):
    fit_, logpmf = FAMILIES[name]
    p = fit_(v, c, xmin, start)
    return p, logpmf(p, v, xmin)


def _per_node(v, c, xmin, starts: dict | None = None) -> dict:
    """Per-node log-likelihood ratio of the better heavy tail against the negative binomial and the exponential.
    `starts`: fitted parameters to start each refit from (the bootstrap's warm start)."""
    tot = {name: float((c * _loglik(name, v, c, xmin, (starts or {}).get(name))[1]).sum())
           for name in (*HEAVY, "negative_binomial", "exponential")}
    better = max(HEAVY, key=lambda name: tot[name])
    n = c.sum()
    return {"better": better, "vs_nb": (tot[better] - tot["negative_binomial"]) / n,
            "vs_exp": (tot[better] - tot["exponential"]) / n}


def fit(degrees, boot: int = BOOT, seed: int = SEED) -> dict:
    """The LAW-1 record of one degree sequence (values < 1 are dropped)."""
    x = np.asarray(degrees, dtype=float)
    x = x[x >= 1]
    out = {"n": int(len(x)), "evaluable": False}
    best = csn(x) if len(x) >= MIN_TAIL else None
    if best is None:
        return {**out, "why": f"no x_min leaves a tail of {MIN_TAIL}"}
    xmin = float(best["xmin"])
    v, c = _counts(x[x >= xmin])
    n_tail = int(c.sum())
    params, ll = {}, {}
    for name in FAMILIES:
        params[name], ll[name] = _loglik(name, v, c, xmin)
    vuong = {}
    for alt in ("exponential", "lognormal", "stretched_exponential", "truncated_power_law"):
        d = ll["power_law"] - ll[alt]
        r = float((c * d).sum())
        mean = r / n_tail
        sd = math.sqrt(float((c * (d - mean) ** 2).sum()) / n_tail)
        vuong[alt] = {"R": r, "p": float(special.erfc(abs(r) / (math.sqrt(2 * n_tail) * sd))) if sd > 0 else 1.0}
    obs = _per_node(v, c, xmin)
    eff, better, eff_exp, better_exp = obs["vs_nb"], obs["better"], obs["vs_exp"], obs["better"]
    rng = np.random.default_rng(seed)
    tail = x[x >= xmin]
    reps, reps_exp = [], []
    for _ in range(boot):
        bv, bc = _counts(rng.choice(tail, n_tail))
        if len(bv) < 3:
            continue
        rep = _per_node(bv, bc, xmin, params)
        reps.append(rep["vs_nb"])
        reps_exp.append(rep["vs_exp"])
    gof = gof_p(x, best, boot, seed)
    alpha = params["power_law"][0]
    not_worse = all(not (vv["R"] < 0 and vv["p"] < 0.1) for vv in vuong.values())
    weak = gof >= 0.1
    frac = n_tail / len(x)
    return {**out, "evaluable": True, "xmin": int(xmin), "n_tail": n_tail, "tail_fraction": frac,
            "coverage_ok": frac >= MIN_TAIL_FRACTION, "alpha": alpha, "ks": best["ks"], "gof_p": gof,
            "params": {k: list(p) for k, p in params.items()}, "vuong_power_law_vs": vuong,
            "effect": float(eff), "se": float(np.std(reps, ddof=1)) if len(reps) > 1 else float("nan"), "better_heavy": better,
            "effect_vs_exponential": float(eff_exp), "se_vs_exponential": float(np.std(reps_exp, ddof=1)) if len(reps_exp) > 1 else float("nan"),
            "better_heavy_vs_exponential": better_exp, "boot": len(reps),
            "strength": "strong" if weak and 2 < alpha < 3 and not_worse else "weak" if weak else "none"}
