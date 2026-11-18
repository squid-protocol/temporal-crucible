#!/usr/bin/env python3
"""Combined watchlist coverage: share of named-cause pairs whose fixed function is on the list "changed functions + top k neighbours" (hypotheses C1-C4 in
docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running). No null models: the loop is ripple_links.analyse without the file-mate draws, so it is fast.

    python tools/sensor/ripple_coverage.py curl openssl freebsd-src"""
import collections
import json
import sys

import numpy as np

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import ripple_links as RL  # noqa: E402
import ripple_rank as RR  # noqa: E402  (its patch of RL.links for the trailer repositories runs on import when their names are in argv)

KS = (0, 5, 10, 20, 50)
LAG = (("under 30 days", 0, 30), ("30 to 365 days", 30, 365), ("a year or more", 365, 1e9))


def pairs(name):
    repo = f"{RL.POOL}/{name}"
    sn = json.load(open(f"{RL.B}/scan_{name}/snapshots.json"))
    cts = np.array([int(RL.git(repo, "show", "-s", "--format=%ct", x["commit"]).strip()) for x in sn])
    L = RL.links(name)
    out, stats = [], collections.Counter()
    for lk in L:
        s = int(np.searchsorted(cts, lk["ind_ct"], side="left"))
        if s >= len(sn):
            stats["no snapshot"] += 1
            continue
        I, F = RL.touched(repo, lk["ind"]), RL.touched(repo, lk["fix"])
        if not I or not F:
            stats["no function in a commit"] += 1
            continue
        if len(I) > 60 or len(F) > 30:
            stats["sweep"] += 1
            continue
        g = RL.graph(sn[s]["db"])
        nodes = g[0]
        Im, Fm = I & set(nodes), F & set(nodes)
        if not Im or not Fm:
            stats["not found in the snapshot"] += 1
            continue
        Fo = Fm - Im
        cov = {k: 1.0 for k in KS} if (Fm & Im) else None
        if cov is None:
            r = RR.rank_one({"graph": g, "Im": Im, "Fo": Fo})
            cov = {k: (0.0 if k == 0 else r["file+graph+size"][0][k]) for k in KS} if r else {k: 0.0 for k in KS}
        out.append({"repo": name, "lag": lk["lag"], "n_changed": len(Im), "cov": cov, "same": bool(Fm & Im)})
    return out, stats, len(L)


def show(label, rows, total):
    if not rows:
        return
    line = " ".join(f"k={k}: {100 * np.mean([r['cov'][k] for r in rows]):5.1f}%" for k in KS)
    print(f"  {label:42s} usable {len(rows):4d}: {line}")
    if total:
        print(f"  {'  (over all named pairs, misses counted)':42s} named {total:4d}: " + " ".join(f"k={k}: {100 * sum(r['cov'][k] for r in rows) / total:5.1f}%" for k in KS))


def main():
    names = [a for a in sys.argv[1:] if not a.startswith("--")]
    allrows, tot = [], 0
    for name in names:
        rows, stats, n = pairs(name)
        allrows += rows
        tot += n
        print(f"\n=== {name}: {n} named pairs, usable {len(rows)}; median changed functions per pair {int(np.median([r['n_changed'] for r in rows]))}; dropped {dict(stats)} ===", flush=True)
        show("all usable pairs", rows, n)
        for lab, lo, hi in LAG:
            show(f"fix {lab} after the change", [r for r in rows if lo <= r["lag"] < hi], 0)
    print(f"\n=== POOLED over {', '.join(names)} ===")
    show("all usable pairs", allrows, tot)
    for lab, lo, hi in LAG:
        show(f"fix {lab} after the change", [r for r in allrows if lo <= r["lag"] < hi], 0)
    print(f"  changed-set size: median {int(np.median([r['n_changed'] for r in allrows]))}, 75th percentile {int(np.percentile([r['n_changed'] for r in allrows], 75))}, 90th {int(np.percentile([r['n_changed'] for r in allrows], 90))}")


if __name__ == "__main__":
    main()
