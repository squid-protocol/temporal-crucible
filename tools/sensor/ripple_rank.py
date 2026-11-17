#!/usr/bin/env python3
"""Retrieval and same-author tests on named-cause pairs. Hypotheses R1-R4, A1-A3: docs/sensor-overhaul/sensors/ripple_radius.md ("Retrieval and same-author tests"),
fixed before running.

    python tools/sensor/ripple_rank.py REPO [REPO ...]       (curl uses the v3c message links; openssl, freebsd-src the Fixes: trailer links)

Retrieval: for each pair with a fixed function outside the inducing commit's changed set, rank every other function of the nearest quarterly snapshot's call graph
by several rankers and report where the fixed function lands (expected hit rate in the top k, ties split evenly; the best-ranked fixed function counts).
Same author: the pairs split by whether the fix and the inducing commit have the same author e-mail; the radius against same-file functions as in ripple_links.py."""
import collections
import json
import subprocess
import sys

import numpy as np

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import ripple_links as RL  # noqa: E402

TRAILER = {"openssl", "freebsd-src"}
if any(n in TRAILER for n in sys.argv[1:]):
    _curl_links = RL.links
    RL.links = lambda name: json.load(open(f"/tmp/gitgalaxy-scratch/claude/argl/links_{name}.json")) if name in TRAILER else _curl_links(name)
KS = (5, 10, 20, 50)
RANKERS = ["random", "size", "file", "graph", "file+graph", "graph+file", "file+graph+size"]


def author(repo, sha, cache={}):
    k = (repo, sha)
    if k not in cache:
        cache[k] = RL.git(f"{RL.POOL}/{repo}", "show", "-s", "--format=%ae", sha).strip().lower()
    return cache[k]


def distances(I, fwd, rev, kmax=3):
    dist, frontier, seen = {}, set(I), set(I)
    for d in range(1, kmax + 1):
        nxt = set()
        for n in frontier:
            nxt |= fwd.get(n, set()) | rev.get(n, set())
        nxt -= seen
        for n in nxt:
            dist[n] = d
        seen |= nxt
        frontier = nxt
    return dist


def rank_one(row):
    nodes, loc, args, fwd, rev, by_file, dec, by_dec = row["graph"]
    I, Fo = row["Im"], row["Fo"]
    cand = [n for n in nodes if n not in I]
    if not cand or not Fo:
        return None
    idx = {n: i for i, n in enumerate(cand)}
    files = {p for p, _ in I}
    dist = distances(I, fwd, rev)
    size = np.array([-loc[n] for n in cand], float)
    infile = np.array([0 if n[0] in files else 1 for n in cand], float)
    dd = np.array([dist.get(n, 4) for n in cand], float)
    scores = {
        "random": np.zeros(len(cand)),
        "size": size,
        "file": infile,
        "graph": dd,
        "file+graph": infile * 10 + dd,
        "graph+file": dd * 10 + infile,
        "file+graph+size": (infile * 10 + dd) * 1e6 + (size - size.min()) / max(size.max() - size.min(), 1.0),
    }
    out = {"N": len(cand), "files": int(sum(1 for n in cand if n[0] in files))}
    targets = [idx[f] for f in Fo if f in idx]
    if not targets:
        return None
    for nm, sc in scores.items():
        best_hit = {k: 0.0 for k in KS}
        best_rank = len(cand)
        for t in targets:
            better = int((sc < sc[t]).sum())
            tied = int((sc == sc[t]).sum())
            exp_rank = better + (tied + 1) / 2
            best_rank = min(best_rank, exp_rank)
            for k in KS:
                best_hit[k] = max(best_hit[k], min(1.0, max(0.0, (k - better) / tied)))
        out[nm] = (best_hit, best_rank)
    return out


def table(rows, label):
    rows = [r for r in rows if r]
    if not rows:
        print(f"  {label}: no pairs")
        return
    print(f"  {label}: {len(rows)} pairs; median candidates {int(np.median([r['N'] for r in rows]))}, median functions in the changed files {int(np.median([r['files'] for r in rows]))}")
    print(f"    {'ranker':18s} " + " ".join(f"{'top ' + str(k):>8s}" for k in KS) + f" {'median rank':>12s}")
    for nm in RANKERS:
        hits = {k: np.mean([r[nm][0][k] for r in rows]) for k in KS}
        mr = np.median([r[nm][1] for r in rows])
        print(f"    {nm:18s} " + " ".join(f"{100 * hits[k]:7.1f}%" for k in KS) + f" {mr:12.0f}")


def main():
    names = [a for a in sys.argv[1:] if not a.startswith("--")]
    allres = []
    for name in names:
        res, stats, n = RL.analyse(name)
        for r in res:
            r["repo"] = name
            r["same_author"] = author(name, r["fix"]) == author(name, r["ind"])
            r["rank"] = rank_one(r) if r["Fo"] else None
        allres += res
        print(f"\n=== {name}: {n} pairs, usable {len(res)}, with a fixed function outside the changed set {sum(1 for r in res if r['Fo'])} ===", flush=True)
        table([r["rank"] for r in res], "RETRIEVAL, all such pairs")
        table([r["rank"] for r in res if r["Fo"] and not ({p for p, _ in r["Fo"]} & {p for p, _ in r["Im"]})], "RETRIEVAL, fix in a different file from every changed function")
        sa = [r for r in res if r["same_author"]]
        da = [r for r in res if not r["same_author"]]
        print(f"  SAME AUTHOR: {len(sa)} pairs same author, {len(da)} different")
        RL.summarise(sa, "same author")
        RL.summarise(da, "different author")
    if len(names) > 1:
        print(f"\n=== POOLED over {', '.join(names)} ===")
        table([r["rank"] for r in allres], "RETRIEVAL, all pairs with a fixed function outside the changed set")
        table([r["rank"] for r in allres if r["Fo"] and not ({p for p, _ in r["Fo"]} & {p for p, _ in r["Im"]})], "RETRIEVAL, fix in a different file from every changed function")
        RL.summarise([r for r in allres if r["same_author"]], "same author")
        RL.summarise([r for r in allres if not r["same_author"]], "different author")
        print("\n  same-function share by author: " + ", ".join(f"{k} {100 * np.mean([r['same_func'] for r in allres if r['same_author'] == k]):.0f}% (n {sum(1 for r in allres if r['same_author'] == k)})" for k in (True, False)))


if __name__ == "__main__":
    main()
