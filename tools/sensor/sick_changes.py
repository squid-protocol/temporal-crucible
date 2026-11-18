#!/usr/bin/env python3
"""Which causing changes need repeated repairs? Hypotheses SK1-SK5: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.

    python tools/sensor/sick_changes.py        (needs measure.pkl, diff_feats.pkl, authors.pkl for linux and dpdk under /tmp/gitgalaxy-scratch/claude/blast; pair lists under argl)"""
import bisect
import collections
import json
import subprocess
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import fix_shapes as FS  # noqa: E402

BASE = "/tmp/gitgalaxy-scratch/claude"
DATA = {"kernel": ("linux", f"{BASE}/argl/links_linux_all.json"), "dpdk": ("dpdk", f"{BASE}/argl/links_dpdk.json")}
SMALL = {"adds a guard", "rewrites a condition", "replaces a call or argument", "small edit"}
rng = np.random.default_rng(2982)
YEAR = 365.25 * 86400


def wilson(k, n):
    if n == 0:
        return 0, 0
    p = k / n
    z = 1.96
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def tenure(repo, cause_shas, cause_ct):
    """author's earlier non-merge commits in the repository, by one git log pass (author e-mail, time)."""
    log = subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "log", "--no-merges", "--format=%H %ae %ct"], capture_output=True, text=True, errors="replace").stdout.splitlines()
    times = collections.defaultdict(list)
    who = {}
    for l in log:
        p = l.split()
        if len(p) == 3:
            times[p[1].lower()].append(int(p[2]))
            who[p[0]] = p[1].lower()
    for v in times.values():
        v.sort()
    return {s: bisect.bisect_left(times[who[s]], cause_ct[s]) if s in who else None for s in cause_shas}


def main():
    allres = {}
    for name, (repo, lp) in DATA.items():
        d = f"{BASE}/blast/{repo}"
        links = json.load(open(lp))
        nfix = collections.Counter(p["ind"] for p in links)
        ind_ct = {p["ind"]: p["ind_ct"] for p in links}
        end = max(p["fix_ct"] for p in links)
        m = pd.read_pickle(f"{d}/measure.pkl")
        m = m[m.status == "ok"]
        c = m.groupby("ind").agg(nI=("nI", "first")).reset_index()
        feats = pd.read_pickle(f"{d}/diff_feats.pkl")
        c = c[c.ind.isin(feats.keys() if isinstance(feats, dict) else feats.index)].copy()
        c["lines"] = [feats[s]["n_add"] + feats[s]["n_rem"] for s in c.ind]
        c["shape"] = [FS.shape(feats[s]) for s in c.ind]
        c["nfix"] = [nfix[s] for s in c.ind]
        c["ct"] = [ind_ct[s] for s in c.ind]
        c["tenure"] = pd.Series(tenure(repo, list(c.ind), ind_ct)).reindex(c.ind).to_numpy()
        c["old"] = c.ct < end - 3 * YEAR
        c["multi"] = c.nfix >= 2
        c = c[c.old & c.tenure.notna()].copy()
        print(f"\n########## {name}: {len(c)} causing commits (measured, at least 3 y old at the end of the history); P(2+ fixes) overall {100 * c.multi.mean():.1f}%; mean fixes {c.nfix.mean():.2f} ##########")

        def row(lab, mask):
            k, n = int(c.multi[mask].sum()), int(mask.sum())
            lo, hi = wilson(k, n)
            print(f"    {lab:34s} n {n:6d}  P(2+) {100 * k / max(n, 1):5.1f}% [{100 * lo:4.1f},{100 * hi:4.1f}]  mean fixes {c.nfix[mask].mean():.2f}")
            return k / max(n, 1), n

        print("  by lines changed:")
        bins = [("under 20", c.lines < 20), ("20 to 99", (c.lines >= 20) & (c.lines < 100)), ("100 to 499", (c.lines >= 100) & (c.lines < 500)), ("500 or more", c.lines >= 500)]
        pb = {lab: row(lab, mk) for lab, mk in bins}
        print("  by causing shape:")
        for k in FS.SHAPES:
            if (c["shape"] == k).sum() >= 30:
                row(k, c["shape"] == k)
        sm = row("small surgical shapes pooled", c["shape"].isin(SMALL))
        ad = row("adds code", c["shape"] == "adds code")
        print("  by the author's earlier commits in the repository:")
        tb = [("under 20", c.tenure < 20), ("20 to 199", (c.tenure >= 20) & (c.tenure < 200)), ("200 or more", c.tenure >= 200)]
        pt = {lab: row(lab, mk) for lab, mk in tb}
        print("  by functions changed:")
        for lab, mk in (("1", c.nI == 1), ("2 to 4", (c.nI >= 2) & (c.nI < 5)), ("5 to 19", (c.nI >= 5) & (c.nI < 20)), ("20 or more", c.nI >= 20)):
            row(lab, mk)
        r1 = pb["100 to 499"][0] if False else (c.multi[c.lines >= 100].mean() / c.multi[c.lines < 20].mean())
        r2 = ad[0] / sm[0]
        r3 = pt["under 20"][0] / pt["200 or more"][0]
        print(f"  SK1 100+ lines / under 20 lines: {r1:.2f} (needs 1.3);  SK2 adds code / small surgical: {r2:.2f} (needs 1.2);  SK3 tenure under 20 / 200+: {r3:.2f} (needs 1.2)")
        # SK4: logistic, separate vs together
        X = pd.DataFrame({"loglines": np.log1p(c.lines), "adds_code": (c["shape"] == "adds code").astype(float), "small": c["shape"].isin(SMALL).astype(float), "newbie": (c.tenure < 20).astype(float), "veteran": (c.tenure >= 200).astype(float)})
        y = c.multi.to_numpy(int)

        def orr(cols):
            lr = LogisticRegression(C=1e6, max_iter=2000).fit(X[cols], y)
            return dict(zip(cols, np.exp(lr.coef_[0])))

        sep = {}
        for cl in ("loglines", "adds_code", "small", "newbie", "veteran"):
            sep[cl] = orr([cl])[cl]
        tog = orr(list(X.columns))
        print("  logistic odds ratios (per log-line for loglines; yes/no for the rest): separate -> together")
        for cl in X.columns:
            print(f"    {cl:10s} {sep[cl]:.2f} -> {tog[cl]:.2f}")
        shrink = {}
        for cl in ("adds_code", "small", "newbie", "veteran"):
            s_, t_ = np.log(sep[cl]), np.log(tog[cl])
            shrink[cl] = 1 - t_ / s_ if abs(s_) > 1e-9 else 0.0
        print("    share of each separate effect removed by adjusting for the others (log-odds): " + ", ".join(f"{k} {100 * v:.0f}%" for k, v in shrink.items()))
        allres[name] = (r1, r2, r3, shrink)
    print("\n=== VERDICTS ===")
    for k, (r1, r2, r3, sh) in allres.items():
        print(f"  {k}: SK1 {'supported' if r1 >= 1.3 else 'not'} ({r1:.2f}); SK2 {'supported' if r2 >= 1.2 else 'not'} ({r2:.2f}); SK3 {'supported' if r3 >= 1.2 else 'not'} ({r3:.2f}); SK4 shape/tenure effects shrink by a third or more: " + ", ".join(f"{a} {'yes' if b >= 1 / 3 else 'no'}" for a, b in sh.items()))
    print("  SK5 direction agrees: " + ", ".join(f"SK{i + 1} {'yes' if (allres['kernel'][i] >= 1) == (allres['dpdk'][i] >= 1) else 'no'}" for i in range(3)))


if __name__ == "__main__":
    main()
