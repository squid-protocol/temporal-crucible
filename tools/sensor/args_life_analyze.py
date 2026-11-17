#!/usr/bin/env python3
"""Arguments over a function's life, and fixes (exploratory; hypotheses H1-H7 in docs/sensor-overhaul/sensors/args_over_life.md, written before the outcomes were read).

    python tools/sensor/args_life_analyze.py REPO [REPO ...]        (needs the pickles from args_life_build.py)

Units: a lineage observed in consecutive snapshots s and s+1 gives one pair; an argument change is a different parameter count in the pair.
Source files only (paths under tests, docs, examples, fuzz, bench are left out). Left-truncated lineages (present in the first snapshot) are
left out of every age statement. Fix link: file level, files touched by the crucible's fix events (v3c), compared within files that were edited
in the interval, stratified by file size and by how many functions were edited, interval-bootstrap intervals."""
import collections
import json
import pickle
import re
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata

SP = "/tmp/gitgalaxy-scratch/claude/argl"
EV = "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/turn/events"
TESTP = re.compile(r"(^|/)(tests?|examples?|docs?|fuzz\w*|bench\w*|testdata|samples?)(/|$)")
rng = np.random.default_rng(2982)


def load(name):
    d = pickle.load(open(f"{SP}/{name}.pkl", "rb"))
    df = pd.DataFrame(d["rows"], columns=["s", "lin", "args", "loc", "path", "fn"])
    df = df[~df.path.map(lambda p: bool(TESTP.search(p)))].copy()
    return df, d["ct"]


def pairs(df):
    df = df.sort_values(["lin", "s"])
    first = df.groupby("lin").s.transform("min")
    df["first"] = first
    nxt = df.groupby("lin").shift(-1)
    ok = nxt.s == df.s + 1
    p = pd.DataFrame({"lin": df.lin[ok], "s": df.s[ok], "a0": df.args[ok], "a1": nxt.args[ok].astype(int), "l0": df["loc"][ok], "l1": nxt["loc"][ok].astype(int), "first": df["first"][ok], "path": df.path[ok], "path1": nxt.path[ok]})
    p["age"] = p.s - p["first"]
    p["chg"] = p.a1 != p.a0
    p["d"] = p.a1 - p.a0
    return df, p


def partial(x, y, z):
    rx, ry, rz = rankdata(x), rankdata(y), rankdata(z)
    A = np.vstack([rz, np.ones_like(rz)]).T
    ex = rx - A @ np.linalg.lstsq(A, rx, rcond=None)[0]
    ey = ry - A @ np.linalg.lstsq(A, ry, rcond=None)[0]
    dd = ex.std() * ey.std()
    return float((ex * ey).mean() / dd) if dd > 0 else float("nan")


def pc(a, b):
    return f"{100 * a / b:.1f}%" if b else "n/a"


def describe(name, df, p):
    out = {}
    life = df.groupby("lin").agg(n=("s", "size"), first=("s", "min"), a_min=("args", "min"), a_max=("args", "max"))
    long = life[life.n >= 3]
    out["h1_const"] = float((long.a_min == long.a_max).mean())
    out["lineages3"] = len(long)
    out["pairs"] = len(p)
    out["pair_chg"] = float(p.chg.mean())
    ch = p[p.chg]
    out["h2_up"] = float((ch.d > 0).mean())
    out["n_chg"] = len(ch)
    out["step1"] = float((ch.d.abs() == 1).mean())
    pa = p[p["first"] > 0]
    out["h3"] = {k: float(pa[(pa.age >= lo) & (pa.age <= hi)].chg.mean()) for k, (lo, hi) in {"age0": (0, 0), "age1-2": (1, 2), "age3-6": (3, 6), "age7+": (7, 999)}.items()}
    out["h3_n"] = {k: int(len(pa[(pa.age >= lo) & (pa.age <= hi)])) for k, (lo, hi) in {"age0": (0, 0), "age1-2": (1, 2), "age3-6": (3, 6), "age7+": (7, 999)}.items()}
    # H4: size change among edited pairs (loc changed or args changed), stratified by starting size
    e = p[(p.l1 != p.l0) | p.chg].copy()
    e["rel"] = (e.l1 - e.l0).abs() / e.l0.clip(lower=1)
    e["q"] = pd.qcut(e.l0, 4, labels=False, duplicates="drop")
    diffs = []
    for q, g in e.groupby("q"):
        a, b = g[g.chg].rel, g[~g.chg].rel
        if len(a) >= 20 and len(b) >= 20:
            diffs.append((float(a.median()), float(b.median()), len(a), len(b)))
    out["h4"] = diffs
    # H4b (found after looking: the edited set above counts argument changes with no size change, which biases H4 against itself): loc-changed pairs only
    e2 = e[e.l1 != e.l0]
    d2 = []
    for q, g in e2.groupby("q"):
        a, b = g[g.chg].rel, g[~g.chg].rel
        if len(a) >= 20 and len(b) >= 20:
            d2.append((float(a.median()), float(b.median()), len(a), len(b)))
    out["h4b"] = d2
    # H7: args at birth against calendar time (births after the first snapshot)
    b = df[(df["first"] > 0) & (df.s == df["first"])]
    out["h7"] = (partial(b.s, b.args, b["loc"]) if len(b) > 500 else float("nan"), len(b))
    return out


def fix_link(name, df, p, ct):
    """File-level link between a parameter-count change in interval i and a fix touching the file in interval i+1 (and, as a check, in interval i)."""
    try:
        ev = json.load(open(f"{EV}/{name}_xc2.json"))["events"]
    except FileNotFoundError:
        return None
    classes = sorted({e["class"] for e in ev})
    by = collections.defaultdict(set)  # (interval, class) -> paths
    iv = np.array(ct)
    for e in ev:
        i = int(np.searchsorted(iv, e["ct"], side="right")) - 1
        if 0 <= i < len(ct) - 1:
            for f in e["c_files"]:
                by[(i, e["class"])].add(f)
                by[(i, "any")].add(f)
    p = p.copy()
    p["edited"] = (p.l1 != p.l0) | p.chg
    g = p[p.edited].groupby(["s", "path1"]).agg(n_edit=("lin", "size"), n_arg=("chg", "sum"), loc=("l0", "sum")).reset_index()
    g["E"] = g.n_arg > 0
    g["sz"] = pd.qcut(g["loc"], 3, labels=False, duplicates="drop")
    g["ne"] = np.minimum(g.n_edit, 4)
    res = {}
    for cls in classes + ["any"]:
        for when, off in (("next", 1), ("same", 0)):
            y = np.array([(r.path1 in by.get((int(r.s) + off, cls), ())) for r in g.itertuples()])
            res[(cls, when)] = (g.assign(Y=y)[["s", "E", "sz", "ne", "Y"]])
    return res


def mh_rr(t):
    num = den = 0.0
    n1s = a1s = n0s = a0s = 0
    for _, h in t.groupby(["sz", "ne"]):
        n1, n0 = int(h.E.sum()), int((~h.E).sum())
        a1, a0 = int((h.E & h.Y).sum()), int((~h.E & h.Y).sum())
        n = n1 + n0
        if n1 and n0:
            num += a1 * n0 / n
            den += a0 * n1 / n
        n1s, a1s, n0s, a0s = n1s + n1, a1s + a1, n0s + n0, a0s + a0
    return (num / den if den else float("nan")), a1s, n1s, a0s, n0s


def boot(t, B=300):
    ivs = t.s.unique()
    groups = {i: t[t.s == i] for i in ivs}
    vals = []
    for _ in range(B):
        pick = rng.choice(ivs, size=len(ivs), replace=True)
        rr = mh_rr(pd.concat([groups[i] for i in pick]))[0]
        if rr == rr and np.isfinite(rr):
            vals.append(rr)
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))) if len(vals) > 50 else (float("nan"), float("nan"))


def main():
    names = sys.argv[1:]
    pooled_link = collections.defaultdict(list)
    for name in names:
        df, ct = load(name)
        df, p = pairs(df)
        d = describe(name, df, p)
        print(f"\n=== {name}: {len(df):,} function-snapshots, {df.lin.nunique():,} lineages, {len(p):,} consecutive pairs (source files) ===")
        print(f"H1  lineages seen in 3+ snapshots: {d['lineages3']:,}; constant parameter count in {100 * d['h1_const']:.1f}%   (prediction: more than 80%)")
        print(f"    a pair changes parameter count in {100 * d['pair_chg']:.2f}% of pairs ({d['n_chg']:,} changes); a change is +-1 in {100 * d['step1']:.0f}%")
        print(f"H2  among changes, parameters were ADDED in {100 * d['h2_up']:.1f}%   (prediction: more than half, every repository)")
        print("H3  change rate by age since birth (born after the first snapshot): " + ", ".join(f"{k} {100 * v:.2f}% (n {d['h3_n'][k]:,})" for k, v in d["h3"].items()) + "   (prediction: highest early)")
        print("H4  median relative size change, edited pairs, by starting-size quartile: " + "; ".join(f"Q{i + 1} arg-change {a:.2f} vs other {b:.2f} (n {x}/{y})" for i, (a, b, x, y) in enumerate(d["h4"])) + "   (prediction: larger with a parameter change)")
        print("H4b (found after looking) same, pairs whose size changed only: " + "; ".join(f"Q{i + 1} {a:.2f} vs {b:.2f} (n {x}/{y})" for i, (a, b, x, y) in enumerate(d["h4b"])))
        print(f"H7  parameter count at birth against time, size controlled (partial Spearman): {d['h7'][0]:+.2f} over {d['h7'][1]:,} births   (prediction: positive)")
        link = fix_link(name, df, p, ct)
        if link is None:
            print("H5/6 no fix events for this repository")
            continue
        print("H5/6 files edited in an interval: risk ratio of a fix touching the file, parameter change vs not (Mantel-Haenszel over size x edits strata; 95% interval over intervals)")
        for (cls, when), t in sorted(link.items(), key=lambda kv: (kv[0][1] != "next", kv[0][0] != "any", kv[0])):
            rr, a1, n1, a0, n0 = mh_rr(t)
            lo, hi = boot(t) if (a1 + a0) >= 20 else (float("nan"), float("nan"))
            print(f"     {when:4s} {cls:12s} RR {rr:5.2f} [{lo:4.2f}, {hi:4.2f}]  with a parameter change {a1}/{n1} ({pc(a1, n1)}), without {a0}/{n0} ({pc(a0, n0)})")
            pooled_link[(cls, when)].append(t.assign(repo=name))
    if len(names) > 1:
        print("\n=== POOLED over repositories with fix events (strata within repository; intervals resampled together) ===")
        for (cls, when), ts in sorted(pooled_link.items(), key=lambda kv: (kv[0][1] != "next", kv[0][0] != "any", kv[0])):
            t = pd.concat([x.assign(s=x.s.astype(str) + x.repo) for x in ts])
            t["sz"] = t.sz.astype(str) + t.repo
            rr, a1, n1, a0, n0 = mh_rr(t)
            lo, hi = boot(t, 200) if (a1 + a0) >= 20 else (float("nan"), float("nan"))
            print(f"     {when:4s} {cls:12s} RR {rr:5.2f} [{lo:4.2f}, {hi:4.2f}]  with {a1}/{n1} ({pc(a1, n1)}), without {a0}/{n0} ({pc(a0, n0)})")


if __name__ == "__main__":
    main()
