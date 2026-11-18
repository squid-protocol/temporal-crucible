#!/usr/bin/env python3
"""Co-change control for the repair radius. Hypotheses CC1-CC3: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.

For each named-cause pair the co-change set = functions that changed in the same commit as any function the causing commit changed, in commits strictly before
the causing commit (all prior history; commits touching more than MAXCO functions are left out). Measured with the same exact same-file baseline as blast_radius.py:
the fixed function (outside the changed set) is (a) in the co-change set, (b) within 2 calls and NOT in it, (c) in it and NOT within 2 calls.

    python tools/sensor/cochange_control.py REPO TAG PAIRS.json OUTDIR      (OUTDIR: the blast_radius.py output directory of the repo; run that first)"""
import bisect
import collections
import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import ripple_forward as RF  # noqa: E402

MAXCO = 40


def main():
    repo, tag, pairs_path, out = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4])
    lang = "c"
    pairs = json.load(open(pairs_path))
    log = subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "log", "--no-merges", "--format=%H %ct"], capture_output=True, text=True).stdout.split("\n")
    allc = [(l.split()[0], int(l.split()[1])) for l in log if l.strip()]
    allc.sort(key=lambda x: x[1])
    shas = [a for a, _ in allc]
    cts = np.array([b for _, b in allc])
    print(f"{repo}: {len(shas)} non-merge commits; reading the functions each touched (one git pass, cached)", flush=True)
    touched = BR.touched_all(repo, shas, lang, out / "touched_all.pkl")
    idx = collections.defaultdict(list)  # function key -> commit positions (ascending, as shas are time-sorted)
    for ci, s in enumerate(shas):
        t = touched[s]
        if 0 < len(t) <= MAXCO:
            for k in t:
                idx[k].append(ci)
    pos = {s: i for i, s in enumerate(shas)}
    sn = json.load(open(f"{BR.B}/scan_{tag}/snapshots.json"))
    snap_cts = np.load(out / "snapshot_cts.npy")
    by_snap, meta = collections.defaultdict(list), []
    for pid, p in enumerate(pairs):
        s = int(np.searchsorted(snap_cts, p["ind_ct"], side="left"))
        I, F = touched.get(p["ind"], []), touched.get(p["fix"], [])
        if s >= len(sn) or not I or not F or len(I) > 60 or len(F) > 30:
            continue
        cut = bisect.bisect_left(cts, p["ind_ct"])
        co = set()
        for k in I:
            lst = idx.get(k, [])
            for ci in lst[: bisect.bisect_left(lst, cut)]:
                if shas[ci] != p["ind"]:
                    co.update(touched[shas[ci]])
        by_snap[s].append({"pid": pid, "I": I, "F": F, "CO": sorted(co)})
        meta.append({"pid": pid, "lag": p["lag"], "ind": p["ind"], "fix": p["fix"]})
    print(f"{sum(len(v) for v in by_snap.values())} pairs to measure in {len(by_snap)} snapshots", flush=True)
    jobs = [(sn[s]["db"], sn[s - 1]["db"] if s >= 1 else None, items) for s, items in sorted(by_snap.items())]
    rows = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for r in ex.map(BR.measure_snapshot, jobs):
            rows += r
    df = pd.DataFrame(rows).merge(pd.DataFrame(meta), on="pid")
    df.to_pickle(out / "cochange.pkl")
    ok = df[(df.status == "ok") & (df.nFo > 0)]
    rng = np.random.default_rng(2982)
    print(f"\n=== {repo}: {len(ok)} pairs with a fixed function outside the changed set; {int((ok.co_n == 0).sum())} have no earlier co-change history for the changed functions (median co-change set {int(ok.co_n.median())} functions) ===")
    for lab, d in (("all pairs", ok), ("pairs whose changed functions have co-change history", ok[ok.co_n > 0])):
        print(f"  {lab} ({len(d)}):")
        for nm, rel in (("repair radius (within 2 calls)", "either2"), ("(a) in the co-change set", "cochange"), ("(b) within 2 calls, NOT in the co-change set", "near2_nocochange"), ("(c) in the co-change set, NOT within 2 calls", "cochange_notnear2")):
            print(f"    {nm:48s} {BR.fmt(BR.ratio(d, rel, 'eB', rng))}")
    hit = ok[ok.o_either2 == 1]
    print(f"\n  of {len(hit)} pairs with a fixed function within 2 calls, {100 * (hit.o_both == 1).mean():.0f}% also have one in the co-change set (both signals)")
    hit2 = ok[ok.o_cochange == 1]
    print(f"  of {len(hit2)} pairs with a fixed function in the co-change set, {100 * (hit2.o_both == 1).mean():.0f}% also have one within 2 calls")


if __name__ == "__main__":
    main()
