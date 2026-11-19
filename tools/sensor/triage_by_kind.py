#!/usr/bin/env python3
"""Reverse triage by fix category, and a category lag prior (N1L). Hypotheses FT4, FT5: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.
    python tools/sensor/triage_by_kind.py dpdk mesa"""
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
import change_kinds as CK  # noqa: E402
import change_kinds_diff as CDF  # noqa: E402
import fix_shapes as FS  # noqa: E402
import fix_taxonomy as FX  # noqa: E402
import lang_validation as LV  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
DAY = 86400


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
    CK.REPO = path
    fm = FX.msgs(repo, fixshas)
    feats = CDF.diff_features(fixshas, f"{B}/fixfeats_{repo}.pkl")
    tag = {s: (CK.fix_class(*fm.get(s, ("", "")))[0], FS.shape(feats[s])) for s in fixshas}
    by = defaultdict(list)
    for p in pairs:
        G = fixinfo.get(p["fix"], ([], 0, 0))[0]
        s = int(np.searchsorted(cts, p["fix_ct"], side="right")) - 1
        ci = idx_of.get(p["ind"])
        if G and s >= 0 and ci is not None and ok[ci] and p["fix_ct"] - 730 * DAY <= times[ci] < p["fix_ct"]:
            by[s].append((p, G, ci))
    allitems = [(s, it) for s, items in sorted(by.items()) for it in items]
    fold = {id(it[1][0]): (hash(it[1][0]["fix"]) % 2) for it in allitems}
    # lag prior: mean log-age of the true cause by mechanism class and by shape, fitted on the other fold
    prior = {}
    for f in (0, 1):
        tr = [it for _, it in allitems if fold[id(it[0])] != f]
        la = np.array([np.log1p((p["fix_ct"] - times[ci]) / DAY) for p, _, ci in tr])
        mu0 = float(la.mean())
        mech = defaultdict(list)
        shp = defaultdict(list)
        for (p, _, ci), l in zip(tr, la):
            mech[tag[p["fix"]][0]].append(l)
            shp[tag[p["fix"]][1]].append(l)
        mm = {k: float(np.mean(v)) if len(v) >= 30 else mu0 for k, v in mech.items()}
        sm = {k: float(np.mean(v)) if len(v) >= 30 else mu0 for k, v in shp.items()}
        res_ = [l - (mm[tag[p["fix"]][0]] + sm[tag[p["fix"]][1]]) / 2 for (p, _, ci), l in zip(tr, la)]
        prior[f] = (mu0, mm, sm, float(np.std(res_)) or 1.0)
    out = []
    for s, items in sorted(by.items()):
        g = BR.Graph(sn[s]["db"])
        for p, G, ci in items:
            Gn = [g.index[k] for k in G if k in g.index]
            if not Gn:
                continue
            near = g.near(np.array(Gn, dtype=np.int64))
            dnode = np.full(g.n, 4, dtype=np.int64)
            dnode[near["either3"]] = 3
            dnode[near["either2"]] = 2
            dnode[near["either1"]] = 1
            dnode[Gn] = 0
            Gk, Gp, Gd = set(G), {k[0] for k in G}, {dirof(k[0]) for k in G}
            tf = p["fix_ct"]
            lo, hi = bisect.bisect_left(times, tf - 730 * DAY), bisect.bisect_left(times, tf)
            cand = [i for i in range(lo, hi) if ok[i] and shas[i] != p["fix"]]
            F = np.zeros((len(cand), 6))
            for j, i in enumerate(cand):
                ks = keys_of[i]
                nodes = [g.index[k] for k in ks if k in g.index]
                F[j] = [any(k in Gk for k in ks), any(k[0] in Gp for k in ks), (dnode[nodes].min() if nodes else 4), any(dirof(k[0]) in Gd for k in ks), len(ks), tf - times[i]]
            sf, sfile, dist, sdir, nf, rec = F.T
            dsc = np.where(dist <= 3, 4 - dist, 0)
            base = sf * 1e4 + sfile * 1e3 + dsc * 1e2 + sdir * 10
            mu0, mm, sm, sd = prior[1 - fold[id(p)]] if False else prior[fold[id(p)]]
            mech, shp = tag[p["fix"]]
            target = (mm.get(mech, mu0) + sm.get(shp, mu0)) / 2
            z = (np.log1p(rec / DAY) - target) / sd
            lag_score = -np.minimum(z * z, 1e4)
            sc = {"N1": base * 1e10 - rec, "N1L": base * 1e10 + lag_score * 1e5}
            jt = cand.index(ci)
            out.append({"mech": mech, "shape": shp, "repo": repo, "rank": {k: 1 + int((v > v[jt]).sum()) for k, v in sc.items()}})
    print(f"{repo}: {len(out)} pairs ranked", flush=True)
    return out


def main():
    res = []
    for repo in sys.argv[1:]:
        res += run(repo)
    t20 = lambda rs, k: float(np.mean([x["rank"][k] <= 20 for x in rs])) if rs else float("nan")  # noqa: E731
    print(f"\n=== POOLED ({len(res)} pairs) top 20: N1 {100 * t20(res, 'N1'):.1f}%, N1L (category lag prior, cross-fitted) {100 * t20(res, 'N1L'):.1f}%; top 5: N1 {100 * np.mean([x['rank']['N1'] <= 5 for x in res]):.1f}%, N1L {100 * np.mean([x['rank']['N1L'] <= 5 for x in res]):.1f}%; MRR N1 {np.mean([1 / x['rank']['N1'] for x in res]):.3f}, N1L {np.mean([1 / x['rank']['N1L'] for x in res]):.3f}")
    cats = {}
    for col in ("mech", "shape"):
        print(f"\n--- by {col}: N1 top 20 / N1L top 20 ---")
        for k in sorted({x[col] for x in res}, key=lambda k: -sum(x[col] == k for x in res)):
            sub = [x for x in res if x[col] == k]
            cats[(col, k)] = (len(sub), t20(sub, "N1"), t20(sub, "N1L"))
            print(f"  {k:30s} n {len(sub):4d}  {100 * t20(sub, 'N1'):5.1f}%  {100 * t20(sub, 'N1L'):5.1f}%")
    big = {k: v for k, v in cats.items() if v[0] >= 50}
    lo, hi = min(big, key=lambda k: big[k][1]), max(big, key=lambda k: big[k][1])
    print("\n=== VERDICTS ===")
    print(f"  FT4 categories of 50+ pairs: {len(big)}; lowest N1 top 20 {lo[1]} {100 * big[lo][1]:.1f}%, highest {hi[1]} {100 * big[hi][1]:.1f}% (needs all at least 55% and a spread of at most 25 points): {'supported' if big[lo][1] >= 0.55 and big[hi][1] - big[lo][1] <= 0.25 else 'not supported'}")
    d = 100 * (t20(res, "N1L") - t20(res, "N1"))
    print(f"  FT5 N1L minus N1 top 20 {d:+.1f} points (needs +2): {'supported' if d >= 2 else 'not supported'}")


if __name__ == "__main__":
    main()
