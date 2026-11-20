#!/usr/bin/env python3
"""Exploratory bisect: first commit (first-parent) in (A, B] at which the 'onepl' control (one file per language) costs >= THRESH CPU seconds."""
import json, subprocess, sys, shutil, statistics as st
import speed_probe as sp
A, B, THRESH = sys.argv[1], sys.argv[2], float(sys.argv[3])
commits = subprocess.run(["git","--git-dir",str(sp.MIRROR),"log","--first-parent","--reverse","--format=%H",f"{A}..{B}"],capture_output=True,text=True).stdout.split()
print(len(commits),"commits in window", flush=True)
cache = {}
def cost(i):
    if i in cache: return cache[i]
    sha = commits[i]; s = {"slot": f"b{sha[:9]}", "date": "bisect", "sha": sha}
    vals = []
    for rep in (1, 2):
        r = sp.one_run(s, "onepl", 200 + rep, True)
        if r.get("exit"): vals.append(None)
        else: vals.append(r["cpu_s"])
    ok = [v for v in vals if v is not None]
    c = st.median(ok) if ok else None
    subprocess.run(["git","--git-dir",str(sp.MIRROR),"worktree","remove","--force",str(sp.ENG / s["slot"])],capture_output=True)
    cache[i] = c
    log = subprocess.run(["git","--git-dir",str(sp.MIRROR),"log","-1","--format=%h %cd %s","--date=short",sha],capture_output=True,text=True).stdout.strip()
    print(f"  idx {i:4d} {log[:100]}  cpu={c}", flush=True)
    return c
lo, hi = 0, len(commits) - 1           # assume commits[lo] fast, commits[hi] slow
while hi - lo > 1:
    mid = (lo + hi) // 2
    c = cost(mid)
    if c is None:                       # engine did not run at this commit: probe neighbours
        for d in (1, -1, 2, -2, 3, -3):
            j = mid + d
            if lo < j < hi and (c := cost(j)) is not None: mid = j; break
    if c is None: print("cannot evaluate around", mid); break
    if c >= THRESH: hi = mid
    else: lo = mid
print("FIRST SLOW COMMIT:", commits[hi])
print(subprocess.run(["git","--git-dir",str(sp.MIRROR),"show","--stat","--format=%H%n%cd%n%s%n%b","--date=iso","--no-renames",commits[hi]],capture_output=True,text=True,errors="replace").stdout[:2500])
