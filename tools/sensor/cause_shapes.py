#!/usr/bin/env python3
"""Shape of the causing change, and causing shape x fix shape. Hypotheses CS1-CS5: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.

    python tools/sensor/cause_shapes.py --measure /tmp/.../blast/linux      (needs shapes.pkl from fix_shapes.py)"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import change_kinds as CK  # noqa: E402
import change_kinds_diff as CD  # noqa: E402
import fix_shapes as FS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", required=True)
    a = ap.parse_args()
    rng = np.random.default_rng(2982)
    out = Path(a.measure)
    df = pd.read_pickle(out / "shapes.pkl").rename(columns={"shape": "fix_shape"})
    feats = CD.diff_features(list(df.ind) + list(df.fix), out / "diff_feats.pkl")
    df["cause_shape"] = [FS.shape(feats[s]) for s in df.ind]
    df["cross"] = ~df.same_file.astype(bool)
    CK.args_total = len(df)
    print(f"{len(df)} measured kernel pairs; causing-change shape from the causing commit's .c/.h diff")
    print("\n=== BY CAUSING SHAPE ===")
    print(f"  {'causing shape':32s} {'pairs':>6s} {'share':>6s} {'lag':>6s} {'same fn':>8s} {'cross-file':>10s}   within 2 calls")
    rows = {}
    for k in FS.SHAPES:
        d = df[df.cause_shape == k]
        if not len(d):
            continue
        o = d[d.nFo > 0]
        r = BR.ratio(o, "either2", "eB", rng)
        rows[k] = (len(d), np.median(d.lag), d.same_func.mean(), d.cross.mean(), r)
        print(f"  {k:32s} {len(d):6d} {100 * len(d) / len(df):5.1f}% {np.median(d.lag):5.0f}d {100 * d.same_func.mean():7.0f}% {100 * d.cross.mean():9.1f}%   {BR.fmt(r) if r else 'n/a'}")
    big = {k: v for k, v in rows.items() if v[0] >= 500 and v[4]}
    lags = {k: v[1] for k, v in big.items()}
    vals = [v[4][0] for v in big.values()]
    print(f"\n  lag: slowest {max(lags, key=lags.get)} {max(lags.values()):.0f} d, fastest {min(lags, key=lags.get)} {min(lags.values()):.0f} d (factor {max(lags.values()) / min(lags.values()):.2f}); radius across causing shapes with 500+ pairs {min(vals):.2f} to {max(vals):.2f} (factor {max(vals) / min(vals):.2f})")

    print("\n=== PARAMETER COUNT CHANGED BY THE CAUSING COMMIT ===")
    for lab, d in (("signature changed", df[df.sig == True]), ("no signature change", df[df.sig == False])):  # noqa: E712
        o = d[d.nFo > 0]
        r = BR.ratio(o, "either2", "eB", rng)
        print(f"  {lab:20s} {len(d):6d} lag {np.median(d.lag):4.0f}d same fn {100 * d.same_func.mean():3.0f}% cross-file {100 * d.cross.mean():4.1f}%  {BR.fmt(r) if r else 'n/a'}; fix shape 'adds a guard' {100 * (d.fix_shape == 'adds a guard').mean():.1f}% (all pairs {100 * (df.fix_shape == 'adds a guard').mean():.1f}%)")

    print("\n=== CAUSING SHAPE x FIX SHAPE: lift (observed / expected if independent), cells of 100+ pairs ===")
    ct = pd.crosstab(df.cause_shape, df.fix_shape)
    tot = ct.values.sum()
    cells = []
    for c in ct.index:
        for f in ct.columns:
            n = ct.loc[c, f]
            exp = ct.loc[c].sum() * ct[f].sum() / tot
            if n >= 100 and exp > 0:
                cells.append((n / exp, c, f, int(n)))
    print("  most over-represented:")
    for lift, c, f, n in sorted(cells, reverse=True)[:10]:
        print(f"    {c:30s} -> {f:30s} lift {lift:4.2f} (n {n})")
    print("  most under-represented:")
    for lift, c, f, n in sorted(cells)[:8]:
        print(f"    {c:30s} -> {f:30s} lift {lift:4.2f} (n {n})")
    diag = [(k, ct.loc[k, k] / (ct.loc[k].sum() * ct[k].sum() / tot), int(ct.loc[k, k])) for k in FS.SHAPES if k in ct.index and k in ct.columns and ct.loc[k].sum() >= 500 and ct[k].sum() >= 500]
    print("  diagonal (a fix with the same shape as its cause): " + ", ".join(f"{k} {l:.2f}" for k, l, _ in diag) + f"; {sum(1 for _, l, _ in diag if l >= 1.2)} of {len(diag)} at 1.2 or more")
    for c, f in (("adds code", "adds a guard"), ("replaces a call or argument", "adds a guard")):
        if c in ct.index and f in ct.columns:
            print(f"  {c} -> {f}: lift {ct.loc[c, f] / (ct.loc[c].sum() * ct[f].sum() / tot):.2f} (n {int(ct.loc[c, f])})")
    print("\n  causing shape x subject-classified fix mechanism (row shares, mechanism-classified fixes only):")
    m = df[df.subj_kind.notna()]
    print(pd.crosstab(m.cause_shape, m.subj_kind, normalize="index").round(2).to_string())
    df.to_pickle(out / "cause_shapes.pkl")


if __name__ == "__main__":
    main()
