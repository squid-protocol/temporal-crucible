#!/usr/bin/env python3
"""Controls on the kind-of-change result of the will-it-need-a-fix test. Hypotheses CT1-CT6: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.

    python tools/sensor/needs_fix_controls.py dpdk mesa      (needs the caches of needs_fix_kinds.py and blast/<repo>/touched_all.pkl)"""
import bisect
import collections
import json
import pickle
import re
import subprocess
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import needs_fix as NF  # noqa: E402
import needs_fix_kinds as NK  # noqa: E402
import needs_fix_patterns as NP  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
POOL = NK.POOL
DAY = 86400
rng = np.random.default_rng(2982)
FIX = re.compile(r"\bfix(?:es|ed|ing)?\b")


def metadata(repo):
    out = subprocess.run(["git", "-C", f"{POOL}/{repo}", "log", "--no-merges", "--name-status", "--format=@@%H%x1f%ae%x1f%s"], capture_output=True, text=True, errors="replace").stdout
    meta, cur = {}, None
    for l in out.splitlines():
        if l.startswith("@@"):
            h, ae, subj = (l[2:].split("\x1f") + ["", ""])[:3]
            cur = meta[h] = {"ae": ae.lower(), "subj": subj, "new": False, "dirs": collections.Counter()}
        elif cur is not None and "\t" in l:
            parts = l.split("\t")
            path = parts[-1]
            if path.endswith((".c", ".h")):
                cur["dirs"]["/".join(path.split("/")[:2])] += 1
                if parts[0] == "A":
                    cur["new"] = True
    return meta


def lift(df, scols, kcols, label="y", split=0.6, reverse=False, boot=200):
    n = int(split * len(df))
    tr, te = (df.iloc[len(df) - n :], df.iloc[: len(df) - n]) if reverse else (df.iloc[:n], df.iloc[n:])
    tr, te = tr.assign(y=tr[label]), te.assign(y=te[label])
    s0 = NF.fit(tr, scols)(te)
    s1 = NF.fit(tr, scols + kcols)(te)
    y = te.y.to_numpy()
    a0, a1 = roc_auc_score(y, s0), roc_auc_score(y, s1)
    bs = []
    for _ in range(boot):
        ix = rng.integers(0, len(te), len(te))
        if y[ix].min() != y[ix].max():
            bs.append(roc_auc_score(y[ix], s1[ix]) - roc_auc_score(y[ix], s0[ix]))
    return a0, a1, a1 - a0, np.percentile(bs, 2.5), np.percentile(bs, 97.5), y.mean(), len(te)


def line(nm, r):
    return f"    {nm:46s} base AUC {r[0]:.3f} -> {r[1]:.3f}  lift {r[2]:+.3f} [{r[3]:+.3f},{r[4]:+.3f}]  (test n {r[6]}, positives {100 * r[5]:.1f}%)"


def main():
    res = {}
    for repo in sys.argv[1:]:
        df, K, T = NP.load(repo)
        KT = K + T
        SPN = NF.GROUPS["S"] + NF.GROUPS["P"] + NF.GROUPS["N"]
        meta = metadata(repo)
        links = json.load(open(NF.LINKS[repo]))
        minlag = {}
        for p in links:
            minlag[p["ind"]] = min(minlag.get(p["ind"], 1e18), (p["fix_ct"] - p["ind_ct"]) / DAY)
        print(f"\n########## {repo}: {len(df)} changes ##########")
        r = {}
        # C1: label from later fix-subject commits touching the same functions
        touched = pickle.load(open(f"{B}/blast/{repo}/touched_all.pkl", "rb"))
        ct_all = {l.split()[0]: int(l.split()[1]) for l in subprocess.run(["git", "-C", f"{POOL}/{repo}", "log", "--no-merges", "--format=%H %ct"], capture_output=True, text=True).stdout.splitlines() if l.strip()}
        idx = collections.defaultdict(list)
        for sha, keys in touched.items():
            if sha in ct_all and 0 < len(keys) <= 60 and FIX.search(meta.get(sha, {}).get("subj", "").lower()):
                for k in keys:
                    idx[tuple(k)].append((ct_all[sha], sha))
        for v in idx.values():
            v.sort()
        lab = []
        for sha, ct in zip(df.sha, df.ct):
            hit = 0
            for k in touched[sha]:
                lst = idx.get(tuple(k), [])
                i = bisect.bisect_right(lst, (ct, "~"))
                if i < len(lst) and lst[i][0] <= ct + 365 * DAY and lst[i][1] != sha:
                    hit = 1
                    break
            lab.append(hit)
        df["y_alt"] = lab
        r["C1"] = lift(df, SPN, KT, label="y_alt")
        print(f"  C1 label = a later fix-subject commit touches a changed function within 365 days: positives {100 * df.y_alt.mean():.1f}% of changes; overlap with the trailer label: {100 * df[df.y_alt == 1].y.mean():.1f}% of them are also named causes")
        print(line("trailer label (reference, 730 d)", lift(df, SPN, KT)))
        print(line("alternative label (365 d)", r["C1"]))
        ac = NF.within_auc("k_add_cond", df.assign(y=df.y_alt))
        print(f"    added conditions, within-size-decile AUC on the alternative label: {ac:.3f} (trailer label {NF.within_auc('k_add_cond', df):.3f})")
        d1 = df.assign(y=df.y_alt)
        pdel = NP.rr(d1.assign(dec=df.dec), (df.r_n_add.to_numpy() == 0) & (df.r_n_rem.to_numpy() > 0))
        padd = NP.rr(d1.assign(dec=df.dec), (df.r_n_add.to_numpy() > 0) & (df.r_n_rem.to_numpy() == 0))
        print(f"    rate ratio on the alternative label: pure deletion {NP.fmt(pdel)}; pure addition {NP.fmt(padd)}")
        r["C1_ac"], r["C1_del"] = ac, pdel[0]
        # C2: directory and author indicators
        dirs = df.sha.map(lambda s: meta[s]["dirs"].most_common(1)[0][0] if meta.get(s) and meta[s]["dirs"] else "other")
        auth = df.sha.map(lambda s: meta[s]["ae"] if meta.get(s) else "other")
        topd = set(dirs.value_counts().index[:40])
        topa = set(auth.value_counts().index[:300])
        df2 = df.copy()
        D = pd.get_dummies(dirs.where(dirs.isin(topd), "other"), prefix="dir").astype(float)
        A = pd.get_dummies(auth.where(auth.isin(topa), "other"), prefix="au").astype(float)
        df2 = pd.concat([df2, D, A], axis=1)
        fe = list(D.columns) + list(A.columns)
        r["C2"] = lift(df2, SPN + fe, KT)
        print(f"  C2 directory ({D.shape[1]}) and author ({A.shape[1]}) indicators in both models:")
        print(line("lift with directory and author indicators", r["C2"]))
        # C3: no new files
        newf = df.sha.map(lambda s: meta[s]["new"] if meta.get(s) else False).to_numpy()
        dn = df[~newf].reset_index(drop=True)
        r["C3"] = lift(dn, SPN, KT)
        print(f"  C3 drop the {int(newf.sum())} changes that add a new C/H file ({100 * newf.mean():.1f}%): {len(dn)} left, positives {100 * dn.y.mean():.1f}% (all {100 * df.y.mean():.1f}%)")
        print(line("lift without new-file changes", r["C3"]))
        pdel3 = NP.rr(dn, (dn.r_n_add.to_numpy() == 0) & (dn.r_n_rem.to_numpy() > 0))
        padd3 = NP.rr(dn, (dn.r_n_add.to_numpy() > 0) & (dn.r_n_rem.to_numpy() == 0))
        print(f"    rate ratio without new-file changes: pure deletion {NP.fmt(pdel3)}; pure addition {NP.fmt(padd3)}")
        r["C3_del"] = pdel3[0]
        # C4: shuffle K+T within size decile
        n = int(0.6 * len(df))
        obs = lift(df, SPN, KT, boot=20)[2]
        nulls = []
        grp = [np.where(df.dec.to_numpy() == d)[0] for d in np.unique(df.dec)]
        for _ in range(60):
            perm = np.arange(len(df))
            for g in grp:
                perm[g] = rng.permutation(g)
            dp = df.copy()
            dp[KT] = df[KT].to_numpy()[perm]
            nulls.append(lift(dp, SPN, KT, boot=2)[2])
        r["C4"] = (obs, np.percentile(nulls, 95), np.mean(nulls), max(nulls))
        print(f"  C4 observed lift {obs:+.3f}; K+T shuffled within size deciles (60 shuffles): mean {np.mean(nulls):+.3f}, 95th percentile {np.percentile(nulls, 95):+.3f}, largest {max(nulls):+.3f}")
        # C5: horizons on the common population (changes at least 3 years before the end)
        end = df.ct.max() + 730 * DAY
        pop = df[df.ct <= end - 1095 * DAY].reset_index(drop=True)
        r["C5"] = {}
        print(f"  C5 horizons on the {len(pop)} changes at least three years before the end:")
        for H in (365, 730, 1095):
            pop["yh"] = [int(minlag.get(s, 1e18) <= H) for s in pop.sha]
            r["C5"][H] = lift(pop, SPN, KT, label="yh")
            print(line(f"named as a cause within {H} days", r["C5"][H]))
        # C6: reverse time
        r["C6"] = lift(df, SPN, KT, reverse=True)
        print("  C6 train on the latest 60%, test on the earliest 40%:")
        print(line("lift, reversed time split", r["C6"]))
        res[repo] = r
    print("\n=== VERDICTS ===")
    rp = list(res)
    f = lambda k: [res[r][k][2] for r in rp]  # noqa: E731
    print("  CT1 lift on the alternative label: " + ", ".join(f"{r} {v:+.3f}" for r, v in zip(rp, f("C1"))) + "; added conditions within-size AUC " + ", ".join(f"{r} {res[r]['C1_ac']:.3f}" for r in rp) + f" (needs +0.01 and 0.55 in both): {'supported' if all(v >= 0.01 for v in f('C1')) and all(res[r]['C1_ac'] >= 0.55 for r in rp) else 'not supported'}")
    print("  CT2 lift with directory and author indicators: " + ", ".join(f"{r} {v:+.3f}" for r, v in zip(rp, f("C2"))) + f" (needs +0.01 in both): {'supported' if all(v >= 0.01 for v in f('C2')) else 'not supported'}")
    print("  CT3 lift without new-file changes: " + ", ".join(f"{r} {v:+.3f}" for r, v in zip(rp, f("C3"))) + "; pure deletions " + ", ".join(f"{r} {res[r]['C3_del']:.2f}" for r in rp) + f" (needs +0.01 and 0.8 in both): {'supported' if all(v >= 0.01 for v in f('C3')) and all(res[r]['C3_del'] <= 0.8 for r in rp) else 'not supported'}")
    print("  CT4 observed lift against the 95th percentile of shuffled: " + ", ".join(f"{r} {res[r]['C4'][0]:+.3f} vs {res[r]['C4'][1]:+.3f}" for r in rp) + f": {'supported' if all(res[r]['C4'][0] > res[r]['C4'][1] for r in rp) else 'not supported'}")
    print("  CT5 lift by horizon (365 / 730 / 1095 days): " + "; ".join(f"{r} " + " / ".join(f"{res[r]['C5'][H][2]:+.3f}" for H in (365, 730, 1095)) for r in rp) + f" (needs +0.01 everywhere): {'supported' if all(res[r]['C5'][H][2] >= 0.01 for r in rp for H in (365, 730, 1095)) else 'not supported'}")
    print("  CT6 lift, reversed time: " + ", ".join(f"{r} {v:+.3f}" for r, v in zip(rp, f("C6"))) + f" (needs +0.01 in both): {'supported' if all(v >= 0.01 for v in f('C6')) else 'not supported'}")
    art = all(v < 0.005 for v in f("C1")) or any(v < 0.005 for v in f("C2"))
    print(f"  surprise bar (lift under +0.005 on the alternative label in both, or under C2): {'MET' if art else 'not met'}")


if __name__ == "__main__":
    main()
