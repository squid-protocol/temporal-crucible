#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""GR-H1..H4 (docs/gr_hypotheses.md): crucible keyword grammar in the five C repos; grammar fit vs later fixes.
Run with the engine venv (tree-sitter for the fix mapping):

    <engine venv>/bin/python tools/gr_eval.py --crucible <kw_scan db>
"""
from __future__ import annotations

import argparse
import bisect
import itertools
import multiprocessing
import pathlib
import sqlite3
import sys
import time
from collections import Counter, defaultdict

import numpy as np
from scipy.optimize import minimize
from scipy.stats import binomtest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import kw_eval as K  # noqa: E402
from _engine import DOCS_DIR  # noqa: E402
from chg_eval import REPOS, WINDOW, fix_events, map_fix, mh_boot, mh_point  # noqa: E402
from nh_eval import DBS, snapshots  # noqa: E402

SEED, ALPHA, MIN_EV = 2982, 0.01 / 4, 30
CLS = ("latent", "regression", "other-fix", "extrinsic")


def fit_p(x, z):
    Z = np.c_[np.ones_like(z), z, z * z]

    def f(b):
        t = np.clip(Z @ b, -30, 30)
        p = 1 / (1 + np.exp(-t))
        return -np.sum(x * np.log(p + 1e-12) + (1 - x) * np.log(1 - p + 1e-12)), Z.T @ (p - x)
    b = minimize(f, np.zeros(3), jac=True, method="L-BFGS-B").x
    return 1 / (1 + np.exp(-np.clip(Z @ b, -30, 30)))


def oe(X, loc):
    z = np.log10(loc)
    z = (z - z.mean()) / (z.std() + 1e-9)
    P = np.column_stack([fit_p(X[:, i].astype(float), z) for i in range(X.shape[1])])
    O = X.T.astype(float) @ X
    E = P.T @ P
    M = np.log((O + .5) / (E + .5))
    np.fill_diagonal(M, 0)
    return M


def crucible_grammar(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    cols = [c[1] for c in con.execute("PRAGMA table_info(function_data)")]
    sig = [c for c in cols if c not in K.NON_SIGNAL and c not in K.STYLE]
    rows = con.execute(f"SELECT fd.language, f.loc, {', '.join('f.' + c for c in sig)} FROM function_data f "
                       "JOIN file_data fd ON f.file_id = fd.id WHERE f.loc >= 3").fetchall()
    con.close()
    lang = np.array([r[0] for r in rows])
    loc = np.array([float(r[1] or 0) for r in rows])
    X = np.array([[(v or 0) > 0 for v in r[2:]] for r in rows], dtype=bool)
    agg = defaultdict(list)
    langs = [l for l in sorted(set(lang)) if (lang == l).sum() >= K.MIN_FUNCS]
    for l in langs:
        m = lang == l
        prev = X[m].mean(0)
        used = np.flatnonzero((prev >= K.LO) & (prev <= K.HI))
        M = oe(X[m][:, used], loc[m])
        s = [sig[i] for i in used]
        for i, j in itertools.combinations(range(len(s)), 2):
            agg[tuple(sorted((s[i], s[j])))].append(M[i, j])
    w = {}
    for k, v in agg.items():
        if len(v) >= 11:
            med = float(np.median(v))
            if np.mean(np.sign(v) == np.sign(med)) >= 0.7 and med != 0:
                w[k] = med
    return w


def load_repo(r, sigs):
    snaps = snapshots(r)
    con = sqlite3.connect(f"file:{DBS[r]}?mode=ro", uri=True)
    have = {c[1] for c in con.execute("PRAGMA table_info(function_data)")}
    sc = [s for s in sigs if s in have]
    per = []
    for s in snaps:
        rows = con.execute(f"SELECT fd.file_path, f.func_name, f.start_line, f.loc, f.complexity, f.func_archetype, "
                           f"{', '.join('f.' + c for c in sc)} FROM function_data f JOIN file_data fd ON f.file_id = fd.id "
                           "WHERE fd.commit_hash = ? AND fd.language IN ('c','cpp') AND f.func_name IS NOT NULL AND f.func_name != ''",
                           (s["sha"],)).fetchall()
        d = {}
        for row in sorted(rows, key=lambda x: (x[0], x[1], x[2] or 0)):
            d.setdefault((row[0], row[1]), (row[3] or 0, row[4] or 0, row[5] or "", tuple((v or 0) > 0 for v in row[6:])))
        per.append(d)
    con.close()
    return snaps, per, sc


def gfit(pres, sc, w):
    g = 0.0
    on = {s for s, p in zip(sc, pres) if p}
    for (a, b), v in w.items():
        if a not in sc or b not in sc:
            continue
        ia, ib = a in on, b in on
        if ia and ib:
            g += v
        elif (ia != ib) and v > 0:
            g -= v
    return g


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--crucible", required=True)
    a = ap.parse_args()
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    w = crucible_grammar(a.crucible)
    sigs = sorted({s for p in w for s in p})
    print(f"consensus pairs {len(w)} over {len(sigs)} signals ({time.time() - t0:.0f}s)", flush=True)
    # fix hits (CHG mapping)
    all_ev, last_ct = [], {}
    for r in REPOS:
        ev, last_ct[r] = fix_events(r)
        all_ev += [e for e in ev if e[3] in CLS]
    with multiprocessing.get_context("fork").Pool(8) as p:
        hits = [h for hs in p.imap_unordered(map_fix, all_ev, chunksize=8) for h in hs]
    print(f"hits {len(hits):,} ({time.time() - t0:.0f}s)", flush=True)
    h1_rows, units, trans4 = [], [], []
    for r in REPOS:
        snaps, per, sc_all = load_repo(r, sigs)
        cts = [s["ct"] for s in snaps]
        names = [set(d) for d in per]
        # repo-used signals: prevalence 2-98% at the latest snapshot
        last = per[-1]
        Pm = np.array([v[3] for v in last.values() if v[0] >= 3], dtype=bool)
        prev = Pm.mean(0)
        keep = [i for i, s in enumerate(sc_all) if K.LO <= prev[i] <= K.HI]
        sc = [sc_all[i] for i in keep]
        # H1: sign agreement at the latest snapshot
        locs = np.array([float(v[0]) for v in last.values() if v[0] >= 3])
        M = oe(Pm[:, keep], locs)
        for (x, y), v in w.items():
            if x in sc and y in sc:
                h1_rows.append((r, x, y, np.sign(M[sc.index(x), sc.index(y)]) == np.sign(v), float(M[sc.index(x), sc.index(y)]), v))
        # fix index (A1 join)
        idx = defaultdict(list)
        for (_r, path, nm, ct, klass) in (h for h in hits if h[0] == r):
            j = bisect.bisect_right(cts, ct) - 1
            if j < 0:
                continue
            key = None
            for jj in (j, j + 1):
                if jj < len(names):
                    for cand in ((path, nm), (path, nm.split("::")[-1])):
                        if key is None and cand in names[jj]:
                            key = cand
            idx[key or (path, nm)].append((ct, klass))
        for v in idx.values():
            v.sort()
        # identity + transitions (CHG rule)
        prev_d, prev_ids, nxt = None, {}, 0
        for k, d in enumerate(per):
            cur, moved = {}, {}
            if prev_d is not None:
                vn, nn = defaultdict(list), defaultdict(list)
                for key in prev_d:
                    if key not in d:
                        vn[key[1]].append(key)
                for key in d:
                    if key not in prev_d:
                        nn[key[1]].append(key)
                moved = {nn[n][0]: vn[n][0] for n in nn if len(nn[n]) == 1 and len(vn.get(n, [])) == 1}
            for key in d:
                if prev_d is not None and key in prev_d:
                    cur[key] = prev_ids[key]
                elif key in moved:
                    cur[key] = prev_ids[moved[key]]
                else:
                    cur[key] = nxt
                    nxt += 1
            if prev_d is not None:
                inv = {v: key for key, v in prev_ids.items()}
                c1 = cts[k]
                if c1 + WINDOW <= last_ct[r]:
                    for key, f in cur.items():
                        if f not in inv:
                            continue
                        a_, b_ = prev_d[inv[f]], d[key]
                        if b_[0] < 3:
                            continue
                        pres1 = [b_[3][i] for i in keep]
                        pres0 = [a_[3][i] for i in keep]
                        got = set()
                        vv = idx.get(key, [])
                        i0 = bisect.bisect_right(vv, (c1, "￿"))
                        while i0 < len(vv) and vv[i0][0] <= c1 + WINDOW:
                            got.add(vv[i0][1])
                            i0 += 1
                        g1 = gfit(pres1, sc, w)
                        g0 = gfit(pres0, sc, w)
                        state = 2 if (a_[1] != b_[1] or a_[2] != b_[2]) else 1 if (a_[0] != b_[0] or pres0 != pres1) else 0
                        lb = int(np.floor(np.log10(b_[0]) / 0.1))
                        units.append((r, f"{r}:{key[0]}", lb, sum(pres1), g1, got))
                        if state >= 1:
                            trans4.append((r, f"{r}:{key[0]}", lb, state, g1 - g0, got))
            prev_d, prev_ids = d, cur
        print(f"{r}: snapshots {len(snaps)}, used signals {len(sc)}, units {len(units):,} ({time.time() - t0:.0f}s)", flush=True)
    # ---------------- H1
    agree = sum(x[3] for x in h1_rows)
    n1 = len(h1_rows)
    p1 = binomtest(agree, n1, 0.5, alternative="greater").pvalue if n1 else 1.0
    v1 = "SUPPORTED" if n1 and agree / n1 > 0.5 and p1 < ALPHA else "not supported"
    per_repo = Counter()
    tot_repo = Counter()
    for x in h1_rows:
        tot_repo[x[0]] += 1
        per_repo[x[0]] += x[3]
    # ---------------- H2/H3: atypical = bottom quintile of G within (repo, loc bin, n present), n present >= 2
    U = [u for u in units if u[3] >= 2]
    groups = defaultdict(list)
    for i, u in enumerate(U):
        groups[(u[0], u[2], u[3])].append(i)
    atyp = np.zeros(len(U), bool)
    for g, ii in groups.items():
        if len(ii) < 5:
            continue
        gs = np.array([U[i][4] for i in ii])
        ranks = (np.argsort(np.argsort(gs, kind="stable"), kind="stable") + 0.5) / len(ii)
        for i, rk in zip(ii, ranks):
            atyp[i] = rk <= 0.2
    valid = np.array([len(groups[(u[0], u[2], u[3])]) >= 5 for u in U])
    cl = np.array([u[1] for u in U])
    st = np.array([f"{u[0]}|{u[2]}|{u[3]}" for u in U])
    L = ["# GR-H1..H4 — crucible keyword grammar in the five C repos, vs later fixes (SCORED)", "",
         f"- crucible consensus pairs: {len(w)} over {len(sigs)} signals; function-quarter units {len(units):,}; with ≥ 2 used signals {len(U):,}", "",
         "| claim | result | verdict |", "|---|---|---|",
         f"| **GR-H1** crucible grammar signs hold in the 5 repos | {agree}/{n1} = {agree / max(n1, 1):.0%} agree; p = {p1:.2g}; per repo " +
         ", ".join(f"{r} {per_repo[r]}/{tot_repo[r]}" for r in REPOS) + f" | **{v1}** |"]
    res = {}
    for cid, klass in (("GR-H2", "latent"), ("GR-H3", "regression")):
        y = np.array([1.0 if klass in u[5] else 0.0 for u in U])
        m = valid
        rr, lo, ea, eb, n1_, n0_ = mh_boot(cl[m], st[m], atyp[m].astype(float), y[m], rng)
        ok = ea >= MIN_EV and eb >= MIN_EV
        v = ("SUPPORTED" if rr > 1 and lo > 1 else "not supported") if ok else "not evaluable"
        res[cid] = (rr, lo, ea, eb)
        L.append(f"| **{cid}** atypical (bottom-quintile fit) → {klass} fix | RR **{rr:.2f}** (lo {lo:.2f}); events {ea} / {eb} (n {n1_:,} / {n0_:,}) | **{v}** |")
    # H4
    T4 = [t for t in trans4 if t[4] <= -1 or t[4] == 0]
    e4 = np.array([1.0 if t[4] <= -1 else 0.0 for t in T4])
    y4 = np.array([1.0 if "regression" in t[5] else 0.0 for t in T4])
    rr4, lo4, ea4, eb4, n14, n04 = mh_boot(np.array([t[1] for t in T4]), np.array([f"{t[0]}|{t[2]}|{t[3]}" for t in T4]), e4, y4, rng)
    ok4 = ea4 >= MIN_EV and eb4 >= MIN_EV
    v4 = ("SUPPORTED" if rr4 > 1 and lo4 > 1 else "not supported") if ok4 else "not evaluable"
    L.append(f"| **GR-H4** grammar-fit drop ≥ 1 vs unchanged (edited functions) → regression | RR **{rr4:.2f}** (lo {lo4:.2f}); events {ea4} / {eb4} (n {n14:,} / {n04:,}) | **{v4}** |")
    # descriptive
    L += ["", "## Descriptive", ""]
    for klass in ("other-fix", "extrinsic"):
        y = np.array([1.0 if klass in u[5] else 0.0 for u in U])
        L.append(f"- atypical → {klass}: MH RR {mh_point(st[valid], atyp[valid].astype(float), y[valid]):.2f}")
    for cid, klass in (("H2", "latent"), ("H3", "regression")):
        y = np.array([1.0 if klass in u[5] else 0.0 for u in U])
        L.append(f"- {cid} per repo (MH point): " + ", ".join(
            f"{r} {mh_point(st[valid & (np.array([u[0] for u in U]) == r)], atyp[valid & (np.array([u[0] for u in U]) == r)].astype(float), y[valid & (np.array([u[0] for u in U]) == r)]):.2f}"
            for r in REPOS))
    dg = np.array([t[4] for t in trans4])
    L.append(f"- edits: grammar fit up {np.mean(dg > 0):.0%}, down {np.mean(dg < 0):.0%}, unchanged {np.mean(dg == 0):.0%} (n {len(dg):,})")
    agreeing = sorted(h1_rows, key=lambda x: -abs(x[5]))[:12]
    L += ["", "Strongest crucible pairs and their sign in each repo (repo log O/E vs crucible):"]
    for x in agreeing:
        L.append(f"- {x[0]}: {x[1]} / {x[2]}: repo {x[4]:+.2f} vs crucible {x[5]:+.2f} {'✓' if x[3] else '✗'}")
    L += ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED}."]
    (DOCS_DIR / "gr.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
