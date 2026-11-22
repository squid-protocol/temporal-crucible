#!/usr/bin/env python3
"""EXPLORATORY evolution analysis of GitGalaxy on itself, engine code only (Amendment 1 unit rules). Reads evo/ledger_all.pkl.
Units (declared here, before reading results): ENGINE = functions whose path at the time is under gitgalaxy/ or backend/, excluding tests/, any /standards/ or
gitgalaxy_standards path (pattern tables), __init__.py, and anything else (vendored trees, site/, docs/, estate/...). SCAN = ENGINE minus gitgalaxy/tools/; TOOLS = gitgalaxy/tools/.
Eras (HYPOTHESES.md GG-H1/H2/FLT-H1): Gemini < 2026-07-06; Claude 2026-07-22..2026-09-26; fleet >= 2026-09-27; 07-06..07-21 = transition (reported, not assigned)."""
import sys, pickle, json, datetime as dt, collections
import numpy as np
sys.path.insert(0, "/srv/storage_16tb/projects/structural-fingerprint-scanner/src")
from pathlib import Path
H = Path("/srv/storage_16tb/projects/gitgalaxy-history")
led = pickle.load(open(H / "evo" / "ledger_all.pkl", "rb"))
S = len(led.ids)
date = [dt.date.fromisoformat(s.label) for s in led.snapshots]
def unit(path):
    p = path.replace("backend/", "gitgalaxy/", 1) if path.startswith("backend/") else path
    if not p.startswith("gitgalaxy/") or "/tests/" in p or p.startswith("tests/") or "/standards/" in p or "gitgalaxy_standards" in p or p.endswith("__init__.py"): return None
    return "TOOLS" if p.startswith("gitgalaxy/tools/") else "SCAN"
def era(d):
    if d < dt.date(2026, 7, 6): return "gemini"
    if d < dt.date(2026, 7, 22): return "transition"
    if d < dt.date(2026, 9, 27): return "claude"
    return "fleet"
U = [np.array([unit(k[0]) or "" for k in led.keys[s]]) for s in range(S)]
files = [collections.defaultdict(set) for _ in range(S)]
for s in range(S):
    for i, (p, n) in enumerate(led.keys[s]): files[s][p].add(i)
# per-snapshot measurement arrays aligned to ids
meas = []
for s in range(S):
    sn = led._snaps[s]; r = sn.view.rows
    meas.append((np.asarray(sn.table.loc)[r].astype(float), np.asarray(sn.table.vectors)[r].astype(float)))
out = {"snapshots": S, "dates": [str(d) for d in date]}
def sel(s, which): return np.flatnonzero((U[s] != "") if which == "ENGINE" else (U[s] == which))
# 1. size and growth
out["counts"] = {w: [int(len(sel(s, w))) for s in range(S)] for w in ("ENGINE", "SCAN", "TOOLS")}
# 2. births (stage startswith birth, s>=1) split by file existing in s-1; deaths split by file still existing in s+1
def birth_death(which):
    rows = []
    for s in range(1, S):
        ix = sel(s, which); b_new = b_old = 0
        for i in ix:
            if led.stage[s][i].startswith("birth"):
                if led.keys[s][i][0] in files[s - 1]: b_old += 1
                else: b_new += 1
        rows.append((s, b_new, b_old))
    drows = []
    for s in range(0, S - 1):
        ix = sel(s, which); d_file = d_in = 0
        for i in ix:
            if i not in led.links[s]:
                if led.keys[s][i][0] in files[s + 1]: d_in += 1
                else: d_file += 1
        drows.append((s, d_file, d_in))
    return rows, drows
agg = {}
for w in ("ENGINE", "SCAN", "TOOLS"):
    b, d = birth_death(w)
    byera = collections.defaultdict(lambda: [0, 0, 0, 0])
    for s, bn, bo in b: e = era(date[s]); byera[e][0] += bn; byera[e][1] += bo
    for s, df, di in d: e = era(date[s]); byera[e][2] += df; byera[e][3] += di
    tot = [sum(v[i] for v in byera.values()) for i in range(4)]
    agg[w] = {"all": tot, **{e: v for e, v in byera.items()}}
out["births_deaths"] = {w: {e: {"births_new_file": v[0], "births_existing_file": v[1], "deaths_file_removed": v[2], "deaths_in_surviving_file": v[3]} for e, v in a.items()} for w, a in agg.items()}
# 3. settle-in / survival, lineage level, engine units by path at birth
first = {}
for s in range(S):
    for i, lid in enumerate(led.ids[s]):
        if int(lid) not in first: first[int(lid)] = (s, i)
def settle(which, ks=(7, 30, 90)):
    res = {k: collections.defaultdict(lambda: [0, 0, 0]) for k in ks}  # per era: [eligible, alive, unchanged]
    pos = [dict() for _ in range(S)]
    for s in range(S):
        for i, lid in enumerate(led.ids[s]): pos[s][int(lid)] = i
    for lid, (b, i) in first.items():
        if b == 0: continue
        if which == "ENGINE":
            if U[b][i] == "": continue
        elif U[b][i] != which: continue
        for k in ks:
            tgt = date[b] + dt.timedelta(days=k)
            s2 = next((s for s in range(b + 1, S) if date[s] >= tgt), None)
            if s2 is None: continue
            e = era(date[b]); r = res[k][e]; r[0] += 1
            j = pos[s2].get(lid)
            if j is not None:
                r[1] += 1
                l0, v0 = meas[b][0][i], meas[b][1][i]; l1, v1 = meas[s2][0][j], meas[s2][1][j]
                if l0 == l1 and np.allclose(v0, v1): r[2] += 1
    return {str(k): {e: {"eligible": v[0], "alive": v[1], "unchanged_of_alive": v[2]} for e, v in d.items()} for k, d in res.items()}
out["settle"] = {w: settle(w) for w in ("ENGINE", "SCAN")}
# 4. orchestrator and hub-candidate files: size, functions, mean function size, in/out degree rank among engine files (edge counts from scan db)
import sqlite3, glob
targets = ["gitgalaxy/galaxyscope.py", "gitgalaxy/cobol_refractor_controller.py", "gitgalaxy/cobol_to_java_controller.py", "gitgalaxy/core/detector.py"]
def canon(p): return p.replace("backend/", "gitgalaxy/", 1) if p.startswith("backend/") else p
dbs = sorted(glob.glob(str(H / "dbs" / "*.db")))
hub = {t: [] for t in targets}
for s in range(0, S, 6):
    c = sqlite3.connect(f"file:{dbs[s]}?mode=ro&immutable=1", uri=True)
    fl = {r[0]: (canon(r[1]), r[2] or 0, r[3] or 0) for r in c.execute("select id,file_path,coding_loc,function_count from file_data")}
    eng = {fid: v for fid, v in fl.items() if unit(v[0])}
    indeg, outdeg = collections.Counter(), collections.Counter()
    for a, b in c.execute("select src_file_id,dst_file_id from edge_data"):
        if a in eng and b in eng: outdeg[a] += 1; indeg[b] += 1
    n = len(eng)
    for t in targets:
        fid = next((f for f, v in eng.items() if v[0] == t), None)
        if fid is None: hub[t].append({"date": str(date[s]), "present": False, "engine_files": n}); continue
        ins = sorted(indeg.values(), reverse=True); outs = sorted(outdeg.values(), reverse=True)
        rin = 1 + sum(1 for v in indeg.values() if v > indeg[fid]); rout = 1 + sum(1 for v in outdeg.values() if v > outdeg[fid])
        v = eng[fid]; hub[t].append({"date": str(date[s]), "present": True, "engine_files": n, "loc": int(v[1]), "funcs": int(v[2]), "mean_func_loc": round(v[1] / max(v[2], 1), 1), "fan_in": indeg[fid], "fan_out": outdeg[fid], "rank_in": rin, "rank_out": rout})
    c.close()
out["hubs"] = hub
json.dump(out, open(H / "evo" / "evolution_results.json", "w"), indent=1)
print("done")
