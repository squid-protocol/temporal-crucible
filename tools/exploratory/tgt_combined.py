"""EXPLORATORY (not registered; follows TGT-H1..H3): does 'named platform first, then size' rank a platform fix's
files better than size alone? Same commits and candidates as tools/tgt_eval.py.

    python tools/exploratory/tgt_combined.py      (run from the repo root)
"""
import json, multiprocessing, sys
from collections import defaultdict
import numpy as np
sys.path.insert(0, "tools")
import tgt_eval as T
from frec_eval import auc

def one(task):
    r = T.one(task)
    if r is None:
        return None
    repo_name, exts, e, fam, pool_fams = task
    repo = T.POOL_DIR / repo_name
    parent = T._git(repo, "rev-parse", f"{e['sha']}^").strip()
    files = [p for p in T._git(repo, "-c", "core.quotepath=off", "ls-tree", "-r", "--name-only", parent).splitlines() if p.endswith(exts)]
    lines = {}
    for ln in T._git(repo, "-c", "core.quotepath=off", "grep", "-c", "", parent, "--", *[f"*{x}" for x in exts]).splitlines():
        _, _, rest = ln.partition(":"); p, _, n = rest.rpartition(":")
        if n.isdigit(): lines[p] = int(n)
    fc, pc = defaultdict(int), defaultdict(int)
    for rec in T._git(repo, "-c", "core.quotepath=off", "grep", "-n", "--null", "-P", "-e", T.PATTERNS["P"], "-e", T.FAM_GREP, parent, "--", *[f"*{x}" for x in exts]).splitlines():
        parts = rec.split("\0")
        if len(parts) < 3: continue
        path = parts[0].split(":", 1)[1]
        if T.P_RE.search(parts[2]): pc[path] += 1
        if T.MAC[fam].search(parts[2]): fc[path] += 1
    y = np.array([1.0 if p in set(e["c_files"]) else 0.0 for p in files])
    loc = np.array([float(max(lines.get(p, 0), 1)) for p in files])
    has_f = np.array([fc.get(p, 0) > 0 for p in files], dtype=float)
    has_p = np.array([pc.get(p, 0) > 0 for p in files], dtype=float)
    big = loc.max() + 1
    return {**r, "lex_f": auc(has_f * big + loc, y), "lex_p": auc(has_p * big + loc, y)}

tasks = []
for repo, exts in T.REPOS.items():
    for e in json.load(open(f"events/{repo}_xc.json"))["events"]:
        if e["class"] == "extrinsic":
            fams = [f for f, rx in T.SUBJ.items() if rx.search(e["subject"])]
            if len(fams) == 1: tasks.append((repo, exts, e, fams[0]))
pool = sorted({t[3] for t in tasks})
with multiprocessing.get_context("fork").Pool(6) as p:
    res = [x for x in p.imap_unordered(one, [(*t, pool) for t in tasks], chunksize=4) if x]
print(f"{len(res)} commits")
for lab, k in (("size alone", "auc_size"), ("generic platform conditionals", "auc_p"), ("named platform conditionals", "auc_f"),
               ("files with ANY platform conditional first, then size", "lex_p"), ("files with the NAMED platform's conditional first, then size", "lex_f")):
    print(f"| {lab} | {np.mean([x[k] for x in res]):.3f} |")
print("windows only:", {k: round(float(np.mean([x[k] for x in res if x['family']=='windows'])),3) for k in ("auc_size","lex_p","lex_f")})
