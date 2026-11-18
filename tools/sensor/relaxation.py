#!/usr/bin/env python3
"""Relaxation test (RX1-RX4, docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running): do repairs spread outward over time and settle?

    python tools/sensor/relaxation.py        (needs measure.pkl for linux and dpdk, and the pair lists, under /tmp/gitgalaxy-scratch/claude)"""
import collections
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402

BASE = "/tmp/gitgalaxy-scratch/claude"
SUF = os.environ.get("BLAST_SUFFIX", "")  # "_v" reads the verified-function measurements
DATA = {"kernel": (f"{BASE}/blast/linux{SUF}", f"{BASE}/argl/links_linux_all.json"), "dpdk": (f"{BASE}/blast/dpdk{SUF}", f"{BASE}/argl/links_dpdk.json")}
rng = np.random.default_rng(2982)
YEAR = 365.25


def main():
    res = {}
    for name, (d, lp) in DATA.items():
        df = pd.read_pickle(f"{d}/measure.pkl")
        df = df[df.status == "ok"].copy()
        out = df[df.nFo > 0].copy()
        print(f"\n########## {name}: {len(df)} measured pairs, {len(out)} with a fixed function outside the changed set ##########")
        # RX1: ratio by lag at distance 1, 2, 3
        print("  RX1 radius by lag (ratio against same-file; share within k calls):")
        lagb = [("under 30 d", out.lag < 30), ("30 to 365 d", (out.lag >= 30) & (out.lag < 365)), ("1 to 2 y", (out.lag >= 365) & (out.lag < 730)), ("over 2 y", out.lag >= 730)]
        r1 = {}
        for lab, m in lagb:
            line = f"    {lab:12s} n {int(m.sum()):5d} "
            for rel in ("either1", "either2", "either3"):
                r = BR.ratio(out[m], rel, "eB", rng)
                line += f"| {rel} {r[0]:.2f} [{r[1]:.2f},{r[2]:.2f}] " if r else f"| {rel} n/a "
                r1[(lab, rel)] = r
            print(line)
        a, b = r1[("under 30 d", "either1")], r1[("1 to 2 y", "either1")]
        a2, b2 = r1[("under 30 d", "either1")], r1[("over 2 y", "either1")]
        fast, slow = out[out.lag < 30], out[out.lag >= 365]
        rf, rs = BR.ratio(fast, "either1", "eB", rng), BR.ratio(slow, "either1", "eB", rng)
        print(f"    RX1: either1 ratio under 30 d {rf[0]:.2f} vs over a year {rs[0]:.2f}: fast/slow = {rf[0] / rs[0]:.2f} (needs at least 1.15)")
        res[(name, "RX1")] = rf[0] / rs[0] >= 1.15
        # RX2: paired within cause
        g = out.sort_values("lag").groupby("ind")
        pairs = [(x.iloc[0], x.iloc[-1]) for _, x in g if len(x) >= 2 and x.fix.nunique() >= 2]
        e1 = np.array([p[0].o_either2 for p in pairs])
        e2 = np.array([p[1].o_either2 for p in pairs])
        e1a = np.array([p[0].o_either1 for p in pairs])
        e2a = np.array([p[1].o_either1 for p in pairs])
        diff = e2 - e1
        bs = [rng.choice(diff, len(diff)).mean() for _ in range(1000)]
        print(f"  RX2: {len(pairs)} causes with two or more fixes outside the changed set; within 2 calls: earlier fix {100 * e1.mean():.1f}%, later fix {100 * e2.mean():.1f}% (difference {100 * diff.mean():+.1f} points, 95% interval {100 * np.percentile(bs, 2.5):+.1f} to {100 * np.percentile(bs, 97.5):+.1f}); within 1 call: {100 * e1a.mean():.1f}% -> {100 * e2a.mean():.1f}%; median lag earlier {np.median([p[0].lag for p in pairs]):.0f} d, later {np.median([p[1].lag for p in pairs]):.0f} d")
        res[(name, "RX2")] = diff.mean() <= -0.05
        # RX3 / RX4 from the pair list
        links = json.load(open(lp))
        by = collections.defaultdict(list)
        for p in links:
            by[p["ind"]].append(p["fix_ct"])
        counts = np.array([len(v) for v in by.values()])
        print(f"  RX3 chains: {len(counts)} causes with at least one named fix; fixes per cause: " + ", ".join(f"{k}: {int((counts == k).sum())}" for k in range(1, 6)) + f", 6+: {int((counts >= 6).sum())}")
        cont = []
        for k in range(1, 6):
            n1 = int((counts >= k).sum())
            n2 = int((counts >= k + 1).sum())
            cont.append(n2 / n1 if n1 else float("nan"))
        print("    P(at least k+1 | at least k): " + ", ".join(f"k={k}: {c:.3f}" for k, c in zip(range(1, 6), cont)))
        res[(name, "RX3")] = cont[0] > cont[1] > cont[2]
        # fix of fix: share of fixes that are themselves causes of a later fix
        fixes = {p["fix"] for p in links}
        inds = {p["ind"] for p in links}
        print(f"    share of causes that are themselves fixes (fix-of-fix): {100 * len(fixes & inds) / len(inds):.1f}%; share of fixes that have a fix of their own: {100 * len(fixes & inds) / len(fixes):.1f}%")
        # RX4: gaps, causes old enough, fixes within 3 years
        end = max(p["fix_ct"] for p in links)
        gaps = {1: [], 2: [], 3: []}
        for ind, v in by.items():
            ct = [p for p in links if False]
        ind_ct = {}
        for p in links:
            ind_ct[p["ind"]] = p["ind_ct"]
        for ind, v in by.items():
            if ind_ct[ind] > end - 3 * YEAR * 86400:
                continue
            fx = sorted(t for t in v if t - ind_ct[ind] <= 3 * YEAR * 86400)
            if len(fx) >= 3:
                gaps[1].append((fx[0] - ind_ct[ind]) / 86400)
                gaps[2].append((fx[1] - fx[0]) / 86400)
                gaps[3].append((fx[2] - fx[1]) / 86400)
        n3 = len(gaps[1])
        if n3 >= 30:
            m = {k: float(np.median(v)) for k, v in gaps.items()}
            print(f"  RX4: {n3} causes (3+ fixes within 3 y, cause at least 3 y before the end): median lag to fix 1 {m[1]:.0f} d, gap fix 1 to 2 {m[2]:.0f} d, gap 2 to 3 {m[3]:.0f} d")
            res[(name, "RX4")] = m[3] > m[2] > m[1]
        else:
            print(f"  RX4: only {n3} causes; not testable")
    print("\n=== VERDICTS (supported = True) ===")
    for k, v in res.items():
        print(f"  {k[0]:7s} {k[1]}: {'supported' if v else 'not supported'}")


if __name__ == "__main__":
    main()
