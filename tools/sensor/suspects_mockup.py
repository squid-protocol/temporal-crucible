#!/usr/bin/env python3
"""Mock-up of a 'suspects if this breaks' list for real changes whose later fix is known (DPDK, trailer-named pairs; cause under 100 lines; a repaired function outside the changed
set). The ranking is the validated one: same file as a changed function, then call distance (1, 2, 3 calls, either direction), then function size. Reason tags per suspect.
The pairs are drawn with a fixed seed so the examples are not chosen by outcome; where the actual repaired function ranks is printed for every one.

    python tools/sensor/suspects_mockup.py [N] [SEED]"""
import json
import random
import sys

import numpy as np

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import lang_validation as LV  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
REPO = "dpdk"


def subj(sha):
    import subprocess
    return subprocess.run(["git", "-C", f"{BR.POOL}/{REPO}", "show", "-s", "--format=%h %s", sha], capture_output=True, text=True).stdout.strip()[:100]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 11
    pairs = json.load(open(f"{B}/argl/links_{REPO}.json"))
    sn = json.load(open(f"{BR.B}/scan_{REPO}/snapshots.json"))
    cts = np.load(f"{B}/blast/{REPO}/snapshot_cts.npy")
    pool = list(range(len(pairs)))
    random.Random(seed).shuffle(pool)
    shown = 0
    for pid in pool:
        p = pairs[pid]
        info = LV.commit_worker((f"{BR.POOL}/{REPO}", "c", [p["ind"], p["fix"]]))
        I, ci, _ = info[p["ind"]]
        F, _, _ = info[p["fix"]]
        s = int(np.searchsorted(cts, p["ind_ct"], side="left"))
        if s >= len(sn) or not I or not F or len(I) > 8 or ci >= 100:
            continue
        g = BR.Graph(sn[s]["db"])
        Iidx = np.array(sorted({g.index[k] for k in I if k in g.index}), dtype=np.int64)
        Fidx = np.array(sorted({g.index[k] for k in F if k in g.index}), dtype=np.int64)
        Fo = np.setdiff1d(Fidx, Iidx)
        if not len(Iidx) or not len(Fo):
            continue
        near = g.near(Iidx)
        keys = sorted(g.index, key=g.index.get)
        dist = np.full(g.n, 4, dtype=np.int64)
        for d, nm in ((3, "either3"), (2, "either2"), (1, "either1")):
            dist[near[nm]] = d
        samefile = np.isin(g.fid, np.unique(g.fid[Iidx]))
        callers1, callees1 = near["callers1"], near["callees1"]
        score = samefile.astype(np.int64) * 10**9 - dist * 10**6 + g.loc
        score[Iidx] = -10**12
        order = np.argsort(-score, kind="stable")
        rank = {int(i): r + 1 for r, i in enumerate(order)}
        files = {}
        for i in order[:2000]:
            f = keys[int(i)][0]
            files.setdefault(f, len(files) + 1)
        shown += 1
        print(f"\n================ example {shown} (pair {pid}) ================")
        print(f"CHANGE   {subj(p['ind'])}")
        print(f"  changed functions: " + ", ".join(f"{keys[int(i)][1]} ({keys[int(i)][0]})" for i in Iidx) + f"; {ci} lines")
        print("SUSPECTS IF THIS BREAKS (ranked: same file, then call distance, then size)")
        for r, i in enumerate(order[:12], 1):
            i = int(i)
            tags = []
            if samefile[i]:
                tags.append("same file as a changed function")
            if callers1[i]:
                tags.append("calls a changed function")
            if callees1[i]:
                tags.append("called by a changed function")
            if not (callers1[i] or callees1[i]) and dist[i] in (2, 3):
                tags.append(f"{dist[i]} calls from a changed function")
            print(f"  {r:2d}. {keys[i][1]:38s} {keys[i][0][:52]:52s} {int(g.loc[i]):4d} lines | " + "; ".join(tags))
        print(f"  ({g.n - len(Iidx)} candidate functions; {len(files)} files)")
        top_files = list(files)[:10]
        print("SUSPECT FILES (top 10): " + "; ".join(f.split('/')[-1] for f in top_files))
        print(f"WHAT ACTUALLY HAPPENED ({(p['fix_ct'] - p['ind_ct']) / 86400:.0f} days later): {subj(p['fix'])}")
        for i in Fo:
            i = int(i)
            ff = keys[i][0]
            print(f"  repaired {keys[i][1]} ({ff}): function rank {rank[i]} of {g.n - len(Iidx)}; its file ranks {files.get(ff, '>2000')} of {len(files)}")
        if shown >= n:
            break


if __name__ == "__main__":
    main()
