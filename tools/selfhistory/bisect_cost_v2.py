#!/usr/bin/env python3
"""PASS-2 version (review fix: the lower bracket commit A is index 0 and is the known-uncrossed endpoint, so a step at the first commit after A is no longer skipped).
Exploratory bisect over first-parent commits in (A, B]: find the first commit where METRIC on TARGET crosses THRESH.

  bisect_cost.py A B TARGET THRESH [--metric cpu_s|files_mapped|pipeline_s] [--down] [--reps N]

Default direction: A fast/low, B slow/high ('crosses upward'); --down for the reverse. Assumes the crossing persists to B (checked
only at the endpoints). Every probe is printed with its CPU seconds and files mapped, so a ramp (many small steps) is visible
and not mistaken for one jump. Engines that do not run at a probed commit are skipped by probing neighbours."""
import argparse, statistics as st, subprocess
import speed_probe as sp

ap = argparse.ArgumentParser()
ap.add_argument("A"); ap.add_argument("B"); ap.add_argument("target"); ap.add_argument("thresh", type=float)
ap.add_argument("--metric", default="cpu_s"); ap.add_argument("--down", action="store_true"); ap.add_argument("--reps", type=int, default=1)
a = ap.parse_args()
commits = [subprocess.run(["git", "--git-dir", str(sp.MIRROR), "rev-parse", a.A], capture_output=True, text=True).stdout.strip()] + subprocess.run(
    ["git", "--git-dir", str(sp.MIRROR), "log", "--first-parent", "--reverse", "--format=%H", f"{a.A}..{a.B}"], capture_output=True, text=True).stdout.split()
print(len(commits), "commits in window; target", a.target, "metric", a.metric, "threshold", a.thresh, "down" if a.down else "up", flush=True)
cache = {}


def probe(i):
    if i in cache: return cache[i]
    sha = commits[i]; s = {"slot": f"b{sha[:9]}", "date": "bisect", "sha": sha}
    vals, files, cpu = [], [], []
    for rep in range(a.reps):
        r = sp.one_run(s, a.target, 400 + rep, True)
        if not r.get("exit") and r.get(a.metric) is not None:
            vals.append(r[a.metric]); files.append(r.get("files_mapped")); cpu.append(r.get("cpu_s"))
    subprocess.run(["git", "--git-dir", str(sp.MIRROR), "worktree", "remove", "--force", str(sp.ENG / s["slot"])], capture_output=True)
    v = st.median(vals) if vals else None
    cache[i] = (v, files[0] if files else None, st.median(cpu) if cpu else None)
    log = subprocess.run(["git", "--git-dir", str(sp.MIRROR), "log", "-1", "--format=%h %cd %s", "--date=short", sha], capture_output=True, text=True).stdout.strip()
    print(f"  idx {i:4d} {log[:92]:92s} {a.metric}={v} cpu={cache[i][2]} files={cache[i][1]}", flush=True)
    return cache[i]


def crossed(v):                      # has the metric reached the 'B side'?
    return v <= a.thresh if a.down else v >= a.thresh


lo, hi = 0, len(commits) - 1
while hi - lo > 1:
    mid = (lo + hi) // 2
    r = probe(mid)
    if r[0] is None:
        for d in (1, -1, 2, -2, 3, -3):
            j = mid + d
            if lo < j < hi and (r := probe(j))[0] is not None: mid = j; break
    if r[0] is None: print("cannot evaluate around", mid); break
    if crossed(r[0]): hi = mid
    else: lo = mid
print("FIRST COMMIT PAST THRESHOLD:", commits[hi])
print(subprocess.run(["git", "--git-dir", str(sp.MIRROR), "show", "--stat", "--no-renames", "--format=%h %cd%n%s%n%n%b", "--date=short", commits[hi]],
                     capture_output=True, text=True, errors="replace").stdout[:1800])
# confirm the boundary with the parent in the window (2 repeats each)
if hi > 0:
    print("boundary check (parent vs found commit), 2 repeats each:")
    a.reps = 2; cache.clear()
    for i in (hi - 1, hi): probe(i)
