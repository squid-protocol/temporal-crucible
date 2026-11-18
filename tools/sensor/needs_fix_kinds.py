#!/usr/bin/env python3
"""Will this change need a fix? Adds kind-of-change features (diff line kinds, diff shape, subject verb) to size, process and neighbourhood. Hypotheses KC1-KC5:
docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running. Population, label and split as needs_fix.py.

    python tools/sensor/needs_fix_kinds.py dpdk mesa"""
import os
import pickle
import subprocess
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

POOL = "/srv/storage_16tb/projects/temporal-crucible-pool"
sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
os.environ.setdefault("BLAST_REPO_PATH", f"{POOL}/dpdk")
import change_kinds as CK  # noqa: E402
import change_kinds_diff as CD  # noqa: E402
import fix_shapes as FS  # noqa: E402
import needs_fix as NF  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
CTYPES = ["fix", "feature", "restructure", "optimization", "other"]


def population(repo):
    f = f"{B}/blast/{repo}/needs_fix_df.pkl"
    if os.path.exists(f):
        return pd.read_pickle(f)
    df = NF.build(repo)
    df.to_pickle(f)
    return df


def add_kinds(df, repo):
    CK.REPO = f"{POOL}/{repo}"
    feats = CD.diff_features(list(df.sha), f"{B}/blast/{repo}/needs_fix_diff_feats.pkl")
    log = subprocess.run(["git", "-C", f"{POOL}/{repo}", "log", "--no-merges", "--format=%H%x1f%s"], capture_output=True, text=True, errors="replace").stdout.splitlines()
    subj = dict(l.split("\x1f", 1) for l in log if "\x1f" in l)
    kcols = []
    for n in CD.NAMES:  # names already carry the add_ / rem_ prefix
        df["k_" + n] = [np.log1p(feats[s][n]) for s in df.sha]
        kcols.append("k_" + n)
    for n in ("cond_rewrite", "n_hunks"):
        df["k_" + n] = [np.log1p(feats[s][n]) for s in df.sha]
        kcols.append("k_" + n)
    shapes = [FS.shape(feats[s]) for s in df.sha]
    ctypes = [CK.cause_type(subj.get(s, ""))[0] for s in df.sha]
    tcols = []
    for sh in FS.SHAPES:
        df["t_shape_" + sh] = [float(x == sh) for x in shapes]
        tcols.append("t_shape_" + sh)
    for ct in CTYPES:
        df["t_type_" + ct] = [float(x == ct) for x in ctypes]
        tcols.append("t_type_" + ct)
    return df, kcols, tcols


def main():
    res = {}
    for repo in sys.argv[1:]:
        df = population(repo)
        df, K, T = add_kinds(df, repo)
        k = int(0.6 * len(df))
        tr, te = df.iloc[:k], df.iloc[k:]
        yv = te.y.to_numpy()
        SPN = NF.GROUPS["S"] + NF.GROUPS["P"] + NF.GROUPS["N"]
        sets = {"S+P+N": SPN, "S+P+N+K": SPN + K, "S+P+N+K+T": SPN + K + T}
        print(f"\n########## {repo}: {len(df)} changes (test {len(te)}); named as the cause of a fix within 730 days: {100 * df.y.mean():.1f}%; {len(K)} diff-line features, {len(T)} shape and verb indicators ##########")
        sc, auc, hgb = {}, {}, {}
        for nm, cols in sets.items():
            sc[nm] = NF.fit(tr, cols)(te)
            auc[nm] = roc_auc_score(yv, sc[nm])
            m = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.05, random_state=0).fit(tr[cols], tr.y)
            hgb[nm] = roc_auc_score(yv, m.predict_proba(te[cols])[:, 1])
            sc["hgb " + nm] = m.predict_proba(te[cols])[:, 1]
        print("  test AUC logistic: " + ", ".join(f"{n} {a:.3f}" for n, a in auc.items()))
        print("  test AUC gradient boosting: " + ", ".join(f"{n} {a:.3f}" for n, a in hgb.items()))
        bs = []
        rng = np.random.default_rng(2982)
        for _ in range(200):
            ix = rng.integers(0, len(te), len(te))
            if yv[ix].min() != yv[ix].max():
                bs.append(roc_auc_score(yv[ix], sc["S+P+N+K+T"][ix]) - roc_auc_score(yv[ix], sc["S+P+N"][ix]))
        print(f"  S+P+N+K+T minus S+P+N: logistic {auc['S+P+N+K+T'] - auc['S+P+N']:+.3f} [{np.percentile(bs, 2.5):+.3f},{np.percentile(bs, 97.5):+.3f}], boosting {hgb['S+P+N+K+T'] - hgb['S+P+N']:+.3f}")
        q = np.quantile(tr.lines, [0.25, 0.5, 0.75])
        qi = np.searchsorted(q, te.lines.to_numpy())
        wq = {}
        print(f"  test AUC within size quartiles (lines under {', '.join(f'{x:.0f}' for x in q)}):")
        for nm in ("S+P+N", "S+P+N+K+T", "hgb S+P+N", "hgb S+P+N+K+T"):
            wq[nm] = [roc_auc_score(yv[qi == j], np.asarray(sc[nm])[qi == j]) if len(set(yv[qi == j])) == 2 else float("nan") for j in range(4)]
            print(f"    {nm:15s} " + "  ".join(f"Q{j + 1} {v:.3f}" for j, v in enumerate(wq[nm])))
        ts = {nm: NF.top_share(sc[nm], te.y) for nm in ("S+P+N", "S+P+N+K+T", "hgb S+P+N+K+T")}
        print("  share of the fixed-cause changes in the top decile: " + ", ".join(f"{n} {100 * v:.1f}%" for n, v in ts.items()) + " (random 10%)")
        uni = {c: NF.within_auc(c, df) for c in K + T}
        top = sorted(uni.items(), key=lambda kv: -abs(kv[1] - 0.5) if kv[1] == kv[1] else 0)[:10]
        print("  strongest single features, within-size-decile AUC (all changes; above 0.5 = more often fixed): " + ", ".join(f"{c.replace('k_', '').replace('t_', '')} {v:.3f}" for c, v in top))
        bestk = max((v for c, v in uni.items() if c in K and v == v), default=float("nan"))
        # fix-of-fix: rate for fix-subject commits against others within size decile
        dec = pd.qcut(df.lines, 10, duplicates="drop")
        num = den = 0.0
        for _, d in df.groupby(dec, observed=True):
            a, b = d[d.t_type_fix == 1], d[d.t_type_fix == 0]
            if len(a) >= 20 and len(b) >= 20 and b.y.mean() > 0:
                num += len(a) * a.y.mean() / b.y.mean()
                den += len(a)
        fx = num / den if den else float("nan")
        print(f"  changes whose subject marks them as fixes: {100 * df.t_type_fix.mean():.1f}% of changes; named-as-cause rate against other changes of the same size decile = {fx:.2f}")
        res[repo] = (auc, hgb, wq, ts, bestk, fx, bs)
    print("\n=== VERDICTS ===")
    rp = list(res)
    d = {r: res[r][0]["S+P+N+K+T"] - res[r][0]["S+P+N"] for r in rp}
    print("  KC1 full model minus S+P+N (logistic): " + ", ".join(f"{r} {v:+.3f}" for r, v in d.items()) + f" (needs +0.02 in both): {'supported' if all(v >= 0.02 for v in d.values()) else 'not supported'}")
    print("  KC2 smallest quartile, full model: " + ", ".join(f"{r} {res[r][2]['S+P+N+K+T'][0]:.3f}" for r in rp) + f" (needs 0.60 in both): {'supported' if all(res[r][2]['S+P+N+K+T'][0] >= 0.60 for r in rp) else 'not supported'}")
    r3 = {r: res[r][3]["S+P+N+K+T"] / res[r][3]["S+P+N"] for r in rp}
    print("  KC3 top-decile share, full over S+P+N: " + ", ".join(f"{r} {v:.2f}" for r, v in r3.items()) + f" (needs 1.15 in both): {'supported' if all(v >= 1.15 for v in r3.values()) else 'not supported'}")
    print("  KC4 best single K feature, within-size AUC: " + ", ".join(f"{r} {res[r][4]:.3f}" for r in rp) + f" (needs 0.56 in both): {'supported' if all(res[r][4] >= 0.56 for r in rp) else 'not supported'}")
    print("  KC5 fix-subject changes, rate against others of the same size: " + ", ".join(f"{r} {res[r][5]:.2f}" for r in rp) + f" (needs 1.3 in both): {'supported' if all(res[r][5] >= 1.3 for r in rp) else 'not supported'}")
    print(f"  surprise bar (full model adds under 0.01 over S+P+N in both): {'MET' if all(v < 0.01 for v in d.values()) else 'not met'}")


if __name__ == "__main__":
    main()
