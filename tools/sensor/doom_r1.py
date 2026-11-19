#!/usr/bin/env python3
"""DOOM-R1: repair around inherited functions in independent C lineages. Hypotheses DB1-DB5: docs/sensor-overhaul/sensors/doom_ports_plan.md section 6, fixed before any scan.

    python tools/sensor/doom_r1.py      (needs the quarterly scans of the lineages in turn_v2 and the clones under temporal-crucible-pool)"""
import collections
import glob
import json
import re
import sqlite3
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import lang_validation as LV  # noqa: E402

LIN = ["crispy-doom", "dsda-doom", "nugget-doom", "doomretro", "fastdoom", "inter-doom"]
CTRL = "chocolate-doom"
REFDB = glob.glob("/srv/storage_16tb/projects/gitgalaxy/doom-study/scans_r2/linuxdoom/*_master.db")[0]
rng = np.random.default_rng(2982)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def latest_names(repo):
    db = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))[-1]["db"]
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    return {norm(n) for (n,) in con.execute("select func_name from function_data where loc >= 3") if n}


def main():
    g = BR.Graph(REFDB)
    keys = sorted(g.index, key=g.index.get)
    name_nodes = collections.defaultdict(list)
    for i, (p, n) in enumerate(keys):
        if g.loc[i] >= 3:
            name_nodes[norm(n)].append(i)
    refnames = set(name_nodes)
    fan = np.asarray(g.callers_m.sum(axis=0)).ravel()
    ref_loc = {n: max(int(g.loc[i]) for i in ids) for n, ids in name_nodes.items()}
    ref_fan = {n: max(int(fan[i]) for i in ids) for n, ids in name_nodes.items()}
    ref_dec = {}
    locs = np.array(sorted(ref_loc.values()))
    for n, l in ref_loc.items():
        ref_dec[n] = int(np.searchsorted(np.percentile(locs, np.arange(10, 100, 10)), l))
    n2cache = {}

    def n2(name):
        if name not in n2cache:
            ids = np.array(name_nodes[name], dtype=np.int64)
            near = g.near(ids)["either2"]
            n2cache[name] = sorted({norm(keys[i][1]) for i in np.nonzero(near)[0] if norm(keys[i][1]) in refnames} - {name})
        return n2cache[name]

    present = {r: latest_names(r) for r in LIN + [CTRL]}
    universe = sorted(n for n in refnames if sum(1 for r in LIN if n in present[r]) >= 4)
    print(f"linuxdoom: {len(refnames)} function names of 3+ lines; inherited names present in at least 4 of the 6 lineages: {len(universe)}")
    data = {}
    res = {}
    for repo in LIN + [CTRL]:
        try:
            pairs, info = LV.build(repo, 3000)
        except Exception as e:  # noqa: BLE001
            print(f"{repo}: could not build pairs ({e})")
            continue
        info_inh = {s: ([k for k in v[0] if norm(k[1]) in refnames], v[1], v[2]) for s, v in info.items()}
        df_all, _ = LV.measure(repo, pairs, info)
        df_inh, _ = LV.measure(repo, pairs, info_inh)
        s_all, s_inh = LV.summarize(df_all), LV.summarize(df_inh)
        # per inherited function: distinct fixes that modified it
        fixcount = collections.Counter()
        seen = set()
        for p in pairs:
            if p["fix"] in seen:
                continue
            seen.add(p["fix"])
            for k in {norm(x[1]) for x in info[p["fix"]][0]}:
                if k in refnames:
                    fixcount[k] += 1
        obs = set()
        for p in pairs:
            Fn = {norm(x[1]) for x in info[p["fix"]][0]} & refnames
            In = {norm(x[1]) for x in info[p["ind"]][0]} & refnames
            for f in In:
                nb = set(n2(f))
                for gname in Fn:
                    if gname != f and gname in nb:
                        obs.add((f, gname))
        data[repo] = {"fixcount": fixcount, "obs": obs, "pairs": len(pairs)}
        res[repo] = (s_all, s_inh)
        f = lambda r: f"{r[0]:.2f} [{r[1]:.2f},{r[2]:.2f}]" if r else "n/a"  # noqa: E731
        print(f"\n{repo}: {len(pairs)} blame pairs; ALL functions: outside {s_all[1]}, radius within 2 calls {f(s_all[3]['either2'])}; INHERITED only: outside {s_inh[1]}, radius {f(s_inh[3]['either2'])}; inherited (cause, repair) pairs within 2 calls in linuxdoom: {len(obs)}", flush=True)
    print("\n=== DB3: do independent lineages repair the same functions? ===")
    cov = pd.DataFrame({"loc": [np.log1p(ref_loc[n]) for n in universe], "fan": [np.log1p(ref_fan[n]) for n in universe]}, index=universe)
    vec = {r: np.array([data[r]["fixcount"].get(n, 0) for n in universe], dtype=float) for r in data}
    def resid(y):
        r = rankdata(y)
        X = np.column_stack([np.ones(len(universe)), rankdata(cov["loc"]), rankdata(cov["fan"])])
        return r - X @ np.linalg.lstsq(X, r, rcond=None)[0]
    raw, par = [], []
    for i, a in enumerate(LIN):
        for b in LIN[i + 1 :]:
            if a in vec and b in vec and vec[a].sum() > 0 and vec[b].sum() > 0:
                raw.append(spearmanr(vec[a], vec[b])[0])
                par.append(float(np.corrcoef(resid(vec[a]), resid(vec[b]))[0, 1]))
    sc = spearmanr(vec[CTRL], vec["crispy-doom"])[0] if CTRL in vec and "crispy-doom" in vec else float("nan")
    print(f"  {len(universe)} inherited functions; mean pairwise Spearman between lineages {np.mean(raw):.3f} (range {min(raw):.2f} to {max(raw):.2f}), partial (size and fan-in removed) {np.mean(par):.3f}; shared-history control chocolate-doom with crispy-doom {sc:.3f}")
    print("\n=== DB4: do independent lineages repair the same neighbours? ===")
    ok = [r for r in LIN if r in data and len(data[r]["obs"]) >= 30]
    print("  inherited (cause, repair) pairs within 2 calls per lineage: " + ", ".join(f"{r} {len(data[r]['obs'])}" for r in data))
    def overlap(sets):
        tot = 0
        for i, a in enumerate(sets):
            for b in sets[i + 1 :]:
                tot += len(a & b)
        return tot
    observed = overlap([data[r]["obs"] for r in ok]) if len(ok) >= 3 else None
    null = []
    if observed is not None:
        for _ in range(300):
            ns = []
            for r in ok:
                ns.append({(f, rng.choice(n2(f))) for f, _ in data[r]["obs"] if n2(f)})
            null.append(overlap(ns))
        print(f"  overlap over {len(ok)} lineages: observed {observed}, null mean {np.mean(null):.1f} (95th percentile {np.percentile(null, 95):.0f}): ratio {observed / max(np.mean(null), 1e-9):.2f}")
        if CTRL in data and "crispy-doom" in data:
            c_obs = len(data[CTRL]["obs"] & data["crispy-doom"]["obs"])
            c_null = np.mean([len({(f, rng.choice(n2(f))) for f, _ in data[CTRL]["obs"] if n2(f)} & {(f, rng.choice(n2(f))) for f, _ in data["crispy-doom"]["obs"] if n2(f)}) for _ in range(300)])
            print(f"  shared-history control chocolate-doom with crispy-doom: observed {c_obs}, null mean {c_null:.1f}")
    print("\n=== VERDICTS ===")
    f = lambda r: r[0] if r else float("nan")  # noqa: E731
    db1 = {r: res[r][0] for r in LIN if r in res and res[r][0][1] >= 100}
    print("  DB1 radius within 2 calls (lineages with at least 100 pairs outside the changed set): " + ", ".join(f"{r} {f(s[3]['either2']):.2f} [{s[3]['either2'][1]:.2f}]" for r, s in db1.items()) + f": {'supported' if db1 and all(s[3]['either2'] and s[3]['either2'][0] >= 1.3 and s[3]['either2'][1] > 1.1 for s in db1.values()) else 'not supported'}")
    d2 = {r: (res[r][1][3]["either2"][0] / res[r][0][3]["either2"][0] - 1) for r in db1 if res[r][1][3]["either2"] and res[r][0][3]["either2"]}
    print("  DB2 inherited-only radius against all-functions radius: " + ", ".join(f"{r} {100 * v:+.0f}%" for r, v in d2.items()) + f" (needs within 25% in each): {'supported' if d2 and all(abs(v) <= 0.25 for v in d2.values()) else 'not supported'}")
    print(f"  DB3 mean pairwise Spearman {np.mean(raw):.3f} (needs 0.20), partial {np.mean(par):.3f} (needs 0.10): {'supported' if np.mean(raw) >= 0.2 and np.mean(par) >= 0.1 else 'not supported'}")
    if observed is None:
        print(f"  DB4 untestable (fewer than 30 inherited pairs in at least three lineages: {[r for r in data if len(data[r]['obs']) >= 30]})")
    else:
        print(f"  DB4 observed overlap {observed} against null {np.mean(null):.1f} = {observed / max(np.mean(null), 1e-9):.2f} (needs 2): {'supported' if observed >= 2 * np.mean(null) else 'not supported'}")
    print(f"  surprise bar (partial DB3 below 0.05 and DB4 at or below the null): {'MET' if np.mean(par) < 0.05 and (observed is not None and observed <= np.mean(null)) else 'not met'}")


if __name__ == "__main__":
    main()
