#!/usr/bin/env python3
"""Shape tables (fix shape, causing shape, causing x fix lift) on the kernel, OpenSSL and FreeBSD side by side; directional checks RS1-RS5
(docs/sensor-overhaul/sensors/ripple_radius.md, "Replicating the shape tables on OpenSSL and FreeBSD", fixed before running).

    python tools/sensor/shape_replication.py        (needs measure.pkl for linux, openssl, freebsd-src under /tmp/gitgalaxy-scratch/claude/blast/)"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import change_kinds as CK  # noqa: E402
import change_kinds_diff as CD  # noqa: E402
import fix_shapes as FS  # noqa: E402

POOL = "/srv/storage_16tb/projects/temporal-crucible-pool"
BASE = Path("/tmp/gitgalaxy-scratch/claude/blast")
DATA = [("kernel", "linux", f"{POOL}/linux"), ("openssl", "openssl", f"{POOL}/openssl"), ("freebsd", "freebsd-src", f"{POOL}/freebsd-src"), ("dpdk", "dpdk", f"{POOL}/dpdk"), ("mesa", "mesa", f"{POOL}/mesa")]
rng = np.random.default_rng(2982)
SUF = os.environ.get("BLAST_SUFFIX", "")  # "_v" reads the verified-function measurements


def load(label, d, path):
    CK.REPO = path
    df = pd.read_pickle(BASE / (d + SUF) / "measure.pkl")
    df = df[df.status == "ok"].copy()
    feats = CD.diff_features(list(df.ind) + list(df.fix), BASE / (d + SUF) / "diff_feats.pkl")
    df["fix_shape"] = [FS.shape(feats[s]) for s in df.fix]
    df["cause_shape"] = [FS.shape(feats[s]) for s in df.ind]
    df["cross"] = ~df.same_file.astype(bool)
    df["ds"] = label
    return df


def table(df, col, title, minn=1):
    out = df[df.nFo > 0]
    print(f"  {title}")
    print(f"    {'shape':30s} {'pairs':>5s} {'share':>6s} {'lag':>6s} {'same fn':>7s} {'cross':>6s}   within 2 calls")
    for k in FS.SHAPES:
        d = df[df[col] == k]
        if len(d) < minn:
            continue
        r = BR.ratio(out[out[col] == k], "either2", "eB", rng)
        print(f"    {k:30s} {len(d):5d} {100 * len(d) / len(df):5.1f}% {np.median(d.lag):5.0f}d {100 * d.same_func.mean():6.0f}% {100 * d.cross.mean():5.1f}%   {BR.fmt(r) if r else 'n/a'}")
    print(f"    {'ALL':30s} {len(df):5d} {'':6s} {np.median(df.lag):5.0f}d {100 * df.same_func.mean():6.0f}% {100 * df.cross.mean():5.1f}%")


def lift(df, c, f):
    ct = pd.crosstab(df.cause_shape, df.fix_shape)
    if c not in ct.index or f not in ct.columns:
        return None, 0
    exp = ct.loc[c].sum() * ct[f].sum() / ct.values.sum()
    n = int(ct.loc[c, f])
    return (n / exp if exp > 0 else None), n


def checks(df, name):
    res = {}
    g = df[df.fix_shape == "adds a guard"]
    if len(g) >= 8:
        res["RS1 guard fixes: same-function share below all, lag above the median"] = (g.same_func.mean() < df.same_func.mean() and np.median(g.lag) > np.median(df.lag), f"{100 * g.same_func.mean():.0f}% vs {100 * df.same_func.mean():.0f}%; {np.median(g.lag):.0f} d vs {np.median(df.lag):.0f} d (n {len(g)})")
    m = df[df.fix_shape.isin(["replaces a call or argument", "changes a type or declaration", "removes code"])]
    if len(m) >= 10:
        res["RS2 call/type/removal fixes: lag below the median"] = (np.median(m.lag) < np.median(df.lag), f"{np.median(m.lag):.0f} d vs {np.median(df.lag):.0f} d (n {len(m)})")
    out = df[df.nFo > 0]
    rr = {k: BR.ratio(out[out.fix_shape == k], "either2", "eB", rng) for k in FS.SHAPES}
    rr = {k: v for k, v in rr.items() if v and v[3] >= 15}
    if len(rr) >= 3:
        low = min(rr, key=lambda k: rr[k][0])
        res["RS3 lowest radius is the large fixes"] = (low == "large (100+ lines)", f"lowest: {low} {rr[low][0]:.2f} (shapes with 15+ pairs: {len(rr)})")
    big = (df.cause_shape == "large (100+ lines)").mean()
    cs = {k: df[df.cause_shape == k] for k in FS.SHAPES}
    cs = {k: v for k, v in cs.items() if len(v) >= 15}
    ok4 = big >= 0.30 and "large (100+ lines)" in cs and min(cs, key=lambda k: cs[k].same_func.mean()) == "large (100+ lines)" and max(cs, key=lambda k: np.median(cs[k].lag)) == "large (100+ lines)"
    res["RS4 causes mostly large; large causes lowest same-function share, longest lag"] = (ok4, f"large causes {100 * big:.0f}%; lowest same-function: {min(cs, key=lambda k: cs[k].same_func.mean())}; longest lag: {max(cs, key=lambda k: np.median(cs[k].lag))}")
    l1, n1 = lift(df, "adds sync or release", "adds sync or release")
    l2, n2 = lift(df, "replaces a call or argument", "replaces a call or argument")
    got = [(l, n) for l, n in ((l1, n1), (l2, n2)) if l is not None and n >= 8]
    if got:
        res["RS5 diagonal lifts (sync->sync, call->call) at least 1.0"] = (all(l >= 1.0 for l, _ in got), f"sync {l1 if l1 is None else round(l1, 2)} (n {n1}), call {l2 if l2 is None else round(l2, 2)} (n {n2})")
    return res


def main():
    dfs = {lab: load(lab, d, p) for lab, d, p in DATA}
    dfs["openssl+freebsd"] = pd.concat([dfs["openssl"], dfs["freebsd"]], ignore_index=True)
    for lab in ("kernel", "dpdk", "mesa", "openssl", "freebsd", "openssl+freebsd"):
        df = dfs[lab]
        print(f"\n########## {lab}: {len(df)} measured pairs ({int((df.nFo > 0).sum())} with a fixed function outside the changed set) ##########")
        table(df, "fix_shape", "FIX SHAPE", minn=3 if lab != "kernel" else 1)
        table(df, "cause_shape", "CAUSING SHAPE", minn=3 if lab != "kernel" else 1)
    print("\n########## DIRECTIONAL CHECKS (kernel first for reference) ##########")
    allres = {lab: checks(dfs[lab], lab) for lab in ("kernel", "dpdk", "mesa", "openssl", "freebsd", "openssl+freebsd")}
    keys = list(allres["kernel"].keys())
    for k in keys:
        print(f"  {k}")
        for lab in ("kernel", "dpdk", "mesa", "openssl", "freebsd", "openssl+freebsd"):
            r = allres[lab].get(k)
            print(f"    {lab:16s} " + ("not testable (too few pairs)" if r is None else f"{'AGREES' if r[0] else 'differs'}: {r[1]}"))
    tested = [(lab, k, v) for lab in ("dpdk", "mesa", "openssl", "freebsd") for k, v in allres[lab].items()]
    print(f"\n  per repository (DPDK, Mesa, OpenSSL, FreeBSD): {sum(1 for _, _, v in tested if v[0])} of {len(tested)} testable checks agree with the kernel's direction")
    pooled = allres["openssl+freebsd"]
    print(f"  pooled OpenSSL + FreeBSD: {sum(1 for v in pooled.values() if v[0])} of {len(pooled)} agree")
    print("\n  causing x fix lifts, pooled OpenSSL+FreeBSD (cells of 8+ pairs), kernel in brackets:")
    for c, f in (("adds sync or release", "adds sync or release"), ("replaces a call or argument", "replaces a call or argument"), ("small edit", "small edit"), ("adds a guard", "adds a guard"), ("large (100+ lines)", "large (100+ lines)"), ("adds code", "adds code"), ("adds code", "adds a guard")):
        l, n = lift(dfs["openssl+freebsd"], c, f)
        lk, nk = lift(dfs["kernel"], c, f)
        print(f"    {c:28s} -> {f:28s} {('n/a' if l is None else f'{l:.2f}'):>5s} (n {n}) [kernel {lk:.2f}]")


if __name__ == "__main__":
    main()
