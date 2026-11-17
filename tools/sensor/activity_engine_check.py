#!/usr/bin/env python3
"""Does `gitgalaxy activity` give the research mock-up's numbers? Recompute each file's readings the mock-up's way (activity_mockup.py: numpy searchsorted over
a forward, rename-following history) at the same commit and compare with the engine command's JSON, file by file.

    python tools/sensor/activity_engine_check.py REPO [COMMIT]          (REPO is a clone in the temporal-crucible pool; engine checkout via ENGINE env)"""
import collections
import json
import os
import subprocess
import sys

import numpy as np

POOL = "/srv/storage_16tb/projects/temporal-crucible-pool"
ENGINE = os.environ.get("ENGINE", "/srv/storage_16tb/projects/gitgalaxy-worktrees/include-counts")
PY = os.environ.get("ENGINE_PY", "/srv/storage_16tb/projects/gitgalaxy/venvs/selfscan/bin/python")
DAY = 86400
name = sys.argv[1]
repo = f"{POOL}/{name}"
rev = sys.argv[2] if len(sys.argv) > 2 else "HEAD"


def git(*a):
    return subprocess.run(["git", "-c", "core.quotepath=off", "-C", repo, *a], capture_output=True, text=True, errors="replace").stdout


sha = git("rev-parse", rev).strip()
T = int(git("show", "-s", "--format=%ct", sha).strip())
out = f"/tmp/gitgalaxy-scratch/claude/act_check_{name}.json"
subprocess.run(
    [PY, "-m", "gitgalaxy.cli", "activity", repo, "--rev", sha, "--json", out], cwd=ENGINE, env={**os.environ, "PYTHONPATH": ENGINE}, capture_output=True, check=True
)
eng = {r["path"]: r for r in json.load(open(out))["files"]}

# the mock-up's computation (activity_mockup.py), verbatim in logic
log = git("log", "--no-merges", "--reverse", "-M", "--name-status", "--format=@@%ct\t%ae", sha)
fid, nid, evid, au, cur = {}, 0, collections.defaultdict(list), collections.defaultdict(list), None
for ln in log.splitlines():
    if ln.startswith("@@"):
        t, a = ln[2:].split("\t")
        cur = (int(t), a.lower())
        au[cur[1]].append(cur[0])
    elif ln and cur:
        parts = ln.split("\t")
        st = parts[0][0]
        if st in "RC" and len(parts) == 3:
            old, new = parts[1], parts[2]
            i = fid.get(old)
            if i is None:
                i = nid
                nid += 1
            if st == "R":
                fid.pop(old, None)
            fid[new] = i
            evid[i].append(cur)
        elif st == "A" and len(parts) >= 2:
            i = nid
            nid += 1
            fid[parts[1]] = i
            evid[i].append(cur)
        elif st == "M" and len(parts) >= 2:
            i = fid.get(parts[1])
            if i is None:
                i = nid
                nid += 1
                fid[parts[1]] = i
            evid[i].append(cur)
        elif st == "D" and len(parts) >= 2:
            fid.pop(parts[1], None)
au = {a: np.array(sorted(v)) for a, v in au.items()}
times = {i: np.array([x[0] for x in sorted(v)]) for i, v in evid.items()}
for i in evid:
    evid[i].sort()
bad = collections.Counter()
checked = 0
for p, row in eng.items():
    i = fid.get(p)
    arr = times.get(i)
    n = int(np.searchsorted(arr, T, side="right"))
    lo = lambda d: int(n - np.searchsorted(arr[:n], T - d * DAY, side="right"))  # noqa: E731
    recent = [x[1] for x in evid[i][:n] if x[0] > T - 365 * DAY]
    c = collections.Counter(recent)
    top = c.most_common(1)[0][0] if c else evid[i][n - 1][1]
    owner = bool(len(au.get(top, [])) and (au[top] <= T).any() and au[top][au[top] <= T][-1] > T - 2 * 365.25 * DAY)
    want = {
        "commits_90d": lo(90),
        "commits_365d": lo(365),
        "commits_lifetime": n,
        "age_years": (T - arr[0]) / (365.25 * DAY),
        "days_since_last_change": (T - arr[n - 1]) / DAY,
        "authors_365d": len(c),
        "top_author_share": (max(c.values()) / len(recent)) if recent else None,
        "owner_active": owner,
    }
    checked += 1
    for k, v in want.items():
        g = row[k]
        ok = (g is None and v is None) or (g is not None and v is not None and abs(float(g) - float(v)) <= {"age_years": 0.006, "top_author_share": 0.0006, "days_since_last_change": 0.051}.get(k, 0))
        if not ok:
            bad[k] += 1
print(f"{name} at {sha[:10]}: {checked} files compared; fields that differ: {dict(bad) or 'none'}")
