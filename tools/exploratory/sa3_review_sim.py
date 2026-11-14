#!/usr/bin/env python3
"""Synthetic check of SA3's statistic. No real data. y depends on LOC (and, in 'alt' runs, on a file trait)."""
import sys, json
import numpy as np
from scipy.stats import rankdata

rng = np.random.default_rng(20261113)


def bands_of(loc, k):
    order = np.argsort(loc, kind="stable")
    b = np.empty(len(loc), int)
    b[order] = (np.arange(len(loc)) * k) // len(loc)
    return b


def sauc(x, y, b, k):
    num = den = 0.0
    for j in range(k):
        m = b == j
        yy = y[m]
        p = yy.sum(); n = len(yy) - p
        if p == 0 or n == 0:
            continue
        r = rankdata(x[m])
        num += r[yy == 1].sum() - p * (p + 1) / 2
        den += p * n
    return num / den if den else np.nan


def resid_within(x, lg, b, k):
    """rank-normalise x within band, remove its within-band linear fit on log LOC"""
    out = np.zeros(len(x))
    for j in range(k):
        m = b == j
        r = rankdata(x[m]); r = (r - r.mean()) / (r.std() + 1e-12)
        l = lg[m] - lg[m].mean()
        beta = (r * l).sum() / ((l * l).sum() + 1e-12)
        out[m] = r - beta * l
    return out


def logit_beta(x, lg, y, b, k):
    """y ~ band FE + log LOC + z(x); returns beta_x / se (Wald z) and beta"""
    z = (x - x.mean()) / (x.std() + 1e-12)
    X = np.zeros((len(x), k + 2))
    X[np.arange(len(x)), b] = 1
    X[:, k] = lg - lg.mean(); X[:, k + 1] = z
    keep = [j for j in range(k) if 0 < y[b == j].sum() < (b == j).sum()]
    rows = np.isin(b, keep)
    X = X[rows][:, keep + [k, k + 1]]; yy = y[rows]
    w = np.zeros(X.shape[1])
    for _ in range(30):
        eta = np.clip(X @ w, -30, 30); p = 1 / (1 + np.exp(-eta))
        W = p * (1 - p) + 1e-9
        H = X.T @ (X * W[:, None]) + 1e-6 * np.eye(X.shape[1])
        step = np.linalg.solve(H, X.T @ (yy - p))
        w += step
        if np.abs(step).max() < 1e-7:
            break
    cov = np.linalg.inv(H)
    return w[-1], w[-1] / np.sqrt(cov[-1, -1])


def make(n, prev, sigma, slope, kind, c=0.0):
    lg = rng.normal(5.0, sigma, n)
    loc = np.exp(lg)
    trait = rng.normal(0, 1, n)            # a file trait independent of LOC (its "density")
    if kind == "noisy_size_hi":
        x = lg + rng.normal(0, 0.45 * sigma, n)
    elif kind == "noisy_size_lo":
        x = lg + rng.normal(0, 1.3 * sigma, n)
    elif kind == "count":                  # e.g. branch keywords: Poisson(LOC * density)
        x = rng.poisson(loc * 0.12 * np.exp(0.6 * trait)).astype(float)
    elif kind == "sparse_count":           # mostly zero
        x = rng.poisson(loc * 0.002 * np.exp(1.0 * trait)).astype(float)
    elif kind == "score":                  # 0-100 density score; exactly 0 when no "attack" hit (small files)
        hits = rng.poisson(loc * 0.01 * np.exp(0.6 * trait))
        net = 0.05 * trait * loc / (loc + 20) + rng.normal(0, 0.02, n)
        x = np.where(hits > 0, 100 / (1 + np.exp(-4 * net)), 0.0)
    elif kind == "noise":
        x = rng.normal(0, 1, n)
    else:
        raise ValueError(kind)
    lin = slope * (lg - 5.0) + c * trait
    lo, hi = -20.0, 20.0                   # calibrate intercept to the prevalence
    for _ in range(40):
        a = (lo + hi) / 2
        if (1 / (1 + np.exp(-(a + lin)))).mean() > prev:
            hi = a
        else:
            lo = a
    y = (rng.random(n) < 1 / (1 + np.exp(-(a + lin)))).astype(int)
    return loc, lg, x, y


def stats(n, prev, sigma, slope, kind, c, k=None):
    loc, lg, x, y = make(n, prev, sigma, slope, kind, c)
    if k is None:
        k = 10 if n >= 300 else 5
    b = bands_of(loc, k)
    sx, sl = sauc(x, y, b, k), sauc(loc, y, b, k)
    s2 = sauc(resid_within(x, lg, b, k), y, b, k)
    g = np.log1p(x) if kind in ("count", "sparse_count") else x
    beta, z = logit_beta(g, lg, y, b, k)
    return sx - sl, sx - 0.5, s2 - 0.5, beta, z, sl


def cell(n, prev, sigma, slope, kind, c, reps, k=None):
    r = np.array([stats(n, prev, sigma, slope, kind, c, k) for _ in range(reps)])
    return r


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "grid":   # one repo, repeated: mean of each statistic under the NULL (c=0)
        print("NULL (y depends on LOC only). mean over reps of: S0 registered = sAUC(x)-sAUC(LOC); S1 = sAUC(x)-0.5; "
              "S2 = sAUC(resid)-0.5; S3 = logistic beta (z); and sAUC(LOC)")
        print(f"{'kind':15}{'n':>6}{'prev':>6}{'sig':>5}{'k':>4}{'S0':>9}{'S1':>9}{'S2':>9}{'S3beta':>9}{'|z|>1.96':>9}{'sAUC(LOC)':>10}")
        for kind in ("noise", "noisy_size_hi", "noisy_size_lo", "count", "sparse_count", "score"):
            for (n, prev, sigma, k) in ((250, 0.15, 1.2, 5), (320, 0.15, 1.2, 10), (320, 0.15, 1.2, 5), (1000, 0.15, 1.2, 10),
                                         (1000, 0.15, 1.2, 5), (1000, 0.15, 1.2, 20), (1000, 0.04, 1.2, 10), (1000, 0.40, 1.2, 10),
                                         (1000, 0.15, 0.8, 10), (1000, 0.15, 1.8, 10), (6000, 0.15, 1.2, 10)):
                r = cell(n, prev, sigma, 0.9, kind, 0.0, 300, k)
                print(f"{kind:15}{n:>6}{prev:>6}{sigma:>5}{k:>4}{np.nanmean(r[:,0]):>+9.4f}{np.nanmean(r[:,1]):>+9.4f}"
                      f"{np.nanmean(r[:,2]):>+9.4f}{np.nanmean(r[:,3]):>+9.3f}{np.mean(np.abs(r[:,4])>1.96):>9.3f}{np.nanmean(r[:,5]):>10.4f}", flush=True)
    if mode == "study":  # the cross-repo test: R repos with the real (n, positives) mix; mean effect; normal-approx CI over repos
        mix = json.loads(sys.argv[2])   # [[n, pos], ...]
        reps = int(sys.argv[3])
        print(f"repos {len(mix)}; reps {reps}. Columns: mean of the study-mean, and share of studies whose 95% CI over repos "
              "lies wholly ABOVE / BELOW zero (97.5% CI in brackets for the Holm-first test)")
        for c in (0.0, 0.15, 0.3, 0.5):
            for kind in ("noise", "noisy_size_hi", "count", "sparse_count", "score"):
                if c and kind in ("noise", "noisy_size_hi"):
                    continue
                res = {s: [] for s in ("S0", "S1", "S2", "S3")}
                for _ in range(reps):
                    per = np.array([stats(n, p / n, 1.2, 0.9, kind, c)[:4] for n, p in mix])
                    for i, s in enumerate(("S0", "S1", "S2", "S3")):
                        v = per[:, i]; v = v[~np.isnan(v)]
                        res[s].append((v.mean(), v.std(ddof=1) / np.sqrt(len(v))))
                line = f"c={c:<5}{kind:14}"
                for s in ("S0", "S1", "S2", "S3"):
                    a = np.array(res[s]); m, se = a[:, 0], a[:, 1]
                    line += (f" | {s} mean {m.mean():+.4f} up {np.mean(m-1.96*se>0):.2f}[{np.mean(m-2.24*se>0):.2f}]"
                             f" dn {np.mean(m+1.96*se<0):.2f}")
                print(line, flush=True)
