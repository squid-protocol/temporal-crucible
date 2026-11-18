#!/usr/bin/env python3
"""Back-test gate for 'where to look first' (docs/sensor-overhaul/sensors/suspects.md, section 11, fixed before running): held-out repositories, causes by blame, the validated
ranking (same file, then call distance, then size) against size alone, at function and file level.

    python tools/sensor/backtest_gate.py"""
import collections
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import lang_validation as LV  # noqa: E402
import retrieval_added_deleted as RAD  # noqa: E402
import retrieval_lift as RL  # noqa: E402

GROUPS = {"C": ["libgit2", "redis", "libxml2"], "Python": ["sphinx", "scapy", "sqlmap"], "Go": ["prometheus"]}
GATE = {"C": (0.30, 0.65), "Python": (0.25, 0.60), "Go": (0.25, 0.60)}


def rows_for(repo):
    pairs, info = LV.build(repo, 2500)
    import json
    sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
    cts = np.load(f"{LV.B}/blast/lang_{repo}_snapcts.npy") if __import__("os").path.exists(f"{LV.B}/blast/lang_{repo}_snapcts.npy") else None
    if cts is None:
        import subprocess
        cts = np.array([int(subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "show", "-s", "--format=%ct", x["commit"]], capture_output=True, text=True).stdout.strip()) for x in sn])
        np.save(f"{LV.B}/blast/lang_{repo}_snapcts.npy", cts)
    by = collections.defaultdict(list)
    for pid, p in enumerate(pairs):
        I, F = info[p["ind"]][0], info[p["fix"]][0]
        s = int(np.searchsorted(cts, p["ind_ct"], side="left"))
        if s < len(sn) and I and F and len(I) <= 60 and len(F) <= 30:
            by[s].append({"pid": pid, "I": I, "F": F})
    jobs = [(sn[s]["db"], it) for s, it in sorted(by.items())]
    rows, frows = [], []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for r in ex.map(RL.worker, jobs):
            rows += r
        for r in ex.map(RAD.file_worker, jobs):
            frows += r
    return rows, frows, len(pairs)


def main():
    sd = RL.CELLS[:, 2].astype(float)
    fl, ds = RL.CELLS[:, 0].astype(float), RL.CELLS[:, 1].astype(float)
    fr = {"size alone": sd, "call distance alone": -ds, "same file, distance, then size": fl * 1000 - ds * 100 + sd}
    flr = {"file size alone": RAD.FC[:, 2].astype(float), "event file, distance, then size": RAD.FC[:, 0] * 1000 - RAD.FC[:, 1] * 100.0 + RAD.FC[:, 2]}
    res = {}
    for g, repos in GROUPS.items():
        allr, allf = [], []
        for r in repos:
            rows, frows, npairs = rows_for(r)
            print(f"\n{r} ({g}): {npairs} blame pairs; {len(rows)} ranked (a repaired function outside the changed set exists in the graph); median candidates {int(np.median([x['C'].sum() for x in rows])) if rows else 0} functions", flush=True)
            if len(rows) >= 30:
                out = {nm: RL.evaluate(rows, s) for nm, s in fr.items()}
                w = RL.evaluate(rows, fr["call distance alone"], within=True)[0]
                fo = {nm: RAD.file_eval(frows, s) for nm, s in flr.items()}
                print("  functions: " + "; ".join(f"{nm} top 20 {100 * v[1]:.1f}% top 100 {100 * v[2]:.1f}% AUC {v[0]:.3f}" for nm, v in out.items()) + f"; call distance within-size AUC {w:.3f}")
                print("  files: " + "; ".join(f"{nm} top 10 n/a, top 20 {100 * v[1][20]:.1f}%" for nm, v in fo.items()))
            allr += rows
            allf += frows
        if not allr:
            continue
        out = {nm: RL.evaluate(allr, s) for nm, s in fr.items()}
        w = RL.evaluate(allr, fr["call distance alone"], within=True)[0]
        fo = {nm: RAD.file_eval(allf, s, ks=(5, 10, 20)) for nm, s in flr.items()}
        res[g] = (len(allr), out, w, fo)
        print(f"\n######## {g} pooled over {', '.join(repos)}: {len(allr)} pairs ########")
        for nm, v in out.items():
            print(f"  functions, {nm:32s} AUC {v[0]:.3f}  top 20 {100 * v[1]:5.1f}%  top 100 {100 * v[2]:5.1f}%")
        print(f"  functions, call distance alone within-size AUC {w:.3f}")
        for nm, v in fo.items():
            print(f"  files, {nm:34s} AUC {v[0]:.3f}  top 5 {100 * v[1][5]:5.1f}%  top 10 {100 * v[1][10]:5.1f}%  top 20 {100 * v[1][20]:5.1f}%")
    print("\n=== GATE (suspects.md section 11) ===")
    for g, (n, out, w, fo) in res.items():
        top20 = out["same file, distance, then size"][1]
        base = max(out["size alone"][1], 1e-6)
        t, wa = GATE[g]
        ok = top20 >= t and top20 / base >= 50 and w >= wa
        print(f"  {g}: top 20 {100 * top20:.1f}% (needs {100 * t:.0f}%), {top20 / base:.0f} times size alone (needs 50), within-size AUC {w:.3f} (needs {wa:.2f}), n {n}: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
