#!/usr/bin/env python3
"""Ranking test (AUC, top 20) with the added (ADD) and deleted (DEL) function events as the change, at function level and file level. Hypotheses RL1-RL5:
docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.

    python tools/sensor/retrieval_added_deleted.py dpdk mesa      (needs blast/<repo>/ad_sens_cache.pkl from added_deleted_sensitivity.py)"""
import collections
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import added_deleted_sensitivity as SENS  # noqa: E402
import blast_radius as BR  # noqa: E402
import retrieval_lift as RL  # noqa: E402

NF_CELL = 2 * 4 * 10
FC = np.array([(e, d, s) for e in range(2) for d in range(4) for s in range(10)])


def file_worker(args):
    db, items = args
    g = BR.Graph(db)
    nfile = g.nfiles
    floc = np.bincount(g.fid, weights=g.loc, minlength=nfile)
    present = np.bincount(g.fid, minlength=nfile) > 0
    if not present.any():
        return []  # a snapshot with no functions
    cuts = np.percentile(floc[present], np.arange(10, 100, 10))
    fdec = np.searchsorted(cuts, floc)
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
        mind = np.full(nfile, 3, dtype=np.int64)
        np.minimum.at(mind, g.fid, dist)
        ev = np.zeros(nfile, dtype=np.int64)
        ev[g.fid[I]] = 1
        cell = (ev * 4 + mind) * 10 + fdec
        C = np.bincount(cell[present], minlength=NF_CELL)
        P = np.bincount(cell[np.unique(g.fid[Fo])], minlength=NF_CELL)
        other = np.setdiff1d(np.unique(g.fid[Fo]), np.unique(g.fid[I]))  # repaired files other than the event's own file
        P2 = np.bincount(cell[other], minlength=NF_CELL)
        out.append({"pid": it["pid"], "C": C.astype(np.int32), "P": P.astype(np.int16), "P2": P2.astype(np.int16)})
    return out


def file_eval(rows, s, ks=(5, 20, 50)):
    hits = {k: [] for k in ks}
    aucs = []
    for r in rows:
        C, P = r["C"], r["P"]
        best = {k: 0.0 for k in ks}
        a = []
        for c in np.nonzero(P)[0]:
            better, tied, lower = C[s > s[c]].sum(), C[s == s[c]].sum(), C[s < s[c]].sum()
            for k in ks:
                best[k] = max(best[k], min(1.0, max(0.0, (k - better) / tied)))
            n = C.sum()
            if n > 1:
                a.append((lower + 0.5 * (tied - 1)) / (n - 1))
        for k in ks:
            hits[k].append(best[k])
        aucs.append(np.mean(a) if a else np.nan)
    return np.nanmean(aucs), {k: float(np.mean(v)) for k, v in hits.items()}


def main():
    repos = sys.argv[1:]
    sd = RL.CELLS[:, 2].astype(float)
    fl, ds = RL.CELLS[:, 0].astype(float), RL.CELLS[:, 1].astype(float)
    fr = {"random": np.zeros(RL.NCELL), "size (largest first)": sd, "same file": fl, "call distance": -ds, "file, then distance": fl * 100 - ds * 10, "file, distance, then size": fl * 1000 - ds * 100 + sd}
    flr = {"random": np.zeros(NF_CELL), "file size (largest first)": FC[:, 2].astype(float), "event file": FC[:, 0].astype(float), "call distance": -FC[:, 1].astype(float), "event file, then distance": FC[:, 0] * 100 - FC[:, 1] * 10.0, "event file, distance, then size": FC[:, 0] * 1000 - FC[:, 1] * 100.0 + FC[:, 2]}
    res = {}
    for repo in repos:
        pairs, sn, cts, (ver, events) = SENS.load(repo)
        for g in ("ADD", "DEL"):
            by = collections.defaultdict(list)
            for pid, p in enumerate(pairs):
                ev = events.get(p["ind"])
                if not ev or not ver.get(p["fix"]):
                    continue
                keys = [(e["path"], e["name"]) for e in ev if e["kind"] == g and SENS.keep(e, "union")]
                if not keys:
                    continue
                s = int(np.searchsorted(cts, p["ind_ct"], side="left")) - (1 if g == "DEL" else 0)
                if 0 <= s < len(sn):
                    by[s].append({"pid": pid, "I": keys, "F": ver[p["fix"]]})
            jobs = [(sn[s]["db"], it) for s, it in sorted(by.items())]
            rows, frows = [], []
            with ProcessPoolExecutor(max_workers=6) as ex:
                for r in ex.map(RL.worker, jobs):
                    rows += r
                for r in ex.map(file_worker, jobs):
                    frows += r
            print(f"\n########## {repo} {g}: {sum(len(v) for v in by.values())} pairs with events; {len(rows)} ranked (a repaired function outside the event set exists in the graph); median candidates {int(np.median([r['C'].sum() for r in rows]))} functions, {int(np.median([r['C'].sum() for r in frows]))} files ##########", flush=True)
            print(f"  FUNCTIONS    {'ranker':28s} {'AUC':>6s} {'top 20':>8s} {'top 100':>8s} {'within-size AUC':>16s}")
            for nm, s in fr.items():
                a, h20, h100 = RL.evaluate(rows, s)
                w = RL.evaluate(rows, s, within=True)[0] if nm not in ("random", "size (largest first)") else float("nan")
                res[(repo, g, "f", nm)] = (a, h20, h100, w)
                print(f"               {nm:28s} {a:6.3f} {100 * h20:7.1f}% {100 * h100:7.1f}% {w:16.3f}")
            hard = [{"C": r["C"], "P": r["P2"]} for r in frows if r["P2"].sum() > 0]
            print(f"  FILES        {'ranker':28s} {'AUC':>6s} {'top 5':>8s} {'top 20':>8s} {'top 50':>8s}   | repairs in OTHER files only ({len(hard)} pairs): top 5, top 20, top 50")
            for nm, s in flr.items():
                a, h = file_eval(frows, s)
                res[(repo, g, "file", nm)] = (a, h[5], h[20], h[50])
                a2, h2 = file_eval(hard, s)
                res[(repo, g, "hard", nm)] = (a2, h2[5], h2[20], h2[50])
                print(f"               {nm:28s} {a:6.3f} {100 * h[5]:7.1f}% {100 * h[20]:7.1f}% {100 * h[50]:7.1f}%   | {100 * h2[5]:5.1f}% {100 * h2[20]:5.1f}% {100 * h2[50]:5.1f}%")
    print("\n=== VERDICTS ===")
    groups = [(r, g) for r in repos for g in ("ADD", "DEL")]
    r1 = {k: res[(*k, "f", "file, distance, then size")][1] / max(res[(*k, "f", "size (largest first)")][1], 1e-6) for k in groups}
    print("  RL1 combined top 20 over size-alone top 20: " + ", ".join(f"{r} {g} {v:.0f}x" for (r, g), v in r1.items()) + f" (needs 3x in all): {'supported' if all(v >= 3 for v in r1.values()) else 'not supported'}")
    r2 = {k: res[(*k, "f", "call distance")][3] for k in groups}
    print("  RL2 call distance within-size AUC: " + ", ".join(f"{r} {g} {v:.3f}" for (r, g), v in r2.items()) + f" (needs 0.65 in all): {'supported' if all(v >= 0.65 for v in r2.values()) else 'not supported'}")
    r3 = {(r, "DEL"): res[(r, "DEL", "f", "call distance")][1] for r in repos}
    print("  RL3 DEL call distance top 20: " + ", ".join(f"{r} {100 * v:.1f}%" for (r, _), v in r3.items()) + f" (needs 30% in both): {'supported' if all(v >= 0.3 for v in r3.values()) else 'not supported'}")
    r4 = {k: res[(*k, "file", "event file, distance, then size")][2] for k in groups}
    print("  RL4 combined file ranker, repaired file in the top 20: " + ", ".join(f"{r} {g} {100 * v:.0f}%" for (r, g), v in r4.items()) + f" (needs 60% in all): {'supported' if all(v >= 0.6 for v in r4.values()) else 'not supported'}")
    r5 = {k: res[(*k, "f", "file, distance, then size")][1] for k in groups}
    print("  RL5 combined function ranker top 20: " + ", ".join(f"{r} {g} {100 * v:.0f}%" for (r, g), v in r5.items()) + f" (needs 40% in all): {'supported' if all(v >= 0.4 for v in r5.values()) else 'not supported'}")
    low = [(k, v) for k, v in r2.items() if v <= 0.55]
    print(f"  surprise bar (call distance within-size AUC at or below 0.55): {'MET ' + str(low) if low else 'not met'}")


if __name__ == "__main__":
    main()
