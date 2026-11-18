#!/usr/bin/env python3
"""Fix mechanism from the DIFF, validated against the subject-based labels, then applied to the fixes the subject could not classify.
Hypotheses D1-D5: docs/sensor-overhaul/sensors/ripple_radius.md ("Reading the diff instead of the subject"), fixed before training.

    python tools/sensor/change_kinds_diff.py --measure /tmp/.../blast/linux

Features come from `git log --no-walk --stdin -p -U0` over the fix commits (.c/.h files only): counts and shares of added and removed lines matching patterns for NULL and
error-pointer checks, locking and atomics, free/put/refcount, error paths, bounds arithmetic, zero-initialisation, condition rewrites, type and endianness changes, build-only
lines, comments, plus size. Model: gradient boosting, 5-fold cross-validated on the subject-classified fixes; prediction for the rest kept at probability 0.6 or more."""
import argparse
import collections
import pickle
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_predict

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import change_kinds as CK  # noqa: E402

PAT = {
    "null": r"\b(?:if|while)\s*\(\s*!|==\s*NULL|!=\s*NULL|\bIS_ERR\w*|\bPTR_ERR\b|\bunlikely\(\s*!|\bWARN_ON\w*\(\s*!",
    "lock": r"\b(?:mutex|spin|raw_spin|read|write|rw|local)_?(?:un)?lock\w*\(|\brcu_\w+|\bsynchronize_\w+|\bdown_(?:read|write)|\bup_(?:read|write)|\bREAD_ONCE|\bWRITE_ONCE|\bsmp_\w+|\batomic\w*\(|\bcmpxchg|\bbarrier\(|\blockdep\w*|\bguard\(|\bscoped_guard|\bpreempt_\w+|\bsrcu_\w+|\bspin_\w+|\bmutex_\w+",
    "free": r"\bk?v?free\w*\(|\b\w*_put\(|\bput_\w+\(|\brelease\w*\(|\bdestroy\w*\(|\bkref_\w+|\brefcount_\w+|\bdev_put|\bfree_\w+\(|\b\w+_free\(|\bmem_cgroup_\w+",
    "get": r"\b\w*_get\(|\bget_\w+\(|\batomic_inc|\bgrab\w*\(",
    "err": r"\bgoto\s+\w+|\breturn\s+-E\w+|\breturn\s+(?:err|ret|rc|error|status)\b|\b(?:ret|err|rc|error|status)\s*=\s*-?\w*E\w+|\bif\s*\(\s*\(?(?:ret|err|rc|error|status)\b|\bout:|\berr\w*:",
    "bound": r"\b(?:min|max|clamp|min_t|max_t|array_size|struct_size|size_add|size_mul|check_add_overflow|check_mul_overflow|ARRAY_SIZE|array_index_nospec|sizeof|BUILD_BUG_ON|round_up|roundup)\b|\b(?:len|size|count|idx|index|nr|num|max|limit)\w*\s*(?:<=|>=|<|>)|(?:<=|>=|<|>)\s*\w*(?:len|size|count|max|nr|num|limit)\w*",
    "init": r"\bkzalloc\w*|\bkcalloc|\bmemset\(|=\s*(?:0|NULL|false)\s*;|=\s*\{\s*0?\s*\}|\bzalloc|\bINIT_\w+|__GFP_ZERO|\bmemzero|\bmemcpy\(",
    "alloc": r"\bkmalloc\w*\(|\bkvmalloc\w*\(|\bvmalloc\(|\b\w*alloc\w*\(",
    "cond": r"\b(?:if|while|for)\s*\(|\?\s*\w+\s*:|&&|\|\|",
    "type": r"\b(?:u8|u16|u32|u64|s8|s16|s32|s64|size_t|ssize_t|int|long|unsigned|__be\d+|__le\d+|ntohs|ntohl|htons|htonl|cpu_to_\w+|\w+_to_cpu|\(\s*(?:u|s)\d+\s*\)|\(\s*(?:unsigned|long|int)\b)",
    "build": r"^\s*#\s*(?:include|if|ifdef|ifndef|else|elif|endif|define|undef)|\bEXPORT_SYMBOL\w*|^\s*static\b|__maybe_unused|\b__init\b|\b__exit\b|\binline\b|\b__always_inline|\bconst\b|\b__user\b|\b__rcu\b|\b__iomem\b|\bunused\b|\bMODULE_\w+|\b__must_check\b|\bnoinline\b",
    "comment": r"^\s*(?:/\*|\*|//)",
    "ret": r"\breturn\b",
    "call": r"\b[a-z_]\w*\(",
}
PATC = {k: re.compile(v) for k, v in PAT.items()}
NAMES = [f"{side}_{k}" for side in ("add", "rem") for k in PAT]
FEATS = NAMES + [n + "_share" for n in NAMES] + ["n_add", "n_rem", "n_hunks", "n_files", "log_changed", "net_lines", "cond_rewrite", "only_comment"]


def diff_features(shas, cache_file):
    cache = pickle.load(open(cache_file, "rb")) if Path(cache_file).exists() else {}
    need = [s for s in dict.fromkeys(shas) if s not in cache]
    if need:
        proc = subprocess.Popen(["git", "-C", CK.REPO, "log", "--no-walk=unsorted", "--stdin", "-p", "-U0", "--no-color", "--format=@@C %H"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, errors="replace")
        import threading

        threading.Thread(target=lambda: (proc.stdin.write("\n".join(need) + "\n"), proc.stdin.close()), daemon=True).start()
        sha, cur, accum = None, None, None

        def flush():
            if sha is not None and accum is not None:
                cache[sha] = finish(accum)

        for line in proc.stdout:
            if line.startswith("@@C "):
                flush()
                sha, cur = line[4:].strip(), None
                accum = {"add": [], "rem": [], "hunks": 0, "files": set(), "cond_rewrite": 0, "_h": [[], []]}
            elif sha:
                if line.startswith("+++ b/"):
                    cur = line[6:].rstrip("\n")
                    if cur.endswith((".c", ".h")):
                        accum["files"].add(cur)
                    else:
                        cur = None
                elif cur and line.startswith("@@"):
                    if accum["_h"][0] and accum["_h"][1]:
                        a_if = any(PATC["cond"].search(x) for x in accum["_h"][0])
                        r_if = any(PATC["cond"].search(x) for x in accum["_h"][1])
                        accum["cond_rewrite"] += int(a_if and r_if)
                    accum["_h"] = [[], []]
                    accum["hunks"] += 1
                elif cur and line.startswith("+") and not line.startswith("+++"):
                    accum["add"].append(line[1:].rstrip("\n"))
                    accum["_h"][0].append(line[1:])
                elif cur and line.startswith("-") and not line.startswith("---"):
                    accum["rem"].append(line[1:].rstrip("\n"))
                    accum["_h"][1].append(line[1:])
        flush()
        proc.wait()
        for s in need:
            cache.setdefault(s, finish({"add": [], "rem": [], "hunks": 0, "files": set(), "cond_rewrite": 0, "_h": [[], []]}))
        pickle.dump(cache, open(cache_file, "wb"))
    return cache


def finish(acc):
    row = {}
    for side in ("add", "rem"):
        lines = acc[side][:600]  # a cap: a huge diff is a sweep, its pattern shares are what matter
        n = max(len(lines), 1)
        for k, rx in PATC.items():
            c = sum(1 for x in lines if rx.search(x))
            row[f"{side}_{k}"] = c
            row[f"{side}_{k}_share"] = c / n
    row["n_add"], row["n_rem"] = len(acc["add"]), len(acc["rem"])
    row["n_hunks"], row["n_files"] = acc["hunks"], len(acc["files"])
    row["log_changed"] = float(np.log1p(len(acc["add"]) + len(acc["rem"])))
    row["net_lines"] = len(acc["add"]) - len(acc["rem"])
    row["cond_rewrite"] = acc["cond_rewrite"]
    row["only_comment"] = float(bool(acc["add"] + acc["rem"]) and all(PATC["comment"].search(x) or not x.strip() for x in acc["add"] + acc["rem"]))
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", required=True)
    ap.add_argument("--threshold", type=float, default=0.6)
    a = ap.parse_args()
    rng = np.random.default_rng(2982)
    out = Path(a.measure)
    df = pd.read_pickle(out / "measure.pkl")
    df = df[df.status == "ok"].copy()
    CK.args_total = len(df)
    msg = CK.messages(list(df.fix) + list(df.ind), out / "messages.pkl")
    fx = [CK.fix_class(*msg.get(s, ("", ""))) for s in df.fix]
    df["subj_kind"] = [x[0] if x[1] == "subject" else None for x in fx]
    feats = diff_features(list(df.fix), out / "diff_feats.pkl")
    X = pd.DataFrame([feats[s] for s in df.fix])[FEATS].fillna(0.0).to_numpy(float)
    lab = df.subj_kind.notna().to_numpy()
    y = df.subj_kind.to_numpy()
    classes = sorted(set(y[lab]))
    print(f"{len(df)} pairs; subject-classified {lab.sum()} ({100 * lab.mean():.0f}%); classes {classes}")

    # D1: how much of the subject label does the diff alone recover?
    model = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.08, random_state=0)
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    proba = cross_val_predict(model, X[lab], y[lab], cv=cv, method="predict_proba")
    pred = np.array(sorted(set(y[lab])))[proba.argmax(1)]
    rep = classification_report(y[lab], pred, output_dict=True, zero_division=0)
    print("\n=== D1: cross-validated recovery of the subject label from the diff alone ===")
    for k in classes:
        r = rep[k]
        print(f"  {k:16s} precision {r['precision']:.2f} recall {r['recall']:.2f} F1 {r['f1-score']:.2f} (n {int(r['support'])})")
    print(f"  accuracy {rep['accuracy']:.2f}, macro-F1 {rep['macro avg']['f1-score']:.2f} (majority-class accuracy {max(collections.Counter(y[lab]).values()) / lab.sum():.2f})")
    hi = proba.max(1) >= a.threshold
    print(f"  at probability >= {a.threshold}: covers {100 * hi.mean():.0f}% of labelled fixes, accuracy {100 * (pred[hi] == y[lab][hi]).mean():.0f}%")
    cm = pd.DataFrame(confusion_matrix(y[lab], pred, labels=classes), index=classes, columns=[c[:6] for c in classes])
    print("  confusion (rows true, columns predicted):\n" + cm.to_string())

    # D2: apply to the rest
    model.fit(X[lab], y[lab])
    pu = model.predict_proba(X[~lab])
    pk = np.array(model.classes_)[pu.argmax(1)]
    keep = pu.max(1) >= a.threshold
    df["diff_kind"] = None
    df.loc[~lab, "diff_kind"] = np.where(keep, pk, None)
    df["kind"] = np.where(lab, df.subj_kind, df.diff_kind)
    n_un = (~lab).sum()
    print(f"\n=== D2: the {n_un} fixes the subject could not classify ===")
    print(f"  assigned at probability >= {a.threshold}: {keep.sum()} ({100 * keep.mean():.0f}%); coverage of all pairs: {100 * df.kind.notna().mean():.0f}% (from {100 * lab.mean():.0f}%)")
    print("  predicted classes: " + ", ".join(f"{k} {v}" for k, v in collections.Counter(pk[keep]).most_common()))
    # precision check by reading: 8 random predicted-class fixes per class with their (unused) subjects
    rr = np.random.default_rng(11)
    sub_un = df[~lab].reset_index(drop=True)
    print("  reading check (subject of a random fix the diff classified, not used by the model):")
    for k in classes:
        idx = np.where(keep & (pk == k))[0]
        for i in rr.choice(idx, min(5, len(idx)), replace=False) if len(idx) else []:
            print(f"    [{k[:10]}] {msg[sub_un.fix[i]][0][:110]}")

    # what are the leftovers?
    left = ~keep
    if left.sum() > 100:
        km = MiniBatchKMeans(10, random_state=0, n_init=5).fit(X[~lab][left][:, :len(NAMES)])
        print(f"\n=== the {left.sum()} left over (probability below {a.threshold}): ten clusters by diff pattern ===")
        sub_left = sub_un[left].reset_index(drop=True)
        base = X[~lab][left][:, :len(NAMES)].mean(0)
        for c in range(10):
            m = km.labels_ == c
            cen = X[~lab][left][m][:, :len(NAMES)].mean(0)
            top = np.argsort(cen - base)[::-1][:3]
            ex = sub_left[m].fix.iloc[:3]
            print(f"  cluster {c}: {m.sum():5d} fixes; over-represented {', '.join(NAMES[t] for t in top)}; e.g. " + " | ".join(msg[s][0][:60] for s in ex))

    # D3-D5: the radius, lag and locality tables on the larger labelled set
    print("\n=== D3-D5: lag, locality and radius by mechanism, subject-classified plus diff-classified ===")
    df["cross"] = ~df.same_file.astype(bool)
    base = df.cross.mean()
    print(f"  {'class':16s} {'pairs':>6s} {'lag':>6s} {'same fn':>8s} {'cross-file':>11s} {'x overall':>9s}   within 2 calls")
    rows = {}
    for k in classes + ["unclassified"]:
        d = df[df.kind.isna()] if k == "unclassified" else df[df.kind == k]
        o = d[d.nFo > 0]
        r = BR.ratio(o, "either2", "eB", rng)
        rows[k] = (np.median(d.lag), d.cross.mean(), r)
        print(f"  {k:16s} {len(d):6d} {np.median(d.lag):5.0f}d {100 * d.same_func.mean():7.0f}% {100 * d.cross.mean():10.1f}% {d.cross.mean() / base:8.2f}x   {BR.fmt(r) if r else 'n/a'}")
    big = {k: v for k, v in rows.items() if k != "unclassified" and v[2] and v[2][3] >= 300}
    if big:
        vals = [v[2][0] for v in big.values()]
        print(f"  radius across classes with 300+ pairs: {min(vals):.2f} to {max(vals):.2f} (factor {max(vals) / min(vals):.2f})")
    short = [rows[k][0] for k in ("build/compile", "uninitialized", "null deref") if k in rows]
    long_ = [rows[k][0] for k in ("concurrency", "lifetime", "bounds/overflow") if k in rows]
    print(f"  median lag of the short classes (build, uninitialised, NULL): {np.mean(short):.0f} d against the long classes (concurrency, lifetime, bounds): {np.mean(long_):.0f} d")
    df.drop(columns=["fix_files", "ind_files"], errors="ignore").to_pickle(out / "kinds_diff.pkl")


if __name__ == "__main__":
    main()
