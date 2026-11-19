#!/usr/bin/env python3
"""Which fixes cluster with the repair radius: mechanism class, fix shape, cause type, on DPDK and Mesa trailer pairs. Hypotheses FT1-FT3, FT6: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.
    python tools/sensor/fix_taxonomy.py"""
import pickle
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import change_kinds as CK  # noqa: E402
import change_kinds_diff as CDF  # noqa: E402
import fix_shapes as FS  # noqa: E402

S = "/tmp/gitgalaxy-scratch/claude"
SRC = [("dpdk", f"{S}/fr_base"), ("mesa", f"{S}/fr_mesa")]
TAGS = f"{S}/fix_tags.pkl"


def msgs(repo, shas):
    out = subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "log", "--no-walk=unsorted", "--stdin", "--format=%H%x1f%s%x1f%b%x1e"], input="\n".join(shas) + "\n", capture_output=True, text=True, errors="replace").stdout
    res = {}
    for rec in out.split("\x1e"):
        p = rec.strip("\n").split("\x1f")
        if len(p) >= 2:
            res[p[0]] = (p[1], p[2] if len(p) > 2 else "")
    return res


def build():
    frames = []
    tags = {}
    for repo, d in SRC:
        df = pd.read_pickle(f"{d}/measure.pkl")
        df = df[df.status == "ok"].copy()
        df["repo"] = repo
        CK.REPO = f"{BR.POOL}/{repo}"
        fixm = msgs(repo, list(dict.fromkeys(df.fix)))
        indm = msgs(repo, list(dict.fromkeys(df.ind)))
        feats = CDF.diff_features(list(dict.fromkeys(df.fix)), f"{S}/fixfeats_{repo}.pkl")
        df["mech"] = [CK.fix_class(*fixm.get(s, ("", "")))[0] for s in df.fix]
        df["shape"] = [FS.shape(feats[s]) for s in df.fix]
        df["cause"] = [CK.cause_type(indm.get(s, ("", ""))[0])[0] for s in df.ind]
        for r in df.itertuples():
            tags[(repo, r.fix)] = (r.mech, r.shape, r.cause)
        frames.append(df)
    pickle.dump(tags, open(TAGS, "wb"))
    return pd.concat(frames)


def table(df, col, rng, minn=40):
    out = df[df.nFo > 0]
    print(f"  {col:30s} {'pairs':>6s} {'share':>6s} {'lag d':>6s} {'same fn':>8s} {'cross-file':>10s} | within 2 calls (against same-file) | within 1 call")
    res = {}
    for k, g in sorted(df.groupby(col), key=lambda kv: -len(kv[1])):
        o = out[out[col] == k]
        r2 = BR.ratio(o, "either2", "eB", rng) if len(o) >= 15 else None
        r1 = BR.ratio(o, "either1", "eB", rng) if len(o) >= 15 else None
        res[k] = (len(g), len(o), r2, g.same_func.mean(), (~g.same_file.astype(bool)).mean())
        print(f"  {k:30s} {len(g):6d} {100 * len(g) / len(df):5.1f}% {g.lag.median():6.0f} {100 * g.same_func.mean():7.0f}% {100 * (~g.same_file.astype(bool)).mean():9.0f}% | {BR.fmt(r2)} | {BR.fmt(r1)}")
    return res


def main():
    rng = np.random.default_rng(2982)
    df = build()
    print(f"{len(df)} measured pairs (dpdk {int((df.repo == 'dpdk').sum())}, mesa {int((df.repo == 'mesa').sum())}); with a fixed function outside the changed set {int((df.nFo > 0).sum())}")
    allr = {}
    for col, label in (("mech", "MECHANISM CLASS (fix subject and body)"), ("shape", "FIX SHAPE (fix diff)"), ("cause", "CAUSING-CHANGE TYPE (cause subject verb)")):
        print(f"\n=== {label}, pooled DPDK + Mesa ===")
        allr[col] = table(df, col, rng)
        for repo in ("dpdk", "mesa"):
            print(f"  -- {repo} only, radius within 2 calls:")
            sub = df[df.repo == repo]
            for k, g in sorted(sub.groupby(col), key=lambda kv: -len(kv[1])):
                o = g[g.nFo > 0]
                r2 = BR.ratio(o, "either2", "eB", rng) if len(o) >= 15 else None
                print(f"     {k:30s} n {len(g):5d} {BR.fmt(r2)}")
    print("\n=== FT6: (mechanism, shape) cells of at least 40 pairs with a fixed function outside the changed set, by radius within 2 calls ===")
    cells = []
    out = df[df.nFo > 0]
    for (m, s), g in out.groupby(["mech", "shape"]):
        if len(g) >= 40:
            r = BR.ratio(g, "either2", "eB", rng)
            if r:
                cells.append((r[0], r[1], r[2], len(g), m, s, g.same_func.mean()))
    for r, lo, hi, n, m, s, sf in sorted(cells, reverse=True):
        print(f"  {m:16s} x {s:30s} n {n:4d}  radius {r:.2f} [{lo:.2f}, {hi:.2f}]")
    print("\n=== VERDICTS ===")
    mr = {k: v for k, v in allr["mech"].items() if v[0] >= 100 and v[2]}
    if mr:
        rs = {k: v[2][0] for k, v in mr.items()}
        mx, mn = max(rs, key=rs.get), min(rs, key=rs.get)
        print(f"  FT1 mechanism radii (classes of 100+ pairs): highest {mx} {rs[mx]:.2f}, lowest {mn} {rs[mn]:.2f}, ratio {rs[mx] / rs[mn]:.2f} (needs 1.3): {'supported' if rs[mx] / rs[mn] >= 1.3 else 'not supported'}")
    sh = {k: v for k, v in allr["shape"].items() if v[0] >= 100}
    top_same = sorted(sh, key=lambda k: -sh[k][3])[:3]
    top_cross = sorted(sh, key=lambda k: -sh[k][4])[:3]
    print(f"  FT2 highest same-function shapes: {[(k, round(100 * sh[k][3])) for k in top_same]}; highest cross-file: {[(k, round(100 * sh[k][4])) for k in top_cross]} (needs guard and small edit on top of the first, large and adds code on the second)")
    ct = allr["cause"]
    print(f"  FT3 same-function share by cause type: " + ", ".join(f"{k} {100 * v[3]:.0f}% (n {v[0]})" for k, v in ct.items()))


if __name__ == "__main__":
    main()
