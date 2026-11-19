#!/usr/bin/env python3
"""Test selection as a call-graph problem. Hypotheses TS1-TS5: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running."""
import collections
import json
import math
import os
import random
import re
import subprocess
import sys

import numpy as np
from scipy.stats import rankdata

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import lang_validation as LV  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
DATASETS = [("dpdk", "trailer"), ("mesa", "trailer"), ("libgit2", "blame"), ("redis", "blame"), ("libxml2", "blame")]
RK = ["SIZE", "DIR", "NAME", "N", "N+NAME"]
TESTRE = re.compile(r"(^|/)(tests?|testing|t|spec|unittests?)/|(^|/)test_[^/]*$|_test\.[a-z]+$|(^|/)tests?\.[a-z]+$")
TOK = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z]+|[a-z]+")


def is_test(p):
    return bool(TESTRE.search(p))


def toks(p):
    return {t.lower() for t in TOK.findall(re.sub(r"[^A-Za-z]+", " ", p)) if len(t) > 2 and t.lower() not in ("test", "tests", "src", "lib", "include", "the", "unit")}


def prefix(a, b):
    n = 0
    for x, y in zip(a.split("/")[:-1], b.split("/")[:-1]):
        if x != y:
            break
        n += 1
    return n


def load(repo, kind):
    if kind == "trailer":
        from concurrent.futures import ProcessPoolExecutor
        pairs = json.load(open(f"{B}/argl/links_{repo}.json"))
        random.Random(3).shuffle(pairs)
        pairs = pairs[:2500]
        fixshas = list(dict.fromkeys(p["fix"] for p in pairs))
        info = {}
        with ProcessPoolExecutor(max_workers=6) as ex:
            for r in ex.map(LV.commit_worker, [(f"{BR.POOL}/{repo}", "c", fixshas[i : i + 25]) for i in range(0, len(fixshas), 25)]):
                info.update(r)
    else:
        pairs, info = LV.build(repo, 2500)
    fixes = {}
    for p in pairs:
        if p["fix"] not in fixes:
            fixes[p["fix"]] = (p["fix_ct"], sorted({tuple(k) for k in info.get(p["fix"], ([], 0, 0))[0]}))
    return fixes


def files_of(repo, shas):
    out = subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "show", "--no-walk=unsorted", "--stdin", "--name-only", "--format=\x1e%H"], input="\n".join(shas) + "\n", capture_output=True, text=True, errors="replace").stdout
    res = {}
    for blk in out.split("\x1e")[1:]:
        lines = blk.strip().split("\n")
        res[lines[0].strip()] = [l for l in lines[1:] if l]
    return res


def main():
    allres = []
    for repo, kind in DATASETS:
        fixes = load(repo, kind)
        files = files_of(repo, list(fixes))
        sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
        cf = f"{B}/blast/{repo}/snapshot_cts.npy" if os.path.exists(f"{B}/blast/{repo}/snapshot_cts.npy") else f"{B}/blast/lang_{repo}_snapcts.npy"
        if os.path.exists(cf):
            cts = np.load(cf)
        else:
            cts = np.array([int(subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "show", "-s", "--format=%ct", x["commit"]], capture_output=True, text=True).stdout.strip()) for x in sn])
            np.save(f"{B}/blast/lang_{repo}_snapcts.npy", cts)
        by = collections.defaultdict(list)
        for sha, (ct, ks) in fixes.items():
            s = int(np.searchsorted(cts, ct, side="right")) - 1
            if s >= 0:
                by[s].append((sha, ks))
        res = []
        ntests = []
        for s, items in sorted(by.items()):
            g = BR.Graph(sn[s]["db"])
            keys = sorted(g.index, key=g.index.get)
            fpaths = sorted({k[0] for k in keys})
            tfid = [i for i, p in enumerate(fpaths) if is_test(p)]
            if len(tfid) < 5:
                continue
            tpaths = [fpaths[i] for i in tfid]
            tset = set(tpaths)
            floc = np.bincount(g.fid, weights=g.loc, minlength=g.nfiles)[tfid]
            ttok = [toks(p) for p in tpaths]
            inv = collections.defaultdict(list)
            for i, t in enumerate(ttok):
                for w in t:
                    inv[w].append(i)
            idf = {w: math.log(len(tpaths) / len(v)) for w, v in inv.items()}
            for sha, ks in items:
                src = [k for k in ks if not is_test(k[0]) and k in g.index]
                truth = {f for f in files.get(sha, []) if f in tset}
                if not src or not truth:
                    continue
                nodes = np.array([g.index[k] for k in src], dtype=np.int64)
                near = g.near(nodes)
                dist = np.full(g.n, 3, dtype=np.int64)
                dist[near["either3"]] = 2
                dist[near["either2"]] = 1
                dist[near["either1"]] = 0
                mind = np.full(g.nfiles, 3, dtype=np.int64)
                np.minimum.at(mind, g.fid, dist)
                mind = mind[tfid]
                spaths = {k[0] for k in src}
                pre = np.array([max(prefix(sp, tp) for sp in spaths) for tp in tpaths], dtype=float)
                stoks = set().union(*[toks(sp) for sp in spaths])
                name = np.array([sum(idf.get(w, 0) for w in (stoks & t)) for t in ttok])
                sc = {"SIZE": floc, "DIR": pre * 1e9 + floc, "NAME": name * 1e9 + floc, "N": -mind * 1e12 + pre * 1e9 + floc}
                sc["N+NAME"] = 1 / (60 + rankdata(-sc["N"], method="min")) + 1 / (60 + rankdata(-sc["NAME"], method="min"))
                ti = [tpaths.index(f) for f in truth]
                row = {}
                for k, v in sc.items():
                    srt = np.sort(v)
                    rk = len(v) - np.searchsorted(srt, v[ti], side="right") + 1
                    first = int(rk.min())
                    row[k] = (first <= 1, first <= 5, first <= 10, first / len(v))
                row["nt"] = len(tpaths)
                row["repo"] = repo
                res.append(row)
        print(f"{repo}: {len(res)} fixes with a source function and a touched test file; median test files {int(np.median([r['nt'] for r in res])) if res else 0}; " + "; ".join(f"{k} top5 {100 * np.mean([r[k][1] for r in res]):.1f}% budget {100 * np.mean([r[k][3] for r in res]):.1f}%" for k in RK) if res else f"{repo}: none", flush=True)
        allres += res
    print(f"\n=== POOLED ({len(allres)} fixes) ===")
    print(f"  {'ranker':8s} {'top 1':>7s} {'top 5':>7s} {'top 10':>7s} {'run budget':>11s}")
    for k in RK:
        print(f"  {k:8s} " + " ".join(f"{100 * np.mean([r[k][i] for r in allres]):6.1f}%" for i in range(3)) + f" {100 * np.mean([r[k][3] for r in allres]):10.1f}%")
    print("  by repository, top 5 (SIZE / DIR / NAME / N / N+NAME): " + "; ".join(f"{repo} " + " / ".join(f"{100 * np.mean([r[k][1] for r in allres if r['repo'] == repo]):.0f}" for k in RK) for repo, _ in DATASETS if any(r["repo"] == repo for r in allres)))
    t5 = {k: np.mean([r[k][1] for r in allres]) for k in RK}
    print("\n=== VERDICTS ===")
    print(f"  TS1 N top 5 {100 * t5['N']:.1f}% (needs 40%), SIZE {100 * t5['SIZE']:.1f}% (needs 10% or less): {'supported' if t5['N'] >= 0.4 and t5['SIZE'] <= 0.1 else 'not supported'}")
    print(f"  TS2 N minus DIR {100 * (t5['N'] - t5['DIR']):+.1f} points (needs +5): {'supported' if t5['N'] - t5['DIR'] >= 0.05 else 'not supported'}")
    b = np.mean([r["N"][3] for r in allres])
    print(f"  TS3 N run budget {100 * b:.1f}% (needs 15% or less): {'supported' if b <= 0.15 else 'not supported'}")
    print(f"  TS4 N+NAME minus N {100 * (t5['N+NAME'] - t5['N']):+.1f} points (needs +3): {'supported' if t5['N+NAME'] - t5['N'] >= 0.03 else 'not supported'}")
    wins = sum(np.mean([r['N'][1] for r in allres if r['repo'] == repo]) - np.mean([r['SIZE'][1] for r in allres if r['repo'] == repo]) >= 0.15 for repo, _ in DATASETS if any(r["repo"] == repo for r in allres))
    print(f"  TS5 repositories where N beats SIZE by 15 points: {wins} of 5 (needs 4): {'supported' if wins >= 4 else 'not supported'}")
    print(f"  surprise bar (N top 5 within 2 points of DIR): {'MET' if abs(t5['N'] - t5['DIR']) <= 0.02 else 'not met'}")


if __name__ == "__main__":
    main()
