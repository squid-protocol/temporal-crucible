#!/usr/bin/env python3
"""What is changing: identifiers shared between the cause and its repairs. Hypotheses WC1-WC5: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.

    python tools/sensor/what_changes.py linux dpdk mesa openssl        (needs blast/<repo>_v/repair_structure.pkl with the idents column, measure.pkl)"""
import collections
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import repair_structure as RS  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude/blast"
RELS = RS.RELS
DATA = ("field", "macro", "variable", "type")
rng = np.random.default_rng(2982)
DRAWS = 20


def cause_idents(repo, shas):
    out = subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "log", "--no-walk=unsorted", "--stdin", "-p", "-U0", "--no-color", "--format=@@COMMIT %H", "--", "*.c", "*.h"], input="\n".join(shas) + "\n", capture_output=True, text=True, errors="replace").stdout
    res, cur, lines = {}, None, collections.defaultdict(list)
    for l in out.splitlines():
        if l.startswith("@@COMMIT "):
            cur = l[9:].strip()
        elif cur and l[:1] in "+-" and not l.startswith(("+++", "---")):
            t = l[1:].strip()
            if t and not t.startswith(("*", "/*", "//")):
                lines[cur].append(t)
    for s in shas:
        res[s] = RS.idents(lines[s])
    return res


def load(repo):
    d = pd.read_pickle(f"{B}/{repo}_v/repair_structure.pkl")
    d = d[d.status == "ok"].copy()
    m = pd.read_pickle(f"{B}/{repo}_v/measure.pkl").set_index("pid")
    d["ind"] = d.pid.map(m.ind)
    d["lines"] = d.pid.map(m.lines) if "lines" in m else np.nan
    feats = pd.read_pickle(f"{B}/{repo}_v/diff_feats.pkl")
    d["lines"] = [feats[s]["n_add"] + feats[s]["n_rem"] for s in d.ind]
    ci = cause_idents(BR.POOL.rsplit("/", 0)[0] and repo, list(d.ind.unique()))
    d["cause"] = d.ind.map(ci)
    d["repo"] = repo
    # stopwords: names present in more than 1% of the pairs' diffs (cause or repair side)
    pairs = d.groupby("pid").agg(cause=("cause", "first")).cause
    rep = d.groupby("pid").idents.apply(lambda x: set(n for lst in x for n, _ in lst))
    cnt = collections.Counter()
    for pid in pairs.index:
        cnt.update({n for n, _ in pairs[pid]} | rep[pid])
    stop = {n for n, c in cnt.items() if c > 0.01 * len(pairs)}
    d["shared"] = [[(n, c) for n, c in r if n in {x for x, _ in cs} and n not in stop] for r, cs in zip(d.idents, d.cause)]
    d["has"] = d.shared.map(len) > 0
    d["band"] = np.where(d.lines < 20, 0, 1)
    # shuffled baseline: the same repair against the cause of a different pair of the same band
    cause_by = d.groupby("pid").agg(ind=("ind", "first"), band=("band", "first"), cause=("cause", "first"))
    exp = np.zeros(len(d))
    pools = {b: cause_by[cause_by.band == b] for b in (0, 1)}
    for i, (r, pid, ind, band) in enumerate(zip(d.idents, d.pid, d.ind, d.band)):
        pool = pools[band]
        k = 0
        names = {n for n, _ in r if n not in stop}
        for j in rng.integers(0, len(pool), DRAWS * 2):
            if pool.ind.iloc[j] == ind:
                continue
            k += bool(names & {n for n, _ in pool.cause.iloc[j] if n not in stop})
        exp[i] = k / max(sum(1 for _ in range(DRAWS)), 1)
    d["exp"] = np.minimum(exp, 1.0)
    # area-matched baseline (post hoc): causes of other pairs whose repairs landed in the same directory (the area's own vocabulary)
    d["dir"] = d.path.map(lambda p: p.rsplit("/", 1)[0] if "/" in p else "")
    by_dir = collections.defaultdict(dict)
    for ind, dr, cs in zip(d.ind, d["dir"], d.cause):
        by_dir[dr].setdefault(ind, {n for n, _ in cs if n not in stop})
    exp2 = np.full(len(d), np.nan)
    for i, (r, ind, dr) in enumerate(zip(d.idents, d.ind, d["dir"])):
        cand = [v for k, v in by_dir[dr].items() if k != ind]
        if len(cand) < 5:
            continue
        names = {n for n, _ in r if n not in stop}
        pick = rng.integers(0, len(cand), DRAWS)
        exp2[i] = sum(bool(names & cand[j]) for j in pick) / DRAWS
    d["exp2"] = exp2
    return d


def ratio(x, col="exp"):
    x = x.dropna(subset=[col])
    o, e = x.has.to_numpy(float), x[col].to_numpy(float)
    if len(x) < 30 or e.sum() <= 0:
        return None
    w = rng.multinomial(len(o), np.ones(len(o)) / len(o), size=500)
    v = (w @ o) / np.maximum(w @ e, 1e-9)
    return o.sum() / e.sum(), np.percentile(v, 2.5), np.percentile(v, 97.5), o.mean(), e.mean(), len(x)


def fmt(r):
    return "n/a" if r is None else f"{100 * r[3]:5.1f}% vs {100 * r[4]:4.1f}%  ratio {r[0]:5.2f} [{r[1]:.2f},{r[2]:.2f}] (n {r[5]})"


def classes(x):
    c = collections.Counter(cls for lst in x.shared for _, cls in lst)
    n = sum(c.values())
    return c, n


def main():
    repos = sys.argv[1:]
    frames = {r: load(r) for r in repos}
    pooled = pd.concat(frames.values(), ignore_index=True)
    frames["pooled"] = pooled
    ordering, ver = {}, {}
    for r, d in frames.items():
        print(f"\n########## {r}: {len(d)} records ({d.pid.nunique()} pairs, causes under 100 lines, verified functions) ##########")
        print("  share of repairs with a shared identifier against the shuffled baseline, by relation to the cause:")
        shares = {}
        for rel in RELS:
            x = d[d.rel == rel]
            shares[rel] = ratio(x)
            print(f"    {rel:20s} {fmt(shares[rel])}")
        print("  the same, against the AREA-MATCHED baseline (other pairs' causes whose repairs landed in the same directory; post hoc):")
        for rel in RELS:
            print(f"    {rel:20s} {fmt(ratio(d[d.rel == rel], 'exp2'))}")
        print("  shared identifiers by class (share of shared tokens), by relation:")
        for rel in RELS:
            c, n = classes(d[d.rel == rel])
            if n:
                print(f"    {rel:20s} n {n:5d}  " + "  ".join(f"{k} {100 * c[k] / n:4.1f}%" for k in ("callee", "field", "macro", "variable", "type")))
        ordering[r] = shares
    print("\n=== VERDICTS ===")
    p = ordering["pooled"]
    rat = {rel: (p[rel][0] if p[rel] else None) for rel in RELS}
    print("  WC1 pooled ratio against the baseline, per relation: " + ", ".join(f"{k} {v:.2f}" if v else f"{k} n/a" for k, v in rat.items()) + f" (needs 2 in each): {'supported' if all(v and v >= 2 for v in rat.values()) else 'not supported'}")
    ok = 0
    for r in repos:
        s = {k: (v[3] if v else None) for k, v in ordering[r].items()}
        if None in (s["same"], s["caller"], s["callee"], s["same file, farther"], s["elsewhere"]):
            print(f"  WC2 {r}: not testable")
            continue
        mid = (s["caller"] + s["callee"]) / 2
        good = s["same"] > mid > s["same file, farther"] > s["elsewhere"]
        ok += good
        print(f"  WC2 {r}: same {100 * s['same']:.0f}%, caller/callee {100 * mid:.0f}%, same file farther {100 * s['same file, farther']:.0f}%, elsewhere {100 * s['elsewhere']:.0f}%: {'ordered' if good else 'not ordered'}")
    print(f"  WC2 ordered in {ok} of {len(repos)} repositories (needs 3 of 4): {'supported' if ok >= 3 else 'not supported'}")
    far = pooled[pooled.rel.isin(["callee", "two calls away", "same file, farther", "elsewhere"])]
    c, n = classes(far)
    data = sum(c[k] for k in DATA) / n
    print(f"  WC3 data share (field, macro, variable, type) among shared identifiers outside the same function and the callers: {100 * data:.0f}% (needs 60%): {'supported' if data >= 0.6 else 'not supported'}")
    c, n = classes(pooled[pooled.rel == "elsewhere"])
    fm = (c["field"] + c["macro"]) / n
    print(f"  WC4 'elsewhere' shared identifiers that are fields or macros: {100 * fm:.0f}% (needs 50%): {'supported' if fm >= 0.5 else 'not supported'}")
    r = p["elsewhere"]
    print(f"  surprise bar: 'elsewhere' observed within 1.3 times the baseline: {'MET' if r and r[0] <= 1.3 else 'not met'} (ratio {r[0]:.2f})" if r else "")
    print("  area-matched baseline, pooled: " + ", ".join(f"{rel} {r[0]:.2f}" for rel in RELS for r in [ratio(pooled[pooled.rel == rel], 'exp2')] if r))
    print("\n  by edit type (pooled): share of repairs with a shared identifier, against the baseline:")
    for lab in pooled.label.value_counts().index[:9]:
        print(f"    {lab:34s} {fmt(ratio(pooled[pooled.label == lab]))}")
    pooled.drop(columns=["cause", "idents", "shared"]).to_pickle(f"{B}/what_changes.pkl")


if __name__ == "__main__":
    main()
