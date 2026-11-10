#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Firth-penalised logistic regression with two-way cluster-robust standard errors and average marginal effects
(methods review M7). The defect laws' per-repo model; no data is read here.

  firth(X, y)                     Firth's bias-reduced fit (Jeffreys-prior penalty): finite under separation
  cov_cluster(X, y, fit, a, b)    Cameron-Gelbach-Miller two-way covariance, V_a + V_b - V_ab; one-way with b=None
  ame(X, fit, j, binary)          the average marginal effect of column j on the probability scale
  vif(X)                          variance inflation factors of the columns (the intercept left out)
"""
from __future__ import annotations

import numpy as np


def _p(eta: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(eta, -35, 35)))


def firth(x: np.ndarray, y: np.ndarray, max_iter: int = 200, tol: float = 1e-8) -> dict:
    """Firth logistic regression of y (0/1) on the columns of x (include a constant column yourself). Returns beta,
    the model covariance, fitted probabilities, the penalised log-likelihood and whether it converged."""
    n, k = x.shape
    beta = np.zeros(k)
    conv = False

    def pieces(b):
        p = _p(x @ b)
        w = p * (1 - p)
        xtwx = (x * w[:, None]).T @ x
        inv = np.linalg.pinv(xtwx)
        h = np.einsum("ij,jk,ik->i", x, inv, x) * w  # the hat diagonal
        sign, logdet = np.linalg.slogdet(xtwx)
        ll = float(np.sum(y * np.log(np.clip(p, 1e-300, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-300, 1))))
        return p, inv, h, ll + (0.5 * logdet if sign > 0 else -1e18)

    p, inv, h, pll = pieces(beta)
    for _ in range(max_iter):
        step = inv @ (x.T @ (y - p + h * (0.5 - p)))
        t = 1.0
        while True:
            cand = beta + t * step
            p_c, inv_c, h_c, pll_c = pieces(cand)
            if pll_c >= pll - 1e-10 or t < 1e-6:
                break
            t /= 2
        done = np.max(np.abs(cand - beta)) < tol
        beta, p, inv, h, pll = cand, p_c, inv_c, h_c, pll_c
        if done:
            conv = True
            break
    return {"beta": beta, "cov": inv, "p": p, "pll": pll, "converged": conv and bool(np.all(np.isfinite(beta)))}


def _meat(scores: np.ndarray, cluster: np.ndarray) -> tuple[np.ndarray, int]:
    _, inv = np.unique(cluster, return_inverse=True)
    g = int(inv.max()) + 1
    s = np.zeros((g, scores.shape[1]))
    np.add.at(s, inv, scores)
    return s.T @ s * (g / (g - 1) if g > 1 else 1.0), g


def cov_cluster(x: np.ndarray, y: np.ndarray, fit: dict, a: np.ndarray, b: np.ndarray | None = None) -> dict:
    """Sandwich covariance clustered by `a`, or two-way by `a` and `b` (V_a + V_b - V_ab). `ok` is False when a
    two-way variance on the diagonal is not positive (then use a cluster bootstrap, as M7 says)."""
    scores = x * (y - fit["p"])[:, None]
    bread = fit["cov"]
    ma, ga = _meat(scores, a)
    v = bread @ ma @ bread
    info = {"clusters_a": ga}
    if b is not None:
        mb, gb = _meat(scores, b)
        both = np.unique(np.stack([np.unique(a, return_inverse=True)[1], np.unique(b, return_inverse=True)[1]], axis=1),
                         axis=0, return_inverse=True)[1]
        mab, _ = _meat(scores, both)
        v = v + bread @ mb @ bread - bread @ mab @ bread
        info["clusters_b"] = gb
    return {"cov": v, "ok": bool(np.all(np.diag(v) > 0)), **info}


def ame(x: np.ndarray, fit: dict, j: int, binary: bool = False) -> float:
    """Average marginal effect of column j: for a binary column the mean of p(x_j = 1) - p(x_j = 0); else the mean of
    p (1 - p) beta_j (per unit of the column: standardise the column first for "per SD")."""
    b = fit["beta"]
    if not binary:
        p = fit["p"]
        return float(np.mean(p * (1 - p)) * b[j])
    x1, x0 = x.copy(), x.copy()
    x1[:, j], x0[:, j] = 1.0, 0.0
    return float(np.mean(_p(x1 @ b) - _p(x0 @ b)))


def vif(x: np.ndarray) -> list[float]:
    """Variance inflation factor of each non-constant column (NaN for a constant one)."""
    out = []
    for j in range(x.shape[1]):
        if np.ptp(x[:, j]) == 0:
            out.append(float("nan"))
            continue
        others = np.delete(x, j, axis=1)
        if not np.any(np.ptp(others, axis=0) == 0):
            others = np.column_stack([np.ones(len(x)), others])
        resid = x[:, j] - others @ np.linalg.lstsq(others, x[:, j], rcond=None)[0]
        tss = float(np.sum((x[:, j] - x[:, j].mean()) ** 2))
        r2 = 1 - float(resid @ resid) / tss if tss > 0 else 0.0
        out.append(1 / (1 - r2) if r2 < 1 else float("inf"))
    return out
