#!/usr/bin/env python3
"""Same directory as a ranking feature for 'where to look first'. Hypotheses SD1-SD4: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.

    python tools/sensor/same_directory.py      (DPDK, Mesa: trailer pairs sampled to 4,000; held-out repositories of the gate: blame pairs)"""
import collections
import json
import os
import pickle
import random
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import lang_validation as LV  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
SPOT = ("dpdk", 3061)  # the mock-up's miss: virtio-user, pair index in links_dpdk.json
NC = 2 * 4 * 5 * 10
ID = np.indices((2, 4, 5, 10)).reshape(4, -1)  # file, distance, directory category, size decile, in cell order
F_, D_, DC_, SD_ = (a.astype(float) for a in ID)
RANK = {"B": F_ * 1e8 - D_ * 1e6 + SD_, "S": F_ * 1e8 - D_ * 1e6 + (DC_ == 4) * 1e4 + SD_, "G": F_ * 1e8 - D_ * 1e6 + DC_ * 1e4 + SD_}


def dir_cat(D, E):
    if D == E:
        return 4
    k = 0
    while k < min(len(D), len(E)) and D[k] == E[k]:
        k += 1
    if k >= 1 and k >= len(E) - 1:
        return 3
    if k >= 1 and k >= len(E) - 2:
        return 2
    return 1 if k >= 1 else 0


def worker(args):
    db, items = args
    g = BR.Graph(db)
    keys = sorted(g.index, key=g.index.get)
    fpath = {}
    for i, k in enumerate(keys):
        fpath[int(g.fid[i])] = k[0]
    fdirs = {f: tuple(p.split("/")[:-1]) for f, p in fpath.items()}
    nfile = g.nfiles
    floc = np.bincount(g.fid, weights=g.loc, minlength=nfile)
    present = np.bincount(g.fid, minlength=nfile) > 0
    if not present.any():
        return []
    fdec = np.searchsorted(np.percentile(floc[present], np.arange(10, 100, 10)), floc)
    out = []
    for it in items:
        I = np.array(sorted({g.index[k] for k in it["I"] if k in g.index}), dtype=np.int64)
        F = np.array(sorted({g.index[k] for k in it["F"] if k in g.index}), dtype=np.int64)
        if not len(I) or not len(F):
            continue
        Fo = np.setdiff1d(F, I)
        if not len(Fo):
            continue
        near = g.near(I)
        dist = np.full(g.n, 3, dtype=np.int64)
        dist[near["either3"]] = 2
        dist[near["either2"]] = 1
        dist[near["either1"]] = 0
        evf = np.unique(g.fid[I])
        evd = {fdirs[int(f)] for f in evf}
        cat_cache = {}
        fcat = np.zeros(nfile, dtype=np.int64)
        for f, d in fdirs.items():
            if d not in cat_cache:
                cat_cache[d] = max(dir_cat(d, e) for e in evd)
            fcat[f] = cat_cache[d]
        file_ = np.isin(g.fid, evf).astype(np.int64)
        cell = ((file_ * 4 + dist) * 5 + fcat[g.fid]) * 10 + g.dec
        keep = np.ones(g.n, dtype=bool)
        keep[I] = False
        Fo_other = Fo[~np.isin(g.fid[Fo], evf)]
        row = {"C": np.bincount(cell[keep], minlength=NC).astype(np.int32), "P": np.bincount(cell[Fo], minlength=NC).astype(np.int16), "Po": np.bincount(cell[Fo_other], minlength=NC).astype(np.int16)}
        mind = np.full(nfile, 3, dtype=np.int64)
        np.minimum.at(mind, g.fid, dist)
        evfile = np.zeros(nfile, dtype=np.int64)
        evfile[evf] = 1
        fcell = ((evfile * 4 + mind) * 5 + fcat) * 10 + fdec
        row["Cf"] = np.bincount(fcell[present], minlength=NC).astype(np.int32)
        row["Pf"] = np.bincount(fcell[np.unique(g.fid[Fo])], minlength=NC).astype(np.int16)
        row["Pfo"] = np.bincount(fcell[np.unique(g.fid[Fo_other])] if len(Fo_other) else np.array([], dtype=np.int64), minlength=NC).astype(np.int16)
        if it["pid"] == SPOT[1] and it.get("repo") == SPOT[0]:
            sc = {nm: s[cell] for nm, s in RANK.items()}
            row["spot"] = {nm: [int((np.where(keep, v, -1e18) > v[int(f)]).sum() + 1) for f in Fo] for nm, v in sc.items()}
            row["spot_names"] = [keys[int(f)][1] for f in Fo]
        out.append(row)
    return out


def hits(rows, s, ck, pk, ks):
    acc = {k: [] for k in ks}
    for r in rows:
        P, C = r[pk], r[ck]
        if P.sum() == 0:
            continue
        best = {k: 0.0 for k in ks}
        for c in np.nonzero(P)[0]:
            better, tied = C[s > s[c]].sum(), C[s == s[c]].sum()
            for k in ks:
                best[k] = max(best[k], min(1.0, max(0.0, (k - better) / tied)))
        for k in ks:
            acc[k].append(best[k])
    return {k: (float(np.mean(v)) if v else float("nan")) for k, v in acc.items()}, len(acc[ks[0]])


def prepare(repo, kind):
    if kind == "blame":
        pairs, info = LV.build(repo, 2500)
    else:
        cache = f"{B}/blast/samedir_{repo}.pkl"
        pairs_all = json.load(open(f"{B}/argl/links_{repo}.json"))
        random.Random(5).shuffle(pairs_all)
        pairs = pairs_all[:4000]
        if os.path.exists(cache):
            info = pickle.load(open(cache, "rb"))
        else:
            shas = list(dict.fromkeys(x for p in pairs for x in (p["fix"], p["ind"])))
            info = {}
            with ProcessPoolExecutor(max_workers=6) as ex:
                for res in ex.map(LV.commit_worker, [(f"{BR.POOL}/{repo}", "c", shas[i : i + 25]) for i in range(0, len(shas), 25)]):
                    info.update(res)
            pickle.dump(info, open(cache, "wb"))
    sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
    cf = f"{B}/blast/lang_{repo}_snapcts.npy" if os.path.exists(f"{B}/blast/lang_{repo}_snapcts.npy") else f"{B}/blast/{repo}/snapshot_cts.npy"
    if os.path.exists(cf):
        cts = np.load(cf)
    else:
        cts = np.array([int(subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "show", "-s", "--format=%ct", x["commit"]], capture_output=True, text=True).stdout.strip()) for x in sn])
        np.save(f"{B}/blast/lang_{repo}_snapcts.npy", cts)
    by = collections.defaultdict(list)
    links = json.load(open(f"{B}/argl/links_{repo}.json")) if kind == "trailer" else None
    for pid, p in enumerate(pairs):
        I, F = info[p["ind"]][0], info[p["fix"]][0]
        s = int(np.searchsorted(cts, p["ind_ct"], side="left"))
        if s < len(sn) and I and F and len(I) <= 60 and len(F) <= 30:
            ridx = links.index(p) if (kind == "trailer" and repo == SPOT[0]) else pid
            by[s].append({"pid": ridx if kind == "trailer" else pid, "I": I, "F": F, "repo": repo})
    rows = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for r in ex.map(worker, [(sn[s]["db"], it) for s, it in sorted(by.items())]):
            rows += r
    return rows


def main():
    sets = {"DPDK (trailers, 4,000 pairs sampled)": [("dpdk", "trailer")], "Mesa (trailers, 4,000 pairs sampled)": [("mesa", "trailer")], "C held-out (libgit2, redis, libxml2)": [(r, "blame") for r in ("libgit2", "redis", "libxml2")], "Python held-out (sphinx, scapy, sqlmap)": [(r, "blame") for r in ("sphinx", "scapy", "sqlmap")], "Go held-out (prometheus)": [("prometheus", "blame")]}
    res = {}
    for name, parts in sets.items():
        rows = []
        for repo, kind in parts:
            rows += prepare(repo, kind)
        spot = [r for r in rows if "spot" in r]
        out = {}
        for nm, s in RANK.items():
            allf, n = hits(rows, s, "C", "P", (20, 100))
            oth, no = hits(rows, s, "C", "Po", (20, 100))
            same = [dict(r, Ps=r["P"] - r["Po"]) for r in rows]
            sm, ns = hits(same, s, "C", "Ps", (20,))
            ff, _ = hits(rows, s, "Cf", "Pf", (10, 20))
            fo, nfo = hits(rows, s, "Cf", "Pfo", (10, 20))
            out[nm] = (allf, n, oth, no, sm, ns, ff, fo, nfo)
        res[name] = out
        print(f"\n########## {name}: {len(rows)} pairs ranked ##########")
        print(f"  {'ranker':3s} {'fn top 20':>10s} {'fn top 100':>11s} | other-file repairs only: fn top 20, top 100 (n) | same-file repairs: fn top 20 (n) | files top 10, top 20 | other-file: files top 10, top 20 (n)")
        for nm, (allf, n, oth, no, sm, ns, ff, fo, nfo) in out.items():
            print(f"  {nm:3s} {100 * allf[20]:9.1f}% {100 * allf[100]:10.1f}% | {100 * oth[20]:5.1f}% {100 * oth[100]:5.1f}% ({no}) | {100 * sm[20]:5.1f}% ({ns}) | {100 * ff[10]:5.1f}% {100 * ff[20]:5.1f}% | {100 * fo[10]:5.1f}% {100 * fo[20]:5.1f}% ({nfo})")
        for r in spot:
            print(f"  spot check (the mock-up's miss, virtio-user): repaired {', '.join(r['spot_names'])}: function ranks B {r['spot']['B']}, S {r['spot']['S']}, G {r['spot']['G']}")
    print("\n=== VERDICTS ===")
    names = list(res)
    d1 = {n: 100 * (res[n]["S"][0][20] - res[n]["B"][0][20]) for n in names}
    print("  SD1 S over B, function top 20 (points): " + ", ".join(f"{n.split(' (')[0]} {v:+.1f}" for n, v in d1.items()) + f" (needs +3 in all): {'supported' if all(v >= 3 for v in d1.values()) else 'not supported'}")
    d2 = {n: 100 * (res[n]["G"][0][20] - res[n]["S"][0][20]) for n in names}
    print("  SD2 G minus S (points): " + ", ".join(f"{n.split(' (')[0]} {v:+.1f}" for n, v in d2.items()) + f" (needs -0.5 or better in all): {'supported' if all(v >= -0.5 for v in d2.values()) else 'not supported'}")
    d3a = {n: 100 * (res[n]["S"][2][20] - res[n]["B"][2][20]) for n in names}
    d3b = {n: 100 * (res[n]["S"][7][10] - res[n]["B"][7][10]) for n in names}
    print("  SD3 other-file repairs, S over B: function top 20 " + ", ".join(f"{n.split(' (')[0]} {v:+.1f}" for n, v in d3a.items()) + "; file top 10 " + ", ".join(f"{n.split(' (')[0]} {v:+.1f}" for n, v in d3b.items()) + f" (needs +5 in all): {'supported' if all(v >= 5 for v in d3a.values()) and all(v >= 5 for v in d3b.values()) else 'not supported'}")
    d4 = {n: 100 * (res[n]["S"][4][20] - res[n]["B"][4][20]) for n in names}
    print("  SD4 same-file repairs, S against B, function top 20 (points): " + ", ".join(f"{n.split(' (')[0]} {v:+.1f}" for n, v in d4.items()) + f" (needs no fall beyond 1 point): {'supported' if all(v >= -1 for v in d4.values()) else 'not supported'}")
    print(f"  surprise bar (any gain under 1 point, S over B): {'MET' if any(v < 1 for v in d1.values()) else 'not met'}")


if __name__ == "__main__":
    main()
