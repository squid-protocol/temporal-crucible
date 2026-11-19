#!/usr/bin/env python3
"""A ranker that works in both lag regimes. Hypotheses FU1-FU3: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running."""
import pickle

import numpy as np
from scipy.stats import rankdata

B = "/tmp/gitgalaxy-scratch/claude"
KS = (10, 60, 300, 1000)


def per_pair(p):
    a = p["arr"]
    rec, base, jt = a["rec"].astype(float), a["base"].astype(float), a["jt"]
    n1 = base * 1e10 - rec
    r_rec = rankdata(rec, method="min")  # 1 = most recent
    r_n1 = rankdata(-n1, method="min")
    out = {"REC": 1 + int((rec < rec[jt]).sum()), "N1": 1 + int((n1 > n1[jt]).sum())}
    for k in KS:
        s = 1 / (k + r_rec) + 1 / (k + r_n1)
        out[f"RRF{k}"] = 1 + int((s > s[jt]).sum())
    out["recrank"] = out["REC"]
    return out


def load():
    trailer = pickle.load(open(f"{B}/osv/trailer_triage_arrays.pkl", "rb"))
    src = {"DPDK Fixes pairs": [p for p in trailer if p["repo"] == "dpdk"], "Mesa Fixes pairs": [p for p in trailer if p["repo"] == "mesa"]}
    src["OSS-Fuzz four"] = pickle.load(open(f"{B}/osv/ossfuzz_results_main4.pkl", "rb"))
    src["nDPI"] = pickle.load(open(f"{B}/osv/ossfuzz_results_ndpi.pkl", "rb"))
    src["harfbuzz (n 12)"] = pickle.load(open(f"{B}/osv/ossfuzz_results_harfbuzz.pkl", "rb"))
    return src


def main():
    src = load()
    pp = {k: [per_pair(p) for p in v] for k, v in src.items()}
    rng = np.random.default_rng(2982)
    res = {}
    print(f"{'source':20s} {'pairs':>6s} {'median recency rank of the cause':>34s}")
    for name, rows in pp.items():
        print(f"{name:20s} {len(rows):6d} {np.median([r['recrank'] for r in rows]):34.0f}")
        agg = {k: [] for k in ("REC", "N1", "RRF60", "RRFk", "SWITCH", "ORACLE")}
        for _ in range(20):
            idx = rng.permutation(len(rows))
            h = len(idx) // 2
            for tr, te in ((idx[:h], idx[h:]), (idx[h:], idx[:h])):
                med = float(np.median([rows[i]["recrank"] for i in tr]))
                best_k = max(KS, key=lambda k: np.mean([rows[i][f"RRF{k}"] <= 20 for i in tr]))
                for i in te:
                    r = rows[i]
                    agg["REC"].append(r["REC"])
                    agg["N1"].append(r["N1"])
                    agg["RRF60"].append(r["RRF60"])
                    agg["RRFk"].append(r[f"RRF{best_k}"])
                    agg["SWITCH"].append(r["REC"] if med <= 30 else r["N1"])
                    agg["ORACLE"].append(min(r["REC"], r["N1"]))
        res[name] = agg
    print()
    for name, agg in res.items():
        print(f"=== {name}: held-out halves, top 1 / 5 / 20 ===")
        for k, v in agg.items():
            print(f"    {k:7s} " + " ".join(f"{100 * np.mean([x <= n for x in v]):6.1f}%" for n in (1, 5, 20)))
    t20 = lambda s, k: 100 * np.mean([x <= 20 for x in res[s][k]])  # noqa: E731
    big = ["DPDK Fixes pairs", "Mesa Fixes pairs", "OSS-Fuzz four", "nDPI"]
    dm = [x <= 20 for s in ("DPDK Fixes pairs", "Mesa Fixes pairs") for x in res[s]["RRF60"]]
    print("\n=== VERDICTS ===")
    print(f"  FU1 RRF top 20: DPDK+Mesa pooled {100 * np.mean(dm):.1f}% (needs 65), OSS-Fuzz four {t20('OSS-Fuzz four', 'RRF60'):.1f}% (needs 65), nDPI {t20('nDPI', 'RRF60'):.1f}% (needs 60): {'supported' if np.mean(dm) >= 0.65 and t20('OSS-Fuzz four', 'RRF60') >= 65 and t20('nDPI', 'RRF60') >= 60 else 'not supported'}")
    ok90 = [t20(s, "SWITCH") >= 0.9 * max(t20(s, "REC"), t20(s, "N1")) for s in big]
    beats = sum(t20(s, "SWITCH") > t20(s, "RRF60") for s in big)
    print(f"  FU2 SWITCH within 90% of the better of REC/N1 in {sum(ok90)} of 4 sources (needs all); beats RRF in {beats} of 4 (needs 3): {'supported' if all(ok90) and beats >= 3 else 'not supported'}")
    gains = {s: t20(s, "RRFk") - t20(s, "RRF60") for s in big}
    print(f"  FU3 RRFk minus RRF60 by source: {', '.join(f'{s} {g:+.1f}' for s, g in gains.items())} (needs +2 in one): {'supported' if max(gains.values()) >= 2 else 'not supported'}")
    print(f"  surprise bar (RRF below 50% on DPDK+Mesa): {'MET' if np.mean(dm) < 0.5 else 'not met'}")


if __name__ == "__main__":
    main()
