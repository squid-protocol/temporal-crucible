#!/usr/bin/env python3
"""Controls for the repair radius: (1) a baseline matched on the fixed function's recent churn and age, (2) size bands of the causing change. Hypotheses CH1-CH3:
docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.

    python tools/sensor/radius_controls.py REPO TAG PAIRS.json OUTDIR      (OUTDIR: blast_radius.py output with touched_all.pkl from cochange_control.py)"""
import bisect
import collections
import json
import os
import pickle
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402

MAXCO = 40
DAY = 86400
HIST = {}  # function key -> sorted numpy array of the times of its changes (fork-inherited by the workers)
RELS = ("either1", "either2", "callers1", "callees1")


def stratum(key, ct):
    t = HIST.get(key)
    if t is None:
        return (0, False)
    hi = int(np.searchsorted(t, ct, side="left"))
    lo = int(np.searchsorted(t, ct - 365 * DAY, side="left"))
    n = hi - lo
    young = hi > 0 and t[0] > ct - 365 * DAY
    return (0 if n == 0 else 1 if n == 1 else 2 if n <= 3 else 3, bool(young))


def worker(args):
    db, items = args
    g = BR.Graph(db)
    by_file = collections.defaultdict(list)
    for i, f in enumerate(g.fid):
        by_file[int(f)].append(i)
    keys = sorted(g.index, key=g.index.get)
    rows = []
    for it in items:
        I = np.array(sorted({g.index[k] for k in it["I"] if k in g.index}), dtype=np.int64)
        F = np.array(sorted({g.index[k] for k in it["F"] if k in g.index}), dtype=np.int64)
        if not len(I) or not len(F):
            continue
        Fo = np.setdiff1d(F, I)
        if not len(Fo):
            continue
        near = g.near(I)
        Iset = set(I.tolist())
        row = {"pid": it["pid"], "relaxed": 0, "nfo": len(Fo)}
        st_cache = {}
        plain = {r: [] for r in RELS}
        matched = {r: [] for r in RELS}
        for f in Fo:
            f = int(f)
            d = int(g.dec[f])
            cand = [j for j in by_file[int(g.fid[f])] if j != f and j not in Iset and abs(int(g.dec[j]) - d) <= 1]
            if not cand:
                for r in RELS:
                    plain[r].append(None)
                    matched[r].append(None)
                continue
            sf = st_cache.setdefault(f, stratum(keys[f], it["ct"]))
            for j in cand:
                st_cache.setdefault(j, stratum(keys[j], it["ct"]))
            row["f_hot"] = row.get("f_hot", 0) + int(sf[0] >= 1)
            row["f_young"] = row.get("f_young", 0) + int(sf[1])
            row["c_hot"] = row.get("c_hot", 0.0) + float(np.mean([st_cache[j][0] >= 1 for j in cand]))
            row["c_young"] = row.get("c_young", 0.0) + float(np.mean([st_cache[j][1] for j in cand]))
            row["n_chk"] = row.get("n_chk", 0) + 1
            same = [j for j in cand if st_cache.setdefault(j, stratum(keys[j], it["ct"])) == sf]
            use = same if same else cand
            if not same:
                row["relaxed"] += 1
            for r in RELS:
                plain[r].append(float(near[r][cand].mean()))
                matched[r].append(float(near[r][use].mean()))
        for r in RELS:
            row[f"o_{r}"] = float(near[r][Fo].any())
            for nm, v in (("eB", plain[r]), ("eM", matched[r])):
                row[f"{nm}_{r}"] = 1 - float(np.prod([1 - x for x in v])) if all(x is not None for x in v) else np.nan
        rows.append(row)
    return rows


def main():
    repo, tag, pairs_path, out = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4])
    pairs = json.load(open(pairs_path))
    log = subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "log", "--no-merges", "--format=%H %ct"], capture_output=True, text=True).stdout.split("\n")
    ct_of = {l.split()[0]: int(l.split()[1]) for l in log if l.strip()}
    histdir = Path(os.environ.get("HIST_SRC", out))  # the unverified all-commit function sets (history for churn and age)
    touched = pickle.load(open(histdir / "touched_all.pkl", "rb"))
    touched = {**touched, **pickle.load(open(out / "touched.pkl", "rb"))}  # pair commits: the (verified, if OUTDIR is a _v directory) sets win
    tmp = collections.defaultdict(list)
    for s, fs in touched.items():
        if s in ct_of and 0 < len(fs) <= MAXCO:
            for k in fs:
                tmp[tuple(k)].append(ct_of[s])
    for k, v in tmp.items():
        HIST[k] = np.array(sorted(v))
    print(f"{repo}: change history of {len(HIST)} functions", flush=True)
    meas = pd.read_pickle(out / "measure.pkl")
    meas = meas[meas.status == "ok"].set_index("pid")
    sn = json.load(open(f"{BR.B}/scan_{tag}/snapshots.json"))
    snap_cts = np.load(out / "snapshot_cts.npy")
    by_snap = collections.defaultdict(list)
    for pid, p in enumerate(pairs):
        if pid not in meas.index or not meas.loc[pid, "nFo"] > 0:
            continue
        s = int(np.searchsorted(snap_cts, p["ind_ct"], side="left"))
        by_snap[s].append({"pid": pid, "I": touched[p["ind"]], "F": touched[p["fix"]], "ct": p["ind_ct"]})
    jobs = [(sn[s]["db"], items) for s, items in sorted(by_snap.items())]
    rows = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for r in ex.map(worker, jobs):
            rows += r
    df = pd.DataFrame(rows).merge(meas[["lag", "nI", "ind", "fix"]].reset_index(), on="pid")
    feats = pd.read_pickle(out / "diff_feats.pkl")
    df["lines"] = [feats[s]["n_add"] + feats[s]["n_rem"] if s in feats else np.nan for s in df.ind]
    df.to_pickle(out / "radius_controls.pkl")
    rng = np.random.default_rng(2982)
    print(f"\n=== {repo}: {len(df)} pairs with a fixed function outside the changed set; matched baseline fell back to plain for {100 * df.relaxed.sum() / df.nfo.sum():.1f}% of fixed functions ===")
    print(f"  sanity: fixed functions changed in the prior year {100 * df.f_hot.sum() / df.n_chk.sum():.1f}% vs {100 * df.c_hot.sum() / df.n_chk.sum():.1f}% of their same-file candidates; first change within the prior year {100 * df.f_young.sum() / df.n_chk.sum():.1f}% vs {100 * df.c_young.sum() / df.n_chk.sum():.1f}%")
    print("  radius against the plain same-file baseline and against the churn- and age-matched baseline:")
    for r in RELS:
        a, b = BR.ratio(df, r, "eB", rng), BR.ratio(df, r, "eM", rng)
        print(f"    {r:9s} plain {BR.fmt(a)}   matched {BR.fmt(b)}")
    print("  within 2 calls by size of the causing change (lines):")
    for lab, m in (("under 20", df.lines < 20), ("20 to 99", (df.lines >= 20) & (df.lines < 100)), ("100 to 499", (df.lines >= 100) & (df.lines < 500)), ("500 or more", df.lines >= 500)):
        d = df[m]
        a, b = BR.ratio(d, "either2", "eB", rng), BR.ratio(d, "either2", "eM", rng)
        print(f"    {lab:12s} n {len(d):5d} plain {BR.fmt(a)}   matched {BR.fmt(b)}")
    a, b = BR.ratio(df, "either2", "eB", rng), BR.ratio(df, "either2", "eM", rng)
    bands = [BR.ratio(df[m], "either2", "eB", rng) for m in (df.lines < 20, (df.lines >= 20) & (df.lines < 100), (df.lines >= 100) & (df.lines < 500), df.lines >= 500)]
    print(f"\n  CH1 matched either2 {b[0]:.2f} [{b[1]:.2f},{b[2]:.2f}] (needs 1.25, lower bound above 1.15): {'supported' if b[0] >= 1.25 and b[1] > 1.15 else 'not supported'}")
    print(f"  CH2 matched / plain = {b[0] / a[0]:.2f} (needs 0.90 or lower): {'supported' if b[0] / a[0] <= 0.9 else 'not supported'}")
    print(f"  CH3 size bands with a lower bound above 1.2 (plain baseline): {sum(1 for x in bands if x and x[1] > 1.2)} of 4 (needs 3)")


if __name__ == "__main__":
    main()
