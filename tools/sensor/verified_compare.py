#!/usr/bin/env python3
"""Repair radius on verified functions against the unverified figures; VR1-VR5 (docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running).
    python tools/sensor/verified_compare.py linux dpdk      (needs blast/<repo> and blast/<repo>_v measure.pkl; diff_feats.pkl from blast/<repo>)"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude/blast"
rng = np.random.default_rng(2982)
BANDS = [("under 20", lambda l: l < 20), ("20 to 99", lambda l: (l >= 20) & (l < 100)), ("100 to 499", lambda l: (l >= 100) & (l < 500)), ("500 or more", lambda l: l >= 500)]
res = {}
for repo in sys.argv[1:]:
    feats = pd.read_pickle(f"{B}/{repo}/diff_feats.pkl")
    out = {}
    for tag, d in (("unverified", repo), ("verified", repo + "_v")):
        m = pd.read_pickle(f"{B}/{d}/measure.pkl")
        m = m[m.status == "ok"].copy()
        m["lines"] = [feats[s]["n_add"] + feats[s]["n_rem"] if s in feats else np.nan for s in m.ind]
        out[tag] = m
    print(f"\n########## {repo} ##########")
    print(f"  measured pairs: unverified {len(out['unverified'])}, verified {len(out['verified'])} ({100 * (1 - len(out['verified']) / len(out['unverified'])):.1f}% lost); with a fixed function outside the changed set: {int((out['unverified'].nFo > 0).sum())} -> {int((out['verified'].nFo > 0).sum())}")
    both = set(out["unverified"].pid) & set(out["verified"].pid)
    print(f"  same-function share (all measured pairs): unverified {100 * out['unverified'].same_func.mean():.1f}%, verified {100 * out['verified'].same_func.mean():.1f}% (pairs in both: {len(both)})")
    r = {}
    for tag, m in out.items():
        o = m[m.nFo > 0]
        r[tag] = {rel: BR.ratio(o, rel, "eB", rng) for rel in ("either1", "either2", "either3", "callers1", "callees1")}
        print(f"  {tag:10s} " + "  ".join(f"{rel} {BR.fmt(r[tag][rel])}" for rel in ("either1", "either2")))
    rv, ru = r["verified"]["either2"][0], r["unverified"]["either2"][0]
    print(f"  VR1 radius within 2 calls: {ru:.2f} -> {rv:.2f} ({100 * (rv / ru - 1):+.1f}%): {'supported' if abs(rv / ru - 1) <= 0.10 else 'not supported'}")
    dsame = 100 * (out["verified"].same_func.mean() - out["unverified"].same_func.mean())
    print(f"  VR2 same-function share change {dsame:+.1f} points (needs +2): {'supported' if dsame >= 2 else 'not supported'}")
    lost = 1 - len(out["verified"]) / len(out["unverified"])
    print(f"  VR4 pairs lost {100 * lost:.1f}% (needs 20% or less): {'supported' if lost <= 0.2 else 'not supported'}")
    print("  by size of the causing change (either2), unverified -> verified:")
    band = {}
    for lab, f in BANDS:
        a = BR.ratio(out["unverified"][f(out["unverified"].lines) & (out["unverified"].nFo > 0)], "either2", "eB", rng)
        b = BR.ratio(out["verified"][f(out["verified"].lines) & (out["verified"].nFo > 0)], "either2", "eB", rng)
        band[lab] = (a, b)
        print(f"    {lab:12s} {BR.fmt(a)}  ->  {BR.fmt(b)}")
    vr3 = band["under 20"][1][0] / band["500 or more"][1][0]
    print(f"  VR3 ratio (under 20) / (500 or more), verified: {vr3:.2f} (needs 1.5): {'supported' if vr3 >= 1.5 else 'not supported'}")
    for tag, m in out.items():
        x = m[(m.nFo > 0) & (~m.same_file.astype(bool))]
        c1, c2 = BR.ratio(x, "callers1", "eB", rng), BR.ratio(x, "callees1", "eB", rng)
        print(f"  different-file fixes, {tag:10s} n {len(x)}: callers1 {c1[0]:.2f} [{c1[1]:.2f},{c1[2]:.2f}], callees1 {c2[0]:.2f} [{c2[1]:.2f},{c2[2]:.2f}]")
    x = out["verified"][(out["verified"].nFo > 0) & (~out["verified"].same_file.astype(bool))]
    c1, c2 = BR.ratio(x, "callers1", "eB", rng), BR.ratio(x, "callees1", "eB", rng)
    print(f"  VR5 caller direction survives: {'supported' if c1[0] > c2[0] else 'not supported'}")
    res[repo] = (abs(rv / ru - 1))
print("\n  VR1 worst relative move: " + ", ".join(f"{k} {100 * v:.1f}%" for k, v in res.items()) + " (surprise bar 25%)")
