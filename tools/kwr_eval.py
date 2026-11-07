#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""KW-R (docs/kw_hypotheses.md § KW-R): compositional log-ratio (stoichiometric) co-occurrence, size placebo.

    python tools/kwr_eval.py --db <crucible scan db>
"""
from __future__ import annotations

import argparse
import itertools
import pathlib
import sqlite3
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import kw_eval as K  # noqa: E402
from _engine import DOCS_DIR  # noqa: E402

PERMS, SEED, MIN_TOTAL = 2000, 2982, 3


def rho_matrix(C, pc):
    L = np.log(C + pc)
    clr = L - L.mean(1, keepdims=True)
    v = clr.var(0)
    S = C.shape[1]
    R = np.zeros((S, S))
    for i in range(S):
        d = (clr[:, [i]] - clr).var(0)
        den = v[i] + v
        R[i] = np.where(den > 0, 1 - d / np.where(den > 0, den, 1), 0)
    np.fill_diagonal(R, 0)
    return R


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    a = ap.parse_args()
    t0 = time.time()
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    cols = [c[1] for c in con.execute("PRAGMA table_info(function_data)")]
    sig = [c for c in cols if c not in K.NON_SIGNAL and c not in K.STYLE]
    rows = con.execute(f"SELECT fd.language, f.loc, {', '.join('f.' + c for c in sig)} FROM function_data f "
                       "JOIN file_data fd ON f.file_id = fd.id WHERE f.loc >= 3").fetchall()
    con.close()
    lang = np.array([r[0] for r in rows])
    loc = np.array([float(r[1] or 0) for r in rows])
    Cnt = np.array([[float(v or 0) for v in r[2:]] for r in rows])
    langs = [l for l in sorted(set(lang)) if (lang == l).sum() >= K.MIN_FUNCS]
    base = {}
    for l in langs:
        m = lang == l
        prev = (Cnt[m] > 0).mean(0)
        used = np.flatnonzero((prev >= K.LO) & (prev <= K.HI))
        C = Cnt[m][:, used]
        keep = C.sum(1) >= MIN_TOTAL
        base[l] = {"sig": [sig[i] for i in used], "C": C[keep], "loc": loc[m][keep], "lam": C.sum(0) / max(loc[m].sum(), 1)}
    rng = np.random.default_rng(SEED)

    def cross_r(mats, perm=False):
        rs = []
        P = {l: rng.permutation(len(base[l]["sig"])) for l in langs} if perm else None
        for l1, l2 in itertools.combinations(langs, 2):
            s1, s2 = base[l1]["sig"], base[l2]["sig"]
            sh = [s for s in s1 if s in s2]
            tri = list(itertools.combinations(range(len(sh)), 2))
            if len(tri) < 10:
                continue
            M1, M2 = mats[l1], mats[l2]
            if perm:
                M1 = M1[np.ix_(P[l1], P[l1])]
                M2 = M2[np.ix_(P[l2], P[l2])]
            i1 = [s1.index(s) for s in sh]
            i2 = [s2.index(s) for s in sh]
            v1 = np.array([M1[i1[i], i1[j]] for i, j in tri])
            v2 = np.array([M2[i2[i], i2[j]] for i, j in tri])
            if v1.std() > 0 and v2.std() > 0:
                rs.append(np.corrcoef(v1, v2)[0, 1])
        return float(np.mean(rs)) if rs else float("nan")

    out = {}
    for pc in (0.5, 0.1, 1.0):
        real = {l: rho_matrix(base[l]["C"], pc) for l in langs}
        obs = cross_r(real)
        pl = []
        for _ in range(20):
            sim = {}
            for l in langs:
                b = base[l]
                Cs = rng.poisson(np.outer(b["loc"], b["lam"])).astype(float)
                Cs = Cs[Cs.sum(1) >= MIN_TOTAL]
                sim[l] = rho_matrix(Cs, pc) if len(Cs) > 10 else np.zeros_like(real[l])
            pl.append(cross_r(sim))
        out[pc] = {"obs": obs, "placebo": float(np.mean(pl)), "real": real}
    null = np.array([cross_r(out[0.5]["real"], perm=True) for _ in range(PERMS)])
    thr = float(np.quantile(null, 0.995))
    o = out[0.5]
    h1 = o["placebo"] <= 0.05
    h2 = o["obs"] > thr and o["obs"] - o["placebo"] >= 0.10
    # top universal pairs (pc 0.5)
    agg = {}
    for l in langs:
        s, M = base[l]["sig"], o["real"][l]
        for i, j in itertools.combinations(range(len(s)), 2):
            agg.setdefault(tuple(sorted((s[i], s[j]))), []).append(M[i, j])
    med = {k: (float(np.median(v)), float(np.mean(np.sign(v) == np.sign(np.median(v)))), len(v)) for k, v in agg.items() if len(v) >= len(langs) // 2}
    L = ["# KW-R — stoichiometric (compositional log-ratio) co-occurrence, method check (SCORED)", "",
         f"- languages {len(langs)}; functions kept (total used-signal count ≥ {MIN_TOTAL}): " + ", ".join(f"{l} {len(base[l]['C'])}" for l in langs), "",
         "| claim | result | verdict |", "|---|---|---|",
         f"| **KWR-H1** ratio method removes size | size-only placebo cross-language r = **{o['placebo']:.3f}** (bar ≤ 0.05; KW decile method gave 0.242) | **{'SUPPORTED' if h1 else 'not supported'}** |",
         f"| **KWR-H2** grammar remains under ratios | real r = **{o['obs']:.3f}**; shuffle null 99.5th {thr:.3f}; placebo {o['placebo']:.3f}; real − placebo {o['obs'] - o['placebo']:+.3f} | **{'SUPPORTED' if h2 else 'not supported'}** |",
         "", "Sensitivity (pseudocount: real r / placebo r): " + "; ".join(f"{pc}: {v['obs']:.3f} / {v['placebo']:.3f}" for pc, v in out.items()),
         "", "## Most proportional pairs (median ρ across languages; share agreeing in sign; n languages)", ""]
    L += [f"- {a_} + {b_}: {v[0]:+.2f} ({v[1]:.0%}, {v[2]})" for (a_, b_), v in sorted(med.items(), key=lambda t: -t[1][0])[:15]]
    L += ["", "## Most anti-proportional pairs", ""]
    L += [f"- {a_} × {b_}: {v[0]:+.2f} ({v[1]:.0%}, {v[2]})" for (a_, b_), v in sorted(med.items(), key=lambda t: t[1][0])[:12]]
    L += ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED}."]
    (DOCS_DIR / "kwr.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
