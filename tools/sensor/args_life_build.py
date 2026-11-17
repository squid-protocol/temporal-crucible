#!/usr/bin/env python3
"""Build the per-lineage argument-count history of one repository: the function ledger (lineage ids across snapshots) joined to each snapshot's
function_data.args, loc and path. Cached as a pickle. Exploratory (see docs/sensor-overhaul/sensors/args_over_life.md).

    python tools/sensor/args_life_build.py REPO      -> /tmp/gitgalaxy-scratch/claude/argl/REPO.pkl"""
import collections
import json
import pickle
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = "/srv/storage_16tb/projects"
B = f"{ROOT}/curl_call_graph_evolution/turn_v2"
POOL = f"{ROOT}/temporal-crucible-pool"
sys.path.insert(0, f"{ROOT}/structural-fingerprint-scanner/src")
from structural_fingerprint import ledger as LG  # noqa: E402

name = sys.argv[1]
sn = json.load(open(f"{B}/scan_{name}/snapshots.json"))
t0 = time.time()
snaps = [LG.Snapshot(Path(x["db"]), x["commit"], x.get("label", "")) for x in sn]
led = LG.build_ledger(Path(f"{POOL}/{name}"), snaps, progress=lambda i, n: print(f"{name} pair {i}/{n} {time.time()-t0:.0f}s", file=sys.stderr, flush=True) if i % 10 == 0 else None)
cts = [int(subprocess.run(["git", "-C", f"{POOL}/{name}", "show", "-s", "--format=%ct", x["commit"]], capture_output=True, text=True).stdout.strip()) for x in sn]
rows = []  # (snapshot, lineage, args, loc, path, name)
for s, snap in enumerate(led._snaps):
    con = sqlite3.connect(f"file:{snaps[s].scan}?mode=ro", uri=True)
    files = {r[0]: r[1] for r in con.execute("SELECT id, file_path FROM file_data")}
    by_key = collections.defaultdict(list)
    for fid, fname, loc, args in con.execute("SELECT file_id, func_name, loc, args FROM function_data ORDER BY id"):
        if fid in files and (loc or 0) >= 3:
            by_key[(files[fid], fname)].append((int(args or 0), int(loc or 0)))
    con.close()
    seen = collections.Counter()
    for i, k in enumerate(led.keys[s]):
        j = seen[k]
        seen[k] += 1
        r = by_key.get(k, [])
        if j < len(r):
            rows.append((s, int(led.ids[s][i]), r[j][0], r[j][1], k[0], k[1]))
pickle.dump({"name": name, "ct": cts, "rows": rows, "stages": [list(st) for st in led.stage]}, open(f"/tmp/gitgalaxy-scratch/claude/argl/{name}.pkl", "wb"))
print(name, "snapshots", len(sn), "function-snapshots", len(rows), "lineages", led.n_lineages, f"{time.time()-t0:.0f}s")
