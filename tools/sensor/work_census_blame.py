#!/usr/bin/env python3
"""Census with blame-derived causes for unnamed fixes. Hypotheses UC1-UC4: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.
    python tools/sensor/work_census_blame.py dpdk mesa"""
import os
import pickle
import random
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import lang_validation as LV  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
N = 2500
TRAILER_RADIUS = {"dpdk": 1.45, "mesa": 1.60}
LV.CFG["mesa"] = "c"


def main():
    rng = np.random.default_rng(2982)
    tot = {}
    for repo in sys.argv[1:]:
        path = f"{BR.POOL}/{repo}"
        touched = pickle.load(open(f"{B}/blast/{repo}/touched_all.pkl", "rb"))
        log = subprocess.run(["git", "-C", path, "log", "--no-merges", "--format=%H%x1f%ct%x1f%s"], capture_output=True, text=True, errors="replace").stdout.splitlines()
        trailer = set(subprocess.run(["git", "-C", path, "log", "--no-merges", "-E", "--grep=^Fixes:", "--format=%H"], capture_output=True, text=True).stdout.split())
        ct, cand, nf = {}, [], {}
        for l in log:
            p = l.split("\x1f", 2)
            if len(p) < 3:
                continue
            ct[p[0]] = int(p[1])
            nf[p[0]] = len(touched.get(p[0], []))
            if LV.FIXRE.search(p[2]) and not p[2].lower().startswith("revert") and p[0] not in trailer and 1 <= nf[p[0]] <= 60:
                cand.append((p[0], int(p[1])))
        total_edits = sum(nf.values())
        edits_unnamed = sum(nf[s] for s, _ in cand)
        random.Random(7).shuffle(cand)
        sample = cand[:N]
        cache = f"{B}/blast/census_{repo}.pkl"
        if os.path.exists(cache):
            pairs, info = pickle.load(open(cache, "rb"))
        else:
            print(f"{repo}: {len(cand):,} unnamed fix-like commits (1 to 60 functions), blaming {len(sample)}", flush=True)
            pairs = []
            with ProcessPoolExecutor(max_workers=6) as ex:
                for res in ex.map(LV.szz_worker, [(path, "c", sample[i : i + 15]) for i in range(0, len(sample), 15)]):
                    for fix, ind, n, t in res:
                        if ind != fix and ind in ct and ct[ind] < ct[fix]:
                            pairs.append({"fix": fix, "ind": ind, "fix_ct": ct[fix], "ind_ct": ct[ind], "lag": (ct[fix] - ct[ind]) / 86400, "n": n, "tot": t})
            shas = list(dict.fromkeys(x for p in pairs for x in (p["fix"], p["ind"])))
            info = {}
            with ProcessPoolExecutor(max_workers=6) as ex:
                for res in ex.map(LV.commit_worker, [(path, "c", shas[i : i + 25]) for i in range(0, len(shas), 25)]):
                    info.update(res)
            pickle.dump((pairs, info), open(cache, "wb"))
        rate = len(pairs) / max(len(sample), 1)
        df, drop = LV.measure(repo, pairs, info)
        ok = df[df.status == "ok"].copy()
        ok["nFo"] = ok.nFo.fillna(0)
        mo = ok[(ok.nFo > 0) & ok.o_either2.notna() & ok.eB_either2.notna()]
        r2 = BR.ratio(mo, "either2", "eB", rng)
        r1 = BR.ratio(mo, "either1", "eB", rng)
        # excess per sampled fix, scaled to all unnamed fix-like commits
        excess_per = float((mo.nFo * (mo.o_either2 - mo.eB_either2)).sum()) / len(sample)
        excess = excess_per * len(cand)
        print(f"\n##### {repo}: unnamed fix-like commits {len(cand):,} = {100 * edits_unnamed / total_edits:.1f}% of all function edits ({edits_unnamed:,} of {total_edits:,})")
        print(f"  sampled {len(sample)}; blame cause found for {len(pairs)} ({100 * rate:.0f}%); dropped in measurement {drop}; measured {len(ok)}; with a fixed function outside the changed set {len(mo)} (same function in {100 * ok.same_func.mean():.0f}% of measured)")
        print(f"  repair radius, blame-derived causes: within 2 calls {BR.fmt(r2)}; within 1 call {BR.fmt(r1)}; median lag {ok.lag.median():.0f} d (trailer-named radius {TRAILER_RADIUS.get(repo, float('nan')):.2f})")
        caused_edits = edits_unnamed * rate
        print(f"  scaled: unnamed fix-like edits with a blame cause about {caused_edits:,.0f} = {100 * caused_edits / total_edits:.1f}% of all function edits; radius excess from them about {excess:,.0f} edits = {100 * excess / total_edits:.2f}% of all function edits")
        tot[repo] = (rate, r2, caused_edits / total_edits, excess / total_edits)
    print("\n=== VERDICTS ===")
    for repo, (rate, r2, ce, ex) in tot.items():
        print(f"  {repo}: UC1 cause found {100 * rate:.0f}% (needs 60%): {'supported' if rate >= 0.6 else 'not supported'}; UC2 radius {r2[0]:.2f} lower bound {r2[1]:.2f} (needs 1.3 and 1.2): {'supported' if r2[0] >= 1.3 and r2[1] > 1.2 else 'not supported'}; UC3 gap to trailer-named {r2[0] - TRAILER_RADIUS[repo]:+.2f} (needs within 0.15): {'supported' if abs(r2[0] - TRAILER_RADIUS[repo]) <= 0.15 else 'not supported'}")


if __name__ == "__main__":
    main()
