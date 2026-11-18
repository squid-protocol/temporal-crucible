#!/usr/bin/env python3
"""Will this change need a fix? Features known at change time (size, process, call-graph neighbourhood) against 'named as the cause of a fix within 730 days', on all changes.
Hypotheses WN1-WN6: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.

    python tools/sensor/needs_fix.py dpdk mesa      (needs blast/<repo>/touched_all.pkl and snapshot_cts.npy, the quarterly scans, links_<repo>.json)"""
import bisect
import collections
import json
import pickle
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
LINKS = {"dpdk": f"{B}/argl/links_dpdk.json", "mesa": f"{B}/argl/links_mesa.json"}
DAY = 86400
rng = np.random.default_rng(2982)
GROUPS = {"S": ["log_lines", "log_funcs", "log_files"], "P": ["log_tenure", "log_churn"], "N": ["log_fanin_sum", "log_fanin_max", "log_fanout_sum", "log_caller_files", "log_near2"]}


def commits(repo):
    out = subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "log", "--no-merges", "--numstat", "--format=@@%H %ae %ct"], capture_output=True, text=True, errors="replace").stdout
    res, cur = [], None
    for l in out.splitlines():
        if l.startswith("@@"):
            parts = l[2:].split(" ")
            cur = {"sha": parts[0], "ae": " ".join(parts[1:-1]).lower(), "ct": int(parts[-1]), "lines": 0, "files": []}
            res.append(cur)
        elif cur is not None and "\t" in l:
            a, r, p = l.split("\t", 2)
            if p.endswith((".c", ".h")) and a.isdigit() and r.isdigit():
                cur["lines"] += int(a) + int(r)
                cur["files"].append(p)
    return [c for c in res if c["lines"] > 0]


def worker(args):
    db, items = args
    g = BR.Graph(db)
    fan = np.asarray(g.callers_m.sum(axis=0)).ravel()
    fout = np.asarray(g.callers_m.sum(axis=1)).ravel()
    out = []
    for idx, keys in items:
        I = np.array(sorted({g.index[k] for k in keys if k in g.index}), dtype=np.int64)
        if not len(I):
            continue
        near = g.near(I)
        out.append((idx, float(fan[I].sum()), float(fan[I].max()), float(fout[I].sum()), float(len(np.unique(g.fid[near["callers1"]]))), float(near["either2"].sum())))
    return out


def build(repo):
    tag = repo
    cm = commits(repo)
    cm.sort(key=lambda c: c["ct"])
    touched = pickle.load(open(f"{B}/blast/{repo}/touched_all.pkl", "rb"))
    snap_cts = np.load(f"{B}/blast/{repo}/snapshot_cts.npy")
    sn = json.load(open(f"{BR.B}/scan_{tag}/snapshots.json"))
    end = max(c["ct"] for c in cm)
    seen = collections.Counter()
    times = collections.defaultdict(list)
    for c in cm:
        c["tenure"] = seen[c["ae"]]
        seen[c["ae"]] += 1
        c["churn"] = 0
        for p in c["files"]:
            lst = times[p]
            c["churn"] = max(c["churn"], bisect.bisect_left(lst, c["ct"]) - bisect.bisect_left(lst, c["ct"] - 365 * DAY))
            lst.append(c["ct"])
    links = json.load(open(LINKS[repo]))
    pos = set()
    for p in links:
        if p["fix_ct"] - p["ind_ct"] <= 730 * DAY:
            pos.add(p["ind"])
    by_snap = collections.defaultdict(list)
    for i, c in enumerate(cm):
        if c["ct"] < snap_cts[0] or c["ct"] > end - 730 * DAY:
            continue
        keys = [tuple(k) for k in touched.get(c["sha"], [])]
        if not 1 <= len(keys) <= 60:
            continue
        s = int(np.searchsorted(snap_cts, c["ct"], side="left"))
        if s >= len(sn):
            continue
        by_snap[s].append((i, keys))
    rows = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for res in ex.map(worker, [(sn[s]["db"], it) for s, it in sorted(by_snap.items())]):
            rows += res
    f = {i: r for i, *r in rows}
    data = []
    for i, r in f.items():
        c = cm[i]
        data.append({"ct": c["ct"], "sha": c["sha"], "y": int(c["sha"] in pos), "log_lines": np.log1p(c["lines"]), "log_funcs": np.log1p(len(touched[c["sha"]])), "log_files": np.log1p(len(set(c["files"]))), "log_tenure": np.log1p(c["tenure"]), "log_churn": np.log1p(c["churn"]), "log_fanin_sum": np.log1p(r[0]), "log_fanin_max": np.log1p(r[1]), "log_fanout_sum": np.log1p(r[2]), "log_caller_files": np.log1p(r[3]), "log_near2": np.log1p(r[4]), "lines": c["lines"]})
    df = pd.DataFrame(data).sort_values("ct").reset_index(drop=True)
    return df


def fit(df_tr, cols):
    mu, sd = df_tr[cols].mean(), df_tr[cols].std().replace(0, 1)
    m = LogisticRegression(C=1.0, max_iter=2000).fit((df_tr[cols] - mu) / sd, df_tr.y)
    return lambda d: m.decision_function((d[cols] - mu) / sd)


def top_share(score, y, frac=0.1):
    k = max(int(len(y) * frac), 1)
    idx = np.argsort(-np.asarray(score))[:k]
    return y.to_numpy()[idx].sum() / max(y.sum(), 1)


def within_auc(feat, df):
    tot, n = 0.0, 0
    for _, d in df.groupby(pd.qcut(df.lines, 10, duplicates="drop"), observed=True):
        if d.y.nunique() == 2 and d[feat].nunique() > 1:
            tot += roc_auc_score(d.y, d[feat]) * len(d)
            n += len(d)
    return tot / n if n else float("nan")


def main():
    res = {}
    for repo in sys.argv[1:]:
        df = build(repo)
        k = int(0.6 * len(df))
        tr, te = df.iloc[:k], df.iloc[k:]
        print(f"\n########## {repo}: {len(df)} changes (train {len(tr)}, test {len(te)}); named as the cause of a fix within 730 days: {100 * df.y.mean():.1f}% (train {100 * tr.y.mean():.1f}%, test {100 * te.y.mean():.1f}%) ##########")
        combos = {"S": GROUPS["S"], "P": GROUPS["P"], "N": GROUPS["N"], "S+P": GROUPS["S"] + GROUPS["P"], "S+N": GROUPS["S"] + GROUPS["N"], "S+P+N": GROUPS["S"] + GROUPS["P"] + GROUPS["N"]}
        scores, aucs = {}, {}
        for nm, cols in combos.items():
            scores[nm] = fit(tr, cols)(te)
            aucs[nm] = roc_auc_score(te.y, scores[nm])
        lo = {}
        for nm in ("S+P", "S+P+N"):
            lo[nm] = []
        bs = []
        yv = te.y.to_numpy()
        for _ in range(200):
            ix = rng.integers(0, len(te), len(te))
            if yv[ix].min() == yv[ix].max():
                continue
            bs.append(roc_auc_score(yv[ix], scores["S+P+N"][ix]) - roc_auc_score(yv[ix], scores["S+P"][ix]))
        print("  test AUC (logistic): " + ", ".join(f"{nm} {a:.3f}" for nm, a in aucs.items()))
        print(f"  S+P+N minus S+P: {aucs['S+P+N'] - aucs['S+P']:+.3f} [{np.percentile(bs, 2.5):+.3f},{np.percentile(bs, 97.5):+.3f}]; S+N minus S: {aucs['S+N'] - aucs['S']:+.3f}")
        h = {}
        for nm in ("S+P", "S+P+N"):
            cols = combos[nm]
            m = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, random_state=0).fit(tr[cols], tr.y)
            h[nm] = roc_auc_score(te.y, m.predict_proba(te[cols])[:, 1])
        print(f"  test AUC (gradient boosting): S+P {h['S+P']:.3f}, S+P+N {h['S+P+N']:.3f} ({h['S+P+N'] - h['S+P']:+.3f})")
        q = np.quantile(tr.lines, [0.25, 0.5, 0.75])
        qi = np.searchsorted(q, te.lines.to_numpy())
        wq = {}
        print("  test AUC within size quartiles of the change (lines under " + ", ".join(f"{x:.0f}" for x in q) + "):")
        for nm in ("S+P+N", "S+P", "N", "P"):
            vals = []
            for j in range(4):
                mk = qi == j
                vals.append(roc_auc_score(yv[mk], np.asarray(scores[nm])[mk]) if len(set(yv[mk])) == 2 else float("nan"))
            wq[nm] = vals
            print(f"    {nm:7s} " + "  ".join(f"Q{j + 1} {v:.3f}" for j, v in enumerate(vals)) + f"   (positives per quartile: {', '.join(str(int(yv[qi == j].sum())) for j in range(4))})")
        uni = {c: within_auc(c, df) for c in GROUPS["N"] + GROUPS["P"] + ["log_lines"]}
        print("  within-size-decile AUC of single features (all changes): " + ", ".join(f"{c.replace('log_', '')} {v:.3f}" for c, v in uni.items()))
        ts = {nm: top_share(scores[nm], te.y) for nm in ("S", "S+P", "S+P+N")}
        print(f"  share of the fixed-cause changes found in the top decile of the score: S {100 * ts['S']:.1f}%, S+P {100 * ts['S+P']:.1f}%, S+P+N {100 * ts['S+P+N']:.1f}% (random 10%)")
        res[repo] = (aucs, bs, wq, uni, ts)
    print("\n=== VERDICTS ===")
    rp = list(res)
    print("  WN1 size alone test AUC: " + ", ".join(f"{r} {res[r][0]['S']:.3f}" for r in rp) + f" (needs 0.65 in both): {'supported' if all(res[r][0]['S'] >= 0.65 for r in rp) else 'not supported'}")
    print("  WN2 S+P+N minus S+P: " + ", ".join(f"{r} {res[r][0]['S+P+N'] - res[r][0]['S+P']:+.3f}" for r in rp) + f" (needs +0.02 in both): {'supported' if all(res[r][0]['S+P+N'] - res[r][0]['S+P'] >= 0.02 for r in rp) else 'not supported'}")
    print("  WN3 S+P+N AUC in the smallest size quartile: " + ", ".join(f"{r} {res[r][2]['S+P+N'][0]:.3f}" for r in rp) + f" (needs 0.58 in both): {'supported' if all(res[r][2]['S+P+N'][0] >= 0.58 for r in rp) else 'not supported'}")
    print("  WN4 best single neighbourhood feature, within-size AUC: " + ", ".join(f"{r} {max(res[r][3][c] for c in GROUPS['N']):.3f}" for r in rp) + f" (needs 0.55 in both): {'supported' if all(max(res[r][3][c] for c in GROUPS['N']) >= 0.55 for r in rp) else 'not supported'}")
    print("  WN5 process alone against neighbourhood alone: " + ", ".join(f"{r} {res[r][0]['P']:.3f} vs {res[r][0]['N']:.3f}" for r in rp) + f": {'supported' if all(res[r][0]['P'] > res[r][0]['N'] for r in rp) else 'not supported'}")
    print("  WN6 top-decile share S+P+N over S+P: " + ", ".join(f"{r} {res[r][4]['S+P+N'] / res[r][4]['S+P']:.2f}" for r in rp) + f" (needs 1.2 in both): {'supported' if all(res[r][4]['S+P+N'] / res[r][4]['S+P'] >= 1.2 for r in rp) else 'not supported'}")
    gain = max(res[r][0]['S+P+N'] - res[r][0]['S'] for r in rp)
    print(f"  surprise bar (every group adds under 0.01 over size alone): {'MET' if all(res[r][0]['S+P+N'] - res[r][0]['S'] < 0.01 for r in rp) else 'not met'} (largest gain of S+P+N over S: {gain:+.3f})")


if __name__ == "__main__":
    main()
