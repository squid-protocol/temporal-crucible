#!/usr/bin/env python3
"""Blast radius, per-commit design: pair each fix with the individual commits of the 45 days before it, and ask whether the fixed function is near that
commit's changed functions in the call graph, by lag in days. The tightened version of ripple_forward.py (whose changed set is a whole quarter, so about 40% of
random file-mates are already near it). Design and hypotheses: docs/sensor-overhaul/sensors/ripple_radius.md ("Per-commit design").

    python tools/sensor/ripple_commits.py REPO [REPO ...]

Per fix commit F (class from the v3c events) and each sampled earlier commit c (up to 6 per lag bucket: <1, 1-3, 3-7, 7-14, 14-30, 30-45 days; commits that touch more
than 40 functions left out as sweeps): graph of the first quarterly snapshot at or after c; the fixed functions outside c's changed set; observed = a fixed function
is within 1 call (callers, callees, either) or 2 calls (either) of the changed set; expected = random same-file functions of similar size outside the changed set, exact."""
import collections
import json
import pickle
import re
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import ripple_forward as RF  # noqa: E402

DAY = 86400
BUCKETS = [(0, 1), (1, 3), (3, 7), (7, 14), (14, 30), (30, 45)]
PER_BUCKET = 6
MAXFN = 40
RELS = ("callers1", "callees1", "either1", "either2")
rng = np.random.default_rng(2982)


def all_commits(repo, lang):
    """sha -> (ct, set of (path, function)) for every non-merge commit, from git hunk headers."""
    cmd = ["git", "-c", f"core.attributesFile={RF.ATTRS}", "-C", repo, "log", "--no-merges", "-p", "-U0", "--no-color", "-M", "--format=@@COMMIT %H %ct"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, errors="replace")
    out, sha, cur = {}, None, None
    for line in proc.stdout:
        if line.startswith("@@COMMIT "):
            _, h, t = line.split()
            sha, cur = h, None
            out[sha] = (int(t), set())
        elif sha:
            if line.startswith("+++ b/"):
                cur = line[6:].rstrip("\n")
                if not cur.endswith(RF.EXTS[lang]):
                    cur = None
            elif cur and line.startswith("@@"):
                m = RF.HUNK.match(line.rstrip("\n"))
                n = RF.func_name(m.group(1), lang) if m else None
                if n:
                    out[sha][1].add((cur, n))
    return out


def run(name):
    lang = RF.LANG[name]
    repo = f"{RF.POOL}/{name}"
    sn = json.load(open(f"{RF.B}/scan_{name}/snapshots.json"))
    d = pickle.load(open(f"{RF.SP}/{name}.pkl", "rb"))
    ct = np.array(d["ct"])
    commits = all_commits(repo, lang)
    ordered = sorted((t, h) for h, (t, fs) in commits.items() if fs and len(fs) <= MAXFN)
    times = np.array([t for t, _ in ordered])
    fixes = [e for e in json.load(open(f"{RF.EV}/{name}_xc2.json"))["events"] if e["class"] in RF.CLASSES and e["sha"] in commits and commits[e["sha"]][1]]
    graphs, near_cache = {}, {}

    def G(s):
        if s not in graphs:
            graphs[s] = RF.Graph(sn[s]["db"])
        return graphs[s]

    rows = []
    same = collections.Counter()
    for e in fixes:
        t = commits[e["sha"]][0]
        Ff = commits[e["sha"]][1]
        lo_i = int(np.searchsorted(times, t - 45 * DAY, side="left"))
        hi_i = int(np.searchsorted(times, t, side="left"))
        cand = [ordered[k] for k in range(lo_i, hi_i) if ordered[k][1] != e["sha"]]
        picks = []
        for b, (a, z) in enumerate(BUCKETS):
            pool = [c for c in cand if t - z * DAY <= c[0] < t - a * DAY]
            if len(pool) > PER_BUCKET:
                pool = [pool[k] for k in rng.choice(len(pool), PER_BUCKET, replace=False)]
            picks += [(b, c) for c in pool]
        for b, (tc, hc) in picks:
            s = int(np.searchsorted(ct, tc, side="left"))
            if s >= len(sn):
                continue
            g = G(s)
            C = commits[hc][1] & g.nodes
            Fn = Ff & g.nodes
            if not C or not Fn:
                continue
            same[(e["class"], b, "pairs")] += 1
            same[(e["class"], b, "same function")] += int(bool(Fn & C))
            Fo = Fn - C
            if not Fo:
                continue
            key = (hc, s)
            if key not in near_cache:
                near_cache[key] = g.near(C)
            near = near_cache[key]
            for rel in RELS:
                nr = near[rel]
                pb = []
                for f in Fo:
                    mates = [m for m in g.by_file[f[0]] if m != f and m not in C and abs(g.dec[m] - g.dec[f]) <= 1]
                    if mates:
                        pb.append(sum(1 for m in mates if m in nr) / len(mates))
                if len(pb) == len(Fo):
                    rows.append((name, e["class"], b, rel, e["sha"], float(bool(Fo & nr)), 1 - float(np.prod([1 - x for x in pb]))))
    df = pd.DataFrame(rows, columns=["repo", "cls", "bucket", "rel", "sha", "obs", "e"])
    return df, same, len(fixes)


def ratio(sub, B=300):
    if len(sub) < 40 or sub.e.sum() <= 0:
        return None
    g = sub.groupby("sha").agg(o=("obs", "sum"), e=("e", "sum"))
    o, e = g.o.values, g.e.values
    vals = []
    for _ in range(B):
        w = rng.integers(0, len(o), len(o))
        if e[w].sum() > 0:
            vals.append(o[w].sum() / e[w].sum())
    return o.sum() / e.sum(), float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)), len(sub), float(sub.obs.mean()), float(sub.e.mean())


def fmt(r):
    return "        n/a" if r is None else f"{r[0]:5.2f} [{r[1]:4.2f},{r[2]:4.2f}] ({100 * r[4]:.0f}% vs {100 * r[5]:.0f}%, n {r[3]})"


LABEL = [f"{a}-{z} d" for a, z in BUCKETS]


def main():
    names = sys.argv[1:]
    parts, same_all = [], collections.Counter()
    for nm in names:
        df, same, nfix = run(nm)
        parts.append(df)
        same_all.update(same)
        print(f"{nm}: {nfix} fix commits, {len(df):,} (fix, earlier commit, relation) rows", flush=True)
    D = pd.concat(parts, ignore_index=True)
    print("\n==== SAME FUNCTION: share of (fix, earlier commit) pairs where the fix touches a function the earlier commit touched, by days before the fix ====")
    for c in ("all",) + RF.CLASSES:
        row = []
        for b in range(len(BUCKETS)):
            pr = sum(v for (cl, bb, k), v in same_all.items() if k == "pairs" and bb == b and (c == "all" or cl == c))
            sf = sum(v for (cl, bb, k), v in same_all.items() if k == "same function" and bb == b and (c == "all" or cl == c))
            row.append(f"{LABEL[b]}: {100 * sf / pr:4.1f}% (n {pr})" if pr else f"{LABEL[b]}: n/a")
        print(f"  {c:10s} " + "   ".join(row))
    print("\n==== OBSERVED / EXPECTED FROM FILE-MATES, WITHIN 1 CALL (either direction), BY DAYS BEFORE THE FIX; pooled ====")
    for c in ("all",) + RF.CLASSES:
        row = []
        for b in range(len(BUCKETS)):
            q = D[(D.rel == "either1") & (D.bucket == b)]
            q = q if c == "all" else q[q.cls == c]
            row.append(f"{LABEL[b]}: {fmt(ratio(q))}")
        print(f"  {c:10s}\n    " + "\n    ".join(row))
    print("\n==== DIRECTION AND RADIUS (pooled, all fix types), by days before the fix ====")
    for rel in RELS:
        print(f"  {rel}: " + "   ".join(f"{LABEL[b]} {fmt(ratio(D[(D.rel == rel) & (D.bucket == b)]))}" for b in (0, 2, 4)))
    print("\n==== PER REPOSITORY, within 1 call, fixes within 7 days of an earlier commit (buckets 0-7 d) ====")
    for nm in names:
        q = D[(D.repo == nm) & (D.rel == "either1") & (D.bucket <= 2)]
        late = D[(D.repo == nm) & (D.rel == "either1") & (D.bucket >= 4)]
        print(f"  {nm:12s} within 7 d {fmt(ratio(q))}    14-45 d {fmt(ratio(late))}")
    pickle.dump(D, open(f"{RF.SP}/ripple_commits_rows.pkl", "wb"))


if __name__ == "__main__":
    main()
