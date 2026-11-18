#!/usr/bin/env python3
"""The language result with the call graph admitting ambiguous edges (candidates up to 1, 3, 10, any). Hypotheses CG4-CG5: docs/sensor-overhaul/sensors/ripple_radius.md.

    python tools/sensor/lang_graph_sensitivity.py      (needs the caches of lang_validation.py)"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import lang_validation as LV  # noqa: E402

GROUPS = {"Python": ["sphinx", "scapy", "sqlmap"], "Go": ["prometheus"], "Java": ["commons-lang", "commons-io"], "Rust": ["ripgrep"], "C (blame causes)": ["dpdk", "curl"]}
MAXC = [1, 3, 10, 100000]
rng = np.random.default_rng(2982)


def main():
    data = {r: LV.build(r, 2500) for g in GROUPS.values() for r in g}
    res = {}
    for m in MAXC:
        os.environ["BLAST_MAXC"] = str(m)
        for g, rs in GROUPS.items():
            dfs = [LV.measure(r, *data[r])[0] for r in rs]
            res[(g, m)] = LV.summarize(pd.concat(dfs, ignore_index=True))
    f = lambda r: f"{r[0]:.2f} [{r[1]:.2f},{r[2]:.2f}]" if r else "n/a"  # noqa: E731
    for g in GROUPS:
        print(f"\n{g}")
        for m in MAXC:
            nm, no, sf, rr, far, _, nx = res[(g, m)]
            print(f"  candidates up to {m if m < 1000 else 'any':>4}: measured {nm}, outside {no}; within 1 {f(rr['either1'])}; within 2 {f(rr['either2'])}; callers1 {f(rr['callers1'])}; callees1 {f(rr['callees1'])}; other-file repairs (n {nx}) callers1 {f(far['callers1'])} callees1 {f(far['callees1'])}")
    print("\n=== VERDICTS ===")
    a, b = res[("Python", 1)][3]["either2"], res[("Python", 10)][3]["either2"]
    print(f"  CG4 pooled Python radius within 2 calls: confident only {a[0]:.2f}, up to 10 candidates {b[0]:.2f} ({100 * (b[0] / a[0] - 1):+.0f}%; needs within 20%): {'supported' if abs(b[0] / a[0] - 1) <= 0.2 else 'not supported'}")

    def ratio(k):
        far = res[("Python", k)][4]
        return far["callers1"][0] / far["callees1"][0] if far["callers1"] and far["callees1"] else float("nan")

    r1, r10 = ratio(1), ratio(10)
    print(f"  CG5 pooled Python callers1 over callees1, other-file repairs: confident only {r1:.2f}, up to 10 candidates {r10:.2f} ({r10 / r1:.2f} times; needs 1.2): {'supported' if r10 / r1 >= 1.2 else 'not supported'}")
    allm = [(g, m) for g in GROUPS for m in MAXC]
    print("  radius within 2 calls by language and graph: " + "; ".join(f"{g} " + " / ".join(f"{res[(g, m)][3]['either2'][0]:.2f}" for m in MAXC) for g in GROUPS))


if __name__ == "__main__":
    main()
