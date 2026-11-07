#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""INTS-H1..H2 (docs/int_hypotheses.md § INT-S): whole-life first-fix rates vs defence at birth. Engine venv.

    <engine venv>/bin/python tools/ints_eval.py
"""
from __future__ import annotations

import bisect
import multiprocessing
import pathlib
import sqlite3
import sys
import time
from collections import defaultdict

import numpy as np
from scipy.stats import rankdata

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR  # noqa: E402
from chg_eval import fix_events, map_fix  # noqa: E402
from nh_eval import DBS, snapshots  # noqa: E402

REPOS = ("curl", "openssl", "ndpi", "harfbuzz")
CLS = ("latent", "other-fix", "regression", "extrinsic")
YEAR = 365.25 * 86400
SEED, ITERS, ALPHA = 2982, 2000, 0.01 / 2


def lives(r):
    snaps = snapshots(r)
    con = sqlite3.connect(f"file:{DBS[r]}?mode=ro", uri=True)
    per = []
    for s in snaps:
        rows = con.execute("SELECT fd.file_path, f.func_name, f.start_line, f.loc, f.def_safety, f.state_safety_neg, f.state_bailout_hits "
                           "FROM function_data f JOIN file_data fd ON f.file_id = fd.id WHERE fd.commit_hash = ? "
                           "AND fd.language IN ('c','cpp') AND f.func_name IS NOT NULL AND f.func_name != ''", (s["sha"],)).fetchall()
        d = {}
        for row in sorted(rows, key=lambda x: (x[0], x[1], x[2] or 0)):
            d.setdefault((row[0], row[1]), (row[3] or 0, (row[4] or 0) + (row[5] or 0) + (row[6] or 0)))
        per.append(d)
    con.close()
    ids_at, info, prev, prev_ids, nxt = [], {}, None, {}, 0
    for k, d in enumerate(per):
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
                cur[key] = prev_ids[key]
            elif key in moved:
                cur[key] = prev_ids[moved[key]]
            else:
                cur[key] = nxt
                info[nxt] = {"birth_k": k, "key": key, "loc": d[key][0], "D": d[key][1] / max(d[key][0], 1)}
                nxt += 1
            info[cur[key]]["last_k"] = k
        ids_at.append(cur)
        prev, prev_ids = d, cur
    return snaps, ids_at, info


def mh_rate(e, ev, pt, st):
    _, si = np.unique(st, return_inverse=True)
    a, b = np.bincount(si, ev * e), np.bincount(si, ev * (1 - e))
    t1, t0 = np.bincount(si, pt * e), np.bincount(si, pt * (1 - e))
    T = t1 + t0
    ok = (t1 > 0) & (t0 > 0)
    den = np.sum(b[ok] * t1[ok] / T[ok])
    return np.sum(a[ok] * t0[ok] / T[ok]) / den if den > 0 else np.inf


def main() -> int:
    t0 = time.time()
    ev, last = [], {}
    for r in REPOS:
        e, last[r] = fix_events(r)
        ev += [x for x in e if x[3] in CLS]
    with multiprocessing.get_context("fork").Pool(8) as p:
        hits = [h for hs in p.imap_unordered(map_fix, ev, chunksize=8) for h in hs]
    print(f"hits {len(hits):,} ({time.time() - t0:.0f}s)", flush=True)
    U = []
    for r in REPOS:
        snaps, ids_at, info = lives(r)
        cts = [s["ct"] for s in snaps]
        first = defaultdict(dict)  # id -> class -> first hit ct
        file_cve = defaultdict(list)
        for (_r, path, nm, ct, klass) in (h for h in hits if h[0] == r):
            if klass == "latent":
                file_cve[path].append(ct)
            j = bisect.bisect_right(cts, ct) - 1
            if j < 0:
                continue
            fid = None
            for jj in (j, j + 1):
                if jj < len(ids_at) and fid is None:
                    for cand in ((path, nm), (path, nm.split("::")[-1])):
                        if cand in ids_at[jj]:
                            fid = ids_at[jj][cand]
                            break
            if fid is not None and (klass not in first[fid] or ct < first[fid][klass]):
                first[fid][klass] = ct
        for v in file_cve.values():
            v.sort()
        for fid, inf in info.items():
            if inf["birth_k"] == 0 or inf["loc"] < 3:
                continue
            b = cts[inf["birth_k"]]
            death = cts[inf["last_k"] + 1] if inf["last_k"] + 1 < len(cts) else float("inf")
            end = min(death, last[r])
            if end <= b:
                continue
            prior = bisect.bisect_left(file_cve.get(inf["key"][0], []), b) > 0
            U.append((r, inf["key"][0], int(np.floor(np.log10(inf["loc"]) / 0.1)), prior, inf["D"], b, end,
                      {k: v for k, v in first.get(fid, {}).items() if b < v <= end}))
        print(f"{r}: births {sum(1 for u in U if u[0] == r):,} ({time.time() - t0:.0f}s)", flush=True)
    strata = defaultdict(list)
    for i, u in enumerate(U):
        strata[(u[0], u[2], u[3])].append(i)
    grp = np.full(len(U), -1)
    for ii in strata.values():
        if len(ii) < 3:
            continue
        pr = (rankdata([U[i][4] for i in ii]) - 0.5) / len(ii)
        for i, q in zip(ii, pr):
            grp[i] = 1 if q >= 2 / 3 else 0 if q <= 1 / 3 else -1
    m = grp >= 0
    Um = [u for u, k in zip(U, m) if k]
    e = (grp[m] == 1).astype(float)
    st = np.array([f"{u[0]}|{u[2]}|{u[3]}" for u in Um])
    cl = np.array([f"{u[0]}:{u[1]}" for u in Um])

    def evpt(klass):
        evs = np.array([1.0 if klass in u[7] else 0.0 for u in Um])
        pt = np.array([((u[7][klass] if klass in u[7] else u[6]) - u[5]) / YEAR for u in Um])
        return evs, pt
    EV = {k: evpt(k) for k in CLS}
    rr = {k: mh_rate(e, *EV[k], st) for k in CLS}
    rng = np.random.default_rng(SEED)
    _, ci = np.unique(cl, return_inverse=True)
    groups = [np.flatnonzero(ci == k) for k in range(ci.max() + 1)]
    bl, br = [], []
    for _ in range(ITERS):
        pick = np.concatenate([groups[k] for k in rng.integers(0, len(groups), len(groups))])
        a_ = mh_rate(e[pick], EV["latent"][0][pick], EV["latent"][1][pick], st[pick])
        o_ = mh_rate(e[pick], EV["other-fix"][0][pick], EV["other-fix"][1][pick], st[pick])
        bl.append(a_)
        br.append(a_ / o_ if o_ > 0 else np.nan)
    lo1, hi1 = float(np.nanquantile(bl, ALPHA)), float(np.nanquantile(bl, 1 - ALPHA))
    lo2 = float(np.nanquantile(br, ALPHA))
    evh, evl = int((EV["latent"][0] * e).sum()), int((EV["latent"][0] * (1 - e)).sum())
    v1 = ("SUPPORTED: the authors were right" if rr["latent"] > 1 and lo1 > 1
          else "reversed: defended code is safer" if rr["latent"] < 1 and hi1 < 1 else "not supported")
    ratio = rr["latent"] / rr["other-fix"]
    v2 = "SUPPORTED" if ratio > 1 and lo2 > 1 else "not supported"

    def cum(g, years):
        sel = [u for u, gg in zip(Um, e) if gg == g]
        n_at, ev_ = 0, 0
        surv = 1.0
        for y0 in range(years):
            lo_t, hi_t = y0 * YEAR, (y0 + 1) * YEAR
            risk = [u for u in sel if (u[7].get("latent", u[6]) - u[5]) > lo_t]
            d = sum(1 for u in risk if "latent" in u[7] and lo_t < u[7]["latent"] - u[5] <= hi_t)
            if risk:
                surv *= 1 - d / len(risk)
        return 1 - surv
    pt_tot = EV["latent"][1]
    L = ["# INTS-H1..H2 — whole-life: defence at birth vs first CVE fix (SCORED)", "",
         f"- functions born after the first snapshot: {len(U):,}; high / low thirds {int(e.sum()):,} / {int((1 - e).sum()):,}; "
         f"function-years {pt_tot.sum():,.0f} (median life {np.median(pt_tot):.1f} y)", "",
         "| claim | result | verdict |", "|---|---|---|",
         f"| **INTS-H1** first-CVE-fix rate, high vs low defence at birth | rate ratio **{rr['latent']:.2f}** [{lo1:.2f}, {hi1:.2f}]; first-CVE events {evh} / {evl} | **{v1}** |",
         f"| **INTS-H2** CVE-specific (÷ other-fix rate ratio) | **{ratio:.2f}** (lo {lo2:.2f}); other-fix rate ratio {rr['other-fix']:.2f} | **{v2}** |",
         "", "## Descriptive", "",
         f"- cumulative share reaching a CVE fix: by 5 y high {cum(1, 5):.2%} vs low {cum(0, 5):.2%}; by 10 y high {cum(1, 10):.2%} vs low {cum(0, 10):.2%}",
         f"- first-event rate ratios: regression {rr['regression']:.2f}, extrinsic {rr['extrinsic']:.2f}"]
    for r in REPOS:
        mm = np.array([u[0] == r for u in Um])
        if mm.sum():
            L.append(f"- {r}: CVE rate ratio {mh_rate(e[mm], EV['latent'][0][mm], EV['latent'][1][mm], st[mm]):.2f} "
                     f"(events {int((EV['latent'][0][mm] * e[mm]).sum())} / {int((EV['latent'][0][mm] * (1 - e[mm])).sum())}); "
                     f"other-fix {mh_rate(e[mm], EV['other-fix'][0][mm], EV['other-fix'][1][mm], st[mm]):.2f}")
    L += ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED} · file-cluster bootstrap {ITERS}."]
    (DOCS_DIR / "ints.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
