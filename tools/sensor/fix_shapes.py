#!/usr/bin/env python3
"""Fix shape from the diff (rule-based, complete): lag, locality and radius by shape. Hypotheses SH1-SH4: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.

    python tools/sensor/fix_shapes.py --measure /tmp/.../blast/linux      (needs diff_feats.pkl from change_kinds_diff.py and measure.pkl)"""
import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import change_kinds as CK  # noqa: E402

SHAPES = ["comment only", "large (100+ lines)", "removes code", "adds a guard", "rewrites a condition", "adds sync or release", "replaces a call or argument", "changes a type or declaration", "adds code", "small edit", "other edit"]


def shape(f):
    na, nr = f["n_add"], f["n_rem"]
    tot = na + nr
    if f["only_comment"]:
        return SHAPES[0]
    if tot >= 100:
        return SHAPES[1]
    if nr >= 1 and nr >= 2 * na and na <= 4:
        return SHAPES[2]
    if f["add_cond"] >= 1 and (f["add_ret"] >= 1 or f["add_err"] >= 1) and nr <= 2 and na <= 20:
        return SHAPES[3]
    if f["cond_rewrite"] >= 1 and na <= 10 and nr <= 10:
        return SHAPES[4]
    if (f["add_lock"] >= 1 or f["add_free"] >= 1) and na <= 20:
        return SHAPES[5]
    if f["rem_call"] >= 1 and f["add_call"] >= 1 and abs(na - nr) <= 2 and na <= 6:
        return SHAPES[6]
    if (f["add_type"] >= 1 or f["add_build_share"] > 0.5) and na <= 6:
        return SHAPES[7]
    if na >= 3 * max(nr, 1):
        return SHAPES[8]
    if tot <= 12:
        return SHAPES[9]
    return SHAPES[10]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", required=True)
    a = ap.parse_args()
    rng = np.random.default_rng(2982)
    out = Path(a.measure)
    df = pd.read_pickle(out / "kinds_diff.pkl")
    feats = pickle.load(open(out / "diff_feats.pkl", "rb"))
    df["shape"] = [shape(feats[s]) for s in df.fix]
    df["cross"] = ~df.same_file.astype(bool)
    CK.args_total = len(df)
    print(f"{len(df)} measured kernel pairs; fix shape from the fix commit's .c/.h diff")
    print(f"  {'shape':32s} {'pairs':>6s} {'share':>6s} {'lag':>6s} {'same fn':>8s} {'cross-file':>10s}   within 2 calls (against same-file functions)")
    rows = {}
    for k in SHAPES:
        d = df[df["shape"] == k]
        if not len(d):
            continue
        o = d[d.nFo > 0]
        r = BR.ratio(o, "either2", "eB", rng)
        rows[k] = (len(d), np.median(d.lag), d.same_func.mean(), d.cross.mean(), r)
        print(f"  {k:32s} {len(d):6d} {100 * len(d) / len(df):5.1f}% {np.median(d.lag):5.0f}d {100 * d.same_func.mean():7.0f}% {100 * d.cross.mean():9.1f}%   {BR.fmt(r) if r else 'n/a'}")
    big = {k: v for k, v in rows.items() if v[0] >= 500 and v[4]}
    vals = [v[4][0] for v in big.values()]
    print(f"\n  radius across shapes with 500+ pairs: {min(vals):.2f} to {max(vals):.2f} (factor {max(vals) / min(vals):.2f})")
    if "adds a guard" in rows and "removes code" in rows:
        print(f"  median lag: adds a guard {rows['adds a guard'][1]:.0f} d, removes code {rows['removes code'][1]:.0f} d")
    print(f"  highest same-function share (500+ pairs): {max(big, key=lambda k: big[k][2])} ({100 * max(v[2] for v in big.values()):.0f}%); lowest radius: {min(big, key=lambda k: big[k][4][0])}; highest cross-file: {max(big, key=lambda k: big[k][3])}")
    print("\n  shape x subject-classified mechanism (row share of each shape, mechanism-classified fixes only):")
    ct = pd.crosstab(df[df.subj_kind.notna()]["shape"], df[df.subj_kind.notna()].subj_kind, normalize="index").round(2)
    print(ct.to_string())
    df.to_pickle(out / "shapes.pkl")


if __name__ == "__main__":
    main()
