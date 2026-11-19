#!/usr/bin/env python3
"""DOOM-R3: does a sibling lineage's repair history beat the local call graph? Hypotheses CP1-CP4: docs/sensor-overhaul/sensors/doom_ports_plan.md section 11, fixed before running.
    python tools/sensor/doom_r3.py"""
import bisect
import collections
import json
import math
import subprocess
import sys

import numpy as np
from scipy.stats import rankdata

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import doom_r1 as D  # noqa: E402
import lang_validation as LV  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
INF = 10**18
KS = (10, 20, 100)


def main():
    g0 = BR.Graph(D.REFDB)
    refnames = {D.norm(n) for (p, n), i in g0.index.items() if g0.loc[i] >= 3}
    data = {}
    for repo in D.LIN:
        pairs, info = LV.build(repo, 3000)
        pair_first, hot_times, fixseen = {}, collections.defaultdict(list), set()
        for p in pairs:
            Fn = {D.norm(x[1]) for x in info[p["fix"]][0]} & refnames
            In = {D.norm(x[1]) for x in info[p["ind"]][0]} & refnames
            if p["fix"] not in fixseen:
                fixseen.add(p["fix"])
                for gname in Fn:
                    hot_times[gname].append(p["fix_ct"])
            for f in In:
                for gname in Fn:
                    if gname != f:
                        k = (f, gname)
                        if p["fix_ct"] < pair_first.get(k, INF):
                            pair_first[k] = p["fix_ct"]
        for v in hot_times.values():
            v.sort()
        data[repo] = {"pairs": pairs, "info": info, "pair_first": pair_first, "hot": hot_times}
    res = {}
    for L in D.LIN:
        sibs = [r for r in D.LIN if r != L]
        pairs, info = data[L]["pairs"], data[L]["info"]
        sn = json.load(open(f"{BR.B}/scan_{L}/snapshots.json"))
        cf = f"{B}/blast/lang_{L}_snapcts.npy"
        cts = np.load(cf)
        by = collections.defaultdict(list)
        for p in pairs:
            I, F = info[p["ind"]][0], info[p["fix"]][0]
            s = int(np.searchsorted(cts, p["ind_ct"], side="left"))
            if s < len(sn) and I and F and len(I) <= 60 and len(F) <= 30:
                by[s].append((p, I, F))
        hits = collections.defaultdict(lambda: {k: [] for k in KS})
        for s, items in sorted(by.items()):
            g = BR.Graph(sn[s]["db"])
            keys = sorted(g.index, key=g.index.get)
            nm = np.array([D.norm(k[1]) for k in keys])
            inh = np.array([n in refnames for n in nm])
            for p, I, F in items:
                Iidx = np.array(sorted({g.index[k] for k in I if k in g.index}), dtype=np.int64)
                Fidx = np.array(sorted({g.index[k] for k in F if k in g.index}), dtype=np.int64)
                if not len(Iidx):
                    continue
                pos = np.array([i for i in np.setdiff1d(Fidx, Iidx) if inh[i]], dtype=np.int64)
                if not len(pos):
                    continue
                near = g.near(Iidx)
                dist = np.full(g.n, 3, dtype=np.int64)
                dist[near["either3"]] = 2
                dist[near["either2"]] = 1
                dist[near["either1"]] = 0
                evf = np.unique(g.fid[Iidx])
                local = np.isin(g.fid, evf).astype(float) * 1e9 - dist * 1e7 + g.loc
                cand = np.array([i for i in range(g.n) if inh[i] and i not in set(Iidx.tolist())], dtype=np.int64)
                if len(cand) < 30:
                    continue
                t = p["ind_ct"]
                Fi = {D.norm(x[1]) for x in I} & refnames
                hot = np.zeros(len(cand))
                pri = np.zeros(len(cand))
                for j, c in enumerate(cand):
                    name = nm[c]
                    for r in sibs:
                        ht = data[r]["hot"].get(name)
                        if ht:
                            hot[j] += math.log1p(bisect.bisect_left(ht, t))
                        for f in Fi:
                            if data[r]["pair_first"].get((f, name), INF) < t:
                                pri[j] += 1
                loc = g.loc[cand].astype(float)
                sc = {"L": local[cand], "H": hot * 1e6 + loc, "P": pri * 1e12 + hot * 1e6 + loc}
                rk = {k: rankdata(-v, method="min") for k, v in sc.items()}
                sc["LH"] = 1 / (60 + rk["L"]) + 1 / (60 + rk["H"])
                sc["LP"] = 1 / (60 + rk["L"]) + 1 / (60 + rk["P"])
                rk["LH"], rk["LP"] = rankdata(-sc["LH"], method="min"), rankdata(-sc["LP"], method="min")
                # exploratory (post hoc): T1 = local key with the prior as tie-break instead of size; T2 = local top 10, then the rest by fusion
                fileflag = np.isin(g.fid[cand], evf).astype(float)
                t1 = fileflag * 1e15 - dist[cand] * 1e13 + pri * 1e9 + hot * 1e4 + loc / 1e5
                rk["T1"] = rankdata(-t1, method="min")
                t2 = np.where(rk["L"] <= 10, 1e6 - rk["L"], sc["LP"])
                rk["T2"] = rankdata(-t2, method="min")
                posm = np.isin(cand, pos)
                for name_ in ("L", "H", "P", "LH", "LP", "T1", "T2"):
                    best = rk[name_][posm].min()
                    for k in KS:
                        hits[name_][k].append(float(best <= k))
                hits["N"][20].append(len(cand))
        res[L] = hits
        n = len(hits["L"][20])
        print(f"{L}: {n} changes ranked (median universe {int(np.median(hits['N'][20])) if n else 0} functions): " + "; ".join(f"{nm_} top 20 {100 * np.mean(hits[nm_][20]):.1f}%" for nm_ in ("L", "H", "P", "LH", "LP", "T1", "T2")), flush=True)
    print("\n=== POOLED ===")
    pooled = {nm_: {k: [x for L in D.LIN for x in res[L][nm_][k]] for k in KS} for nm_ in ("L", "H", "P", "LH", "LP", "T1", "T2")}
    N = np.concatenate([res[L]["N"][20] for L in D.LIN])
    print(f"{len(pooled['L'][20])} changes; random top 20 would be about {100 * np.mean(20 / N):.1f}%")
    for nm_, lab in (("L", "local call graph (validated ranking)"), ("H", "hotness only"), ("P", "pair prior"), ("LH", "local + hotness (fusion)"), ("LP", "local + pair prior (fusion)"), ("T1", "T1 local, prior as tie-break (exploratory)"), ("T2", "T2 local top 10 then fusion (exploratory)")):
        print(f"  {lab:38s} top 10 {100 * np.mean(pooled[nm_][10]):5.1f}%  top 20 {100 * np.mean(pooled[nm_][20]):5.1f}%  top 100 {100 * np.mean(pooled[nm_][100]):5.1f}%")
    print("\n=== VERDICTS ===")
    rnd = float(np.mean(20 / N))
    p20 = {k: float(np.mean(v[20])) for k, v in pooled.items()}
    print(f"  CP1 pair prior top 20 {100 * p20['P']:.1f}% against random about {100 * rnd:.1f}% = {p20['P'] / rnd:.1f} times (needs 3): {'supported' if p20['P'] >= 3 * rnd else 'not supported'}")
    gain = 100 * (p20["LP"] - p20["L"])
    perl = {L: 100 * (np.mean(res[L]["LP"][20]) - np.mean(res[L]["L"][20])) for L in D.LIN if res[L]["L"][20]}
    print(f"  CP2 LP minus L (points): pooled {gain:+.1f}; per lineage " + ", ".join(f"{L} {v:+.1f}" for L, v in perl.items()) + f" (needs +3 pooled and positive-3 in 4 lineages): {'supported' if gain >= 3 and sum(1 for v in perl.values() if v >= 3) >= 4 else 'not supported'}")
    g3 = 100 * (p20["LP"] - p20["LH"])
    print(f"  CP3 LP minus LH {g3:+.1f} points (needs +2): {'supported' if g3 >= 2 else 'not supported'}")
    print(f"  CP4 L alone top 20 {100 * p20['L']:.1f}% (needs 30%): {'supported' if p20['L'] >= 0.3 else 'not supported'}")
    print(f"  surprise bar (LP less than 1 point above L): {'MET' if gain < 1 else 'not met'}")
    t1_20, t1_100 = 100 * (p20["T1"] - p20["L"]), 100 * (np.mean(pooled["T1"][100]) - np.mean(pooled["L"][100]))
    print(f"  E1 (exploratory) T1 minus L: top 20 {t1_20:+.1f} points (needs 0 or more), top 100 {t1_100:+.1f} (needs +2): {'supported' if t1_20 >= 0 and t1_100 >= 2 else 'not supported'}")
    t2_20, t2_100 = 100 * (p20["T2"] - p20["L"]), 100 * (np.mean(pooled["T2"][100]) - np.mean(pooled["L"][100]))
    print(f"  E2 (exploratory) T2 minus L: top 20 {t2_20:+.1f} (needs within 1), top 100 {t2_100:+.1f} (needs +3): {'supported' if abs(t2_20) <= 1 and t2_100 >= 3 else 'not supported'}")


if __name__ == "__main__":
    main()
