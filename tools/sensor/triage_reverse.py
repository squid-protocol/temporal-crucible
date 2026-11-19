#!/usr/bin/env python3
"""Reverse triage: from the place a bug was repaired to the change that caused it. Hypotheses RT1-RT5: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.
    python tools/sensor/triage_reverse.py dpdk mesa"""
import bisect
import json
import pickle
import random
import subprocess
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import lang_validation as LV  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
DAY = 86400
RANKERS = ["REC", "SIZE", "FILE", "BLAME", "N1b", "N1"]


def dirof(p):
    return p.rsplit("/", 1)[0] if "/" in p else ""


def run(repo, n=1500):
    path = f"{BR.POOL}/{repo}"
    pairs = json.load(open(f"{B}/argl/links_{repo}.json"))
    random.Random(3).shuffle(pairs)
    pairs = pairs[:n]
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
    by = defaultdict(list)
    drop = defaultdict(int)
    for p in pairs:
        G = fixinfo.get(p["fix"], ([], 0, 0))[0]
        s = int(np.searchsorted(cts, p["fix_ct"], side="right")) - 1
        ci = idx_of.get(p["ind"])
        if not G:
            drop["no failure function"] += 1
        elif s < 0:
            drop["no earlier scan"] += 1
        elif ci is None or not ok[ci] or not (p["fix_ct"] - 730 * DAY <= times[ci] < p["fix_ct"]):
            drop["true cause not a candidate (outside 730 days or no functions)"] += 1
        else:
            by[s].append((p, G, ci))
    res = []
    for s, items in sorted(by.items()):
        g = BR.Graph(sn[s]["db"])
        for p, G, ci in items:
            Gn = [g.index[k] for k in G if k in g.index]
            if not Gn:
                drop["failure function not in the graph"] += 1
                continue
            near = g.near(np.array(Gn, dtype=np.int64))
            dnode = np.full(g.n, 4, dtype=np.int64)
            dnode[near["either3"]] = 3
            dnode[near["either2"]] = 2
            dnode[near["either1"]] = 1
            dnode[Gn] = 0
            Gk, Gp = set(G), {k[0] for k in G}
            Gd = {dirof(k[0]) for k in G}
            tf = p["fix_ct"]
            lo, hi = bisect.bisect_left(times, tf - 730 * DAY), bisect.bisect_left(times, tf)
            cand = [i for i in range(lo, hi) if ok[i] and shas[i] != p["fix"]]
            F = np.zeros((len(cand), 7))
            for j, i in enumerate(cand):
                ks = keys_of[i]
                nodes = [g.index[k] for k in ks if k in g.index]
                F[j, 0] = any(k in Gk for k in ks)
                F[j, 1] = any(k[0] in Gp for k in ks)
                F[j, 2] = (dnode[nodes].min() if nodes else 4)
                F[j, 3] = any(dirof(k[0]) in Gd for k in ks)
                F[j, 4] = len(ks)
                F[j, 5] = tf - times[i]
            sf, sfile, dist, sdir, nf, rec = F[:, 0], F[:, 1], F[:, 2], F[:, 3], F[:, 4], F[:, 5]
            dsc = np.where(dist <= 3, 4 - dist, 0)
            sc = {"REC": -rec, "SIZE": nf * 1e10 - rec, "FILE": sfile * 1e10 - rec, "BLAME": sf * 1e10 - rec,
                  "N1b": (sf * 1e4 + sfile * 1e3 + dsc * 1e2) * 1e10 - rec, "N1": (sf * 1e4 + sfile * 1e3 + dsc * 1e2 + sdir * 10) * 1e10 - rec}
            jt = cand.index(ci)
            res.append({"same_func": bool(sf[jt]), "ncand": len(cand), "rank": {k: 1 + int((v > v[jt]).sum()) for k, v in sc.items()}, "arr": {"rec": rec.astype(np.float32), "base": (sf * 1e4 + sfile * 1e3 + dsc * 1e2 + sdir * 10).astype(np.float32), "jt": jt}, "repo": repo})
    print(f"\n########## {repo}: {len(pairs)} pairs sampled; dropped {dict(drop)}; ranked {len(res)}; median candidates {int(np.median([r['ncand'] for r in res]))} ##########", flush=True)
    return res


def table(res, label):
    if not res:
        return
    print(f"  {label} ({len(res)} pairs)")
    print(f"    {'ranker':7s} {'top 1':>7s} {'top 5':>7s} {'top 20':>7s} {'MRR':>7s}")
    for k in RANKERS:
        r = np.array([x["rank"][k] for x in res])
        print(f"    {k:7s} {100 * np.mean(r <= 1):6.1f}% {100 * np.mean(r <= 5):6.1f}% {100 * np.mean(r <= 20):6.1f}% {np.mean(1 / r):7.3f}")


def main():
    allres = {}
    for repo in sys.argv[1:]:
        res = run(repo)
        allres[repo] = res
        table(res, "all pairs")
        table([x for x in res if not x["same_func"]], "cause elsewhere (the true cause did not change a failure function)")
    pickle.dump([x for r in allres.values() for x in r], open(f"{B}/osv/trailer_triage_arrays.pkl", "wb"))
    pooled = [x for r in allres.values() for x in r]
    print("\n######## pooled ########")
    table(pooled, "all pairs")
    els = [x for x in pooled if not x["same_func"]]
    table(els, "cause elsewhere")
    print(f"  share of pairs where the cause changed a failure function (blame solves it): {100 * (1 - len(els) / len(pooled)):.0f}%")
    t20 = lambda res, k: float(np.mean([x["rank"][k] <= 20 for x in res]))  # noqa: E731
    print("\n=== VERDICTS ===")
    print(f"  RT1 N1 top 20, all pairs {100 * t20(pooled, 'N1'):.1f}% (needs 50%): {'supported' if t20(pooled, 'N1') >= 0.5 else 'not supported'}")
    print(f"  RT2 cause elsewhere: N1 top 20 {100 * t20(els, 'N1'):.1f}% (needs 20%), recency {100 * t20(els, 'REC'):.1f}% (needs 5% or less): {'supported' if t20(els, 'N1') >= 0.2 and t20(els, 'REC') <= 0.05 else 'not supported'}")
    d3 = 100 * (t20(els, "N1b") - t20(els, "FILE"))
    print(f"  RT3 cause elsewhere: N1b minus FILE {d3:+.1f} points (needs +5): {'supported' if d3 >= 5 else 'not supported'}")
    d4 = 100 * (t20(els, "N1") - t20(els, "N1b"))
    print(f"  RT4 cause elsewhere: N1 minus N1b {d4:+.1f} points (needs +2): {'supported' if d4 >= 2 else 'not supported'}")
    print(f"  RT5 recency alone top 20, all pairs {100 * t20(pooled, 'REC'):.1f}% (needs 5% or less): {'supported' if t20(pooled, 'REC') <= 0.05 else 'not supported'}")
    print(f"  surprise bar (cause elsewhere: N1 within 1 point of FILE): {'MET' if abs(t20(els, 'N1') - t20(els, 'FILE')) <= 0.01 else 'not met'}")


if __name__ == "__main__":
    main()
