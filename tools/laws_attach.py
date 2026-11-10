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
    clogit(X, y, cluster)  conditional logit by Newton steps, cluster-robust covariance
    fit(nets)              the LAW-2 record of one repo

Not here yet: the function-fixed-effects sensitivity ("beyond fitness") and the PAFit cross-check.
"""
from __future__ import annotations

import math
from pathlib import PurePosixPath

import numpy as np

SEED = 2982
N_ALT = 50
FEATURES = ("log_k", "same_file", "same_dir", "log_loc", "log_age")
MIN_CHOICES = 200  # fewer new edges than this in a repo's whole history: not evaluable
MIN_QUARTERS = 8  # clusters needed for a clustered standard error


def choices(nets: list, seed: int = SEED, n_alt: int = N_ALT) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """X (n_choices, n_alt + 1, n_features) with the chosen target in column 0; cluster (n_choices,) the index of the
    quarter; and n_candidates (n_choices,) the number of persisting functions the target was chosen among."""
    rng = np.random.default_rng(seed)
    born: dict = {}
    for q, net in enumerate(nets):
        for node in net.nodes:
            born.setdefault(node, q)
    xs, cl, nc = [], [], []
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
    if not xs:
        return np.empty((0, n_alt + 1, len(FEATURES))), np.empty(0, dtype=int), np.empty(0, dtype=int)
    return np.stack(xs), np.array(cl), np.array(nc)


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
