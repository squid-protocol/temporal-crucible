#!/usr/bin/env python3
"""curl, OpenSSL and FreeBSD, unverified and verified, per repository and pooled. SR1-SR5: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.
    python tools/sensor/small_repos_pooled.py"""
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude/blast"
REPOS = ["curl", "openssl", "freebsd-src"]
rng = np.random.default_rng(2982)


def lines_of(repo, shas):
    out = subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "log", "--no-walk=unsorted", "--stdin", "--numstat", "--format=@%H"], input="\n".join(shas) + "\n", capture_output=True, text=True, errors="replace").stdout
    res, cur = {}, None
    for l in out.splitlines():
        if l.startswith("@") and len(l) == 41:
            cur = l[1:]
            res[cur] = 0
        elif cur and "\t" in l:
            a, r, p = l.split("\t", 2)
            if p.endswith((".c", ".h")) and a.isdigit() and r.isdigit():
                res[cur] += int(a) + int(r)
    return res


data = {}
for r in REPOS:
    for tag, d in (("unverified", r), ("verified", r + "_v")):
        m = pd.read_pickle(f"{B}/{d}/measure.pkl")
        m = m[m.status == "ok"].copy()
        m["repo"] = r
        m["lines"] = m.ind.map(lines_of(r, list(m.ind.unique())))
        data[(r, tag)] = m
for tag in ("unverified", "verified"):
    data[("pooled", tag)] = pd.concat([data[(r, tag)] for r in REPOS], ignore_index=True)
print("radius within 1 and 2 calls against same-file functions of similar size (95% interval over pairs):")
res = {}
for r in REPOS + ["pooled"]:
    for tag in ("unverified", "verified"):
        m = data[(r, tag)]
        o = m[m.nFo > 0]
        a1, a2 = BR.ratio(o, "either1", "eB", rng), BR.ratio(o, "either2", "eB", rng)
        res[(r, tag)] = a2
        print(f"  {r:12s} {tag:10s} measured {len(m):4d}, with a fixed function outside {len(o):4d}, same function {100 * m.same_func.mean():3.0f}%  either1 {BR.fmt(a1)}  either2 {BR.fmt(a2)}")
print("\ndifferent-file fixes, callers1 against callees1:")
dirs = {}
for r in REPOS + ["pooled"]:
    for tag in ("unverified", "verified"):
        m = data[(r, tag)]
        x = m[(m.nFo > 0) & (~m.same_file.astype(bool))]
        c1, c2 = BR.ratio(x, "callers1", "eB", rng), BR.ratio(x, "callees1", "eB", rng)
        dirs[(r, tag)] = (c1, c2)
        print(f"  {r:12s} {tag:10s} n {len(x):4d} callers1 {('%.2f [%.2f,%.2f]' % c1[:3]) if c1 else 'n/a'}  callees1 {('%.2f [%.2f,%.2f]' % c2[:3]) if c2 else 'n/a'}")
print("\nsize of the causing change (pooled, verified), either2:")
p = data[("pooled", "verified")]
p = p[p.nFo > 0]
small, big = p[p.lines < 100], p[p.lines >= 100]
rs, rb = BR.ratio(small, "either2", "eB", rng), BR.ratio(big, "either2", "eB", rng)
print(f"  under 100 lines  {BR.fmt(rs)}\n  100 or more      {BR.fmt(rb)}")
print("\nVERDICTS")
pv = res[("pooled", "verified")]
print(f"  SR1 pooled verified radius {pv[0]:.2f} [{pv[1]:.2f},{pv[2]:.2f}] (needs 1.3 with lower bound above 1.1): {'supported' if pv[0] >= 1.3 and pv[1] > 1.1 else 'not supported'}")
pu = res[("pooled", "unverified")]
print(f"  SR2 verification effect on the pooled radius: {pu[0]:.2f} -> {pv[0]:.2f} ({100 * (pv[0] / pu[0] - 1):+.1f}%; needs an increase): {'supported' if pv[0] > pu[0] else 'not supported'}")
c1, c2 = dirs[("pooled", "verified")]
print(f"  SR3 callers above callees (pooled, verified): {c1[0]:.2f} vs {c2[0]:.2f}: {'supported' if c1[0] > c2[0] else 'not supported'}")
if rs and rb:
    print(f"  SR4 under 100 lines / 100 or more = {rs[0] / rb[0]:.2f} (needs 1.2): {'supported' if rs[0] / rb[0] >= 1.2 else 'not supported'}")
ag = [r for r in REPOS if res[(r, "verified")] and res[(r, "verified")][0] > 1.0 and dirs[(r, "verified")][0] and dirs[(r, "verified")][1] and dirs[(r, "verified")][0][0] > dirs[(r, "verified")][1][0]]
print(f"  SR5 repositories agreeing on radius above 1.0 and callers above callees: {ag} ({len(ag)} of 3; needs 3)")
print("  surprise bar: pooled radius below 1.1: " + ("MET" if pv[0] < 1.1 else "not met"))
