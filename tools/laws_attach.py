#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAW-2, preferential attachment (docs/laws_hypotheses.md; methods review M5): each new call edge as a choice.

Between two consecutive quarterly snapshots t and t + 1, every edge u -> v that is new at t + 1 and whose target v
exists at both is one choice among the functions that persist, the caller u itself left out (a function is never
its own target): the chosen v and N_ALT uniformly sampled others (sampling the alternatives uniformly leaves the
conditional-logit estimates consistent). Utility:

    alpha * log(k_v + 1) + b1 * same_file(u, v) + b2 * same_directory(u, v) + b3 * log(LOC_v) + b4 * log(1 + age_v)

with k_v the in-degree of v at t, LOC_v at t and age_v in quarters since v first appeared. The per-repo effect is
alpha-hat with a standard error clustered by quarter (sandwich); margin 0.

    choices(nets)          the choice sets of a repo, from its ordered tools/laws_net.Net list
    fit_fixed_effects(nets) alpha with a fixed effect per frequent target (biased at this data size: see below)
    fitness_null(nets)     alpha against a fitness-only null -- the sensitivity that actually works
    kernel(nets)           the attachment kernel measured non-parametrically: a check on its shape
    clogit(X, y, cluster)  conditional logit by Newton steps, cluster-robust covariance
    fit(nets)              the LAW-2 record of one repo

The function-fixed-effects sensitivity ("beyond fitness") is `fit_fixed_effects`, and `kernel` is a
non-parametric check on the kernel's shape. PAFit proper -- the joint Bayesian kernel-and-fitness estimate --
is still owed; `kernel` is the cheaper Jeong-Neda-Barabasi measurement and controls for nothing.
"""
from __future__ import annotations

import math
from pathlib import PurePosixPath

import numpy as np
from scipy import optimize

import laws_net as N_MOD

SEED = 2982
N_ALT = 50
FEATURES = ("log_k", "same_file", "same_dir", "log_loc", "log_age")
MIN_CHOICES = 200  # fewer new edges than this in a repo's whole history: not evaluable
MIN_QUARTERS = 8  # clusters needed for a clustered standard error
MIN_FE_APPEAR = 2  # a target chosen fewer times than this carries a level, not a slope: it is pooled
FE_RIDGE = 1.0
RIDGES = (0.1, 1.0, 10.0)
FE_BOOT = 40  # quarters resampled for alpha_fe's SE; coarse, and reported as such
FITNESS_REPS = 100  # simulated fitness-only histories (Amendment 5 raised this from 50)
FITNESS_EPS = 0.5  # a target that never took an edge still has some propensity


def choices(nets: list, seed: int = SEED, n_alt: int = N_ALT, with_ids: bool = False):
    """X (n_choices, n_alt + 1, n_features) with the chosen target in column 0; cluster (n_choices,) the index of the
    quarter; and n_candidates (n_choices,) the number of persisting functions the target was chosen among.

    `with_ids` adds a fourth return: ids (n_choices, n_alt + 1), the index of the function in each cell within a
    repo-wide node index. The fixed-effects sensitivity needs to know WHICH function each cell is, which the
    feature matrix alone does not say."""
    rng = np.random.default_rng(seed)
    born: dict = {}
    for q, net in enumerate(nets):
        for node in net.nodes:
            born.setdefault(node, q)
    xs, cl, nc, idx_rows = [], [], [], []
    node_id: dict = {}
    for q in range(len(nets) - 1):
        a, b = nets[q], nets[q + 1]
        if a.sha == b.sha:
            continue  # a quarter with no commit
        persist = [n for n in a.nodes if n in b.nodes]
        if len(persist) <= n_alt + 2:
            continue
        index = {n: i for i, n in enumerate(persist)}
        indeg = a.in_degree()
        k = np.array([indeg.get(n, 0) for n in persist], dtype=float)
        loc = np.array([max(1, a.nodes[n]["loc"]) for n in persist], dtype=float)
        age = np.array([q - born[n] for n in persist], dtype=float)
        files = np.array([hash(n[0]) for n in persist])
        dirs = np.array([hash(str(PurePosixPath(n[0]).parent)) for n in persist])
        base = np.stack([np.log(k + 1), np.zeros(len(persist)), np.zeros(len(persist)), np.log(loc), np.log1p(age)], axis=1)
        for u, v in sorted(b.edges - a.edges):
            if v not in index:
                continue
            iv, iu = index[v], index.get(u)
            skip = sorted({iv} if iu is None else {iv, iu})
            alt = rng.choice(len(persist) - len(skip), n_alt, replace=False)
            for gone in skip:  # every persisting function but v and the caller, uniformly
                alt = alt + (alt >= gone)
            rows = np.concatenate(([iv], alt))
            x = base[rows].copy()
            x[:, 1] = files[rows] == hash(u[0])
            x[:, 2] = dirs[rows] == hash(str(PurePosixPath(u[0]).parent))
            xs.append(x)
            cl.append(q)
            nc.append(len(persist))
            if with_ids:
                idx_rows.append([node_id.setdefault(persist[r], len(node_id)) for r in rows])
    if not xs:
        empty = (np.empty((0, n_alt + 1, len(FEATURES))), np.empty(0, dtype=int), np.empty(0, dtype=int))
        return (*empty, np.empty((0, n_alt + 1), dtype=int)) if with_ids else empty
    out = (np.stack(xs), np.array(cl), np.array(nc))
    return (*out, np.array(idx_rows, dtype=int)) if with_ids else out


def clogit(x: np.ndarray, cluster: np.ndarray, max_iter: int = 100, tol: float = 1e-9) -> dict:
    """Conditional logit where the chosen alternative is column 0 of x (n, J, p). Returns beta, the model-based and
    the cluster-robust covariance, the log-likelihood and whether Newton converged."""
    n, _, p = x.shape

    def parts(b):
        eta = x @ b
        m = eta.max(axis=1, keepdims=True)
        e = np.exp(eta - m)
        tot = e.sum(axis=1, keepdims=True)
        w = e / tot
        ll = float((eta[:, 0] - m[:, 0] - np.log(tot[:, 0])).sum())
        xbar = np.einsum("nj,njp->np", w, x)
        return ll, w, xbar

    beta = np.zeros(p)
    ll, w, xbar = parts(beta)
    conv = False
    for _ in range(max_iter):
        score = (x[:, 0, :] - xbar).sum(axis=0)
        hess = np.einsum("nj,njp,njq->pq", w, x, x) - xbar.T @ xbar
        step = np.linalg.solve(hess + 1e-8 * np.eye(p), score)
        t = 1.0
        while True:  # step halving: a Newton step is taken only as far as it raises the likelihood
            cand = beta + t * step
            ll_new, w_new, xbar_new = parts(cand)
            if ll_new >= ll - 1e-12 or t < 1e-8:
                break
            t /= 2
        done = np.max(np.abs(cand - beta)) < tol or abs(ll_new - ll) < tol * (abs(ll) + 1)
        beta, ll, w, xbar = cand, ll_new, w_new, xbar_new
        if done:
            conv = bool(np.all(np.isfinite(beta)))
            break
    hess = np.einsum("nj,njp,njq->pq", w, x, x) - xbar.T @ xbar
    bread = np.linalg.inv(hess + 1e-10 * np.eye(p))
    s = x[:, 0, :] - xbar
    groups = np.unique(cluster)
    g = len(groups)
    meat = np.zeros((p, p))
    for c in groups:
        sc = s[cluster == c].sum(axis=0)
        meat += np.outer(sc, sc)
    robust = bread @ meat @ bread * (g / (g - 1) if g > 1 else 1.0)
    return {"beta": beta, "cov_model": bread, "cov_cluster": robust, "loglik": ll, "converged": conv, "clusters": int(g)}


def clogit_fe(x: np.ndarray, ids: np.ndarray, cluster: np.ndarray, fe_of: np.ndarray, n_fe: int,
              ridge: float = FE_RIDGE, max_iter: int = 500) -> dict:
    """Conditional logit with a fixed effect per frequent target, by L-BFGS on the ridge-penalised likelihood.

        eta[n, j] = x[n, j, :] @ beta + fe[fe_of[ids[n, j]]]

    `fe_of` maps a node index to its fixed-effect slot, with slot 0 the pooled baseline held at 0 (every target
    too rare to carry its own effect shares it). alpha is then identified only by variation in a target's OWN
    k over time -- which is the point: it cannot be explained by that target being permanently attractive.

    A ridge penalty on fe is not optional. A target that is sampled as an alternative but never chosen drives
    its own effect to minus infinity, so the unpenalised likelihood has no interior maximum. The penalty is
    reported and `fit_fixed_effects` runs it at several values so the reading does not hinge on one."""
    n, j, pdim = x.shape
    slots = fe_of[ids]                                     # (n, J) the fe slot of every cell
    chosen_counts = np.bincount(slots[:, 0], minlength=n_fe)

    def nll_grad(theta):
        beta, fe = theta[:pdim], np.concatenate(([0.0], theta[pdim:]))
        eta = x @ beta + fe[slots]
        m = eta.max(axis=1, keepdims=True)
        e = np.exp(eta - m)
        tot = e.sum(axis=1, keepdims=True)
        w = e / tot
        ll = float((eta[:, 0] - m[:, 0] - np.log(tot[:, 0])).sum()) - 0.5 * ridge * float(fe[1:] @ fe[1:])
        g_beta = (x[:, 0, :] - np.einsum("nj,njp->np", w, x)).sum(axis=0)
        expected = np.bincount(slots.ravel(), weights=w.ravel(), minlength=n_fe)
        g_fe = chosen_counts - expected - ridge * fe
        return -ll, -np.concatenate((g_beta, g_fe[1:]))

    theta0 = np.zeros(pdim + n_fe - 1)
    r = optimize.minimize(nll_grad, theta0, jac=True, method="L-BFGS-B",
                          options={"maxiter": max_iter, "maxfun": max_iter * 2})
    return {"beta": r.x[:pdim], "fe": np.concatenate(([0.0], r.x[pdim:])), "loglik": float(-r.fun),
            "converged": bool(r.success), "iterations": int(r.nit), "ridge": ridge, "n_fe": int(n_fe)}


def _fe_slots(ids: np.ndarray, min_appear: int = MIN_FE_APPEAR) -> tuple[np.ndarray, int, int]:
    """(fe_of, n_fe, n_targets_with_own_effect). A target chosen at least `min_appear` times gets its own slot;
    the rest share slot 0, because a target chosen once carries a level and no slope."""
    n_nodes = int(ids.max()) + 1 if ids.size else 0
    chosen = np.bincount(ids[:, 0], minlength=n_nodes)
    own = np.flatnonzero(chosen >= min_appear)
    fe_of = np.zeros(n_nodes, dtype=int)
    fe_of[own] = np.arange(1, len(own) + 1)
    return fe_of, len(own) + 1, len(own)


def fit_fixed_effects(nets: list, seed: int = SEED, ridges: tuple = RIDGES, boot: int = FE_BOOT) -> dict:
    """LAW-2's "beyond fitness" sensitivity: alpha with a fixed effect per frequent target.

    Without it, alpha conflates preferential attachment with fitness heterogeneity -- an intrinsically useful
    function is both already-called and keeps attracting calls. With a target fixed effect, the only thing left
    to identify alpha is whether the SAME target is chosen more often when its own in-degree is higher.

    Not registered in this form. The ridge penalty, the `min_appear` cut and the quarter bootstrap are choices
    this module makes and reports; they belong in the scorer-freeze amendment.
    """
    x, cl, nc, ids = choices(nets, seed, with_ids=True)
    out = {"choices": int(len(x)), "evaluable": False}
    if len(x) < MIN_CHOICES or len(np.unique(cl)) < MIN_QUARTERS:
        return {**out, "why": f"needs {MIN_CHOICES} new edges in {MIN_QUARTERS} quarters"}
    keep = [j for j in range(len(FEATURES)) if np.ptp(x[:, :, j]) > 0]
    names = [FEATURES[j] for j in keep]
    if "log_k" not in names:
        return {**out, "why": "log(k + 1) never varies"}
    xk = x[:, :, keep]
    a = names.index("log_k")
    fe_of, n_fe, n_own = _fe_slots(ids)
    out.update(targets_with_own_effect=n_own, targets_pooled=int((fe_of == 0).sum()) - 0,
               min_appear=MIN_FE_APPEAR)
    if n_own < 2:
        return {**out, "why": "fewer than 2 targets are chosen more than once: no within-target variation"}
    plain = clogit(xk, cl)
    by_ridge = {}
    for lam in ridges:
        r = clogit_fe(xk, ids, cl, fe_of, n_fe, ridge=lam)
        by_ridge[str(lam)] = {"alpha": float(r["beta"][a]), "converged": r["converged"],
                              "loglik": r["loglik"], "iterations": r["iterations"]}
    mid = clogit_fe(xk, ids, cl, fe_of, n_fe, ridge=ridges[len(ridges) // 2])
    reps = []
    if boot:
        rng = np.random.default_rng(seed)
        qs = np.unique(cl)
        for _ in range(boot):
            pick = rng.choice(qs, len(qs), replace=True)
            rows = np.concatenate([np.flatnonzero(cl == q) for q in pick])
            f2, nf2, own2 = _fe_slots(ids[rows])
            if own2 < 2:
                continue
            rb = clogit_fe(xk[rows], ids[rows], cl[rows], f2, nf2, ridge=ridges[len(ridges) // 2])
            if rb["converged"]:
                reps.append(rb["beta"][a])
    return {**out, "evaluable": True,
            "alpha_plain": float(plain["beta"][a]),
            "se_plain": float(np.sqrt(np.diag(plain["cov_cluster"])[a])),
            "alpha_fe": float(mid["beta"][a]),
            "se_fe": float(np.std(reps, ddof=1)) if len(reps) > 1 else float("nan"),
            "boot": len(reps), "ridge_used": ridges[len(ridges) // 2], "by_ridge": by_ridge,
            "survives": bool(mid["beta"][a] > 0 and (not reps or float(np.std(reps, ddof=1)) == 0
                                                     or mid["beta"][a] > 2 * float(np.std(reps, ddof=1))))}


def fitness_null(nets: list, seed: int = SEED, reps: int = FITNESS_REPS) -> dict:
    """LAW-2 against a fitness-only null: the sensitivity that `fit_fixed_effects` cannot deliver.

    The question is whether alpha reflects preferential attachment or mere fitness heterogeneity -- an
    intrinsically useful function is both already-called and keeps attracting calls. A fixed effect per target
    is the textbook answer and it does not work at this data size (see `fit_fixed_effects`: with about seven
    choices per fixed effect the estimator carries a bias near -0.8 and cannot tell true attachment from pure
    fitness). A null model can, and it is the idiom LAW-3, LAW-4 and LAW-5 already use.

    The null keeps everything the observed history has except the timing. Each target's propensity is fixed at
    its OBSERVED total intake of new edges over the whole history -- a fitness that by construction reproduces
    who ends up popular -- and the same callers make the same number of choices in the same quarters, with the
    target redrawn from that fitness. Under the null a target's chance never depends on its degree *now*, only
    on how attractive it turns out to be overall. alpha is then re-estimated on each simulated history with the
    same estimator, which is unbiased (its calibration is in the module's tests), and the observed alpha is
    read against that distribution.

    So a positive alpha is evidence of attachment only if it exceeds what pure fitness produces. On the pilot's
    own synthetic check, fitness alone yields alpha about 1.09 -- more than a true attachment exponent of 1.0 --
    which is exactly why this comparison is needed rather than a test against zero.

    Amendment 5 makes this excess LAW-2's registered effect, with margin 0 in the positive direction and
    v = se_observed^2 + sd(alpha_null)^2; alpha itself stays descriptive. R is raised to FITNESS_REPS so the
    rank p is not floored, though the rank p is reported rather than used.

    The null draws ignore same-file and same-directory locality, so a simulated history has no locality signal
    while the real one does; both are estimated with the same controls in the model. Not registered in this
    form: it belongs in the scorer-freeze amendment.
    """
    events: list = []
    for q in range(len(nets) - 1):
        a, b = nets[q], nets[q + 1]
        if a.sha == b.sha:
            continue
        persist = set(a.nodes) & set(b.nodes)
        for u, v in sorted(b.edges - a.edges):
            if v in persist:
                events.append((q, u, v))
    out = {"events": len(events), "reps": 0, "evaluable": False}
    if len(events) < MIN_CHOICES:
        return {**out, "why": f"fewer than {MIN_CHOICES} new edges to persisting targets"}
    observed = fit(nets, seed)
    if not observed.get("evaluable"):
        return {**out, "why": f"the observed fit is not evaluable: {observed.get('why')}"}
    intake: dict = {}
    for _, _, v in events:
        intake[v] = intake.get(v, 0) + 1
    by_quarter: dict = {}
    for q, u, v in events:
        by_quarter.setdefault(q, []).append(u)
    rng = np.random.default_rng(seed)
    alphas = []
    for _ in range(reps):
        sim_edges = set(nets[0].edges)
        sim = [nets[0]]
        for q in range(len(nets) - 1):
            a, b = nets[q], nets[q + 1]
            nxt = N_MOD.Net(b.sha, b.date)
            nxt.nodes = b.nodes
            if a.sha != b.sha and q in by_quarter:
                persist = [n for n in a.nodes if n in b.nodes]
                w0 = np.array([intake.get(n, 0) + FITNESS_EPS for n in persist], dtype=float)
                index = {n: i for i, n in enumerate(persist)}
                for u in by_quarter[q]:
                    w = w0.copy()
                    if (iu := index.get(u)) is not None:
                        w[iu] = 0.0           # never itself, as in the observed data
                    if w.sum() <= 0:
                        continue
                    sim_edges.add((u, persist[rng.choice(len(persist), p=w / w.sum())]))
            nxt.edges = set(sim_edges)
            sim.append(nxt)
        r = fit(sim, seed)
        if r.get("evaluable"):
            alphas.append(r["effect"])
    if len(alphas) < max(5, reps // 2):
        return {**out, "reps": len(alphas), "why": "too few simulated histories produced an evaluable fit"}
    arr = np.array(alphas)
    p_val = float((np.sum(arr >= observed["effect"]) + 1) / (len(arr) + 1))
    return {**out, "evaluable": True, "reps": len(arr),
            "alpha_observed": observed["effect"], "se_observed": observed["se"],
            "alpha_null_mean": float(arr.mean()), "alpha_null_sd": float(arr.std(ddof=1)),
            "alpha_null_q": [float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))],
            "excess": float(observed["effect"] - arr.mean()),
            # Amendment 5: the excess is LAW-2's effect, and this is the variance the synthesis pools. The
            # observed alpha's own uncertainty and the null's spread both bear on whether the gap is real.
            "se_excess": float(math.sqrt(observed["se"] ** 2 + arr.var(ddof=1))), "p": p_val,
            "beyond_fitness": bool(p_val < 0.05)}


def kernel(nets: list, seed: int = SEED, min_exposure: int = 5) -> dict:
    """The attachment kernel A(k) measured non-parametrically, and whether log A is straight in log(k + 1).

        A(k)  proportional to  (new edges whose target had in-degree k)  /  (functions with in-degree k)

    pooled over quarter transitions, then log A regressed on log(k + 1) weighted by the new-edge count; a
    quadratic term tests the shape. This is the Jeong-Neda-Barabasi style measurement, NOT PAFit: it controls
    for nothing, so size and locality inflate its slope and it is not a rival estimate of alpha. Its job is the
    functional form -- `clogit` assumes probability proportional to (k + 1)^alpha, and a curved log A says that
    assumption is wrong. PAFit proper (the joint Bayesian kernel-and-fitness estimate) is still owed.
    """
    new: dict = {}
    exposure: dict = {}
    for q in range(len(nets) - 1):
        a, b = nets[q], nets[q + 1]
        if a.sha == b.sha:
            continue
        persist = [n for n in a.nodes if n in b.nodes]
        if len(persist) < 3:
            continue
        indeg = a.in_degree()
        for n in persist:
            k = int(indeg.get(n, 0))
            exposure[k] = exposure.get(k, 0) + 1
        pset = set(persist)
        for u, v in b.edges - a.edges:
            if v in pset:
                k = int(indeg.get(v, 0))
                new[k] = new.get(k, 0) + 1
    ks = sorted(k for k in exposure if exposure[k] >= min_exposure and new.get(k, 0) > 0)
    out = {"degrees": len(ks), "evaluable": False,
           "total_new": int(sum(new.values())), "total_exposure": int(sum(exposure.values()))}
    if len(ks) < 4:
        return {**out, "why": "fewer than 4 degrees with enough exposure and at least one new edge"}
    k = np.array(ks, dtype=float)
    rate = np.array([new[int(x)] / exposure[int(x)] for x in k])
    wt = np.array([new[int(x)] for x in k], dtype=float)
    lk, la = np.log(k + 1), np.log(rate)
    design1 = np.column_stack([np.ones(len(k)), lk])
    design2 = np.column_stack([design1, lk ** 2])
    sw = np.sqrt(wt)
    b1, *_ = np.linalg.lstsq(design1 * sw[:, None], la * sw, rcond=None)
    b2, *_ = np.linalg.lstsq(design2 * sw[:, None], la * sw, rcond=None)
    resid1 = la - design1 @ b1
    ss = float(np.sum(wt * (la - np.average(la, weights=wt)) ** 2))
    return {**out, "evaluable": True, "slope": float(b1[1]), "curvature": float(b2[2]),
            "r2_loglinear": float(1 - np.sum(wt * resid1 ** 2) / ss) if ss > 0 else float("nan"),
            "k_range": [int(k.min()), int(k.max())],
            "note": "confounded by size and locality; a check on the kernel's shape, not a rival alpha"}


def fit(nets: list, seed: int = SEED) -> dict:
    """The LAW-2 record of one repo: alpha-hat (the coefficient of log(k + 1)) and its clustered SE."""
    x, cl, nc = choices(nets, seed)
    out = {"choices": int(len(x)), "quarters_with_new_edges": int(len(np.unique(cl))), "evaluable": False}
    if len(x) < MIN_CHOICES or len(np.unique(cl)) < MIN_QUARTERS:
        return {**out, "why": f"needs {MIN_CHOICES} new edges in {MIN_QUARTERS} quarters"}
    keep = [j for j in range(len(FEATURES)) if np.ptp(x[:, :, j]) > 0]  # a feature that never varies has no coefficient
    r = clogit(x[:, :, keep], cl)
    names = [FEATURES[j] for j in keep]
    se = np.sqrt(np.diag(r["cov_cluster"]))
    coef = {nm: {"b": float(b), "se": float(s), "se_model": float(sm)}
            for nm, b, s, sm in zip(names, r["beta"], se, np.sqrt(np.diag(r["cov_model"])))}
    if "log_k" not in coef or not r["converged"] or not math.isfinite(coef["log_k"]["se"]):
        return {**out, "why": "the model did not converge or log(k + 1) never varies", "coefficients": coef}
    return {**out, "evaluable": True, "effect": coef["log_k"]["b"], "se": coef["log_k"]["se"], "coefficients": coef,
            "loglik": r["loglik"], "median_candidates": float(np.median(nc)), "n_alt": N_ALT}
