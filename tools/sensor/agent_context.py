#!/usr/bin/env python3
"""Context for a coding agent: given the first function a fix edits, rank the other functions (and files) the same fix edits. Hypotheses AC1-AC3:
docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.
    python tools/sensor/agent_context.py"""
import collections
import json
import math
import random
import re
import sys

import numpy as np
from scipy.stats import rankdata

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import lang_validation as LV  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
DAY = 86400
RK = ["SIZE", "SAMEFILE", "N", "LEX", "N+LEX"]
DATASETS = [("dpdk", "trailer"), ("mesa", "trailer"), ("libgit2", "blame"), ("redis", "blame"), ("libxml2", "blame"), ("sphinx", "blame"), ("scapy", "blame"), ("sqlmap", "blame"), ("prometheus", "blame")]
TOK = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z]+|[a-z]+|\d+")


def toks(name):
    return {t.lower() for t in TOK.findall(name.replace("_", " ")) if len(t) > 1}


def dirof(p):
    return p.rsplit("/", 1)[0] if "/" in p else ""


def load(repo, kind):
    if kind == "trailer":
        import subprocess
        from concurrent.futures import ProcessPoolExecutor
        pairs = json.load(open(f"{B}/argl/links_{repo}.json"))
        random.Random(3).shuffle(pairs)
        pairs = pairs[:1500]
        fixshas = list(dict.fromkeys(p["fix"] for p in pairs))
        info = {}
        with ProcessPoolExecutor(max_workers=6) as ex:
            for r in ex.map(LV.commit_worker, [(f"{BR.POOL}/{repo}", "c", fixshas[i : i + 25]) for i in range(0, len(fixshas), 25)]):
                info.update(r)
    else:
        pairs, info = LV.build(repo, 2500)
    fixes = {}
    for p in pairs:
        ks = info.get(p["fix"], ([], 0, 0))[0]
        if len({tuple(k) for k in ks}) >= 2 and p["fix"] not in fixes:
            fixes[p["fix"]] = (p["fix_ct"], sorted({tuple(k) for k in ks}))
    return fixes


def main():
    allres = []
    for repo, kind in DATASETS:
        fixes = load(repo, kind)
        sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
        import os
        cf = f"{B}/blast/{repo}/snapshot_cts.npy" if os.path.exists(f"{B}/blast/{repo}/snapshot_cts.npy") else f"{B}/blast/lang_{repo}_snapcts.npy"
        if not os.path.exists(cf):
            import subprocess
            cts = np.array([int(subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "show", "-s", "--format=%ct", x["commit"]], capture_output=True, text=True).stdout.strip()) for x in sn])
            np.save(f"{B}/blast/lang_{repo}_snapcts.npy", cts)
        else:
            cts = np.load(cf)
        by = collections.defaultdict(list)
        for sha, (ct, ks) in fixes.items():
            s = int(np.searchsorted(cts, ct, side="right")) - 1
            if s >= 0:
                by[s].append((sha, ks))
        res = []
        for s, items in sorted(by.items()):
            g = BR.Graph(sn[s]["db"])
            keys = sorted(g.index, key=g.index.get)
            ntok = [toks(k[1]) for k in keys]
            inv = collections.defaultdict(list)
            for i, t in enumerate(ntok):
                for w in t:
                    inv[w].append(i)
            idf = {w: math.log(g.n / len(v)) for w, v in inv.items() if len(v) <= 0.1 * g.n}
            fdir = {}
            for i, k in enumerate(keys):
                fdir[int(g.fid[i])] = dirof(k[0])
            dirid = np.array([hash(fdir.get(int(f), "")) for f in g.fid])
            for sha, ks in items:
                nodes = [g.index[k] for k in ks if k in g.index]
                if len(nodes) < 2:
                    continue
                seed = nodes[0]
                truth = np.array(nodes[1:], dtype=np.int64)
                near = g.near(np.array([seed], dtype=np.int64))
                dist = np.full(g.n, 3, dtype=np.int64)
                dist[near["either3"]] = 2
                dist[near["either2"]] = 1
                dist[near["either1"]] = 0
                samef = (g.fid == g.fid[seed]).astype(float)
                samed = (dirid == dirid[seed]).astype(float)
                loc = g.loc.astype(float)
                lex = np.zeros(g.n)
                for w in ntok[seed]:
                    if w in idf:
                        for i in inv[w]:
                            lex[i] += idf[w]
                sc = {"SIZE": loc, "SAMEFILE": samef * 1e9 + loc, "N": samef * 1e12 - dist * 1e10 + samed * 1e8 + loc, "LEX": lex * 1e6 + loc}
                sc["N+LEX"] = 1 / (60 + rankdata(-sc["N"], method="min")) + 1 / (60 + rankdata(-sc["LEX"], method="min"))
                for v in sc.values():
                    v[seed] = -1e30
                row = {}
                for k, v in sc.items():
                    srt = np.sort(v)
                    rank = g.n - np.searchsorted(srt, v[truth], side="right") + 1
                    row[k] = (float(np.mean(rank <= 20)), bool((rank <= 20).any()))
                # files other than the seed's: rank the files by the file version of N
                tfiles = {int(g.fid[t]) for t in truth if g.fid[t] != g.fid[seed]}
                if tfiles:
                    nf = g.nfiles
                    mind = np.full(nf, 3, dtype=np.int64)
                    np.minimum.at(mind, g.fid, dist)
                    floc = np.bincount(g.fid, weights=g.loc, minlength=nf)
                    fsame = np.zeros(nf)
                    for f, d in fdir.items():
                        fsame[f] = d == fdir[int(g.fid[seed])]
                    fs = {"N": -mind * 1e10 + fsame * 1e8 + floc, "SIZE": floc}
                    fs = {k: np.where(np.arange(nf) == g.fid[seed], -1e30, v) for k, v in fs.items()}
                    frow = {}
                    for k, v in fs.items():
                        srt = np.sort(v)
                        ranks = [nf - int(np.searchsorted(srt, v[f], side="right")) + 1 for f in tfiles]
                        frow[k] = min(ranks) <= 5
                    row["files"] = frow
                row["ntruth"] = len(truth)
                res.append(row)
        print(f"{repo}: {len(res)} fixes with at least 2 edited functions in the graph; " + "; ".join(f"{k} recall@20 {100 * np.mean([r[k][0] for r in res]):.1f}%" for k in RK), flush=True)
        for r in res:
            r["repo"] = repo
        allres += res
    print(f"\n=== POOLED ({len(allres)} fixes; median other edited functions {int(np.median([r['ntruth'] for r in allres]))}) ===")
    for k in RK:
        print(f"  {k:9s} recall at 20 {100 * np.mean([r[k][0] for r in allres]):5.1f}%   at least one other edited function in the top 20 {100 * np.mean([r[k][1] for r in allres]):5.1f}%")
    fr = [r["files"] for r in allres if "files" in r]
    print(f"  fixes with other edited files: {len(fr)}; at least one in the top 5 files: N {100 * np.mean([f['N'] for f in fr]):.1f}%, size alone {100 * np.mean([f['SIZE'] for f in fr]):.1f}%")
    print("  by repository, recall at 20 (N / LEX / N+LEX): " + "; ".join(f"{repo} {100 * np.mean([r['N'][0] for r in allres if r['repo'] == repo]):.0f} / {100 * np.mean([r['LEX'][0] for r in allres if r['repo'] == repo]):.0f} / {100 * np.mean([r['N+LEX'][0] for r in allres if r['repo'] == repo]):.0f}" for repo, _ in DATASETS if any(r["repo"] == repo for r in allres)))
    print("\n=== VERDICTS ===")
    n20, l20 = np.mean([r["N"][0] for r in allres]), np.mean([r["LEX"][0] for r in allres])
    print(f"  AC1 N recall at 20 {100 * n20:.1f}% (needs 50%): {'supported' if n20 >= 0.5 else 'not supported'}")
    print(f"  AC2 N minus LEX {100 * (n20 - l20):+.1f} points (needs +15): {'supported' if n20 - l20 >= 0.15 else 'not supported'}")
    f5 = np.mean([f["N"] for f in fr])
    print(f"  AC3 other edited file in the top 5 files for {100 * f5:.1f}% (needs 60%): {'supported' if f5 >= 0.6 else 'not supported'}")
    print(f"  surprise bar (AC2 below 5 points): {'MET' if n20 - l20 < 0.05 else 'not met'}")


if __name__ == "__main__":
    main()
