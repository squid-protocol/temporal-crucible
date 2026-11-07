#!/usr/bin/env python3
"""EXPLORATORY: GitGalaxy's own history on the fingerprint lattice.

A. Writing style, Gemini era vs Claude era (GG's binding eras: Gemini before 2026-07-06, transition excluded, Claude
   from 2026-07-22): functions born in each era compared on lattice family / rung, grammar fit against the population's
   Python functions, holes and attractions, and source-level habits; a within-Claude drift reference (early vs late).
B. How functions move on the lattice across GG's 32 weekly snapshots.

Data: temporal-crucible-pool/gg_weekly_scans (engine 32619e4a5, gitgalaxy/ package, history ablated).

    <venv with tree_sitter_language_pack>/bin/python tools/exploratory/gg_lattice.py --repo <gitgalaxy checkout> --pop <population db>
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import subprocess
import sys
from collections import Counter, defaultdict

import numpy as np
from scipy.optimize import minimize
from scipy.stats import rankdata

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import kw_eval as K  # noqa: E402
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402
from agents_lattice import ATTRACT, HOLES, gfit, lattice  # noqa: E402
from gr_eval import crucible_grammar  # noqa: E402

SEED = 2982
G = POOL_DIR / "gg_weekly_scans"
GEM_END, CL_START = "2026-07-06", "2026-07-27"   # birth snapshot dates: Gemini interval ends by 07-06; Claude intervals start after 07-21
EARLY_CL_END, LATE_CL_START = "2026-08-31", "2026-10-05"


def fit(X, y, lam=1.0):
    def f(b):
        z = X @ b[1:] + b[0]
        p = 1 / (1 + np.exp(-np.clip(z, -30, 30)))
        return (-np.sum(y * np.log(p + 1e-12) + (1 - y) * np.log(1 - p + 1e-12)) + lam * np.sum(b[1:] ** 2),
                np.r_[(p - y).sum(), X.T @ (p - y) + 2 * lam * b[1:]])
    return minimize(f, np.zeros(X.shape[1] + 1), jac=True, method="L-BFGS-B").x


def cv_auc(X, y, groups, rng):
    ug = np.unique(groups)
    fold = dict(zip(ug, rng.permutation(len(ug)) % 5))
    fo = np.array([fold[g] for g in groups])
    s = np.zeros(len(y))
    for k in range(5):
        tr, te = fo != k, fo == k
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
        b = fit((X[tr] - mu) / sd, y[tr])
        s[te] = ((X[te] - mu) / sd) @ b[1:] + b[0]
    r = rankdata(s)
    n1, n0 = y.sum(), (1 - y).sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def habits(repo, sha, path, start, loc, cache, parser):
    key = (sha, path)
    if key not in cache:
        r = subprocess.run(["git", "-C", str(repo), "show", f"{sha}:{path}"], capture_output=True)
        cache[key] = (r.stdout, parser.parse(r.stdout).root_node if r.stdout else None)
    src, root = cache[key]
    if root is None:
        return None
    node, stack = None, [root]
    while stack:
        n = stack.pop()
        if n.type == "function_definition" and n.start_point[0] + 1 <= start <= n.start_point[0] + 2:
            node = n
            break
        stack.extend(n.children)
    if node is None:
        return None
    lines = src.decode("utf-8", "replace").split("\n")[node.start_point[0]:node.end_point[0] + 1]
    body = node.child_by_field_name("body")
    f0 = body.children[0] if body is not None and body.children else None
    doc = int(f0 is not None and (f0.type == "string" or (f0.type == "expression_statement" and bool(f0.children)
                                                          and f0.children[0].type == "string")))
    cnt, depth, st = Counter(), 0, [(node, 0)]
    while st:
        x, d = st.pop()
        cnt[x.type] += 1
        dd = d + (x.type in ("if_statement", "for_statement", "while_statement", "try_statement", "with_statement"))
        depth = max(depth, dd)
        st.extend((c, dd) for c in x.children)
    n_ = max(len(lines), 1)
    return [doc, sum(l.strip().startswith("#") for l in lines) / n_, cnt["return_statement"], cnt["while_statement"],
            cnt["call"] / n_ * 10, depth]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--pop", required=True)
    a = ap.parse_args()
    rng = np.random.default_rng(SEED)
    import tree_sitter_language_pack as tslp
    parser = tslp.get_parser("python")
    weeks = json.loads((G / "weeks.json").read_text())
    assign = lattice()
    con = sqlite3.connect(f"file:{a.pop}?mode=ro", uri=True)
    cols = [c[1] for c in con.execute("PRAGMA table_info(function_data)")]
    sig = [c for c in cols if c not in K.NON_SIGNAL and c not in K.STYLE]
    rows = con.execute(f"SELECT f.loc, {', '.join('(COALESCE(f.' + c + ',0) > 0)' for c in sig)} FROM function_data f JOIN file_data fd "
                       "ON f.file_id = fd.id WHERE fd.language = 'python' AND f.loc >= 3 AND f.rowid % 7 = 0").fetchall()
    con.close()
    pl, pp = np.array([r[0] for r in rows], float), np.array([r[1:] for r in rows], bool)
    w = crucible_grammar(POOL_DIR / "kw_scan" / "data_galaxy_master.db")
    pg = gfit(pp, sig, w)
    pst = np.array([f"{int(np.floor(np.log10(x) / 0.2))}|{min(n, 8)}" for x, n in zip(pl, pp.sum(1))])
    byst = defaultdict(list)
    for s_, g_ in zip(pst, pg):
        byst[s_].append(g_)
    byst = {s_: np.sort(v) for s_, v in byst.items() if len(v) >= 200}
    pf, pk = assign(pp, sig)
    print(f"population python sample {len(pl):,}", flush=True)
    # snapshots
    snaps = []
    for wk in weeks:
        d = G / f"{wk['week']}_{wk['sha'][:9]}"
        db = d / "gg_galaxy_master.db"
        if not db.exists():
            continue
        c2 = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        have = {c[1] for c in c2.execute("PRAGMA table_info(function_data)")}
        rs = c2.execute(f"SELECT fd.file_path, f.func_name, f.start_line, f.loc, "
                        f"{', '.join(('(COALESCE(f.' + c + ',0) > 0)') if c in have else '0' for c in sig)} "
                        "FROM function_data f JOIN file_data fd ON f.file_id = fd.id WHERE fd.language = 'python' "
                        "AND fd.file_path LIKE 'gitgalaxy/%' AND f.func_name IS NOT NULL AND f.func_name != ''").fetchall()
        c2.close()
        dct = {}
        for r in sorted(rs, key=lambda x: (x[0], x[1], x[2] or 0)):
            dct.setdefault((r[0], r[1]), (r[2] or 0, r[3] or 0, np.array(r[4:], bool)))
        snaps.append((wk["week"], wk["sha"], dct))
    print(f"snapshots {len(snaps)}", flush=True)
    # identity tracking (unique-name file moves)
    ident, nxt, prev, prev_id = [], 0, None, {}
    births, trans, life = [], [], defaultdict(list)
    for t, (week, sha, d) in enumerate(snaps):
        cur, moved = {}, {}
        if prev is not None:
            vn, nn = defaultdict(list), defaultdict(list)
            for key in prev:
                if key not in d:
                    vn[key[1]].append(key)
            for key in d:
                if key not in prev:
                    nn[key[1]].append(key)
            moved = {nn[n][0]: vn[n][0] for n in nn if len(nn[n]) == 1 and len(vn.get(n, [])) == 1}
        for key in d:
            if prev is not None and key in prev:
                cur[key] = prev_id[key]
            elif key in moved:
                cur[key] = prev_id[moved[key]]
            else:
                cur[key] = nxt
                nxt += 1
                if t > 0:
                    births.append((cur[key], t, week, sha, key))
        if prev is not None:
            inv = {v: k for k, v in prev_id.items()}
            for key, fid in cur.items():
                if fid in inv:
                    trans.append((fid, t, week, prev[inv[fid]], d[key]))
        for key, fid in cur.items():
            life[fid].append(t)
        prev, prev_id = d, cur
    birth_t = {b[0]: b[1] for b in births}
    # ---------------- A: style by era
    B = []
    cache = {}
    for fid, t, week, sha, key in births:
        st, loc, pres = snaps[t][2][key]
        if loc < 3:
            continue
        era = "gemini" if week <= GEM_END else ("claude" if week >= CL_START else None)
        if era is None:
            continue
        h = habits(a.repo, sha, key[0], st, loc, cache, parser)
        if h is None:
            continue
        B.append((era, week, loc, pres, h, key[0]))
    E = np.array([b[0] for b in B])
    WK = np.array([b[1] for b in B])
    LOC = np.array([b[2] for b in B], float)
    P = np.array([b[3] for b in B])
    Hb = np.array([b[4] for b in B], float)
    fam, k = assign(P, sig)
    gf = gfit(P, sig, w)
    pct = np.full(len(B), np.nan)
    for i in range(len(B)):
        s_ = f"{int(np.floor(np.log10(LOC[i]) / 0.2))}|{min(int(P[i].sum()), 8)}"
        if s_ in byst:
            v = byst[s_]
            pct[i] = (np.searchsorted(v, gf[i], "left") + np.searchsorted(v, gf[i], "right")) / 2 / len(v)
    groups = {"Gemini era": E == "gemini", "Claude era": E == "claude",
              "early Claude (to 08-31)": (E == "claude") & (WK <= EARLY_CL_END), "late Claude (from 10-05)": (E == "claude") & (WK >= LATE_CL_START)}
    L = ["# EXPLORATORY — GitGalaxy's own history on the fingerprint lattice", "",
         "Data: GG's 32 weekly scans of the `gitgalaxy/` package (engine `32619e4a5`, history ablated). Eras as bound in GG: "
         "Gemini = born by 2026-07-06; Claude = born from the 2026-07-27 snapshot; transition excluded. Exploratory throughout: "
         "GG already showed the eras are distinguishable (AUC 0.877); this describes *how*. The era bundles model, tooling, "
         "workflow and codebase maturity, so a within-Claude drift reference is shown beside every comparison.", "",
         f"- functions born (loc ≥ 3, with source): " + ", ".join(f"{g} {int(m.sum()):,}" for g, m in groups.items()), "",
         "## A. Writing style by era", "",
         "| | Gemini era | Claude era | early Claude | late Claude | population Python |", "|---|---:|---:|---:|---:|---:|"]

    def col(fn, popv):
        return " | ".join(fn(m) for m in groups.values()) + f" | {popv} |"
    L.append("| median lines | " + col(lambda m: f"{np.median(LOC[m]):.0f}", f"{np.median(pl):.0f}"))
    L.append("| rung k ≤ 3 (bricks) | " + col(lambda m: f"{np.mean(k[m] <= 3):.0%}", f"{np.mean(pk <= 3):.0%}"))
    L.append("| rung k ≥ 6 | " + col(lambda m: f"{np.mean(k[m] >= 6):.0%}", f"{np.mean(pk >= 6):.0%}"))
    for f_, nm in ((7, "F7 public/general"), (8, "F8 private + pointers/state"), (6, "F6 bare one-step"), (3, "F3 annotated/test")):
        L.append(f"| {nm} | " + col(lambda m, f_=f_: f"{np.mean(fam[m] == f_):.0%}", f"{np.mean(pf == f_):.0%}"))
    L.append("| grammar fit, median percentile | " + col(lambda m: f"{np.nanmedian(pct[m]):.0%}", "50%"))
    L.append("| grammar-breaking (bottom 10%) | " + col(lambda m: f"{np.nanmean(pct[m] <= 0.10):.1%}", "10%"))
    hn = ["has docstring", "comment lines / line", "returns", "while loops", "calls per 10 lines", "max nesting"]
    for j, nm in enumerate(hn):
        L.append(f"| {nm} (mean) | " + col(lambda m, j=j: f"{Hb[m][:, j].mean():.2f}", "—"))
    for (x, y_), kind in [(p, "hole") for p in HOLES[:2]] + [(p, "attraction") for p in ATTRACT[1:3]]:
        ix, iy = sig.index(x), sig.index(y_)
        L.append(f"| {x} + {y_} ({kind}) | " + col(lambda m: f"{np.mean(P[m][:, ix] & P[m][:, iy]):.1%}", f"{np.mean(pp[:, ix] & pp[:, iy]):.1%}"))
    # classifiers: era vs within-Claude drift (grouped by file)
    X = np.column_stack([P[:, [sig.index(c) for c in sig if P[:, sig.index(c)].any()]], np.log2(LOC), Hb, np.eye(15)[fam], k]).astype(float)
    files = np.array([b[5] for b in B])
    m1 = groups["Gemini era"] | groups["Claude era"]
    auc_era = cv_auc(X[m1], (E[m1] == "claude").astype(float), files[m1], rng)
    m2 = groups["early Claude (to 08-31)"] | groups["late Claude (from 10-05)"]
    auc_drift = cv_auc(X[m2], (WK[m2] >= LATE_CL_START).astype(float), files[m2], rng)
    # size-matched era AUC: subsample Claude to Gemini's size distribution
    gi, ci = np.flatnonzero(groups["Gemini era"]), np.flatnonzero(groups["Claude era"])
    sb = np.floor(np.log2(LOC)).astype(int)
    pick = []
    for b_ in np.unique(sb[gi]):
        cand = ci[sb[ci] == b_]
        need = int((sb[gi] == b_).sum())
        if len(cand):
            pick += list(rng.choice(cand, min(need, len(cand)), replace=False))
    mm = np.r_[gi, np.array(pick, int)]
    auc_era_sz = cv_auc(X[mm], (E[mm] == "claude").astype(float), files[mm], rng)
    L += ["", f"- **era classifier** (lattice signals + family/rung + size + habits, 5-fold grouped by file): AUC **{auc_era:.3f}**; "
          f"size-matched: **{auc_era_sz:.3f}**; within-Claude drift reference (early vs late Claude): {auc_drift:.3f}. "
          "(GG's registered sfs-feature classifier: 0.877 vs placebos ~0.7.)"]
    # ---------------- B: movement
    M = []
    for fid, t, week, a_, b_ in trans:
        pa, pb = a_[2], b_[2]
        M.append((fid, t, week, pa, pb, b_[1]))
    PA = np.array([m[3] for m in M])
    PB = np.array([m[4] for m in M])
    fa, ka = assign(PA, sig)
    fb, kb = assign(PB, sig)
    step = (PA != PB).sum(1)
    mv = step > 0
    wk_t = np.array([m[2] for m in M])
    t_ = np.array([m[1] for m in M])
    fids = np.array([m[0] for m in M])
    age = np.array([t - birth_t.get(f, 0) for f, t in zip(fids, t_)])
    era_t = np.where(wk_t <= GEM_END, "gemini", np.where(wk_t >= CL_START, "claude", "transition"))
    lifemv = defaultdict(bool)
    for f, x in zip(fids, mv):
        lifemv[f] |= bool(x)
    long_lived = [f for f, ts in life.items() if len(ts) >= 8]
    L += ["", "## B. How functions move on the lattice (week to week)", "",
          f"- function-weeks observed {len(M):,}; functions tracked {len(life):,}",
          f"- **weeks in which a function's shape moved: {mv.mean():.1%}**; functions that never moved over their observed life: "
          f"**{np.mean([not lifemv[f] for f in life if f in lifemv]):.0%}** (of those living ≥ 8 weeks: {np.mean([not lifemv[f] for f in long_lived if f in lifemv]):.0%})",
          f"- among moves: single-signal steps {np.mean(step[mv] == 1):.0%}, jumps (≥ 2) {np.mean(step[mv] >= 2):.0%}; climbs {np.mean(kb[mv] > ka[mv]):.0%}, "
          f"descents {np.mean(kb[mv] < ka[mv]):.0%}, same rung (swap) {np.mean(kb[mv] == ka[mv]):.0%}; family changes {np.mean(fa[mv] != fb[mv]):.0%}",
          "- for comparison, LAT-M's 5 C repos (quarterly): 71% of functions never moved; moves 68% single-step; family changes 11% of moves", "",
          "| interval era | function-weeks | shape moved | climbs : descents | family change (of moves) |", "|---|---:|---:|---:|---:|"]
    for e in ("gemini", "transition", "claude"):
        m = era_t == e
        if m.sum():
            L.append(f"| {e} | {int(m.sum()):,} | {mv[m].mean():.1%} | {np.sum(kb[m & mv] > ka[m & mv])} : {np.sum(kb[m & mv] < ka[m & mv])} | {np.mean(fa[m & mv] != fb[m & mv]):.0%} |")
    L += ["", "| age (weeks since birth) | function-weeks | shape moved | mean rung |", "|---|---:|---:|---:|"]
    for lo_, hi_ in ((1, 1), (2, 3), (4, 7), (8, 15), (16, 99)):
        m = (age >= lo_) & (age <= hi_)
        if m.sum():
            L.append(f"| {lo_}–{hi_} | {int(m.sum()):,} | {mv[m].mean():.1%} | {kb[m].mean():.2f} |")
    gain, loss = Counter(), Counter()
    for j, c in enumerate(sig):
        g_ = int((PB[:, j] & ~PA[:, j]).sum())
        l_ = int((PA[:, j] & ~PB[:, j]).sum())
        if g_:
            gain[c] = g_
        if l_:
            loss[c] = l_
    L.append("")
    L.append("- commonest gains: " + ", ".join(f"+{c} {n:,}" for c, n in gain.most_common(8)))
    L.append("- commonest losses: " + ", ".join(f"−{c} {n:,}" for c, n in loss.most_common(8)))
    T = Counter((int(x), int(y_)) for x, y_ in zip(fa[mv], fb[mv]) if x != y_)
    L.append("- commonest family changes: " + ", ".join(f"F{x}→F{y_} {n}" for (x, y_), n in T.most_common(8)))
    # rung trajectory for functions born in the study window and living >= 12 weeks
    traj = defaultdict(list)
    for f, ag, kk in zip(fids, age, kb):
        traj[ag].append(kk)
    L.append("- mean rung by age, all tracked functions: " + ", ".join(f"wk {ag}: {np.mean(traj[ag]):.2f}" for ag in (1, 2, 4, 8, 12, 16, 20) if traj.get(ag)))
    L += ["", "Caveats: exploratory; one repository; era bundles model, tooling, workflow and codebase maturity; engine 32619e4a5 "
          "rules (before gitgalaxy#8024); population grammar reference scanned with b64f42bf; weekly snapshots miss within-week churn."]
    (DOCS_DIR / "gg_lattice_exploratory.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
