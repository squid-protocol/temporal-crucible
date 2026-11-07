#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""KWP-H1..H3 (docs/kwp_hypotheses.md): the crucible keyword grammar on the population DB.

    python tools/kwp_eval.py --pop <master_db_v2.12.0-b64f42bf.db> --crucible <kw_scan db>
"""
from __future__ import annotations

import argparse
import itertools
import pathlib
import sqlite3
import sys
import time
from collections import defaultdict

import numpy as np
from scipy.stats import binomtest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import kw_eval as K  # noqa: E402
from _engine import DOCS_DIR, REPO_ROOT  # noqa: E402
from gr_eval import crucible_grammar, fit_p, oe  # noqa: E402

SEED, CAP, ALPHA = 2982, 200_000, 0.01 / 3
MIN_LANG, MIN_REPOS, MIN_UNIT, UNIT_CAP = 5000, 5, 2000, 50_000


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pop", required=True)
    ap.add_argument("--crucible", required=True)
    a = ap.parse_args()
    t0 = time.time()
    w = crucible_grammar(a.crucible)
    pred = {k: np.sign(v) for k, v in w.items()}
    print(f"consensus pairs {len(w)} ({time.time() - t0:.0f}s)", flush=True)
    excl = {l.strip().lower() for l in (REPO_ROOT / "events" / "sources" / "crucible_source_repos_757545ba6fd6.txt").read_text().splitlines() if l.strip()}
    con = sqlite3.connect(f"file:{a.pop}?mode=ro", uri=True)
    cols = [c[1] for c in con.execute("PRAGMA table_info(function_data)")]
    sig = [c for c in cols if c not in K.NON_SIGNAL and c not in K.STYLE]
    cur = con.execute(f"SELECT fd.language, fd.repo_name, f.loc, {', '.join('(f.' + c + ' > 0)' for c in sig)} "
                      "FROM function_data f JOIN file_data fd ON f.file_id = fd.id WHERE f.loc >= 3")
    langs, repos, locs, chunks = [], [], [], []
    n = 0
    while True:
        rows = cur.fetchmany(200_000)
        if not rows:
            break
        keep = [r for r in rows if (r[1] or "").lower() not in excl]
        langs += [r[0] for r in keep]
        repos += [r[1] for r in keep]
        locs += [float(r[2]) for r in keep]
        chunks.append(np.array([r[3:] for r in keep], dtype=bool) if keep else np.zeros((0, len(sig)), bool))
        n += len(rows)
        print(f"  read {n:,} rows ({time.time() - t0:.0f}s)", flush=True)
    con.close()
    X = np.concatenate(chunks)
    lang = np.array(langs)
    repo = np.array(repos)
    loc = np.array(locs)
    rng = np.random.default_rng(SEED)
    L_ok = []
    for l in sorted(set(lang)):
        m = lang == l
        if m.sum() >= MIN_LANG and len(set(repo[m])) >= MIN_REPOS:
            L_ok.append(l)
    data = {}
    for l in L_ok:
        idx = np.flatnonzero(lang == l)
        if len(idx) > CAP:
            idx = rng.choice(idx, CAP, replace=False)
        Xl = X[idx]
        prev = Xl.mean(0)
        used = np.flatnonzero((prev >= K.LO) & (prev <= K.HI))
        data[l] = {"sig": [sig[i] for i in used], "M": oe(Xl[:, used], loc[idx]), "X": Xl[:, used], "loc": loc[idx]}
        print(f"  {l}: {len(idx):,} functions, {len(used)} signals ({time.time() - t0:.0f}s)", flush=True)
    # H1
    cells = []
    for l in L_ok:
        s, M = data[l]["sig"], data[l]["M"]
        for (x, y), p in pred.items():
            if x in s and y in s:
                v = M[s.index(x), s.index(y)]
                if v != 0:
                    cells.append((l, x, y, np.sign(v) == p, float(v)))
    agree = sum(c[3] for c in cells)
    p1 = binomtest(agree, len(cells), 0.5, alternative="greater").pvalue
    v1 = "SUPPORTED" if agree / len(cells) > 0.5 and p1 < ALPHA else "not supported"

    # H2
    def cross(mats, perm=False):
        rs = []
        for l1, l2 in itertools.combinations(L_ok, 2):
            s1, s2 = data[l1]["sig"], data[l2]["sig"]
            sh = [s for s in s1 if s in s2]
            tri = list(itertools.combinations(range(len(sh)), 2))
            if len(tri) < 10:
                continue
            i1 = [s1.index(s) for s in sh]
            i2 = [s2.index(s) for s in sh]
            if perm:
                i1 = list(rng.permutation(i1))
                i2 = list(rng.permutation(i2))
            v1_ = np.array([mats[l1][i1[i], i1[j]] for i, j in tri])
            v2_ = np.array([mats[l2][i2[i], i2[j]] for i, j in tri])
            if v1_.std() > 0 and v2_.std() > 0:
                rs.append(np.corrcoef(v1_, v2_)[0, 1])
        return float(np.mean(rs)), len(rs)
    real = {l: data[l]["M"] for l in L_ok}
    obs, npairs = cross(real)
    null = np.array([cross(real, perm=True)[0] for _ in range(1000)])
    thr = float(np.quantile(null, 1 - ALPHA))
    pl = []
    for _ in range(5):
        sim = {}
        for l in L_ok:
            Xl, lc = data[l]["X"], data[l]["loc"]
            z = np.log10(lc)
            z = (z - z.mean()) / (z.std() + 1e-9)
            P = np.column_stack([fit_p(Xl[:, i].astype(float), z) for i in range(Xl.shape[1])])
            sim[l] = oe(rng.random(P.shape) < P, lc)
        pl.append(cross(sim)[0])
    plm = float(np.mean(pl))
    v2 = "SUPPORTED" if obs > thr and obs > plm + 0.05 else "not supported"
    # H3: repo x language units
    units = defaultdict(list)
    for i, (l, r) in enumerate(zip(lang, repo)):
        if l in data:
            units[(r, l)].append(i)
    uagree = []
    for (r, l), ii in units.items():
        if len(ii) < MIN_UNIT:
            continue
        ii = np.array(ii)
        if len(ii) > UNIT_CAP:
            ii = rng.choice(ii, UNIT_CAP, replace=False)
        s = data[l]["sig"]
        si = [sig.index(x) for x in s]
        Xu = X[ii][:, si]
        prev = Xu.mean(0)
        ok = [j for j in range(len(s)) if 0.02 <= prev[j] <= 0.98]
        if len(ok) < 3:
            continue
        Mu = oe(Xu[:, ok], loc[ii])
        su = [s[j] for j in ok]
        hits = [np.sign(Mu[su.index(x), su.index(y)]) == p for (x, y), p in pred.items() if x in su and y in su and Mu[su.index(x), su.index(y)] != 0]
        if len(hits) >= 3:
            uagree.append((r, l, np.mean(hits), len(hits)))
    k3 = sum(u[2] > 0.5 for u in uagree)
    p3 = binomtest(k3, len(uagree), 0.5, alternative="greater").pvalue if uagree else 1.0
    v3 = "SUPPORTED" if uagree and k3 / len(uagree) > 0.5 and p3 < ALPHA else "not supported"
    # descriptive
    by_l = defaultdict(list)
    by_p = defaultdict(list)
    for c in cells:
        by_l[c[0]].append(c[3])
        by_p[(c[1], c[2])].append(c[3])
    L = ["# KWP-H1..H3 — the crucible keyword grammar across the population (SCORED)", "",
         f"- consensus pairs {len(w)}; population functions used (crucible-source repos excluded) {len(lang):,}; languages {len(L_ok)}", "",
         "| claim | result | verdict |", "|---|---|---|",
         f"| **KWP-H1** crucible signs hold pooled | **{agree}/{len(cells)} = {agree / len(cells):.0%}** of language × pair cells; p = {p1:.2g} | **{v1}** |",
         f"| **KWP-H2** shared grammar beyond size | cross-language r **{obs:.3f}** ({npairs} language pairs); shuffle 99.67th {thr:.3f}; size placebo {plm:.3f} | **{v2}** |",
         f"| **KWP-H3** holds within repos | {k3}/{len(uagree)} repo × language units agree on > 50% of pairs ({k3 / max(len(uagree), 1):.0%}); p = {p3:.2g}; median unit agreement {np.median([u[2] for u in uagree]) if uagree else float('nan'):.0%} | **{v3}** |",
         "", "## Per language (agreement with crucible signs)", ""]
    L += [f"- {l}: {np.mean(v):.0%} of {len(v)} pairs" for l, v in sorted(by_l.items(), key=lambda t: -np.mean(t[1]))]
    L += ["", "## Pairs: most and least replicated (share of languages agreeing; crucible sign)", ""]
    pr = sorted(by_p.items(), key=lambda t: -np.mean(t[1]))
    L += [f"- {x} / {y} ({'+' if pred[(x, y)] > 0 else '−'}): {np.mean(v):.0%} of {len(v)}" for (x, y), v in pr[:10]]
    L += ["- …", *[f"- {x} / {y} ({'+' if pred[(x, y)] > 0 else '−'}): {np.mean(v):.0%} of {len(v)}" for (x, y), v in pr[-6:]]]
    L += ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED}."]
    (DOCS_DIR / "kwp.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
