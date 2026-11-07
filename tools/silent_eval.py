#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""SIL-H1..H2 (docs/silent_hypotheses.md): silent security-patch detection from structural change signatures.
Public output: aggregates. Candidate list: private. Engine venv (gitgalaxy rules).

    <engine venv>/bin/python tools/silent_eval.py
"""
from __future__ import annotations

import json
import multiprocessing
import pathlib
import re
import subprocess
import sys
import time

import numpy as np
from scipy.optimize import minimize
from scipy.stats import rankdata

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402
from chg_eval import CEXT, CPPEXT, fix_events  # noqa: E402
from fortv_fixk_eval import C_RULES, CPP_RULES, EXCL, RULES  # noqa: E402
from hunk_grammar import parse_diff_sections  # noqa: E402

REPOS = ("curl", "openssl", "ndpi", "harfbuzz")
SEC = re.compile(r"\b(cve|security|vuln\w*|overflow|use[- ]after[- ]free|uaf|out[- ]of[- ]bounds|oob|heap|buffer|dos|denial|"
                 r"exploit|sanitiz\w*|crash\w*|asan|fuzz\w*|ossfuzz|oss-fuzz)\b", re.I)
DEFENSIVE = ("branch", "safety", "panics_and_aborts", "cleanup")
SEED, ITERS = 2982, 2000
PRIVATE = POOL_DIR / "vz_private" / "silent_candidates.json"


def feat_task(t):
    r, sha, ct, klass = t
    repo = POOL_DIR / r
    d = subprocess.run(["git", "-C", str(repo), "diff", "-U0", f"{sha}^", sha], capture_output=True)
    if d.returncode != 0:
        return None
    secs = [s for s in parse_diff_sections(d.stdout.decode("utf-8", "replace"))
            if s["path"].endswith(CEXT + CPPEXT) and not s["path"].startswith(EXCL)]
    if not secs:
        return None
    net = dict.fromkeys(RULES, 0)
    nl = 0
    for s in secs:
        rules = C_RULES if s["path"].endswith(CEXT) and r != "harfbuzz" else CPP_RULES
        nl += s["n_added"] + s["n_removed"]
        for k in RULES:
            rk = rules.get(k, C_RULES[k])
            if hasattr(rk, "findall"):
                net[k] += len(rk.findall(s["added_text"])) - len(rk.findall(s["removed_text"]))
    subj = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%s", sha], capture_output=True, text=True, errors="replace").stdout.strip()
    return (r, sha, klass, subj, nl, len(secs), net)


def fit(X, y, lam=1.0):
    def f(b):
        z = X @ b[1:] + b[0]
        p = 1 / (1 + np.exp(-np.clip(z, -30, 30)))
        g = p - y
        return (-np.sum(y * np.log(p + 1e-12) + (1 - y) * np.log(1 - p + 1e-12)) + lam * np.sum(b[1:] ** 2),
                np.r_[g.sum(), X.T @ g + 2 * lam * b[1:]])
    return minimize(f, np.zeros(X.shape[1] + 1), jac=True, method="L-BFGS-B").x


def auc(s, y):
    r = rankdata(s)
    n1 = y.sum()
    n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else float("nan")


def main() -> int:
    t0 = time.time()
    ev = []
    for r in REPOS:
        e, _ = fix_events(r)
        ev += [x for x in e if x[3] in ("latent", "other-fix")]
    with multiprocessing.get_context("fork").Pool(8) as p:
        rows = [x for x in p.imap_unordered(feat_task, ev, chunksize=8) if x]
    print(f"commits {len(rows):,} ({time.time() - t0:.0f}s)", flush=True)
    R = np.array([x[0] for x in rows])
    lat = np.array([x[2] == "latent" for x in rows])
    secw = np.array([bool(SEC.search(x[3])) for x in rows])
    size = np.log10(np.array([max(x[4], 1) for x in rows], float))
    files = np.log10(np.array([max(x[5], 1) for x in rows], float))
    gain = np.array([[1.0 if x[6][k] >= 1 else 0.0 for k in RULES] for x in rows])
    loss = np.array([[1.0 if x[6][k] <= -1 else 0.0 for k in RULES] for x in rows])
    di = [RULES.index(k) for k in DEFENSIVE]
    sets = {"full": np.c_[gain, loss, size, files], "size": np.c_[size, files], "defensive": np.c_[gain[:, di], loss[:, di], size, files]}
    names = [f"+{k}" for k in RULES] + [f"-{k}" for k in RULES] + ["log size", "log files"]
    y = lat.astype(float)
    evalm = (lat & ~secw) | (~lat & ~secw)  # silent positives vs ordinary negatives
    scores = {k: np.full(len(rows), np.nan) for k in sets}
    coefs = []
    for hold in REPOS:
        tr, te = R != hold, R == hold
        for k, X in sets.items():
            mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
            b = fit((X[tr] - mu) / sd, y[tr])
            scores[k][te] = ((X[te] - mu) / sd) @ b[1:] + b[0]
            if k == "full":
                coefs.append(b[1:])
    em = evalm & np.isfinite(scores["full"])
    ye = y[em]
    rng = np.random.default_rng(SEED)
    a = {k: auc(scores[k][em], ye) for k in sets}
    idx = np.flatnonzero(em)
    bs = []
    for _ in range(ITERS):
        i = rng.choice(idx, len(idx), replace=True)
        bs.append(auc(scores["full"][i], y[i]) - auc(scores["size"][i], y[i]))
    lo1 = float(np.nanquantile(bs, 0.005))

    def enrich(sel_idx):
        top = exp = 0.0
        for hold in REPOS:
            ii = sel_idx[R[sel_idx] == hold]
            if len(ii) < 20 or y[ii].sum() == 0:
                continue
            k = max(1, int(round(0.10 * len(ii))))
            order = ii[np.argsort(-scores["full"][ii])][:k]
            top += y[order].sum()
            exp += 0.10 * y[ii].sum()
        return top / exp if exp else float("nan")
    e_obs = enrich(idx)
    be = []
    for _ in range(ITERS):
        be.append(enrich(rng.choice(idx, len(idx), replace=True)))
    lo2 = float(np.nanquantile(be, 0.005))
    per = {}
    for hold in REPOS:
        m = em & (R == hold)
        per[hold] = (int(y[m].sum()), int((1 - y[m]).sum()), auc(scores["full"][m], y[m]), auc(scores["size"][m], y[m]))
    exm = (lat & secw) | (~lat & ~secw)
    exm &= np.isfinite(scores["full"])
    a_explicit = auc(scores["full"][exm], y[exm])
    cb = np.mean(coefs, axis=0)
    top_feats = sorted(zip(names, cb), key=lambda t: -abs(t[1]))[:12]
    # private candidates: ordinary fixes scoring above the median silent positive (per held-out repo)
    cands = []
    for hold in REPOS:
        m = em & (R == hold)
        pos = scores["full"][m & lat]
        if len(pos) == 0:
            continue
        thr = np.median(pos)
        for i in np.flatnonzero(m & ~lat & (scores["full"] > thr)):
            cands.append({"repo": rows[i][0], "sha": rows[i][1], "subject": rows[i][3], "score": float(scores["full"][i])})
    PRIVATE.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE.write_text(json.dumps({"note": "PRIVATE: unlabelled fixes scoring like silent CVE fixes (historical); do not publish",
                                   "candidates": sorted(cands, key=lambda c: -c["score"])}, indent=1))
    v1 = "SUPPORTED" if a["full"] - a["size"] > 0 and lo1 > 0 else "not supported"
    v2 = "SUPPORTED" if lo2 > 1.5 else "not supported"
    L = ["# SIL-H1..H2 — silent security-patch detection from structural change signatures (SCORED; aggregates only)", "",
         f"- commits {len(rows):,}; CVE (latent) {int(lat.sum())}, of which silent {int((lat & ~secw).sum())}; ordinary fixes (no security words) {int((~lat & ~secw).sum()):,}", "",
         "| claim | result | verdict |", "|---|---|---|",
         f"| **SIL-H1** signature beats patch size on silent CVE fixes (held-out repos) | AUC full **{a['full']:.3f}** vs size {a['size']:.3f} (defensive-only {a['defensive']:.3f}); gain {a['full'] - a['size']:+.3f}, lo {lo1:+.3f} | **{v1}** |",
         f"| **SIL-H2** silent CVE fixes concentrate in the top 10% | enrichment **{e_obs:.2f}×** (lo {lo2:.2f}) | **{v2}** |",
         "", "## Per held-out repo (silent positives, ordinary negatives, AUC full, AUC size)", ""]
    L += [f"- {h}: {v[0]} / {v[1]:,}: {v[2]:.3f} vs {v[3]:.3f}" for h, v in per.items()]
    L += ["", f"- explicit (security-worded) CVE fixes vs ordinary, AUC full: {a_explicit:.3f}",
          f"- unlabelled ordinary fixes scoring above the median silent CVE fix: **{len(cands):,}** (list private)",
          "", "Most influential features (mean standardised coefficient over folds): " + ", ".join(f"{n} {v:+.2f}" for n, v in top_feats),
          "", f"Runtime {time.time() - t0:.0f}s · seed {SEED}."]
    (DOCS_DIR / "silent.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
