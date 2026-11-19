#!/usr/bin/env python3
"""A typical quarter of a repository: function births and deaths, edits by category, repeat spots. Descriptive (not pre-registered).
    python tools/sensor/typical_quarter.py dpdk mesa"""
import collections
import json
import pickle
import sqlite3
import subprocess
import sys

import numpy as np

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
LAST = 16


def files_of(db):
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    s = {r[0] for r in c.execute("SELECT file_path FROM file_data")}
    c.close()
    return s


def main():
    for repo in sys.argv[1:]:
        sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
        cts = np.load(f"{B}/blast/{repo}/snapshot_cts.npy")
        part = pickle.load(open(f"{B}/partition/{repo}.pkl", "rb"))
        cat, cited = part["cat"], part["cited"]
        touched = pickle.load(open(f"{B}/blast/{repo}/touched_all.pkl", "rb"))
        log = subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "log", "--no-merges", "--format=%H %ct"], capture_output=True, text=True).stdout.split("\n")
        ctime = {l.split()[0]: int(l.split()[1]) for l in log if l.strip()}
        # whole-history repair counts per function (fix commits)
        fixcount = collections.Counter()
        for s, k in cat.items():
            if k.startswith("fix"):
                for f in touched.get(s, []):
                    fixcount[tuple(f)] += 1
        rows = []
        prev_keys = prev_files = None
        for i in range(len(sn) - LAST - 1, len(sn)):
            g = BR.Graph(sn[i]["db"])
            keys = set(g.index)
            files = files_of(sn[i]["db"])
            if prev_keys is not None:
                lo, hi = cts[i - 1], cts[i]
                births, deaths = keys - prev_keys, prev_keys - keys
                names_prev = collections.Counter(k[1] for k in prev_keys)
                names_now = collections.Counter(k[1] for k in keys)
                r = {"funcs": len(keys), "births": len(births), "deaths": len(deaths)}
                r["birth_new_file_new_name"] = sum(1 for k in births if k[0] not in prev_files and k[1] not in names_prev)
                r["birth_existing_file_new_name"] = sum(1 for k in births if k[0] in prev_files and k[1] not in names_prev)
                r["birth_moved"] = sum(1 for k in births if k[1] in names_prev)
                r["death_file_removed_gone"] = sum(1 for k in deaths if k[0] not in files and k[1] not in names_now)
                r["death_file_kept_gone"] = sum(1 for k in deaths if k[0] in files and k[1] not in names_now)
                r["death_moved"] = sum(1 for k in deaths if k[1] in names_now)
                qc = [s for s, t in ctime.items() if lo < t <= hi]
                per = collections.defaultdict(set)
                for s in qc:
                    c = cat.get(s, "none")
                    grp = "sweep" if c == "sweep" else ("fix" if c.startswith("fix") else ("mechanical" if c in ("revert", "tests only", "comment or whitespace only", "formatting, docs, licence (subject)") else ("none" if c == "none" else "organic")))
                    for f in touched.get(s, []):
                        per[grp].add(tuple(f))
                r["commits"] = len(qc)
                r["edited_total"] = len(set().union(*per.values())) if per else 0
                for grp in ("sweep", "fix", "organic", "mechanical"):
                    r["edit_" + grp] = len(per[grp])
                cnt = collections.Counter(tuple(f) for s in qc for f in touched.get(s, []))
                r["edited_twice"] = sum(1 for v in cnt.values() if v >= 2)
                fx = [tuple(f) for s in qc if cat.get(s, "").startswith("fix") for f in touched.get(s, [])]
                r["fix_edits"] = len(fx)
                r["fix_in_repeat_spots"] = sum(1 for f in fx if fixcount[f] >= 2)
                r["fix_in_hot_spots"] = sum(1 for f in fx if fixcount[f] >= 5)
                r["org_also_fixed_same_q"] = len(per["organic"] & per["fix"])
                r["sweep_also_fixed_same_q"] = len(per["sweep"] & per["fix"])
                rows.append(r)
            prev_keys, prev_files = keys, files
        med = {k: float(np.median([r[k] for r in rows])) for k in rows[0]}
        print(f"\n##### {repo}: median over the last {len(rows)} quarters (functions in the graph: {med['funcs']:,.0f})")
        for k in ("commits", "edited_total", "edit_organic", "edit_sweep", "edit_fix", "edit_mechanical", "edited_twice", "births", "birth_new_file_new_name", "birth_existing_file_new_name", "birth_moved", "deaths", "death_file_removed_gone", "death_file_kept_gone", "death_moved", "fix_edits", "fix_in_repeat_spots", "fix_in_hot_spots", "org_also_fixed_same_q", "sweep_also_fixed_same_q"):
            print(f"  {k:32s} {med[k]:10,.0f}")
        hist = sum(fixcount.values())
        top = sorted(fixcount.values(), reverse=True)
        n = len(top)
        print(f"  whole history: {hist:,} fix edits in {n:,} distinct functions; functions fixed 2+ times hold {100 * sum(v for v in top if v >= 2) / hist:.0f}% of fix edits; top 1% of fixed functions hold {100 * sum(top[:max(n // 100, 1)]) / hist:.0f}%, top 10% hold {100 * sum(top[:n // 10]) / hist:.0f}%")


if __name__ == "__main__":
    main()
