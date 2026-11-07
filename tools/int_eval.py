#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""INT-H1..H2 (docs/int_hypotheses.md): defence density at birth vs later CVE fixes. Engine venv (tree-sitter mapping).

    <engine venv>/bin/python tools/int_eval.py
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

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR  # noqa: E402
from chg_eval import fix_events, map_fix  # noqa: E402
from fort_eval import mh  # noqa: E402
from nh_eval import DBS, snapshots  # noqa: E402

REPOS = ("curl", "openssl", "ndpi", "harfbuzz")
CLS = ("latent", "other-fix", "regression", "extrinsic")
YEAR = 365.25 * 86400
FOLLOW = 2 * YEAR
SEED, ITERS, ALPHA, MIN_EV = 2982, 2000, 0.01 / 2, 30


def births(r):
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
    out, prev, prev_ids, nxt = [], None, {}, 0
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
                nxt += 1
                if k > 0 and d[key][0] >= 3:
                    out.append({"key": key, "ct": snaps[k]["ct"], "loc": d[key][0], "D": d[key][1] / d[key][0]})
        prev, prev_ids = d, cur
    return snaps, per, out


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
        snaps, per, B = births(r)
        cts = [s["ct"] for s in snaps]
        names = [set(d) for d in per]
        idx = defaultdict(list)
        file_cve = defaultdict(list)
        for (_r, path, nm, ct, klass) in (h for h in hits if h[0] == r):
            if klass == "latent":
                file_cve[path].append(ct)
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
        for v in file_cve.values():
            v.sort()
        for b in B:
            if b["ct"] + FOLLOW > last[r]:
                continue
            got = {k for ct, k in idx.get(b["key"], []) if b["ct"] < ct <= b["ct"] + FOLLOW}
            prior = bisect.bisect_left(file_cve.get(b["key"][0], []), b["ct"]) > 0
            U.append((r, b["key"][0], int(np.floor(np.log10(b["loc"]) / 0.1)), prior, b["D"], got))
        print(f"{r}: births in window {sum(1 for u in U if u[0] == r):,} ({time.time() - t0:.0f}s)", flush=True)
    strata = defaultdict(list)
    for i, u in enumerate(U):
        strata[(u[0], u[2], u[3])].append(i)
    grp = np.full(len(U), -1)
    for ii in strata.values():
        if len(ii) < 3:
            continue
        D = np.array([U[i][4] for i in ii])
        from scipy.stats import rankdata
        pr = (rankdata(D) - 0.5) / len(ii)
        for i, q in zip(ii, pr):
            grp[i] = 1 if q >= 2 / 3 else 0 if q <= 1 / 3 else -1
    m = grp >= 0
    e = (grp[m] == 1).astype(float)
    st = np.array([f"{u[0]}|{u[2]}|{u[3]}" for u in U])[m]
    cl = np.array([f"{u[0]}:{u[1]}" for u in U])[m]
    Y = {k: np.array([1.0 if k in u[5] else 0.0 for u in U])[m] for k in CLS}
    rr = {k: mh(e, Y[k], st) for k in CLS}
    rng = np.random.default_rng(SEED)
    _, ci = np.unique(cl, return_inverse=True)
    groups = [np.flatnonzero(ci == k) for k in range(ci.max() + 1)]
    bl, br = [], []
    for _ in range(ITERS):
        pick = np.concatenate([groups[k] for k in rng.integers(0, len(groups), len(groups))])
        a_ = mh(e[pick], Y["latent"][pick], st[pick])
        o_ = mh(e[pick], Y["other-fix"][pick], st[pick])
        bl.append(a_)
        br.append(a_ / o_ if o_ > 0 else np.nan)
    bl, br = np.array(bl), np.array(br)
    lo1, hi1 = float(np.nanquantile(bl, ALPHA)), float(np.nanquantile(bl, 1 - ALPHA))
    lo2 = float(np.nanquantile(br, ALPHA))
    ev_hi, ev_lo = int((Y["latent"] * e).sum()), int((Y["latent"] * (1 - e)).sum())
    ok = ev_hi >= MIN_EV and ev_lo >= MIN_EV
    v1 = ("not evaluable" if not ok else "SUPPORTED: the authors were right" if rr["latent"] > 1 and lo1 > 1
          else "reversed: defended code is safer" if rr["latent"] < 1 and hi1 < 1 else "not supported")
    ratio = rr["latent"] / rr["other-fix"]
    v2 = "SUPPORTED" if ok and ratio > 1 and lo2 > 1 else "not supported"
    L = ["# INT-H1..H2 — defensive at birth vs later CVE fixes (SCORED)", "",
         f"- functions born with a full 2-year follow-up: {len(U):,}; in high / low thirds: {int(e.sum()):,} / {int((1 - e).sum()):,}", "",
         "| claim | result | verdict |", "|---|---|---|",
         f"| **INT-H1** high- vs low-defence at birth → CVE fix within 2 y | RR **{rr['latent']:.2f}** [{lo1:.2f}, {hi1:.2f}]; CVE-hit {Y['latent'][e == 1].mean():.2%} vs {Y['latent'][e == 0].mean():.2%} (events {ev_hi} / {ev_lo}) | **{v1}** |",
         f"| **INT-H2** specific to CVEs (RR_latent ÷ RR_other-fix) | **{ratio:.2f}** (lo {lo2:.2f}); RR other-fix {rr['other-fix']:.2f} | **{v2}** |",
         "", "## Descriptive", "",
         f"- RR regression {rr['regression']:.2f}; extrinsic {rr['extrinsic']:.2f}"]
    for r in REPOS:
        mm = np.array([u[0] == r for u in U])[m]
        if mm.sum():
            L.append(f"- {r}: RR latent {mh(e[mm], Y['latent'][mm], st[mm]):.2f}, other-fix {mh(e[mm], Y['other-fix'][mm], st[mm]):.2f} "
                     f"(CVE events {int((Y['latent'][mm] * e[mm]).sum())} / {int((Y['latent'][mm] * (1 - e[mm])).sum())})")
    Dall = np.array([u[4] for u in U])
    eb = (Dall > 0).astype(float)
    stb = np.array([f"{u[0]}|{u[2]}|{u[3]}" for u in U])
    yb = np.array([1.0 if "latent" in u[5] else 0.0 for u in U])
    yo = np.array([1.0 if "other-fix" in u[5] else 0.0 for u in U])
    L.append(f"- binary (any defence at birth vs none): RR latent {mh(eb, yb, stb):.2f}, other-fix {mh(eb, yo, stb):.2f}; share defended {eb.mean():.0%}")
    L += ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED} · file-cluster bootstrap {ITERS}."]
    (DOCS_DIR / "int.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
