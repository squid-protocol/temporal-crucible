#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""KW-H1..H3 (docs/kw_hypotheses.md): keyword-signal co-occurrence grammar on the language-crucible.

    python tools/kw_eval.py --db <crucible scan galaxy_master.db>
"""
from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import sqlite3
import sys
import time

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR  # noqa: E402

NON_SIGNAL = {"id", "file_id", "parent_class_id", "func_name", "complexity", "loc", "start_line", "args", "usage_status",
              "keyword_density", "func_archetype", "func_z_score", "docstring", "calls_out_to", "calls_out_qualifiers",
              "calls_out_receiver_types", "calls_out_arities", "decorated_by", "decorated_by_qualifiers", "references_to",
              "references_qualifiers", "transfers_to", "def_shape", "func_pagerank", "func_fan_in", "func_fan_out", "token_mass",
              "is_public", "is_documented", "impact"}
STYLE = {"struct_tabs", "struct_spaces", "struct_camel_case", "struct_snake_case", "struct_pascal_case", "struct_upper_case",
         "struct_short_vars", "struct_long_vars"}
MIN_FUNCS, LO, HI, K, PERMS, SEED = 500, 0.02, 0.98, 6, 2000, 2982
ALPHA = 0.01 / 3


def family(s):
    p = s.split("_")[0]
    if p in ("struct", "def", "state", "arch", "threat", "sec", "lit"):
        return p
    if p in ("llm", "ml", "dl"):
        return "model"
    return "other"


def mh_logor(X, strata):
    """S x S matrix of MH log odds ratios of co-presence, stratified (0.5 continuity correction)."""
    S = X.shape[1]
    num = np.zeros((S, S))
    den = np.zeros((S, S))
    for s in np.unique(strata):
        Xs = X[strata == s].astype(float)
        n = len(Xs)
        if n < 2:
            continue
        a = Xs.T @ Xs
        ci = Xs.sum(0)
        b = ci[:, None] - a
        c = ci[None, :] - a
        d = n - a - b - c
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
        num += a * d / (n + 2)
        den += b * c / (n + 2)
    M = np.log(num / den)
    np.fill_diagonal(M, 0.0)
    return M


def ari(x, y):
    from collections import Counter
    n = len(x)
    if n < 2:
        return float("nan")
    comb = lambda k: k * (k - 1) / 2  # noqa: E731
    cont = Counter(zip(x, y))
    sij = sum(comb(v) for v in cont.values())
    sa = sum(comb(v) for v in Counter(x).values())
    sb = sum(comb(v) for v in Counter(y).values())
    exp = sa * sb / comb(n)
    mx = (sa + sb) / 2
    return (sij - exp) / (mx - exp) if mx != exp else 0.0


def clusters(M):
    D = 1.0 - np.tanh(M / 2.0)
    np.fill_diagonal(D, 0.0)
    D = (D + D.T) / 2
    Z = linkage(squareform(np.clip(D, 0, None), checks=False), method="average")
    return fcluster(Z, t=K, criterion="maxclust")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    a = ap.parse_args()
    t0 = time.time()
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    cols = [c[1] for c in con.execute("PRAGMA table_info(function_data)")]
    sig = [c for c in cols if c not in NON_SIGNAL and c not in STYLE]
    rows = con.execute(f"SELECT fd.language, f.loc, {', '.join('f.' + c for c in sig)} FROM function_data f "
                       "JOIN file_data fd ON f.file_id = fd.id WHERE f.loc >= 3").fetchall()
    con.close()
    lang = np.array([r[0] for r in rows])
    loc = np.array([float(r[1] or 0) for r in rows])
    X = np.array([[(v or 0) > 0 for v in r[2:]] for r in rows], dtype=bool)
    langs = [l for l in sorted(set(lang)) if (lang == l).sum() >= MIN_FUNCS]
    data = {}
    for l in langs:
        m = lang == l
        Xl = X[m]
        prev = Xl.mean(0)
        used = np.flatnonzero((prev >= LO) & (prev <= HI))
        q = np.quantile(loc[m], np.linspace(0, 1, 11)[1:-1])
        strata = np.searchsorted(q, loc[m], side="right")
        M = mh_logor(Xl[:, used], strata)
        data[l] = {"sig": [sig[i] for i in used], "M": M, "n": int(m.sum())}
    rng = np.random.default_rng(SEED)

    def pair_vectors(l1, l2, cross_only):
        s1, s2 = data[l1]["sig"], data[l2]["sig"]
        shared = [s for s in s1 if s in s2]
        i1 = [s1.index(s) for s in shared]
        i2 = [s2.index(s) for s in shared]
        tri = [(i, j) for i, j in itertools.combinations(range(len(shared)), 2)
               if not cross_only or family(shared[i]) != family(shared[j])]
        return shared, i1, i2, tri

    def mean_r(cross_only, perm=False):
        rs = []
        P = {l: rng.permutation(len(data[l]["sig"])) for l in langs} if perm else None
        for l1, l2 in itertools.combinations(langs, 2):
            shared, i1, i2, tri = pair_vectors(l1, l2, cross_only)
            if len(tri) < 10:
                continue
            M1, M2 = data[l1]["M"], data[l2]["M"]
            if perm:
                p1, p2 = P[l1], P[l2]
                M1 = M1[np.ix_(p1, p1)]
                M2 = M2[np.ix_(p2, p2)]
            v1 = np.array([M1[i1[i], i1[j]] for i, j in tri])
            v2 = np.array([M2[i2[i], i2[j]] for i, j in tri])
            if v1.std() > 0 and v2.std() > 0:
                rs.append(np.corrcoef(v1, v2)[0, 1])
        return float(np.mean(rs)) if rs else float("nan"), len(rs)

    real = {l: data[l]["M"] for l in langs}

    def size_placebo_M():
        out = {}
        for l in langs:
            m = lang == l
            Xl = X[m][:, [sig.index(s) for s in data[l]["sig"]]]
            lb = np.searchsorted(np.quantile(loc[m], np.linspace(0, 1, 51)[1:-1]), loc[m], side="right")
            P = np.zeros(Xl.shape)
            for b in np.unique(lb):
                P[lb == b] = Xl[lb == b].mean(0)
            Xs = rng.random(Xl.shape) < P
            q = np.quantile(loc[m], np.linspace(0, 1, 11)[1:-1])
            out[l] = mh_logor(Xs, np.searchsorted(q, loc[m], side="right"))
        return out
    placebo = {}
    for cid, cross in (("KW-H1", False), ("KW-H2", True)):
        vals = []
        for _ in range(20):
            sim = size_placebo_M()
            for l in langs:
                data[l]["M"] = sim[l]
            vals.append(mean_r(cross)[0])
            for l in langs:
                data[l]["M"] = real[l]
        placebo[cid] = float(np.mean(vals))
    res = {}
    for cid, cross in (("KW-H1", False), ("KW-H2", True)):
        obs, npairs = mean_r(cross)
        null = np.array([mean_r(cross, perm=True)[0] for _ in range(PERMS)])
        thr = float(np.quantile(null, 1 - ALPHA))
        res[cid] = (obs, npairs, thr, float(null.mean()), obs > thr and obs >= 0.30 and obs - placebo[cid] >= 0.10)
    # H3 modules
    lab = {l: dict(zip(data[l]["sig"], clusters(data[l]["M"]))) for l in langs}

    def mean_ari(perm=False):
        vals = []
        for l1, l2 in itertools.combinations(langs, 2):
            shared = [s for s in data[l1]["sig"] if s in data[l2]["sig"]]
            if len(shared) < 8:
                continue
            x = [lab[l1][s] for s in shared]
            y = [lab[l2][s] for s in shared]
            if perm:
                x = list(rng.permutation(x))
                y = list(rng.permutation(y))
            vals.append(ari(x, y))
        return float(np.mean(vals)) if vals else float("nan")
    a_obs = mean_ari()
    a_null = np.array([mean_ari(perm=True) for _ in range(PERMS)])
    a_thr = float(np.quantile(a_null, 1 - ALPHA))
    # ---------------- descriptive: median association across languages
    allsig = sorted({s for l in langs for s in data[l]["sig"]})
    med, cnt = {}, {}
    for i, j in itertools.combinations(range(len(allsig)), 2):
        si, sj = allsig[i], allsig[j]
        v = [data[l]["M"][data[l]["sig"].index(si), data[l]["sig"].index(sj)] for l in langs
             if si in data[l]["sig"] and sj in data[l]["sig"]]
        if len(v) >= max(3, len(langs) // 2):
            med[(si, sj)] = float(np.median(v))
            cnt[(si, sj)] = (len(v), float(np.mean(np.sign(v) == np.sign(np.median(v)))))
    pos = sorted(med.items(), key=lambda t: -t[1])[:15]
    neg = sorted(med.items(), key=lambda t: t[1])[:15]
    core = sorted({s for p in med for s in p})
    Mc = np.zeros((len(core), len(core)))
    for (si, sj), v in med.items():
        i, j = core.index(si), core.index(sj)
        Mc[i, j] = Mc[j, i] = v
    cons = clusters(Mc) if len(core) >= K else []
    typ = {}
    for l in langs:
        rs = []
        for l2 in langs:
            if l2 == l:
                continue
            shared, i1, i2, tri = pair_vectors(l, l2, False)
            if len(tri) >= 10:
                v1 = np.array([data[l]["M"][i1[i], i1[j]] for i, j in tri])
                v2 = np.array([data[l2]["M"][i2[i], i2[j]] for i, j in tri])
                rs.append(np.corrcoef(v1, v2)[0, 1])
        typ[l] = float(np.mean(rs)) if rs else float("nan")
    L = ["# KW-H1..H3 — keyword grammar on the language-crucible (SCORED)", "",
         f"- functions (loc ≥ 3): {len(rows):,}; languages with ≥ {MIN_FUNCS}: **{len(langs)}** — " +
         ", ".join(f"{l} ({data[l]['n']}, {len(data[l]['sig'])} signals)" for l in langs),
         f"- candidate signal columns: {len(sig)}", "",
         "| claim | observed | label-null mean | label-null 99.67th pct | size placebo | verdict |", "|---|---:|---:|---:|---:|---|"]
    for cid in ("KW-H1", "KW-H2"):
        obs, npairs, thr, nm, ok = res[cid]
        what = "mean cross-language r of size-stratified co-occurrence" + (" (cross-family pairs only)" if cid == "KW-H2" else "")
        L.append(f"| **{cid}** {what} ({npairs} language pairs) | **{obs:.3f}** | {nm:.3f} | {thr:.3f} | {placebo[cid]:.3f} | **{'SUPPORTED' if ok else 'not supported'}** |")
    L.append(f"| **KW-H3** module agreement (mean ARI, k = {K}) | **{a_obs:.3f}** | {a_null.mean():.3f} | {a_thr:.3f} | — | **{'SUPPORTED' if a_obs > a_thr else 'not supported'}** |")
    L += ["", "## Universal positive pairs (median log OR across languages; n languages, sign agreement)", ""]
    L += [f"- {si} + {sj}: {v:+.2f} ({cnt[(si, sj)][0]} langs, {cnt[(si, sj)][1]:.0%} same sign)" for (si, sj), v in pos]
    L += ["", "## Pairs that avoid each other (most negative median log OR)", ""]
    L += [f"- {si} × {sj}: {v:+.2f} ({cnt[(si, sj)][0]} langs, {cnt[(si, sj)][1]:.0%} same sign)" for (si, sj), v in neg]
    L += ["", f"## Consensus modules (clustering the median association, k = {K})", ""]
    for c in sorted(set(cons)):
        L.append(f"- **module {c}:** " + ", ".join(s for s, cc in zip(core, cons) if cc == c))
    L += ["", "## Language typicality (mean correlation with the other languages)", ""]
    L += [f"- {l}: {v:.3f}" for l, v in sorted(typ.items(), key=lambda t: -t[1])]
    L += ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED} · {PERMS} label permutations."]
    (DOCS_DIR / "kw.md").write_text("\n".join(L) + "\n")
    json.dump({"langs": langs, "signals": {l: data[l]["sig"] for l in langs}, "M": {l: data[l]["M"].round(3).tolist() for l in langs},
               "median": {f"{a}|{b}": v for (a, b), v in med.items()}},
              open(DOCS_DIR / "kw_matrices.json", "w"))
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
