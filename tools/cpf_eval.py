#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""CPF-F/V/R/N (docs/cpf_hypotheses.md): does a file's comment profile predict its next year of fixes beyond size,
churn and fix history? Reads the per-file profiles written by tools/comment_profiles.py; joins them to fix labels
(chg_eval.fix_events) for the first time here. Plain numpy/scipy (no engine needed):

    python tools/cpf_eval.py --profiles <scratch>/comment_profiles.json.gz      # -> docs/cpf.md
"""
from __future__ import annotations

import argparse
import bisect
import datetime as dt
import gzip
import json
import multiprocessing
import pathlib
import subprocess
import sys
import time
from collections import Counter, defaultdict

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import rankdata

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402
from chg2_eval import select  # noqa: E402
from chg_eval import fix_events  # noqa: E402
from comment_profiles import EXCL  # noqa: E402

CORE = ("curl", "openssl", "ndpi", "harfbuzz", "libarchive")
CVE_REPOS = ("curl", "openssl", "ndpi", "harfbuzz")
UNSEEN = ("libgit2", "libxml2", "postgres", "redis")
SEED, ITERS = 2982, 2000
ALPHA = 0.01 / 4
YEAR = 365.25 * 86400
CGRID = np.logspace(-3, 2, 11)
NFOLD = 5
NULL_BAND = 0.02
P_COLS = ("density", "header_cov", "danger_share", "debt_kloc", "dead_kloc")
P_SCALE = (10, 1, 10, 1, 1)
B_COLS = ("log_code", "prior_fix", "churn", "age", "prior_cve")
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:6.0f}s] {m}", flush=True)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True).stdout.decode("utf-8", "replace")


def touched(t):
    r, sha, ct, klass = t
    out = git(POOL_DIR / r, "diff", "--name-only", "--no-renames", f"{sha}^", sha)
    return r, ct, klass, [p for p in out.splitlines() if p]


def commits(r):
    """(ct, files) for every non-merge commit (churn)."""
    out, ct = [], None
    files = []
    for ln in git(POOL_DIR / r, "log", "--no-merges", "--format=@%ct", "--name-only", "HEAD").splitlines():
        if ln.startswith("@"):
            if ct is not None:
                out.append((ct, files))
            ct, files = int(ln[1:]), []
        elif ln:
            files.append(ln)
    if ct is not None:
        out.append((ct, files))
    return r, out


# ------------------------------------------------------------------ models (as dcs_eval)
def auc(y, s):
    n1 = y.sum()
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return np.nan
    r = rankdata(s)
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def fit_logit(X, y, C):
    def f(w):
        z = X @ w[1:] + w[0]
        pr = expit(z)
        g = np.r_[np.sum(pr - y), X.T @ (pr - y)]
        g[1:] += w[1:] / C
        return np.sum(np.logaddexp(0, z) - y * z) + 0.5 * np.sum(w[1:] ** 2) / C, g
    return minimize(f, np.zeros(X.shape[1] + 1), jac=True, method="L-BFGS-B", options={"maxiter": 10000}).x


def scaler(X):
    mu, sd = X.mean(0), X.std(0)
    return mu, np.where(sd > 0, sd, 1.0)


def fit_model(X, y, groups):
    ug = np.unique(groups)
    perm = np.random.default_rng(SEED).permutation(len(ug))
    fold_of = {ug[i]: j % NFOLD for j, i in enumerate(perm)}
    fold = np.array([fold_of[g] for g in groups])
    best = None
    for C in CGRID:
        aucs = []
        for k in range(NFOLD):
            tr, te = fold != k, fold == k
            if y[te].min() == y[te].max() or y[tr].min() == y[tr].max():
                continue
            mu, sd = scaler(X[tr])
            w = fit_logit((X[tr] - mu) / sd, y[tr], C)
            aucs.append(auc(y[te], ((X[te] - mu) / sd) @ w[1:] + w[0]))
        m = float(np.mean(aucs))
        if best is None or m > best[1] + 1e-12:
            best = (float(C), m)
    mu, sd = scaler(X)
    w = fit_logit((X - mu) / sd, y, best[0])
    return {"C": best[0], "cv": best[1], "mu": mu, "sd": sd, "w": w}


def predict(m, X):
    return ((X - m["mu"]) / m["sd"]) @ m["w"][1:] + m["w"][0]


def file_groups(cl):
    _, ci = np.unique(cl, return_inverse=True)
    order = np.argsort(ci, kind="stable")
    return np.split(order, np.flatnonzero(np.diff(ci[order])) + 1)


def mh_rr(e, y, st):
    _, si = np.unique(st, return_inverse=True)
    a, b = np.bincount(si, y * e), np.bincount(si, y * (1 - e))
    n1, n0 = np.bincount(si, e), np.bincount(si, 1 - e)
    N = n1 + n0
    ok = (n1 > 0) & (n0 > 0)
    den = np.sum(b[ok] * n1[ok] / N[ok])
    return np.sum(a[ok] * n0[ok] / N[ok]) / den if den > 0 else np.nan


# ------------------------------------------------------------------ data
def build(profiles, repos):
    rows = defaultdict(list)
    for x in profiles:
        if x["r"] in repos:
            rows[x["r"]].append(x)
    ev, last = [], {}
    for r in repos:
        e, last[r] = fix_events(r)
        ev += e
    with multiprocessing.get_context("fork").Pool(8) as p:
        tch = list(p.imap_unordered(touched, ev, chunksize=32))
        cms = dict(p.imap_unordered(commits, list(repos)))
    log(f"fix commits {len(ev):,}; repos {len(repos)}")
    U = []
    for r in repos:
        fix_at, cve_at = defaultdict(list), defaultdict(list)
        for rr, ct, klass, files in tch:
            if rr != r:
                continue
            for f in files:
                fix_at[f].append(ct)
                if klass == "latent":
                    cve_at[f].append(ct)
        for d in (fix_at, cve_at):
            for v in d.values():
                v.sort()
        com_at = defaultdict(list)
        for ct, files in cms[r]:
            for f in files:
                com_at[f].append(ct)
        for v in com_at.values():
            v.sort()
        by_ct = defaultdict(dict)
        first_seen = {}
        for x in rows[r]:
            by_ct[x["ct"]][x["path"]] = x
            first_seen[x["path"]] = min(first_seen.get(x["path"], x["ct"]), x["ct"])
        anchors = {}
        for ct in sorted(by_ct):
            anchors[dt.datetime.fromtimestamp(ct, dt.timezone.utc).year] = ct
        yrs = sorted(y for y, ct in anchors.items() if ct + YEAR <= last[r])
        med = float(np.median(yrs))
        prev_ct = None
        for y in sorted(anchors):
            a = anchors[y]
            if y in yrs:
                prev = by_ct[prev_ct] if prev_ct is not None else {}
                for path, x in by_ct[a].items():
                    if x["code"] < 50 or x["funcs"] < 1 or EXCL.search(path):
                        continue

                    def n_in(lst, lo, hi):
                        return bisect.bisect_right(lst, hi) - bisect.bisect_right(lst, lo)
                    fx, cv, cm = fix_at.get(path, []), cve_at.get(path, []), com_at.get(path, [])
                    p0 = prev.get(path)
                    grew = bool(p0 and p0["code"] >= 50 and x["code"] >= 1.2 * p0["code"])
                    code = x["code"]
                    U.append({
                        "r": r, "path": path, "year": y, "test": y > med,
                        "y_fix": n_in(fx, a, a + YEAR) > 0, "y_cve": n_in(cv, a, a + YEAR) > 0,
                        "log_code": np.log(code), "prior_fix": np.log1p(n_in(fx, a - YEAR, a)),
                        "prior_fix_n": n_in(fx, a - YEAR, a), "churn": np.log1p(n_in(cm, a - YEAR, a)),
                        "age": np.log1p(max(a - first_seen[path], 0) / YEAR),
                        "prior_cve": float(bisect.bisect_right(cv, a) > 0),
                        "density": x["comment"] / code, "header_cov": x["headed"] / x["funcs"],
                        "danger_share": x["danger"] / max(x["comment"], 1), "debt_kloc": 1000 * x["debt"] / code,
                        "dead_kloc": 1000 * x["dead"] / code, "grew": grew,
                        "neglect": grew and x["comment"] <= p0["comment"]})
            prev_ct = a
        log(f"{r}: file-years {sum(1 for u in U if u['r'] == r):,} (anchor years {yrs[0]}–{yrs[-1]}, split ≤ {med:g})")
    return U


def matrices(U, repos, extra):
    cols = list(B_COLS) + [f"repo={r}" for r in repos[1:]] + list(extra)
    X = np.zeros((len(U), len(cols)))
    for i, u in enumerate(U):
        for j, c in enumerate(cols):
            if c.startswith("repo="):
                X[i, j] = float(u["r"] == c[5:])
            elif c in P_COLS:
                X[i, j] = np.log1p(u[c] * P_SCALE[P_COLS.index(c)])
            else:
                X[i, j] = u[c]
    return X, cols


def lift_claim(U, repos, yk, label):
    tr = [u for u in U if not u["test"]]
    te = [u for u in U if u["test"]]
    ytr = np.array([u[yk] for u in tr], float)
    yte = np.array([u[yk] for u in te], float)
    g_tr = np.array([f"{u['r']}:{u['path']}" for u in tr])
    out = {"n_tr": len(tr), "n_te": len(te), "pos_tr": int(ytr.sum()), "pos_te": int(yte.sum())}
    S, M = {}, {}
    for name, extra in (("B", ()), ("B+P", P_COLS), ("B+density", ("density",)), ("B+header", ("header_cov",))):
        Xtr, cols = matrices(tr, repos, extra)
        Xte, _ = matrices(te, repos, extra)
        M[name] = fit_model(Xtr, ytr, g_tr)
        M[name]["cols"] = cols
        S[name] = predict(M[name], Xte)
    A = {k: auc(yte, v) for k, v in S.items()}
    groups = file_groups(np.array([f"{u['r']}:{u['path']}" for u in te]))
    rng = np.random.default_rng(SEED)
    bl = []
    for _ in range(ITERS):
        pk = np.concatenate([groups[j] for j in rng.integers(0, len(groups), len(groups))])
        bl.append(auc(yte[pk], S["B+P"][pk]) - auc(yte[pk], S["B"][pk]))
    bl = np.array(bl, float)
    bl = bl[np.isfinite(bl)]
    lift = A["B+P"] - A["B"]
    out.update(A=A, lift=lift, lo1=float(np.quantile(bl, ALPHA)), lo2=float(np.quantile(bl, 0.005)),
               hi2=float(np.quantile(bl, 0.995)), M=M)
    loc = np.exp(np.array([u["log_code"] for u in te]))
    out["recall"] = {k: (yte * select(expit(S[k]), loc, 0.20)).sum() / max(yte.sum(), 1) for k in ("B", "B+P")}
    out["per_repo"] = {}
    for r in repos:
        m = np.array([u["r"] == r for u in te])
        if m.sum() and 0 < yte[m].sum() < m.sum():
            out["per_repo"][r] = (auc(yte[m], S["B"][m]), auc(yte[m], S["B+P"][m]), int(yte[m].sum()), int(m.sum()))
    log(f"{label}: AUC B {A['B']:.3f}, B+P {A['B+P']:.3f}, lift {lift:+.4f} (lo {out['lo1']:+.4f})")
    return out


def call(o, min_pos=0):
    if o["pos_te"] < min_pos:
        return "underpowered"
    if o["lift"] > 0 and o["lo1"] > 0:
        return "SUPPORTED"
    if -NULL_BAND <= o["lo2"] and o["hi2"] <= NULL_BAND:
        return "not supported — replicated null"
    return "not supported — inconclusive"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", type=pathlib.Path, required=True)
    a = ap.parse_args()
    with gzip.open(a.profiles, "rt") as f:
        prof = json.load(f)
    log(f"profile rows {len(prof):,}")
    U = build(prof, CORE + UNSEEN)
    Uc = [u for u in U if u["r"] in CORE]
    Uv = [u for u in U if u["r"] in CVE_REPOS]
    Uu = [u for u in U if u["r"] in UNSEEN]
    F = lift_claim(Uc, CORE, "y_fix", "CPF-F")
    V = lift_claim(Uv, CVE_REPOS, "y_cve", "CPF-V")
    R = lift_claim(Uu, UNSEEN, "y_fix", "CPF-R")
    # CPF-N
    G = [u for u in U if u["grew"]]
    e = np.array([u["neglect"] for u in G], float)
    y = np.array([u["y_fix"] for u in G], float)
    pf = np.array([min(u["prior_fix_n"], 4) if u["prior_fix_n"] < 2 or u["prior_fix_n"] >= 4 else 2 for u in G])
    st = np.array([f"{u['r']}|{int(np.floor(u['log_code'] / np.log(10) / 0.25))}|{p}" for u, p in zip(G, pf)])
    rrN = mh_rr(e, y, st)
    groups = file_groups(np.array([f"{u['r']}:{u['path']}" for u in G]))
    rng = np.random.default_rng(SEED)
    bn = []
    for _ in range(ITERS):
        pk = np.concatenate([groups[j] for j in rng.integers(0, len(groups), len(groups))])
        bn.append(mh_rr(e[pk], y[pk], st[pk]))
    bn = np.array(bn, float)
    bn = bn[np.isfinite(bn)]
    loN, hiN = float(np.quantile(bn, ALPHA / 2)), float(np.quantile(bn, 1 - ALPHA / 2))
    evN = int((e * y).sum())
    vN = ("underpowered" if evN < 20 else "SUPPORTED: neglect precedes more fixes" if loN > 1 else
          "SUPPORTED: neglect precedes fewer fixes" if hiN < 1 else "not supported")
    log(f"CPF-N: RR {rrN:.2f} [{loN:.2f}, {hiN:.2f}], {evN} events")

    def row(cid, o, what, min_pos=0):
        return (f"| **{cid}** | {what} | {o['n_te']:,} ({o['pos_te']:,}) | {o['A']['B']:.3f} | {o['A']['B+P']:.3f} | "
                f"**{o['lift']:+.4f}** | {o['lo1']:+.4f} | [{o['lo2']:+.4f}, {o['hi2']:+.4f}] | **{call(o, min_pos)}** |")
    L = ["# CPF — does a file's comment profile predict its next year of fixes? (SCORED)", "",
         "Registration `docs/cpf_hypotheses.md` (owner OK 2026-11-11). Profiles: `tools/comment_profiles.py` "
         "(engine c7cdf7832). Aggregates only. File-cluster bootstrap 2,000, seed 2982; α = 0.01/4.", "",
         "- file-years: " + ", ".join(f"{r} {sum(1 for u in U if u['r'] == r):,}" for r in CORE + UNSEEN),
         "- training era = anchor years ≤ each repo's median anchor year; claims scored on the later test era", "",
         "## Registered claims", "",
         "| id | outcome, repos | test file-years (positives) | AUC B | AUC B + P | lift | one-sided lower bound | "
         "99% CI | call |", "|---|---|---:|---:|---:|---:|---:|---|---|",
         row("CPF-F", F, "any fix; core 5"), row("CPF-V", V, "CVE fix; curl, OpenSSL, nDPI, harfbuzz", 20),
         row("CPF-R", R, "any fix; unseen libgit2, libxml2, postgres, redis"),
         "", f"| id | claim | result | call |", "|---|---|---|---|",
         f"| **CPF-N** | comment neglect (code +20%, body comments flat) → next-year fix, among {len(G):,} "
         f"growing file-years, all 9 repos | MH RR **{rrN:.2f}** [{loN:.2f}, {hiN:.2f}] (99.75%); neglected "
         f"{int(e.sum()):,} file-years, {evN} with a fix ({y[e == 1].mean():.0%} vs {y[e == 0].mean():.0%}) | "
         f"**{vN}** |", "",
         f"Lift claims: supported iff lift > 0 and lower bound > 0; a failed claim is a replicated null iff its 99% CI "
         f"lies inside ±{NULL_BAND}. CPF-V needs ≥ 20 test-era positives; CPF-N ≥ 20 neglected file-years with a fix.",
         "", "## Descriptive (no verdicts)", ""]
    for cid, o in (("CPF-F", F), ("CPF-V", V), ("CPF-R", R)):
        L.append(f"- **{cid}**: single measures, lift over B: density {o['A']['B+density'] - o['A']['B']:+.4f}, "
                 f"header coverage {o['A']['B+header'] - o['A']['B']:+.4f}; recall at 20% of code lines: "
                 f"B {o['recall']['B']:.1%}, B + P {o['recall']['B+P']:.1%}; C chosen B {o['M']['B']['C']:g}, "
                 f"B + P {o['M']['B+P']['C']:g}")
        m = o["M"]["B+P"]
        L.append("  - P coefficients (standardized): " + ", ".join(
            f"{c} {w:+.3f}" for c, w in zip(m["cols"], m["w"][1:]) if c in P_COLS))
        L.append("  - per repo, AUC B → B + P (positives / file-years): " + "; ".join(
            f"{r} {b:.3f} → {p:.3f} ({k:,} / {n:,})" for r, (b, p, k, n) in o["per_repo"].items()))
    lx = [u for u in U if u["r"] == "libxml2"]
    nlx = sum(1 for u in lx if u["test"] and u["y_cve"])
    if nlx >= 10:
        X = lift_claim(lx, ("libxml2",), "y_cve", "libxml2 CVE")
        L.append(f"- libxml2 CVE (descriptive): {nlx} test positives; AUC B {X['A']['B']:.3f} → B + P "
                 f"{X['A']['B+P']:.3f} (lift {X['lift']:+.4f})")
    else:
        L.append(f"- libxml2 CVE: {nlx} test-era CVE file-years (< 10), not reported")
    L += ["", f"Runtime {time.time() - T0:.0f}s · seed {SEED}."]
    (DOCS_DIR / "cpf.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
