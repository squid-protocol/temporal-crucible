#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""FLT-H1..H3: fleet vs interactive Claude code in the GitGalaxy repo (docs/flt_hypotheses.md).

    SFS_SRC=<popan>/structural-fingerprint-scanner/src python tools/flt_eval.py
"""
from __future__ import annotations

import datetime as dt
import json
import multiprocessing
import pathlib
import re
import sqlite3
import subprocess
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from gg_eval import auc, cv_scores  # noqa: E402
from structural_fingerprint.reference import load_reference  # noqa: E402  (SFS_SRC on sys.path via gg_eval)

SCANS = POOL_DIR / "gg_weekly_scans"
REPO = POOL_DIR / "gitgalaxy"
PERIOD_START = dt.date(2026, 10, 5)
SEED = 2982
ALPHA = 0.01 / 3
PR_RX = re.compile(r"\(#(\d+)\)\s*$|Merge pull request #(\d+)")


def _git(*a):
    return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True, errors="replace").stdout


def label_of(branch):
    if branch.startswith(("churn/", "fleet/")):
        return "fleet"
    if branch.startswith(("auto/", "dependabot/")):
        return None
    return "interactive"


def blame_task(t):
    fid, sha, path, line = t
    out = _git("blame", "--first-parent", "--porcelain", "-L", f"{line},{line}", sha, "--", path)
    return fid, (out.split()[0] if out else None)


def main() -> int:
    t0 = time.time()
    ref = load_reference("structure")
    sig = list(ref.signal_columns)
    weeks = json.loads((SCANS / "weeks.json").read_text())
    snaps = [{**w, "date": dt.date.fromisoformat(w["week"]), "db": SCANS / f"{w['week']}_{w['sha'][:9]}" / "gg_galaxy_master.db"} for w in weeks]
    snaps = [s for s in snaps if s["db"].exists()]
    per = []
    for s in snaps:
        con = sqlite3.connect(f"file:{s['db']}?mode=ro", uri=True)
        have = {c[1] for c in con.execute("PRAGMA table_info(function_data)")}
        cols = [c for c in sig if c in have]
        rows = con.execute(f"SELECT fd.file_path, f.func_name, f.start_line, f.loc, f.complexity, f.args, f.keyword_density, f.func_archetype, "
                           f"{', '.join('f.' + c for c in cols)} FROM function_data f JOIN file_data fd ON f.file_id = fd.id "
                           "WHERE fd.language = 'python' AND f.func_name IS NOT NULL AND f.func_name != ''").fetchall()
        con.close()
        d = {}
        for r in sorted(rows, key=lambda r: (r[0], r[1], r[2] or 0)):
            d.setdefault((r[0], r[1]), r)
        per.append((d, cols))
    # identity + births (GG's rule)
    birth, prev, nxt = {}, None, 0
    for k, (d, _c) in enumerate(per):
        cur = {}
        moved = {}
        if prev is not None:
            van = [x for x in prev if x not in d]
            new = [x for x in d if x not in prev]
            vn, nn = defaultdict(list), defaultdict(list)
            for x in van:
                vn[x[1]].append(x)
            for x in new:
                nn[x[1]].append(x)
            moved = {nn[n][0]: vn[n][0] for n in nn if len(nn[n]) == 1 and len(vn.get(n, [])) == 1}
        for key in d:
            if prev is not None and key in prev:
                cur[key] = prev[key]
            elif key in moved:
                cur[key] = prev[moved[key]]
            else:
                cur[key] = nxt
                birth[nxt] = (k, d[key])
                nxt += 1
        prev = cur
    cand = {f: (k, r) for f, (k, r) in birth.items() if snaps[k]["date"] >= PERIOD_START and (r[3] or 0) >= 3 and r[2]}
    # attribution
    subj = {}
    for line in _git("log", "--first-parent", "--format=%H%x1f%s", "HEAD").splitlines():
        h, _, s = line.partition("\x1f")
        subj[h] = s
    prs = {}
    for line in (REPO_ROOT / "events" / "sources" / "gitgalaxy_merged_prs_2026-11-06.tsv").read_text().splitlines():
        n, br, *_ = line.split("\t")
        prs[int(n)] = br
    with multiprocessing.get_context("fork").Pool(8) as p:
        blamed = dict(p.imap_unordered(blame_task, [(f, snaps[k]["sha"], r[0], r[2]) for f, (k, r) in cand.items()], chunksize=16))
    lab, reasons = {}, Counter()
    for f, c in blamed.items():
        s = subj.get(c or "", "")
        m = PR_RX.search(s)
        if not m:
            reasons["no PR in first-parent subject"] += 1
            continue
        br = prs.get(int(m.group(1) or m.group(2)))
        if br is None:
            reasons["PR not in merged list"] += 1
            continue
        L_ = label_of(br)
        if L_ is None:
            reasons["excluded (auto/dependabot)"] += 1
            continue
        lab[f] = L_
    # features
    ids = sorted(lab)
    X, Y, B, P, A = [], [], [], [], []
    for f in ids:
        k, r = cand[f]
        cols = per[k][1]
        loc = float(r[3])
        x = [np.log10(loc), (r[4] or 0) / loc, float(r[5] or 0), float(r[6] or 0)] + [np.log1p(float(v or 0) / loc) for v in r[8:8 + len(cols)]]
        X.append(x)
        Y.append(1.0 if lab[f] == "fleet" else 0.0)
        B.append(snaps[k]["date"].toordinal())
        P.append(r[0])
        A.append(r[7] or "")
    X, Y, B, P, A = np.array(X), np.array(Y), np.array(B), np.array(P), np.array(A)
    names = ["log10 loc", "complexity/loc", "args", "keyword_density"] + per[0][1]
    rng = np.random.default_rng(SEED)

    def test(mask):
        Xm, Ym, Bm = X[mask], Y[mask], B[mask]
        nf, ni = int(Ym.sum()), int((1 - Ym).sum())
        s_x = cv_scores(Xm, Ym)
        out = {"nf": nf, "ni": ni, "auc": auc(s_x, Ym)}
        pl = []
        for g in (1.0, 0.0):
            gm = Ym == g
            med = np.median(Bm[gm])
            yy = (Bm[gm] > med).astype(float)
            pl.append((cv_scores(Xm[gm], yy), yy))
        out["pf"], out["pi"] = auc(*pl[0]), auc(*pl[1])
        bs = []
        for _ in range(2000):
            def b(s, y):
                i = rng.integers(0, len(y), len(y))
                return auc(s[i], y[i])
            bs.append(b(s_x, Ym) - max(b(*pl[0]), b(*pl[1])))
        out["margin"] = out["auc"] - max(out["pf"], out["pi"])
        out["lo"] = float(np.nanquantile(bs, ALPHA))
        return out

    allm = np.ones(len(Y), bool)
    tools = np.array([p.startswith("gitgalaxy/tools/") for p in P])
    r1 = test(allm) if Y.sum() >= 100 and (1 - Y).sum() >= 100 else None
    r2 = test(tools) if Y[tools].sum() >= 50 and (1 - Y[tools]).sum() >= 50 else None
    sf, si = tools[Y == 1].mean(), tools[Y == 0].mean()
    b3 = []
    for _ in range(5000):
        i = rng.integers(0, len(Y), len(Y))
        yy, tt = Y[i], tools[i]
        b3.append(tt[yy == 1].mean() - tt[yy == 0].mean())
    lo3 = float(np.quantile(b3, ALPHA))
    smd = sorted(((names[j], (X[Y == 1, j].mean() - X[Y == 0, j].mean()) / (X[:, j].std() + 1e-9)) for j in range(X.shape[1])), key=lambda t: -abs(t[1]))
    L = ["# FLT-H1..H3 — fleet vs interactive Claude code in the GitGalaxy repo (SCORED)", "",
         f"- functions born in snapshots ≥ {PERIOD_START}: {len(cand):,}; attributed: fleet {int(Y.sum()):,}, interactive {int((1 - Y).sum()):,}; "
         f"dropped: {dict(reasons)}", "",
         "| claim | result | verdict |", "|---|---|---|"]
    def row(cid, what, r):
        if r is None:
            return f"| **{cid}** | {what}: too few functions | **not evaluable** |"
        v = "SUPPORTED" if r["margin"] > 0 and r["lo"] > 0 else "not supported"
        return (f"| **{cid}** | {what}: AUC **{r['auc']:.3f}** (fleet {r['nf']:,} vs interactive {r['ni']:,}); placebos fleet {r['pf']:.3f}, interactive {r['pi']:.3f}; "
                f"margin {r['margin']:+.3f} (lo {r['lo']:+.3f}) | **{v}** |")
    L.append(row("FLT-H1", "all of gitgalaxy/", r1))
    L.append(row("FLT-H2", "inside gitgalaxy/tools/ only", r2))
    L.append(f"| **FLT-H3** fleet code concentrates in tools/ | share in tools/: fleet **{sf:.0%}**, interactive **{si:.0%}**; difference {sf - si:+.2f} (lo {lo3:+.2f}) | "
             f"**{'SUPPORTED' if sf - si > 0 and lo3 > 0 else 'not supported'}** |")
    L += ["", "## What separates fleet from interactive code (standardised mean difference, fleet − interactive; descriptive)", ""]
    L += [f"- {n}: {v:+.2f}" for n, v in smd[:10]]
    fa, ia = Counter(A[Y == 1]), Counter(A[Y == 0])
    L += ["", "| archetype | fleet | interactive |", "|---|---:|---:|"]
    for k in sorted(set(fa) | set(ia), key=lambda k: -(fa[k] + ia[k])):
        L.append(f"| {k} | {fa[k] / max(sum(fa.values()), 1):.1%} | {ia[k] / max(sum(ia.values()), 1):.1%} |")
    L += ["", f"Median size: fleet {10 ** np.median(X[Y == 1, 0]):.0f} lines, interactive {10 ** np.median(X[Y == 0, 0]):.0f} lines. "
          f"Top dirs — fleet: {Counter('/'.join(p.split('/')[:2]) for p in P[Y == 1]).most_common(3)}; "
          f"interactive: {Counter('/'.join(p.split('/')[:2]) for p in P[Y == 0]).most_common(3)}",
          "", f"Runtime {time.time() - t0:.0f}s · seed {SEED}. H1/H2 bootstrap 2,000 rounds over out-of-fold scores (as GG)."]
    (DOCS_DIR / "flt.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
