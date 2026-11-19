#!/usr/bin/env python3
"""Reverse triage with realistic symptom sites (SY1-SY4) and prior-weighted bisect (BS1-BS3). Hypotheses: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.
    python tools/sensor/triage_sites.py dpdk mesa"""
import bisect
import json
import math
import pickle
import random
import re
import subprocess
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import lang_validation as LV  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
DAY = 86400
SITES = ["ALL", "S1", "S2", "S3", "S4"]
RK = ["REC", "FILE", "BLAME", "N1"]
NPAIRS = 600
rng = random.Random(11)


def dirof(p):
    return p.rsplit("/", 1)[0] if "/" in p else ""


def scores(cand_data, Gk, Gp, Gd, dnode, tf):
    n = len(cand_data)
    sf = np.zeros(n)
    sfile = np.zeros(n)
    dist = np.zeros(n)
    sdir = np.zeros(n)
    rec = np.zeros(n)
    for j, (ks, nodes, paths, dirs, t) in enumerate(cand_data):
        sf[j] = any(k in Gk for k in ks)
        sfile[j] = bool(paths & Gp)
        dist[j] = dnode[nodes].min() if nodes else 4
        sdir[j] = bool(dirs & Gd)
        rec[j] = tf - t
    dsc = np.where(dist <= 3, 4 - dist, 0)
    return {"REC": -rec, "FILE": sfile * 1e10 - rec, "BLAME": sf * 1e10 - rec, "N1": (sf * 1e4 + sfile * 1e3 + dsc * 1e2 + sdir * 10) * 1e10 - rec}, sf


def fit_curve(ranks):
    """log-binned empirical density of the true cause's rank: returns a function rank -> per-candidate probability weight."""
    edges = [1, 2, 3, 5, 9, 17, 33, 65, 129, 257, 513, 1025, 2049, 4097, 8193, 10**9]
    cnt = np.zeros(len(edges) - 1)
    for r in ranks:
        cnt[bisect.bisect_right(edges, r) - 1] += 1
    dens = (cnt + 0.5) / (len(ranks) + 0.5 * len(cnt)) / np.diff(edges)
    return lambda r: dens[np.minimum(np.searchsorted(edges, r, side="right") - 1, len(dens) - 1)]


def wbisect_steps(w, j):
    lo, hi, steps = 0, len(w) - 1, 0
    cs = np.cumsum(w)
    while hi > lo:
        base = cs[lo - 1] if lo > 0 else 0.0
        half = base + (cs[hi] - base) / 2
        k = int(np.searchsorted(cs[lo : hi + 1], half)) + lo
        k = min(k, hi - 1)
        if j <= k:
            hi = k
        else:
            lo = k + 1
        steps += 1
    return steps


def run(repo):
    path = f"{BR.POOL}/{repo}"
    pairs = json.load(open(f"{B}/argl/links_{repo}.json"))
    random.Random(3).shuffle(pairs)
    pairs = pairs[:NPAIRS]
    touched = pickle.load(open(f"{B}/blast/{repo}/touched_all.pkl", "rb"))
    sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
    cts = np.load(f"{B}/blast/{repo}/snapshot_cts.npy")
    log = [l.split() for l in subprocess.run(["git", "-C", path, "log", "--no-merges", "--format=%H %ct"], capture_output=True, text=True).stdout.splitlines()]
    log.sort(key=lambda x: int(x[1]))
    shas = [a for a, _ in log]
    times = [int(b) for _, b in log]
    idx_of = {s: i for i, s in enumerate(shas)}
    keys_of = [[tuple(k) for k in touched.get(s, [])] for s in shas]
    ok = [1 <= len(k) <= 60 for k in keys_of]
    fixshas = list(dict.fromkeys(p["fix"] for p in pairs))
    fixinfo = {}
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=6) as ex:
        for r in ex.map(LV.commit_worker, [(path, "c", fixshas[i : i + 25]) for i in range(0, len(fixshas), 25)]):
            fixinfo.update(r)
    subj = {}
    out = subprocess.run(["git", "-C", path, "log", "--no-walk=unsorted", "--stdin", "--format=%H\x1f%s"], input="\n".join(fixshas) + "\n", capture_output=True, text=True, errors="replace").stdout
    for l in out.splitlines():
        if "\x1f" in l:
            h, s = l.split("\x1f", 1)
            subj[h] = s
    by = defaultdict(list)
    for p in pairs:
        G = fixinfo.get(p["fix"], ([], 0, 0))[0]
        s = int(np.searchsorted(cts, p["fix_ct"], side="right")) - 1
        ci = idx_of.get(p["ind"])
        if G and s >= 0 and ci is not None and ok[ci] and p["fix_ct"] - 730 * DAY <= times[ci] < p["fix_ct"]:
            by[s].append((p, G, ci))
    res = {m: [] for m in SITES}
    bis = []
    for s, items in sorted(by.items()):
        g = BR.Graph(sn[s]["db"])
        gkeys = sorted(g.index, key=g.index.get)
        byname = defaultdict(list)
        for i, k in enumerate(gkeys):
            byname[k[1]].append(i)
        for p, G, ci in items:
            Gn = [g.index[k] for k in G if k in g.index]
            if not Gn:
                continue
            tf = p["fix_ct"]
            lo, hi = bisect.bisect_left(times, tf - 730 * DAY), bisect.bisect_left(times, tf)
            cand = [i for i in range(lo, hi) if ok[i] and shas[i] != p["fix"]]
            cand_data = []
            for i in cand:
                ks = keys_of[i]
                cand_data.append((set(ks), [g.index[k] for k in ks if k in g.index], {k[0] for k in ks}, {dirof(k[0]) for k in ks}, times[i]))
            jt = cand.index(ci)
            sites = {"ALL": list(G)}
            Gs = sorted(G)
            sites["S1"] = [Gs[0]]
            sites["S2"] = [rng.choice(Gs)]
            near0 = g.near(np.array(Gn, dtype=np.int64))
            callers = [i for i in np.nonzero(near0["callers1"])[0] if i not in set(Gn)]
            if callers:
                sites["S3"] = [gkeys[int(rng.choice(callers))]]
            toks = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", subj.get(p["fix"], "")))
            named = [i for t in toks for i in byname.get(t, [])]
            if 0 < len(named) <= 3:
                sites["S4"] = [gkeys[i] for i in named]
            for mode, site in sites.items():
                sn_ = [g.index[k] for k in site if k in g.index]
                if not sn_:
                    continue
                near = g.near(np.array(sn_, dtype=np.int64))
                dnode = np.full(g.n, 4, dtype=np.int64)
                dnode[near["either3"]] = 3
                dnode[near["either2"]] = 2
                dnode[near["either1"]] = 1
                dnode[sn_] = 0
                sc, sf = scores(cand_data, set(site), {k[0] for k in site}, {dirof(k[0]) for k in site}, dnode, tf)
                rank = {k: 1 + int((v > v[jt]).sum()) for k, v in sc.items()}
                res[mode].append({"rank": rank, "same_func": bool(sf[jt])})
                if mode in ("ALL", "S1") and len(bis) < NPAIRS * 2:
                    # time-ordered candidates are already in time order; keep the per-candidate ranks under each ranker
                    full = {}
                    for k, v in sc.items():
                        order = np.argsort(-v, kind="stable")
                        r = np.empty(len(v), dtype=np.int32)
                        r[order] = np.arange(1, len(v) + 1)
                        full[k] = r
                    bis.append({"mode": mode, "j": jt, "m": len(cand), "nall": hi - lo, "ranks": full})
    print(f"\n########## {repo}: {sum(len(v) for v in res.values())} ranked pair-sites; " + ", ".join(f"{m} {len(res[m])}" for m in SITES) + f"; bisect pairs {len(bis)} ##########", flush=True)
    return res, bis


def main():
    allres = {m: [] for m in SITES}
    allbis = []
    for repo in sys.argv[1:]:
        res, bis = run(repo)
        for m in SITES:
            allres[m] += res[m]
        allbis += bis
    t20 = lambda rs, k: float(np.mean([x["rank"][k] <= 20 for x in rs])) if rs else float("nan")  # noqa: E731
    print("\n=== SITES: share of pairs with the true cause in the top 20 (pooled) ===")
    print(f"  {'site':5s} {'pairs':>6s} " + " ".join(f"{k:>7s}" for k in RK))
    for m in SITES:
        print(f"  {m:5s} {len(allres[m]):6d} " + " ".join(f"{100 * t20(allres[m], k):6.1f}%" for k in RK))
    print("\n=== PRIOR-WEIGHTED BISECT (steps to isolate the cause) ===")
    results = {}
    for mode in ("ALL", "S1"):
        bs = [b for b in allbis if b["mode"] == mode]
        idx = list(range(len(bs)))
        random.Random(5).shuffle(idx)
        half = len(idx) // 2
        folds = [(idx[:half], idx[half:]), (idx[half:], idx[:half])]
        steps = {k: [] for k in ["classic_all", "uniform"] + RK}
        for train, test in folds:
            curves = {k: fit_curve([bs[i]["ranks"][k][bs[i]["j"]] for i in train]) for k in RK}
            for i in test:
                b = bs[i]
                steps["classic_all"].append(math.ceil(math.log2(max(b["nall"], 2))))
                steps["uniform"].append(wbisect_steps(np.ones(b["m"]), b["j"]))
                for k in RK:
                    steps[k].append(wbisect_steps(curves[k](b["ranks"][k]), b["j"]))
        results[mode] = steps
        print(f"  site {mode} ({len(bs)} pairs): " + "; ".join(f"{k} mean {np.mean(v):.1f}, median {np.median(v):.0f}, at most 5 steps {100 * np.mean([x <= 5 for x in v]):.0f}%" for k, v in steps.items()))
    print("\n=== VERDICTS ===")
    one = [t20(allres[m], "N1") for m in ("S1", "S2")]
    print(f"  SY1 N1 top 20 with one edited function as the site: S1 {100 * one[0]:.1f}%, S2 {100 * one[1]:.1f}% (needs 55%): {'supported' if min(one) >= 0.55 else 'not supported'}")
    print(f"  SY2 caller as the site (S3): N1 {100 * t20(allres['S3'], 'N1'):.1f}% (needs 25%), FILE {100 * t20(allres['S3'], 'FILE'):.1f}% (needs N1 5 points above): {'supported' if t20(allres['S3'], 'N1') >= 0.25 and t20(allres['S3'], 'N1') - t20(allres['S3'], 'FILE') >= 0.05 else 'not supported'}")
    print(f"  SY3 function named in the subject (S4): N1 {100 * t20(allres['S4'], 'N1'):.1f}% (needs 50%): {'supported' if t20(allres['S4'], 'N1') >= 0.5 else 'not supported'}")
    lows = {m: t20(allres[m], "N1") for m in ("ALL", "S1", "S2", "S3", "S4")}
    print(f"  SY4 lowest N1 top 20 among the sites: {min(lows, key=lows.get)} (needs S3): {'supported' if min(lows, key=lows.get) == 'S3' else 'not supported'}")
    st = results["ALL"]
    print(f"  BS1 N1-weighted mean {np.mean(st['N1']):.1f} against classic over all commits {np.mean(st['classic_all']):.1f}: {np.mean(st['classic_all']) - np.mean(st['N1']):+.1f} steps saved (needs 3): {'supported' if np.mean(st['classic_all']) - np.mean(st['N1']) >= 3 else 'not supported'}")
    print(f"  BS2 N1 against FILE-weighted: {np.mean(st['FILE']) - np.mean(st['N1']):+.2f} steps (needs 0.5): {'supported' if np.mean(st['FILE']) - np.mean(st['N1']) >= 0.5 else 'not supported'}")
    print(f"  BS3 share needing at most 5 tests with N1: {100 * np.mean([x <= 5 for x in st['N1']]):.0f}% (needs 30%): {'supported' if np.mean([x <= 5 for x in st['N1']]) >= 0.3 else 'not supported'}")


if __name__ == "__main__":
    main()
