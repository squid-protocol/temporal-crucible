#!/usr/bin/env python3
"""Blast radius, forward design: are fixes found near the functions changed in an earlier quarter, by fix type and for sweep against organic changes?
Hypotheses V1-V6: docs/sensor-overhaul/sensors/ripple_radius.md ("Validation design"), fixed before this was computed.

    python tools/sensor/ripple_forward.py REPO [REPO ...]       (pickles from args_life_build.py with keys; edit events ts_edits_*; fix events *_xc2.json)

Changed set of interval i: functions with a code edit in the tree-sitter edit events, split into sweep edits (the event is in a sweep or migration found by
tools/turn/sweeps.py) and organic edits. Fix commit in interval i+L (class from the v3c events). A fixed function outside every changed function of interval i is
asked whether it lies within h calls of the changed set, against the exact expectation for random file-mates (and for random functions of the same size)."""
import collections
import json
import pickle
import re
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/turn")
import sweeps as S  # noqa: E402

SP = "/tmp/gitgalaxy-scratch/claude/argl"
EV = "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/turn/events"
A = "/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2/analysis"
B = "/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"
POOL = "/srv/storage_16tb/projects/temporal-crucible-pool"
SRC = {"curl": "ts_edits_c2.pkl", "libgit2": "ts_edits_c2.pkl", "redis": "ts_edits_c2.pkl", "libxml2": "ts_edits_ho_c.pkl", "prometheus": "ts_edits_ho_jg.pkl", "sphinx": "ts_edits_ho_py.pkl", "ripgrep": "ts_edits_lang.pkl"}
LANG = {"curl": "c", "libgit2": "c", "redis": "c", "libxml2": "c", "prometheus": "go", "sphinx": "python", "ripgrep": "rust"}
EXTS = {"c": (".c", ".h"), "go": (".go",), "python": (".py",), "rust": (".rs",), "fortran": (".f", ".F", ".f90", ".F90", ".f95", ".F95", ".for", ".FOR")}
CLASSES = ("regression", "other-fix", "extrinsic", "latent")
ATTRS = f"{SP}/attrs"
open(ATTRS, "w").write("*.go diff=golang\n*.py diff=python\n*.rs diff=rust\n" + "".join(f"*{e} diff=fortran\n" for e in EXTS["fortran"]))
HUNK = re.compile(r"^@@ -\S+ \+\S+ @@ ?(.*)$")
IDENT = re.compile(r"([A-Za-z_]\w*)\s*$")
RELS = ("callers1", "callers2", "callees1", "callees2", "either1", "either2")
LAGS = (0, 1, 2, 3)


def func_name(ctx, lang):
    if lang == "c":
        i = ctx.find("(")
        m = IDENT.search(ctx[:i]) if i > 0 else None
        return m.group(1) if m else None
    if lang == "go":
        m = re.match(r"^func\s*(?:\([^)]*\)\s*)?(\w+)", ctx)
    elif lang == "python":
        m = re.search(r"\bdef\s+(\w+)", ctx)
    elif lang == "fortran":
        m = re.search(r"\b(?:subroutine|function|program|module)\s+(\w+)", ctx, re.I)
    else:
        m = re.search(r"\bfn\s+(\w+)", ctx)
    return m.group(1) if m else None


def fix_hunks(repo, shas, lang):
    want, out = set(shas), {}
    cmd = ["git", "-c", f"core.attributesFile={ATTRS}", "-C", repo, "log", "--no-merges", "-p", "-U0", "--no-color", "-M", "--format=@@COMMIT %H"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, errors="replace")
    sha, cur = None, None
    for line in proc.stdout:
        if line.startswith("@@COMMIT "):
            sha, cur = line[9:].strip(), None
            if sha in want:
                out[sha] = set()
        elif sha in out:
            if line.startswith("+++ b/"):
                cur = line[6:].rstrip("\n")
                if not cur.endswith(EXTS[lang]):
                    cur = None
            elif cur and line.startswith("@@"):
                m = HUNK.match(line.rstrip("\n"))
                n = func_name(m.group(1), lang) if m else None
                if n:
                    out[sha].add((cur, n))
    return out


class Graph:
    """Call graph of one snapshot over functions whose (path, name) is unique in their file."""

    def __init__(self, db):
        import sqlite3

        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        files = {r[0]: r[1] for r in con.execute("SELECT id, file_path FROM file_data")}
        rows = [(fid, files[ff], nm, int(lo or 0)) for fid, ff, nm, lo in con.execute("SELECT id, file_id, func_name, loc FROM function_data") if ff in files]
        cnt = collections.Counter((p, n) for _, p, n, _ in rows)
        key = {fid: (p, n) for fid, p, n, _ in rows if cnt[(p, n)] == 1}
        self.loc = {(p, n): lo for fid, p, n, lo in rows if cnt[(p, n)] == 1}
        self.fwd, self.rev = collections.defaultdict(set), collections.defaultdict(set)
        for s, d in con.execute("SELECT src_func_id, dst_func_id FROM fcall_data WHERE kind = 'call' AND dst_func_id IS NOT NULL AND COALESCE(candidates, 1) <= 1"):
            if s in key and d in key and key[s] != key[d]:
                self.fwd[key[s]].add(key[d])
                self.rev[key[d]].add(key[s])
        con.close()
        self.nodes = set(self.loc)
        sizes = np.array(sorted(self.loc.values()))
        cuts = np.percentile(sizes, np.arange(10, 100, 10)) if len(sizes) else []
        self.dec = {k: int(np.searchsorted(cuts, v)) for k, v in self.loc.items()}
        self.by_file = collections.defaultdict(list)
        self.by_dec = collections.defaultdict(set)
        for k in self.nodes:
            self.by_file[k[0]].append(k)
            self.by_dec[self.dec[k]].add(k)

    @staticmethod
    def hops(start, adj, h):
        seen, frontier, acc, out = set(start), set(start), set(), []
        for _ in range(h):
            nxt = set()
            for n in frontier:
                nxt |= adj.get(n, set())
            nxt -= seen
            seen |= nxt
            acc |= nxt
            out.append(set(acc))
            frontier = nxt
        return out

    def near(self, start):
        cal, cae = self.hops(start, self.rev, 2), self.hops(start, self.fwd, 2)
        return {"callers1": cal[0], "callers2": cal[1], "callees1": cae[0], "callees2": cae[1], "either1": cal[0] | cae[0], "either2": cal[1] | cae[1]}


def edit_sets(name, keys, rows_by_id):
    evs = pickle.load(open(f"{A}/{SRC[name]}", "rb"))[name]["events"]
    _, _, ins = S.detect(evs)
    org, sw, sg = collections.defaultdict(set), collections.defaultdict(set), collections.defaultdict(set)
    for i, e in enumerate(evs):
        if not e["code"]:
            continue
        s = e["s"]
        if "x" in e:
            k = tuple(keys[s][e["x"]]) if s < len(keys) and e["x"] < len(keys[s]) else None
        else:
            k = rows_by_id.get((s, e["id"]))
        if k is None:
            continue
        (sw if i in ins else org)[s].add(k)
        if e.get("sig"):
            sg[s].add(k)
    return org, sw, sg


def run(name, fixcache):
    lang = LANG[name]
    d = pickle.load(open(f"{SP}/{name}.pkl", "rb"))
    ct = np.array(d["ct"])
    n = len(ct)
    rows_by_id = {(r[0], r[1]): (r[4], r[5]) for r in d["rows"]}
    org, sw, sg = edit_sets(name, d["keys"], rows_by_id)
    sn = json.load(open(f"{B}/scan_{name}/snapshots.json"))
    ev = [e for e in json.load(open(f"{EV}/{name}_xc2.json"))["events"] if e["class"] in CLASSES]
    hunks = fix_hunks(f"{POOL}/{name}", [e["sha"] for e in ev], lang)
    graphs = {}

    def G(s):
        if s not in graphs:
            graphs[s] = Graph(sn[s]["db"])
        return graphs[s]

    prep = {}

    def prepare(i):
        """Per interval i: graph at snapshot i+1, changed sets restricted to its nodes, near-sets for each, pools of non-changed nodes."""
        if i in prep:
            return prep[i]
        g = G(i + 1)
        co, cs = org.get(i, set()) & g.nodes, (sw.get(i, set()) - org.get(i, set())) & g.nodes
        call = co | cs
        info = {"g": g, "call": call, "sets": {"organic": co, "sweep": cs, "signature": sg.get(i, set()) & g.nodes}, "near": {}, "pool": {dd: v - call for dd, v in g.by_dec.items()}}
        for X, st in info["sets"].items():
            if st:
                info["near"][X] = g.near(st)
        prep[i] = info
        return info

    units = []
    recur = collections.Counter()
    for e in ev:
        j = int(np.searchsorted(ct, e["ct"], side="left")) - 1
        if not (0 <= j < n - 1) or e["sha"] not in hunks:
            continue
        for L in LAGS:
            i = j - L
            if i < 0 or i + 1 >= n:
                continue
            P = prepare(i)
            g = P["g"]
            Fn = hunks[e["sha"]] & g.nodes
            if not Fn:
                continue
            Fo = Fn - P["call"]
            recur[(e["class"], L, "fix in a changed function")] += int(bool(Fn & P["call"]))
            recur[(e["class"], L, "units")] += 1
            if not Fo:
                continue
            for X, near in P["near"].items():
                for rel in RELS:
                    nr = near[rel]
                    pa, pb, ok_b = [], [], True
                    for f in Fo:
                        pool = P["pool"].get(g.dec[f], set())
                        if pool:
                            pa.append(len(nr & pool) / len(pool))
                        mates = [m for m in g.by_file[f[0]] if m != f and m not in P["call"] and abs(g.dec[m] - g.dec[f]) <= 1]
                        if mates:
                            pb.append(sum(1 for m in mates if m in nr) / len(mates))
                    eA = 1 - float(np.prod([1 - x for x in pa])) if pa else np.nan
                    eB = 1 - float(np.prod([1 - x for x in pb])) if pb and len(pb) == len(Fo) else np.nan
                    units.append((name, e["class"], L, X, rel, e["sha"], float(bool(Fo & nr)), eA, eB))
    df = pd.DataFrame(units, columns=["repo", "cls", "lag", "X", "rel", "sha", "obs", "eA", "eB"])
    sizes = {X: np.mean([len(prepare(i)["sets"][X]) for i in range(n - 2)]) for X in ("organic", "sweep", "signature")}
    return df, recur, sizes


def ratio(sub, col="eB", B=300, rng=np.random.default_rng(2982)):
    s = sub.dropna(subset=[col])
    if len(s) < 30 or s[col].sum() <= 0:
        return None
    g = s.groupby("sha").agg(o=("obs", "sum"), e=(col, "sum"))
    o, e = g.o.values, g.e.values
    est = o.sum() / e.sum()
    vals = []
    for _ in range(B):
        w = rng.integers(0, len(o), len(o))
        ee = e[w].sum()
        if ee > 0:
            vals.append(o[w].sum() / ee)
    return est, float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)), len(s), float(s.obs.mean()), float(s[col].mean())


def fmt(r):
    return "      n/a" if r is None else f"{r[0]:5.2f} [{r[1]:4.2f},{r[2]:4.2f}] (n {r[3]}, {100 * r[4]:.0f}% vs {100 * r[5]:.0f}%)"


def main():
    names = sys.argv[1:]
    parts = []
    for nm in names:
        df, recur, sizes = run(nm, None)
        parts.append(df)
        print(f"\n{nm}: {len(df):,} (fix commit, lag, change type, relation) units; changed functions per quarter: organic {sizes['organic']:.0f}, sweep {sizes['sweep']:.0f}, signature edits {sizes['signature']:.0f}", flush=True)
        for c in CLASSES:
            u = recur.get((c, 1, "units"), 0)
            if u:
                print(f"   {c:10s} fix commits with a function matched a quarter after a change: {u}; of them the fixed function was itself changed that quarter in {100 * recur[(c, 1, 'fix in a changed function')] / u:.0f}%")
    D = pd.concat(parts, ignore_index=True)
    pooled = D
    print("\n==== V1/V3. ONE QUARTER LATER (lag 1), WITHIN 1 CALL (either direction), ORGANIC CHANGES: observed / expected from file-mates ====")
    print(f"{'repo':12s} " + " ".join(f"{c:>38s}" for c in ("all fix types",) + CLASSES))
    for nm in names + ["POOLED"]:
        sub = pooled if nm == "POOLED" else pooled[pooled.repo == nm]
        row = [f"{nm:12s}"]
        for c in ("all",) + CLASSES:
            q = sub[(sub.lag == 1) & (sub.X == "organic") & (sub.rel == "either1")]
            q = q if c == "all" else q[q.cls == c]
            row.append(f"{fmt(ratio(q)):>38s}")
        print(" ".join(row))
    print("\n==== V2. SWEEP AGAINST ORGANIC CHANGES (lag 1, within 1 call either direction), pooled and per repository ====")
    for nm in names + ["POOLED"]:
        sub = pooled if nm == "POOLED" else pooled[pooled.repo == nm]
        q = sub[(sub.lag == 1) & (sub.rel == "either1")]
        print(f"  {nm:12s} organic {fmt(ratio(q[q.X == 'organic']))}    sweep {fmt(ratio(q[q.X == 'sweep']))}")
    print("\n==== V2 by fix type (pooled, lag 1, within 1 call) ====")
    for c in CLASSES:
        q = pooled[(pooled.lag == 1) & (pooled.rel == "either1") & (pooled.cls == c)]
        print(f"  {c:10s} organic {fmt(ratio(q[q.X == 'organic']))}    sweep {fmt(ratio(q[q.X == 'sweep']))}")
    print("\n==== V4. TIME: ratio by lag (pooled, within 1 call, organic) ====")
    for c in ("all",) + CLASSES:
        row = [f"  {c:10s}"]
        for L in LAGS:
            q = pooled[(pooled.lag == L) & (pooled.X == "organic") & (pooled.rel == "either1")]
            q = q if c == "all" else q[q.cls == c]
            row.append(f"lag {L}: {fmt(ratio(q)):>40s}")
        print(" ".join(row))
    print("\n==== V5/V6. SPACE AND DIRECTION (pooled, lag 1, organic): ratio vs file-mates ====")
    for c in ("all",) + CLASSES[:2]:
        for rel in RELS:
            q = pooled[(pooled.lag == 1) & (pooled.X == "organic") & (pooled.rel == rel)]
            q = q if c == "all" else q[q.cls == c]
            print(f"  {c:10s} {rel:9s} {fmt(ratio(q))}    vs same-size random: {fmt(ratio(q, 'eA'))}")
    print("\n==== ADDED AFTER LOOKING: SIGNATURE-CHANGING EDITS ONLY (a much smaller changed set), lag 1: ratio vs file-mates ====")
    for nm in names + ["POOLED"]:
        sub = pooled if nm == "POOLED" else pooled[pooled.repo == nm]
        q = sub[(sub.lag == 1) & (sub.X == "signature")]
        print(f"  {nm:12s} " + "   ".join(f"{rel} {fmt(ratio(q[q.rel == rel]))}" for rel in ("callers1", "callees1", "either1")))
    for c in CLASSES:
        q = pooled[(pooled.lag == 1) & (pooled.X == "signature") & (pooled.cls == c)]
        print(f"  pooled {c:10s} " + "   ".join(f"{rel} {fmt(ratio(q[q.rel == rel]))}" for rel in ("callers1", "callees1")))
    pickle.dump(D, open(f"{SP}/ripple_forward_units.pkl", "wb"))


if __name__ == "__main__":
    main()
