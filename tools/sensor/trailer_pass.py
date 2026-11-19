#!/usr/bin/env python3
"""What the commit trailers add. Hypotheses TP1-TP5: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.
    python tools/sensor/trailer_pass.py"""
import collections
import json
import pickle
import re
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402

S = "/tmp/gitgalaxy-scratch/claude"
SRC = [("dpdk", f"{S}/fr_base"), ("mesa", f"{S}/fr_mesa")]
KEYS = ["reported-by", "tested-by", "reviewed-by", "acked-by", "suggested-by", "co-developed-by", "link", "closes", "bugzilla", "fixes"]
T2015 = 1420070400


def trailers(repo):
    out = subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "log", "--no-merges", "--format=@@%H%x1f%ct%x1f%B"], capture_output=True, text=True, errors="replace").stdout
    res = {}
    for blk in out.split("@@")[1:]:
        p = blk.split("\x1f", 2)
        if len(p) < 3:
            continue
        keys = set()
        stable = False
        for l in p[2].splitlines():  # the whole body: DPDK puts Fixes and Cc in a paragraph apart from Signed-off-by, which git's trailer parser does not see
            m = re.match(r"^([A-Za-z][A-Za-z-]{1,30}):\s*(.*)$", l)
            if not m:
                continue
            k, v = m.group(1).lower(), m.group(2)
            if k in KEYS:
                keys.add(k)
            if k == "cc" and "stable" in v.lower():
                stable = True
        if stable:
            keys.add("cc-stable")
        res[p[0]] = (int(p[1]), keys)
    return res


def mh_ratio(rows, rng, boot=500):
    """rows: DataFrame with stratum, flag (trailer present), y (cited). Mantel-Haenszel rate ratio of flag vs not, bootstrap interval over rows."""
    def est(d):
        num = den = 0.0
        for _, g in d.groupby("stratum"):
            a = g[g.flag]
            b = g[~g.flag]
            if len(a) == 0 or len(b) == 0:
                continue
            n = len(g)
            num += a.y.sum() * len(b) / n
            den += b.y.sum() * len(a) / n
        return num / den if den > 0 else np.nan
    pt = est(rows)
    bs = []
    idx = np.arange(len(rows))
    for _ in range(boot):
        s = rng.choice(idx, len(idx))
        bs.append(est(rows.iloc[s]))
    return pt, np.nanpercentile(bs, 2.5), np.nanpercentile(bs, 97.5)


def main():
    rng = np.random.default_rng(2982)
    frames, org = [], []
    for repo, d in SRC:
        tr = trailers(repo)
        end = max(t for t, _ in tr.values())
        print(f"\n##### {repo}: {len(tr):,} commits; trailer prevalence since 2015: " + ", ".join(f"{k} {100 * np.mean([k in ks for t, ks in tr.values() if t >= T2015]):.0f}%" for k in KEYS[:-1] + ["cc-stable"]), flush=True)
        part = pickle.load(open(f"{S}/partition/{repo}.pkl", "rb"))
        cat, cited = part["cat"], part["cited"]
        touched = pickle.load(open(f"{S}/blast/{repo}/touched_all.pkl", "rb"))
        m = pd.read_pickle(f"{d}/measure.pkl")
        m = m[m.status == "ok"].copy()
        m["repo"] = repo
        m["report"] = [("reported-by" in tr.get(s, (0, set()))[1]) for s in m.fix]
        m["stable"] = [("cc-stable" in tr.get(s, (0, set()))[1]) for s in m.fix]
        m["fix_ct"] = [tr.get(s, (0, set()))[0] for s in m.fix]
        frames.append(m[m.fix_ct >= T2015])
        for s, k in cat.items():
            if k in ("adds code", "removes code") or k.startswith("modifies") or k in ("tests only", "formatting, docs, licence (subject)"):
                t, ks = tr.get(s, (0, set()))
                if t >= T2015 and t <= end - 3 * 365 * 86400:
                    org.append({"repo": repo, "n": len(touched.get(s, [])), "review": bool(ks & {"reviewed-by", "acked-by", "tested-by"}), "reviewed": "reviewed-by" in ks, "tested": "tested-by" in ks, "acked": "acked-by" in ks, "y": s in cited})
    m = pd.concat(frames)
    print(f"\n=== FIX SIDE: {len(m):,} measured named-cause pairs since 2015 ===")
    res = {}
    for col, label in (("report", "Reported-by"), ("stable", "Cc: stable")):
        for repo in ("dpdk", "mesa", "both"):
            sub = m if repo == "both" else m[m.repo == repo]
            for flag in (True, False):
                g = sub[sub[col] == flag]
                o = g[g.nFo > 0]
                r2 = BR.ratio(o, "either2", "eB", rng) if len(o) >= 15 else None
                res[(col, repo, flag)] = (len(g), g.lag.median(), g.same_func.mean(), r2)
                print(f"  {label:12s} {'with' if flag else 'without':7s} {repo:5s} n {len(g):5d} ({100 * len(g) / len(sub):4.1f}%) median lag {g.lag.median():5.0f} d  same function {100 * g.same_func.mean():3.0f}%  radius {BR.fmt(r2)}")
    o = pd.DataFrame(org)
    o["stratum"] = [f"{r}{min(int(np.log2(max(n, 1))), 7)}" for r, n in zip(o.repo, o.n)]
    print(f"\n=== CAUSE SIDE: {len(o):,} organic commits since 2015, older than 3 years before the end ===")
    for repo in ("dpdk", "mesa", "both"):
        sub = o if repo == "both" else o[o.repo == repo]
        print(f"  {repo}: cited rate overall {100 * sub.y.mean():.1f}%")
        for col, label in (("review", "Reviewed/Acked/Tested-by"), ("reviewed", "Reviewed-by"), ("tested", "Tested-by"), ("acked", "Acked-by")):
            sub2 = sub.assign(flag=sub[col])
            pt, lo, hi = mh_ratio(sub2, rng)
            print(f"     {label:26s} with {int(sub2.flag.sum()):6d} ({100 * sub2.flag.mean():4.1f}%): cited {100 * sub2[sub2.flag].y.mean():5.1f}% vs without {100 * sub2[~sub2.flag].y.mean():5.1f}%; rate ratio within size strata {pt:.2f} [{lo:.2f}, {hi:.2f}]")
    print("\n=== VERDICTS ===")
    rp = {r: res[("report", r, True)][0] / (res[("report", r, True)][0] + res[("report", r, False)][0]) for r in ("dpdk", "mesa")}
    print(f"  TP1 Reported-by share of fix commits: DPDK {100 * rp['dpdk']:.1f}% (needs 15%), Mesa {100 * rp['mesa']:.1f}% (needs 10%): {'supported' if rp['dpdk'] >= 0.15 and rp['mesa'] >= 0.10 else 'not supported'}")
    a, b = res[("report", "both", True)], res[("report", "both", False)]
    print(f"  TP2 median lag with {a[1]:.0f} d, without {b[1]:.0f} d, ratio {a[1] / b[1]:.2f} (needs 1.3): {'supported' if a[1] / b[1] >= 1.3 else 'not supported'}")
    if a[3] and b[3]:
        print(f"  TP3 radius with {a[3][0]:.2f}, without {b[3][0]:.2f}, gap {a[3][0] - b[3][0]:+.2f} (needs within 0.2): {'supported' if abs(a[3][0] - b[3][0]) <= 0.2 else 'not supported'}")
    pt, lo, hi = mh_ratio(o.assign(flag=o.review), rng)
    print(f"  TP4 rate ratio for reviewed/acked/tested {pt:.2f} [{lo:.2f}, {hi:.2f}] (needs below 0.9 with the interval excluding 1): {'supported' if pt < 0.9 and hi < 1 else 'not supported'}")
    c, d2 = res[("stable", "both", True)], res[("stable", "both", False)]
    print(f"  TP5 Cc: stable: n {c[0]}, median lag {c[1]:.0f} d vs {d2[1]:.0f} d; radius {c[3][0] if c[3] else float('nan'):.2f} vs {d2[3][0] if d2[3] else float('nan'):.2f}")


if __name__ == "__main__":
    main()
