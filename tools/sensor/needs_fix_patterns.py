#!/usr/bin/env python3
"""Transfer of the will-it-need-a-fix model between repositories, and the pattern of additions and deletions. Hypotheses TR1-TR2, EX1-EX5: docs/sensor-overhaul/sensors/ripple_radius.md,
fixed before running.

    python tools/sensor/needs_fix_patterns.py dpdk mesa      (needs the caches of needs_fix_kinds.py)"""
import pickle
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import change_kinds_diff as CD  # noqa: E402
import needs_fix as NF  # noqa: E402
import needs_fix_kinds as NK  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
rng = np.random.default_rng(2982)


def load(repo):
    df = NK.population(repo)
    df, K, T = NK.add_kinds(df, repo)
    feats = pickle.load(open(f"{B}/blast/{repo}/needs_fix_diff_feats.pkl", "rb"))
    for n in CD.NAMES + ["n_add", "n_rem"]:
        df["r_" + n] = [feats[s][n] for s in df.sha]
    df["dec"] = pd.qcut(df.lines, 10, labels=False, duplicates="drop")
    return df, K, T


def mh(dec, x, y):
    """Mantel-Haenszel rate ratio of exposed (x) against unexposed over strata (dec)."""
    num = den = 0.0
    for d in np.unique(dec):
        m = dec == d
        n1, n0 = x[m].sum(), (~x[m]).sum()
        if n1 == 0 or n0 == 0:
            continue
        a, c = y[m & x].sum(), y[m & ~x].sum()
        N = n1 + n0
        num += a * n0 / N
        den += c * n1 / N
    return num / den if den > 0 else np.nan


def rr(df, x, ref=None, boot=200):
    """Rate ratio of the mask x against the rest (or against the mask ref), within size deciles, with a bootstrap interval."""
    keep = np.ones(len(df), bool) if ref is None else (x | ref)
    d = df.dec.to_numpy()[keep]
    xx = x[keep]
    yy = df.y.to_numpy()[keep].astype(bool)
    est = mh(d, xx, yy)
    bs = []
    for _ in range(boot):
        ix = rng.integers(0, len(d), len(d))
        bs.append(mh(d[ix], xx[ix], yy[ix]))
    return est, np.nanpercentile(bs, 2.5), np.nanpercentile(bs, 97.5), int(xx.sum())


def fmt(r):
    return f"{r[0]:.2f} [{r[1]:.2f},{r[2]:.2f}] (n {r[3]})"


def main():
    repos = sys.argv[1:]
    data = {r: load(r) for r in repos}
    SPN = NF.GROUPS["S"] + NF.GROUPS["P"] + NF.GROUPS["N"]
    print("=== PART A: TRANSFER (train on the whole of one repository, test on the whole of the other) ===")
    tr_res = {}
    coefs = {}
    for src in repos:
        dsrc, K, T = data[src]
        sets = {"size alone": NF.GROUPS["S"], "S+P+N": SPN, "S+P+N+K": SPN + K, "S+P+N+K+T": SPN + K + T}
        for dst in repos:
            if dst == src:
                continue
            ddst = data[dst][0]
            y = ddst.y.to_numpy()
            out, hg = {}, {}
            for nm, cols in sets.items():
                out[nm] = roc_auc_score(y, NF.fit(dsrc, cols)(ddst))
                m = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.05, random_state=0).fit(dsrc[cols], dsrc.y)
                hg[nm] = roc_auc_score(y, m.predict_proba(ddst[cols])[:, 1])
            ts = {nm: NF.top_share(NF.fit(dsrc, cols)(ddst), ddst.y) for nm, cols in sets.items() if nm in ("S+P+N", "S+P+N+K+T")}
            print(f"\n  {src} -> {dst}: base rate in the test repository {100 * y.mean():.1f}%")
            print("    logistic AUC: " + ", ".join(f"{n} {a:.3f}" for n, a in out.items()))
            print("    boosting AUC: " + ", ".join(f"{n} {a:.3f}" for n, a in hg.items()))
            print(f"    top decile share of the fixed-cause changes: S+P+N {100 * ts['S+P+N']:.1f}%, full {100 * ts['S+P+N+K+T']:.1f}% (random 10%)")
            tr_res[(src, dst)] = (out, hg)
    for r in repos:
        d, K, T = data[r]
        cols = SPN + K + T
        mu, sd = d[cols].mean(), d[cols].std().replace(0, 1)
        lr = LogisticRegression(C=1.0, max_iter=3000).fit((d[cols] - mu) / sd, d.y)
        coefs[r] = pd.Series(lr.coef_[0], index=cols)
    kt = [c for c in coefs[repos[0]].index if c.startswith(("k_", "t_"))]
    sp = coefs[repos[0]][kt].corr(coefs[repos[1]][kt], method="spearman")
    print(f"\n  standardised logistic coefficients, diff-line and shape features: Spearman correlation between {repos[0]} and {repos[1]} = {sp:.2f}; same sign for {int((np.sign(coefs[repos[0]][kt]) == np.sign(coefs[repos[1]][kt])).sum())} of {len(kt)}")
    both = pd.DataFrame({r: coefs[r][kt] for r in repos})
    print("  largest coefficients (" + " / ".join(repos) + "): " + ", ".join(f"{c.replace('k_', '').replace('t_', '')} {both.loc[c, repos[0]]:+.2f}/{both.loc[c, repos[1]]:+.2f}" for c in both.abs().sum(axis=1).sort_values(ascending=False).index[:10]))
    print(f"  add_cond coefficient: " + ", ".join(f"{r} {coefs[r]['k_add_cond']:+.2f}" for r in repos))

    print("\n=== PART B: ADDITIONS AND DELETIONS (Mantel-Haenszel rate ratio within size deciles; rate = named as the cause of a fix within 730 days) ===")
    pat = {}
    for r in repos:
        d = data[r][0]
        a = lambda n: d["r_" + n].to_numpy() > 0  # noqa: E731
        add, rem = d.r_n_add.to_numpy(), d.r_n_rem.to_numpy()
        masks = {
            "pure addition (nothing removed)": (add > 0) & (rem == 0),
            "pure deletion (nothing added)": (add == 0) & (rem > 0),
            "mixed (added and removed)": (add > 0) & (rem > 0),
            "adds an allocation, no release added": a("add_alloc") & ~a("add_free"),
            "adds calls but no condition, null check, error handling or return": a("add_call") & ~a("add_cond") & ~a("add_null") & ~a("add_err") & ~a("add_ret"),
            "removes conditions, adds none": a("rem_cond") & ~a("add_cond"),
            "adds synchronisation, removes none": a("add_lock") & ~a("rem_lock"),
        }
        print(f"\n  {r}: {len(d)} changes; named-as-cause rate {100 * d.y.mean():.1f}%")
        rs = {}
        for nm, m in masks.items():
            rs[nm] = rr(d, m)
            print(f"    {nm:70s} {fmt(rs[nm])}")
        ref = a("add_alloc") & a("add_free")
        rs["alloc vs alloc+free"] = rr(d, masks["adds an allocation, no release added"], ref=ref)
        withcheck = a("add_call") & (a("add_cond") | a("add_null") | a("add_err") | a("add_ret"))
        rs["calls without vs with a check"] = rr(d, masks["adds calls but no condition, null check, error handling or return"], ref=withcheck)
        print(f"    {'allocation without release against allocation with release':70s} {fmt(rs['alloc vs alloc+free'])}")
        print(f"    {'added calls without a check against added calls with one':70s} {fmt(rs['calls without vs with a check'])}")
        pat[r] = rs
    print("\n  EXPLORATORY SCAN: each add or remove line kind present, rate ratio against absent, within size deciles")
    scan = {}
    for r in repos:
        d = data[r][0]
        for n in CD.NAMES:
            x = d["r_" + n].to_numpy() > 0
            if x.sum() >= 200 and (~x).sum() >= 200:
                scan[(r, n)] = rr(d, x, boot=100)
    agree = []
    for n in CD.NAMES:
        v = [scan.get((r, n)) for r in repos]
        if all(v) and all(x[1] > 1 for x in v) or all(v) and all(x[2] < 1 for x in v):
            agree.append((n, v))
    agree.sort(key=lambda t: -abs(np.log(np.mean([x[0] for x in t[1]]))))
    print("    same direction in both, intervals exclude 1: " + "; ".join(f"{n} " + " / ".join(f"{x[0]:.2f}" for x in v) for n, v in agree))
    print("    all: " + "; ".join(f"{n} " + " / ".join(f"{scan[(r, n)][0]:.2f}" if (r, n) in scan else "n/a" for r in repos) for n in CD.NAMES))
    print("\n=== VERDICTS ===")
    for (src, dst), (o, h) in tr_res.items():
        print(f"  TR1 {src}->{dst}: full {o['S+P+N+K+T']:.3f} against S+P+N {o['S+P+N']:.3f} = {o['S+P+N+K+T'] - o['S+P+N']:+.3f}; size alone {o['size alone']:.3f}")
    print(f"  TR1 (needs +0.01 in both directions): {'supported' if all(o['S+P+N+K+T'] - o['S+P+N'] >= 0.01 for o, _ in tr_res.values()) else 'not supported'}")
    print(f"  TR2 add_cond positive in both: {all(coefs[r]['k_add_cond'] > 0 for r in repos)}; Spearman {sp:.2f} (needs 0.4): {'supported' if all(coefs[r]['k_add_cond'] > 0 for r in repos) and sp >= 0.4 else 'not supported'}")
    ok1 = all(pat[r]["pure addition (nothing removed)"][0] >= 1.2 and pat[r]["pure deletion (nothing added)"][0] <= 0.8 for r in repos)
    print(f"  EX1 pure additions >= 1.2 and pure deletions <= 0.8: " + ", ".join(f"{r} {pat[r]['pure addition (nothing removed)'][0]:.2f} / {pat[r]['pure deletion (nothing added)'][0]:.2f}" for r in repos) + f": {'supported' if ok1 else 'not supported'}")
    for key, need, ex in (("alloc vs alloc+free", 1.3, "EX2"), ("calls without vs with a check", 1.2, "EX3"), ("removes conditions, adds none", 1.3, "EX4"), ("adds synchronisation, removes none", 1.3, "EX5")):
        vals = [pat[r][key][0] for r in repos]
        print(f"  {ex} {key}: " + ", ".join(f"{r} {v:.2f}" for r, v in zip(repos, vals)) + f" (needs {need} in both): {'supported' if all(v >= need for v in vals) else 'not supported'}")
    below = [(s, d) for (s, d), (o, _) in tr_res.items() if o["S+P+N+K+T"] < o["size alone"]]
    print(f"  surprise bar (cross-repository AUC below size alone in either direction): {'MET ' + str(below) if below else 'not met'}")


if __name__ == "__main__":
    main()
