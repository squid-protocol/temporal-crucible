#!/usr/bin/env python3
"""A learned lag window for the neighbourhood ranking. Hypotheses LW1-LW3 (and NR1-NR3 through ossfuzz_triage.py): docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.
    python tools/sensor/lag_window.py [holdout_pickle ...]"""
import pickle
import sys

import numpy as np

B = "/tmp/gitgalaxy-scratch/claude"


def rank_of(score, jt):
    return 1 + int((score > score[jt]).sum())


def recency_rank(rec, jt):
    return 1 + int((rec < rec[jt]).sum())  # 1 = the most recent candidate


def fit_window(pairs, q=90):
    return float(np.percentile([recency_rank(p["arr"]["rec"], p["arr"]["jt"]) for p in pairs], q))


def ranks(p, W):
    a = p["arr"]
    rec, base, jt = a["rec"].astype(float), a["base"].astype(float), a["jt"]
    n1 = base * 1e10 - rec
    out = {"REC": rank_of(-rec, jt), "N1": rank_of(n1, jt)}
    cut = np.sort(rec)[min(int(W) - 1, len(rec) - 1)]
    inwin = rec <= cut
    out["N1W"] = 1 + int(((inwin > inwin[jt]) | ((inwin == inwin[jt]) & (n1 > n1[jt]))).sum())  # exact lexicographic order: in-window first, then N1 (adding a large constant to float scores loses ties)
    return out


def evaluate(train, test, own_W, other_W=None):
    res = {"REC": [], "N1": [], "N1W": [], "N1W100": [], "N1Wother": []}
    for p in test:
        r = ranks(p, own_W)
        res["REC"].append(r["REC"])
        res["N1"].append(r["N1"])
        res["N1W"].append(r["N1W"])
        res["N1W100"].append(ranks(p, 100)["N1W"])
        if other_W:
            res["N1Wother"].append(ranks(p, other_W)["N1W"])
    return res


def show(name, res):
    print(f"    {name:9s} " + " ".join(f"{100 * np.mean([x <= n for x in res]):6.1f}%" for n in (1, 5, 20)) if res else f"    {name:9s} -")


def split(pairs, seed):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(pairs))
    h = len(idx) // 2
    return [pairs[i] for i in idx[:h]], [pairs[i] for i in idx[h:]]


def main():
    trailer = pickle.load(open(f"{B}/osv/trailer_triage_arrays.pkl", "rb"))
    fuzz = pickle.load(open(f"{B}/osv/ossfuzz_results_main4.pkl", "rb"))
    sources = {"DPDK+Mesa Fixes pairs": trailer, "OSS-Fuzz (4 repositories)": fuzz}
    Wall = {k: fit_window(v) for k, v in sources.items()}
    print("windows fitted on each whole source (90th percentile of the cause's recency rank): " + ", ".join(f"{k} W = {w:.0f}" for k, w in Wall.items()))
    names = list(sources)
    held = {}
    for src in names:
        other = [n for n in names if n != src][0]
        agg = {k: [] for k in ("REC", "N1", "N1W", "N1W100", "N1Wother")}
        for seed in range(20):
            a, b = split(sources[src], seed)
            for tr, te in ((a, b), (b, a)):
                W = fit_window(tr)
                r = evaluate(tr, te, W, Wall[other])
                for k in agg:
                    agg[k] += r[k]
        held[src] = agg
        print(f"\n=== {src}: {len(sources[src])} pairs; held-out halves (20 random 2-fold splits); top 1 / 5 / 20 ===")
        for k in ("REC", "N1", "N1W", "N1W100", "N1Wother"):
            show(k, agg[k])
    t20 = lambda src, k: 100 * np.mean([x <= 20 for x in held[src][k]])  # noqa: E731
    t5 = lambda src, k: 100 * np.mean([x <= 5 for x in held[src][k]])  # noqa: E731
    d, f = names
    print("\n=== VERDICTS ===")
    print(f"  LW1 OSS-Fuzz N1W {t20(f, 'N1W'):.1f}% vs N1 {t20(f, 'N1'):.1f}% (needs +20): {'ok' if t20(f, 'N1W') - t20(f, 'N1') >= 20 else 'no'}; DPDK/Mesa N1W {t20(d, 'N1W'):.1f}% vs N1 {t20(d, 'N1'):.1f}% (needs not worse than -2): {'ok' if t20(d, 'N1W') - t20(d, 'N1') >= -2 else 'no'}")
    print(f"  LW2 OSS-Fuzz N1W top 20 {t20(f, 'N1W'):.1f}% vs REC {t20(f, 'REC'):.1f}% (needs +5); top 5 {t5(f, 'N1W'):.1f}% vs {t5(f, 'REC'):.1f}% (needs +20): {'supported' if t20(f, 'N1W') - t20(f, 'REC') >= 5 and t5(f, 'N1W') - t5(f, 'REC') >= 20 else 'not supported'}")
    print(f"  LW3 OSS-Fuzz window on DPDK/Mesa loses {t20(d, 'N1W') - t20(d, 'N1Wother'):.1f} points (needs 20); DPDK/Mesa window on OSS-Fuzz loses {t20(f, 'N1W') - t20(f, 'N1Wother'):.1f} points (needs 10)")
    for path in sys.argv[1:]:
        hold = pickle.load(open(path, "rb"))
        print(f"\n=== HOLD-OUT {path.split('/')[-1]}: {len(hold)} entries; windows fitted on OSS-Fuzz (4 repositories) W = {Wall[f]:.0f} ===")
        res = evaluate(None, hold, Wall[f], Wall[d])
        for k in ("REC", "N1", "N1W", "N1W100", "N1Wother"):
            show(k, res[k])
        lags = [h["lag"] for h in hold]
        print(f"    median lag {np.median(lags):.0f} d; under 14 d {100 * np.mean([x < 14 for x in lags]):.0f}%")


if __name__ == "__main__":
    main()
