#!/usr/bin/env python3
"""EXPLORATORY lattice-position stability (plan: docs/self_lattice_and_radius_plan.md, section A, declared before these numbers)."""
import sys, pickle, json, datetime as dt, collections
sys.path.insert(0, "/srv/storage_16tb/projects/structural-fingerprint-scanner/src")
from pathlib import Path
import numpy as np
H = Path("/srv/storage_16tb/projects/gitgalaxy-history")
led = pickle.load(open(H / "evo" / "ledger_all.pkl", "rb")); S = len(led.ids)
date = [dt.date.fromisoformat(s.label) for s in led.snapshots]
def unit(p):
    q = p.replace("backend/", "gitgalaxy/", 1) if p.startswith("backend/") else p
    return q.startswith("gitgalaxy/") and "/tests/" not in q and "/standards/" not in q and "gitgalaxy_standards" not in q and not q.endswith("__init__.py")
def era(d):
    return "gemini" if d < dt.date(2026, 7, 6) else "transition" if d < dt.date(2026, 7, 22) else "claude" if d < dt.date(2026, 9, 27) else "fleet"
V, LOC = [], []
for s in range(S):
    sn = led._snaps[s]; r = sn.view.rows
    V.append(np.asarray(sn.table.vectors)[r].astype(np.float32)); LOC.append(np.asarray(sn.table.loc)[r].astype(float))
pos = [dict((int(l), i) for i, l in enumerate(led.ids[s])) for s in range(S)]
first = {}
for s in range(S):
    for i, l in enumerate(led.ids[s]): first.setdefault(int(l), (s, i))
# typical spacing: median distance between a function and its nearest other function in the final snapshot (sample), to put displacements in context
rng = np.random.default_rng(2982); v = V[-1]; idx = rng.choice(len(v), 600, replace=False)
nn = []
for i in idx:
    d = np.linalg.norm(v - v[i], axis=1); d[i] = np.inf; nn.append(d.min())
ref = {"nearest_neighbour_median": float(np.median(nn)), "random_pair_median": float(np.median([np.linalg.norm(v[a] - v[b]) for a, b in rng.integers(0, len(v), (600, 2)) if a != b]))}
res = {k: collections.defaultdict(list) for k in (7, 30, 90)}; size = {k: collections.defaultdict(list) for k in (7, 30, 90)}
for l, (b, i) in first.items():
    if b == 0 or not unit(led.keys[b][i][0]): continue
    for k in (7, 30, 90):
        tgt = date[b] + dt.timedelta(days=k); s2 = next((s for s in range(b + 1, S) if date[s] >= tgt), None)
        if s2 is None: continue
        j = pos[s2].get(l)
        if j is None: continue
        d = float(np.linalg.norm(V[s2][j] - V[b][i])); e = era(date[b])
        res[k][e].append(d); res[k]["all"].append(d); size[k][e].append((LOC[b][i], d))
out = {"reference_spacing": ref, "displacement": {}}
print("context: nearest-neighbour distance in the final snapshot (median) = %.2f; random pair = %.2f" % (ref["nearest_neighbour_median"], ref["random_pair_median"]))
print("\nDISPLACEMENT FROM BIRTH POSITION (37-d reference frame, z-units): median [p25-p75] p90, share that did not move at all, n")
for k in (7, 30, 90):
    for e in ("all", "gemini", "claude", "fleet"):
        a = np.array(res[k].get(e, []))
        if len(a) >= 30:
            print(f" {k:2d}d {e:7s} n={len(a):5d}: median {np.median(a):5.2f} [{np.percentile(a,25):5.2f}-{np.percentile(a,75):5.2f}] p90 {np.percentile(a,90):6.2f} | did not move {np.mean(a<1e-6):.0%}")
            out["displacement"][f"{k}d_{e}"] = {"n": len(a), "median": float(np.median(a)), "p25": float(np.percentile(a, 25)), "p75": float(np.percentile(a, 75)), "p90": float(np.percentile(a, 90)), "zero_share": float(np.mean(a < 1e-6))}
m30, m90 = np.median(res[30]["all"]), np.median(res[90]["all"])
print("\nL1: median displacement at 30d / at 90d = %.2f / %.2f = %.2f  (supports >= 0.70, refuted < 0.50)" % (m30, m90, m30 / m90))
# also among movers only
mv30 = [x for x in res[30]["all"] if x > 1e-6]; mv90 = [x for x in res[90]["all"] if x > 1e-6]
print("   among functions that moved at all: median 30d %.2f (n=%d), 90d %.2f (n=%d), ratio %.2f" % (np.median(mv30), len(mv30), np.median(mv90), len(mv90), np.median(mv30) / np.median(mv90)))
def spearman(x, y):
    from scipy.stats import spearmanr
    return spearmanr(x, y)
try:
    print("\nL2: rank correlation of 30-day displacement with lines at birth (within era)")
    for e in ("gemini", "claude", "fleet"):
        a = np.array(size[30][e])
        if len(a) >= 50:
            r = spearman(a[:, 0], a[:, 1]); print(f"   {e:7s} n={len(a):5d} rho={r.correlation:+.2f} (p={r.pvalue:.1e})"); out.setdefault("L2", {})[e] = {"n": len(a), "rho": float(r.correlation)}
except Exception as ex:
    print("   (scipy unavailable:", ex, ")")
json.dump(out, open(H / "evo" / "lattice_stability.json", "w"), indent=1)
