#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""GG-H1..H3: GitGalaxy's own history, Gemini vs Claude eras (docs/gg_hypotheses.md).

    SFS_SRC=<popan>/structural-fingerprint-scanner/src python tools/gg_eval.py --scans <gg_scans dir>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import time
from collections import Counter, defaultdict

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, os.environ["SFS_SRC"])
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from structural_fingerprint.compare import compare_cohort  # noqa: E402
from structural_fingerprint.fingerprint import build  # noqa: E402
from structural_fingerprint.reference import load_reference  # noqa: E402
from structural_fingerprint.scan_io import load_scan  # noqa: E402
from structural_fingerprint.timeline import _kept  # noqa: E402
from structural_fingerprint.twins import TwinParams, find_twins  # noqa: E402

from _engine import DOCS_DIR, POOL_DIR  # noqa: E402

GEM_END = dt.date(2026, 7, 6)     # snapshots dated <= this hold Gemini-era births
CLA_START = dt.date(2026, 8, 3)   # births first seen in snapshots >= this are Claude-era (the 07-27 snapshot straddles 07-22)
SEED = 2982


def auc(s, y):
    from scipy.stats import rankdata
    r = rankdata(s)
    n1 = y.sum()
    n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else float("nan")


def fit_logit(X, y, lam=1.0):
    def f(w):
        z = X @ w[1:] + w[0]
        p = 1 / (1 + np.exp(-np.clip(z, -30, 30)))
        return -np.sum(y * np.log(p + 1e-12) + (1 - y) * np.log(1 - p + 1e-12)) + lam * np.sum(w[1:] ** 2)
    return minimize(f, np.zeros(X.shape[1] + 1), method="L-BFGS-B").x


def cv_scores(X, y, k=5, seed=SEED):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(y))
    out = np.zeros(len(y))
    for f in range(k):
        te = idx[f::k]
        tr = np.setdiff1d(idx, te)
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
        w = fit_logit((X[tr] - mu) / sd, y[tr])
        out[te] = ((X[te] - mu) / sd) @ w[1:] + w[0]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scans", type=pathlib.Path, required=True)
    a = ap.parse_args()
    t0 = time.time()
    ref = load_reference("structure")
    sig = list(ref.signal_columns)
    weeks = json.loads((a.scans / "weeks.json").read_text())
    snaps = []
    for w in weeks:
        db = a.scans / f"{w['week']}_{w['sha'][:9]}" / "gg_galaxy_master.db"
        if db.exists():
            snaps.append({**w, "date": dt.date.fromisoformat(w["week"]), "db": db})
    # ---- per-week function tables (python, gitgalaxy/ package)
    fam_cols = None
    per = []
    for s in snaps:
        con = sqlite3.connect(f"file:{s['db']}?mode=ro", uri=True)
        have = {c[1] for c in con.execute("PRAGMA table_info(function_data)")}
        cols = [c for c in sig if c in have]
        rows = con.execute(f"SELECT fd.file_path, f.func_name, f.start_line, f.loc, f.complexity, f.args, f.keyword_density, f.func_archetype, "
                           f"{', '.join('f.' + c for c in cols)} FROM function_data f JOIN file_data fd ON f.file_id = fd.id "
                           "WHERE fd.language = 'python' AND f.func_name IS NOT NULL AND f.func_name != ''").fetchall()
        if fam_cols is None:
            fam_cols = sorted(c[1] for c in con.execute("PRAGMA table_info(file_data)") if c[1].startswith("fam_"))
        fam = np.array(con.execute(f"SELECT {', '.join('SUM(' + c + ')' for c in fam_cols)} FROM file_data WHERE language='python'").fetchone(), float)
        n_files = con.execute("SELECT COUNT(*) FROM file_data WHERE language='python'").fetchone()[0]
        con.close()
        d = {}
        for r in sorted(rows, key=lambda r: (r[0], r[1], r[2] or 0)):
            d.setdefault((r[0], r[1]), r)
        per.append({"funcs": d, "fam": fam / fam.sum() if fam.sum() else fam, "n_files": n_files, "sigcols": cols})
    # ---- identity and births (NH move rule)
    fid, birth, alive = {}, {}, []
    nxt = 0
    prev = None
    for k, p in enumerate(per):
        cur = {}
        if prev is not None:
            van = [x for x in prev if x not in p["funcs"]]
            new = [x for x in p["funcs"] if x not in prev]
            vn, nn = defaultdict(list), defaultdict(list)
            for x in van:
                vn[x[1]].append(x)
            for x in new:
                nn[x[1]].append(x)
            moved = {nn[n][0]: vn[n][0] for n in nn if len(nn[n]) == 1 and len(vn.get(n, [])) == 1}
        else:
            moved = {}
        for key in p["funcs"]:
            if prev is not None and key in prev:
                cur[key] = prev[key]
            elif key in moved:
                cur[key] = prev[moved[key]]
            else:
                cur[key] = nxt
                birth[nxt] = (k, p["funcs"][key])
                nxt += 1
        alive.append(set(cur.values()))
        prev = cur
    # ---- features at birth
    def era(k):
        d = snaps[k]["date"]
        return "gemini" if d <= GEM_END else "claude" if d >= CLA_START else "transition"
    X, Y, E, B, ARCH = [], [], [], [], []
    for f, (k, r) in birth.items():
        loc = float(r[3] or 0)
        if loc < 3:
            continue
        ncols = len(per[k]["sigcols"])
        x = [np.log10(max(loc, 1)), (r[4] or 0) / max(loc, 1), float(r[5] or 0), float(r[6] or 0)]
        x += [np.log1p(float(v or 0) / max(loc, 1)) for v in r[8:8 + ncols]]
        X.append(x)
        E.append(era(k))
        B.append(snaps[k]["date"].toordinal())
        ARCH.append(r[7] or "")
    X, E, B = np.array(X), np.array(E), np.array(B)
    feat_names = ["log10 loc", "complexity/loc", "args", "keyword_density"] + per[0]["sigcols"]

    def comparison(mask_a, mask_b):
        m = mask_a | mask_b
        y = mask_a[m].astype(float)
        return cv_scores(X[m], y), y

    gem, cla = E == "gemini", E == "claude"
    s_x, y_x = comparison(cla, gem)
    gmed, cmed = np.median(B[gem]), np.median(B[cla])
    s_g, y_g = comparison(gem & (B > gmed), gem & (B <= gmed))
    s_c, y_c = comparison(cla & (B > cmed), cla & (B <= cmed))
    a_x, a_g, a_c = auc(s_x, y_x), auc(s_g, y_g), auc(s_c, y_c)
    rng = np.random.default_rng(SEED)
    boots = []
    for _ in range(2000):
        def b(s, y):
            i = rng.integers(0, len(y), len(y))
            return auc(s[i], y[i])
        boots.append(b(s_x, y_x) - max(b(s_g, y_g), b(s_c, y_c)))
    lo1 = float(np.quantile(boots, 0.01))
    # top separating features (standardised mean difference)
    smd = [(feat_names[j], (X[cla, j].mean() - X[gem, j].mean()) / (X[np.r_[np.where(cla)[0], np.where(gem)[0]], j].std() + 1e-9)) for j in range(X.shape[1])]
    smd.sort(key=lambda t: -abs(t[1]))
    # ---- H2: change points
    def best_break(series, dist):
        n = len(series)
        best = None
        for k in range(3, n - 3):
            v = dist(k)
            if best is None or v > best[1]:
                best = (k, v)
        return best
    fam = np.array([p["fam"] for p in per])
    def jsd(p, q):
        m = (p + q) / 2
        kl = lambda a_, b_: float(np.sum(a_[a_ > 0] * np.log2(a_[a_ > 0] / b_[a_ > 0])))  # noqa: E731
        return 0.5 * kl(p, m) + 0.5 * kl(q, m)
    kb_fam = best_break(fam, lambda k: jsd(fam[:k].mean(0), fam[k:].mean(0)))
    fps = [build(load_scan(s["db"], ref.signal_columns, name=s["week"]), ref, min_loc=3) for s in snaps]
    coh = compare_cohort(fps)
    D = coh.composite
    kb_sfs = best_break(fps, lambda k: float(D[:k, k:].mean()))
    lo_d, hi_d = dt.date(2026, 7, 1), dt.date(2026, 8, 12)
    in_win = lambda k: lo_d <= snaps[k]["date"] <= hi_d  # noqa: E731
    params = TwinParams()
    retention = []
    for k in range(1, len(fps)):
        pt, st = fps[k - 1].functions, fps[k].functions
        retention.append((snaps[k]["week"], _kept(pt, find_twins(pt, st, params), find_twins(st, pt, params), params.min_loc)))
    # ---- H3: hazard of Gemini-born functions dying, 8 weeks before 07-06 vs 8 weeks after 07-22
    gem_ids = {f for f, (k, _r) in birth.items() if era(k) == "gemini"}
    def weekly_hazards(d0, d1):
        hz = []
        for k in range(len(snaps) - 1):
            if d0 <= snaps[k]["date"] < d1:
                at = alive[k] & gem_ids
                if at:
                    hz.append((len(at - alive[k + 1]), len(at)))
        return hz
    before = weekly_hazards(GEM_END - dt.timedelta(weeks=8), GEM_END)
    after = weekly_hazards(CLA_START - dt.timedelta(days=7), CLA_START + dt.timedelta(weeks=7))
    rate = lambda h: sum(x for x, _ in h) / max(sum(n for _, n in h), 1)  # noqa: E731
    r3 = rate(after) / rate(before) if rate(before) else float("inf")
    b3 = []
    for _ in range(5000):
        bb = [before[i] for i in rng.integers(0, len(before), len(before))]
        aa = [after[i] for i in rng.integers(0, len(after), len(after))]
        b3.append(rate(aa) / rate(bb) if rate(bb) else np.inf)
    lo3 = float(np.quantile(b3, 0.01))
    # ---- report
    L = ["# GG-H1..H3 — GitGalaxy's own history: Gemini era vs Claude era (SCORED)", "",
         f"- {len(snaps)} weekly snapshots of the `gitgalaxy/` package; functions born: Gemini {int(gem.sum()):,}, Claude {int(cla.sum()):,}, "
         f"transition {int((E == 'transition').sum()):,} (excluded)", "",
         "| claim | result | verdict |", "|---|---|---|",
         f"| **GG-H1** Claude-born vs Gemini-born functions distinguishable beyond within-era drift | cross-era AUC **{a_x:.3f}**; placebos: early-vs-late Gemini {a_g:.3f}, early-vs-late Claude {a_c:.3f}; margin {a_x - max(a_g, a_c):+.3f} (lo {lo1:+.3f}) | **{'SUPPORTED' if a_x - max(a_g, a_c) > 0 and lo1 > 0 else 'not supported'}** |",
         f"| **GG-H2** drastic change point at the switch (both best breaks in 07-01 → 08-12) | keyword-mix break **{snaps[kb_fam[0]]['week']}**; sfs-fingerprint break **{snaps[kb_sfs[0]]['week']}** | **{'SUPPORTED' if in_win(kb_fam[0]) and in_win(kb_sfs[0]) else 'not supported'}** |",
         f"| **GG-H3** Gemini code rewritten faster after the switch | weekly death hazard of Gemini-born functions: before {rate(before):.4f}, after {rate(after):.4f}; ratio **{r3:.2f}** (lo {lo3:.2f}) | **{'SUPPORTED' if r3 > 1 and lo3 > 1 else 'not supported'}** |",
         "", "## What separates the eras (standardised mean difference, Claude − Gemini; descriptive)", ""]
    L += [f"- {n}: {v:+.2f}" for n, v in smd[:10]]
    ga, ca = Counter(np.array(ARCH)[gem]), Counter(np.array(ARCH)[cla])
    L += ["", "## Archetype mix of functions born in each era (descriptive)", "", "| archetype | Gemini | Claude |", "|---|---:|---:|"]
    for k in sorted(set(ga) | set(ca), key=lambda k: -(ga[k] + ca[k])):
        L.append(f"| {k} | {ga[k] / max(sum(ga.values()), 1):.1%} | {ca[k] / max(sum(ca.values()), 1):.1%} |")
    L += ["", "## Weekly series (descriptive)", "", "| week | python files | functions | sfs twin retention vs previous week |", "|---|---:|---:|---:|"]
    ret = dict(retention)
    for k, s in enumerate(snaps):
        L.append(f"| {s['week']} | {per[k]['n_files']} | {len(per[k]['funcs'])} | {ret.get(s['week'], float('nan')):.2f} |")
    L += ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED}. Note: GG-H1's bootstrap uses 2,000 rounds over out-of-fold scores."]
    (DOCS_DIR / "gg.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
