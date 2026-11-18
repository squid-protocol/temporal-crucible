#!/usr/bin/env python3
"""How good is the neighbourhood as a ranker, and is there lift over size? Hypotheses PL1-PL5: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.

For each verified pair with a fixed function outside the changed set, every other function of the nearest quarterly snapshot is a candidate. Features of a candidate: size decile (10),
same file as a changed function (2), call distance to the changed set (4: 1, 2, 3 calls, farther), number of callers (3: 0, 1 to 2, 3+) = 240 cells. Per pair the candidates and the
positives are counted per cell, and every ranker (a score per cell) is scored exactly from the counts, ties split evenly.

    python tools/sensor/retrieval_lift.py linux dpdk mesa        (blast/<repo>_v/measure.pkl and touched.pkl; the pair lists under argl)"""
import collections
import json
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
PAIRS = {"linux": f"{B}/blast/linux_pairs.json", "dpdk": f"{B}/argl/links_dpdk.json", "mesa": f"{B}/argl/links_mesa.json"}
TAG = {"linux": "linux-core", "dpdk": "dpdk", "mesa": "mesa"}
NCELL = 2 * 4 * 10 * 3
rng = np.random.default_rng(2982)


def cell_index(file_, dist, sd, fan):
    return ((file_ * 4 + dist) * 10 + sd) * 3 + fan


CELLS = np.array([(f, d, s, n) for f in range(2) for d in range(4) for s in range(10) for n in range(3)])  # index order matches cell_index


def worker(args):
    db, items = args
    g = BR.Graph(db)
    fan = np.asarray(g.callers_m.sum(axis=0)).ravel()  # number of callers of each node
    fanbin = np.where(fan == 0, 0, np.where(fan <= 2, 1, 2))
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
        file_ = np.isin(g.fid, np.unique(g.fid[I])).astype(np.int64)
        cell = cell_index(file_, dist, g.dec, fanbin)
        keep = np.ones(g.n, dtype=bool)
        keep[I] = False
        C = np.bincount(cell[keep], minlength=NCELL)
        P = np.bincount(cell[Fo], minlength=NCELL)
        out.append({"pid": it["pid"], "C": C.astype(np.int32), "P": P.astype(np.int16), "nfo": len(Fo), "diff_file": not bool(file_[Fo].any())})
    return out


def score_pair(C, P, s, ks=(20, 100), within=None):
    """AUC and top-k hit probability of the score s (per cell, higher is better) for one pair. within: mask of cells restricting the candidates per positive (size decile)."""
    N = C.sum()
    aucs, hits = [], {k: 0.0 for k in ks}
    for c in np.nonzero(P)[0]:
        mc = np.ones(NCELL, bool) if within is None else (CELLS[:, 2] == CELLS[c, 2])
        Cm = C * mc
        n = Cm.sum()
        if n < 2:
            continue
        lower = Cm[s < s[c]].sum()
        equal = Cm[s == s[c]].sum() - 1
        aucs.append((lower + 0.5 * equal) / (n - 1))
        if within is None:
            better = Cm[s > s[c]].sum()
            tied = Cm[s == s[c]].sum()
            for k in ks:
                hits[k] = max(hits[k], min(1.0, max(0.0, (k - better) / tied)))
    return (float(np.mean(aucs)) if aucs else np.nan), hits


def evaluate(rows, s, within=False):
    a, h20, h100 = [], [], []
    for r in rows:
        auc, hits = score_pair(r["C"], r["P"], s, within=True if within else None)
        a.append(auc)
        h20.append(hits[20])
        h100.append(hits[100])
    return np.nanmean(a), np.mean(h20), np.mean(h100)


def main():
    repos = sys.argv[1:]
    allrows = {}
    for repo in repos:
        d = f"{B}/blast/{repo}_v"
        m = pd.read_pickle(f"{d}/measure.pkl")
        m = m[(m.status == "ok") & (m.nFo > 0)]
        pairs = json.load(open(PAIRS[repo]))
        touched = pickle.load(open(f"{d}/touched.pkl", "rb"))
        sn = json.load(open(f"{BR.B}/scan_{TAG[repo]}/snapshots.json"))
        by = collections.defaultdict(list)
        for r in m.itertuples():
            p = pairs[r.pid]
            by[int(r.snapshot)].append({"pid": r.pid, "I": [tuple(k) for k in touched[p["ind"]]], "F": [tuple(k) for k in touched[p["fix"]]]})
        rows = []
        with ProcessPoolExecutor(max_workers=6) as ex:
            for res in ex.map(worker, [(sn[s]["db"], it) for s, it in sorted(by.items())]):
                rows += res
        for r in rows:
            r["ct"] = pairs[r["pid"]]["ind_ct"]
            r["repo"] = repo
        rows.sort(key=lambda r: r["ct"])
        allrows[repo] = rows
        print(f"{repo}: {len(rows)} pairs ranked against {int(np.median([r['C'].sum() for r in rows]))} candidates (median)", flush=True)
    sd = CELLS[:, 2].astype(float)
    fl, ds, fn = CELLS[:, 0].astype(float), CELLS[:, 1].astype(float), CELLS[:, 3].astype(float)
    rankers = {"random": np.zeros(NCELL), "size (largest first)": sd, "same file": fl, "call distance": -ds, "file, then distance": fl * 100 - ds * 10, "file, distance, then size": fl * 1000 - ds * 100 + sd, "caller count": fn}
    # fitted model: earliest 60% of each repository's pairs, scored on the latest 40%
    train = [r for repo in repos for r in allrows[repo][: int(0.6 * len(allrows[repo]))]]
    test = {repo: allrows[repo][int(0.6 * len(allrows[repo])) :] for repo in repos}
    Pc = sum(r["P"].astype(float) for r in train)
    Nc = sum(r["C"].astype(float) - r["P"] for r in train)
    X = np.column_stack([CELLS[:, 0], CELLS[:, 1] == 0, CELLS[:, 1] == 1, CELLS[:, 1] == 2, CELLS[:, 2], CELLS[:, 2] ** 2, CELLS[:, 3] == 1, CELLS[:, 3] == 2, CELLS[:, 0] * (CELLS[:, 1] == 0)]).astype(float)
    X = (X - X.mean(axis=0)) / X.std(axis=0)  # standardised: the fit converges
    w = np.r_[Pc, Nc]
    w = w / w.sum() * 1e5 + 1e-9  # weights scaled (they spanned nine orders of magnitude)
    y2 = np.r_[np.ones(NCELL), np.zeros(NCELL)]

    def fit(cols):
        m = LogisticRegression(C=1e3, max_iter=5000).fit(np.vstack([X[:, cols]] * 2), y2, sample_weight=w)
        return m.decision_function(X[:, cols])

    rankers["fitted (size, file, distance, callers)"] = fit(list(range(X.shape[1])))
    rankers["fitted without size"] = fit([0, 1, 2, 3, 6, 7, 8])
    print("\n=== RANKING THE FIXED FUNCTION AMONG ALL FUNCTIONS (all pairs; AUC = chance the fixed function outranks a random other function) ===")
    res = {}
    for repo in repos + ["pooled"]:
        rows = [r for rp in repos for r in allrows[rp]] if repo == "pooled" else allrows[repo]
        print(f"\n  {repo}: {len(rows)} pairs")
        print(f"    {'ranker':40s} {'AUC':>6s} {'top 20':>8s} {'top 100':>8s} {'within-size AUC':>16s}")
        for nm, s in rankers.items():
            if nm.startswith("fitted"):
                continue
            a, h20, h100 = evaluate(rows, s)
            w = evaluate(rows, s, within=True)[0] if nm != "size (largest first)" and nm != "random" else float("nan")
            res[(repo, nm)] = (a, h20, h100, w)
            print(f"    {nm:40s} {a:6.3f} {100 * h20:7.1f}% {100 * h100:7.1f}% {w:16.3f}")
    print("\n=== FITTED MODEL (trained on the earliest 60% of each repository's pairs, scored on the latest 40%) ===")
    for repo in repos + ["pooled"]:
        rows = [r for rp in repos for r in test[rp]] if repo == "pooled" else test[repo]
        print(f"\n  {repo} (test): {len(rows)} pairs")
        for nm in ("size (largest first)", "file, distance, then size", "fitted (size, file, distance, callers)", "fitted without size"):
            a, h20, h100 = evaluate(rows, rankers[nm])
            w = evaluate(rows, rankers[nm], within=True)[0] if nm != "size (largest first)" else float("nan")
            res[(repo, "test " + nm)] = (a, h20, h100, w)
            print(f"    {nm:40s} {a:6.3f} {100 * h20:7.1f}% {100 * h100:7.1f}% {w:16.3f}")
    print("\n=== WITHIN-SIZE AUC BY SIZE QUARTILE OF THE FIXED FUNCTION (pooled; the repowise form) ===")
    pooled = [r for rp in repos for r in allrows[rp]]
    for nm in ("file, then distance", "call distance"):
        s = rankers[nm]
        per = collections.defaultdict(list)
        for r in pooled:
            for c in np.nonzero(r["P"])[0]:
                sdc = CELLS[c, 2]
                mc = CELLS[:, 2] == sdc
                Cm = r["C"] * mc
                if Cm.sum() < 2:
                    continue
                per[min(int(sdc) // 3, 3) if sdc < 9 else 3].append(((Cm[s < s[c]].sum() + 0.5 * (Cm[s == s[c]].sum() - 1)) / (Cm.sum() - 1)))
        print(f"  {nm:24s} " + ", ".join(f"size deciles {['1-3', '4-6', '7-9', '10'][q]}: {np.mean(per[q]):.3f} (n {len(per[q])})" for q in range(4)))
    dfp = [r for r in pooled if r["diff_file"]]
    a, h20, h100 = evaluate(dfp, rankers["call distance"])
    w = evaluate(dfp, rankers["call distance"], within=True)[0]
    s20 = evaluate(dfp, rankers["size (largest first)"])
    print(f"\n  fixes in a different file from every changed function ({len(dfp)} pairs): call distance AUC {a:.3f}, top 20 {100 * h20:.1f}%, top 100 {100 * h100:.1f}%, within-size AUC {w:.3f}; size alone AUC {s20[0]:.3f}, top 20 {100 * s20[1]:.1f}%")
    print("\n=== VERDICTS ===")
    pr = {r: res[(r, "size (largest first)")][0] for r in repos}
    print(f"  PL1 size-alone AUC by repository: {', '.join(f'{r} {v:.3f}' for r, v in pr.items())} (needs 0.65 or less in each): {'supported' if all(v <= 0.65 for v in pr.values()) else 'not supported'}")
    sz, fd = res[("pooled", "size (largest first)")], res[("pooled", "file, distance, then size")]
    print(f"  PL2 top 20, combined against size alone: {100 * fd[1]:.1f}% against {100 * sz[1]:.1f}% = {fd[1] / sz[1]:.1f} times (needs 3): {'supported' if fd[1] >= 3 * sz[1] else 'not supported'}")
    w = res[("pooled", "file, then distance")][3]
    print(f"  PL3 within-size AUC of file then distance, pooled: {w:.3f} (needs 0.65; the two smallest quartiles are listed above): {'supported' if w >= 0.65 else 'not supported'}")
    print(f"  PL4 different-file fixes, distance alone, within-size AUC {evaluate(dfp, rankers['call distance'], within=True)[0]:.3f} (needs 0.60)")
    ft, st = res[("pooled", "test fitted (size, file, distance, callers)")], res[("pooled", "test size (largest first)")]
    print(f"  PL5 test AUC fitted {ft[0]:.3f} against size alone {st[0]:.3f}: +{ft[0] - st[0]:.3f} (needs +0.15): {'supported' if ft[0] - st[0] >= 0.15 else 'not supported'}")
    print(f"  surprise bar (within-size AUC at or below 0.55): {'MET' if w <= 0.55 else 'not met'}")


if __name__ == "__main__":
    main()
