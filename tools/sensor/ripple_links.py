#!/usr/bin/env python3
"""Blast radius of a change: where do the fixes for it land? Design and hypotheses R1-R6: docs/sensor-overhaul/sensors/ripple_radius.md (fixed before any distance was computed).

    python tools/sensor/ripple_links.py REPO [REPO ...]       (C repositories; regression fixes that name their inducing commit)

For each (inducing commit, fix commit) pair: the functions each touched (git hunk-header context), the call graph of the first quarterly snapshot at or after
the inducing commit, and the relation of the fixed functions to the changed ones: same function, same file, caller within k hops, callee within k hops.
Compared with a repo-wide null (random functions of the same size decile) and a same-file null (random file-mates of each fixed function)."""
import collections
import json
import re
import sqlite3
import subprocess
import sys

import numpy as np

EV = "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/turn/events"
B = "/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"
POOL = "/srv/storage_16tb/projects/temporal-crucible-pool"
HUNK = re.compile(r"^@@ -\S+ \+\S+ @@ ?(.*)$")
IDENT = re.compile(r"([A-Za-z_]\w*)\s*$")
K = (1, 2, 3)
M = 200
rng = np.random.default_rng(2982)


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, errors="replace").stdout


def func_name(ctx):
    i = ctx.find("(")
    if i <= 0:
        return None
    m = IDENT.search(ctx[:i])
    return m.group(1) if m else None


def touched(repo, sha):
    out = set()
    cur = None
    for line in git(repo, "show", "-U0", "--no-color", "-M", "--format=", sha).splitlines():
        if line.startswith("+++ b/"):
            cur = line[6:]
            if not cur.endswith((".c", ".h")):
                cur = None
        elif cur and line.startswith("@@"):
            m = HUNK.match(line)
            n = func_name(m.group(1)) if m else None
            if n:
                out.add((cur, n))
    return out


_graphs = {}


def graph(db):
    if db in _graphs:
        return _graphs[db]
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    files = {r[0]: r[1] for r in con.execute("SELECT id, file_path FROM file_data")}
    key, loc, args = {}, {}, {}
    for fid, ffile, name, lo, ar in con.execute("SELECT id, file_id, func_name, loc, args FROM function_data"):
        if ffile in files:
            k = (files[ffile], name)
            key[fid] = k
            loc[k] = max(loc.get(k, 0), int(lo or 0))
            args[k] = int(ar or 0)
    fwd, rev = collections.defaultdict(set), collections.defaultdict(set)
    for s, d in con.execute("SELECT src_func_id, dst_func_id FROM fcall_data WHERE kind = 'call' AND dst_func_id IS NOT NULL AND COALESCE(candidates, 1) <= 1"):
        if s in key and d in key and key[s] != key[d]:
            fwd[key[s]].add(key[d])
            rev[key[d]].add(key[s])
    con.close()
    nodes = sorted(loc)
    by_file = collections.defaultdict(list)
    for k in nodes:
        by_file[k[0]].append(k)
    sizes = np.array([loc[k] for k in nodes])
    dec = {k: int(np.searchsorted(np.percentile(sizes, np.arange(10, 100, 10)), loc[k])) for k in nodes}
    by_dec = collections.defaultdict(list)
    for k in nodes:
        by_dec[dec[k]].append(k)
    _graphs[db] = (nodes, loc, args, fwd, rev, by_file, dec, by_dec)
    return _graphs[db]


def bfs(start, adj, kmax):
    seen = set(start)
    layers = []
    frontier = set(start)
    for _ in range(kmax):
        nxt = set()
        for n in frontier:
            nxt |= adj.get(n, set())
        nxt -= seen
        seen |= nxt
        layers.append(set(nxt))
        frontier = nxt
    out = []
    acc = set()
    for layer in layers:
        acc |= layer
        out.append(set(acc))
    return out  # out[k-1] = nodes within k hops (excluding the start set)


def indicators(F, I, callers, callees):
    """Relation of the fixed set F to the changed set I; call relations over fixed functions not in I."""
    Fo = F - I
    r = {"same_func": bool(F & I), "same_file": bool({f for f, _ in F} & {f for f, _ in I})}
    for k in K:
        r[f"callers{k}"] = bool(Fo & callers[k - 1])
        r[f"callees{k}"] = bool(Fo & callees[k - 1])
        r[f"either{k}"] = r[f"callers{k}"] or r[f"callees{k}"]
    return r


def links(name):
    repo = f"{POOL}/{name}"
    ev = [e for e in json.load(open(f"{EV}/{name}_xc2.json"))["events"] if e["class"] == "regression"]
    out = []
    for e in ev:
        m = re.search(r"references ([0-9a-f]{7,40}) \((\d+) d earlier\)", e.get("why", ""))
        if not m or e.get("subject", "").lower().startswith("revert"):
            continue
        full = git(repo, "rev-parse", "--verify", "-q", m.group(1) + "^{commit}").strip()
        if not full or full == e["sha"]:
            continue
        ict = int(git(repo, "show", "-s", "--format=%ct", full).strip() or 0)
        out.append({"fix": e["sha"], "ind": full, "fix_ct": e["ct"], "ind_ct": ict, "lag": (e["ct"] - ict) / 86400})
    return out


def analyse(name):
    repo = f"{POOL}/{name}"
    sn = json.load(open(f"{B}/scan_{name}/snapshots.json"))
    cts = np.array([int(git(repo, "show", "-s", "--format=%ct", x["commit"]).strip()) for x in sn])
    L = links(name)
    res = []
    stats = collections.Counter()
    for lk in L:
        s = int(np.searchsorted(cts, lk["ind_ct"], side="left"))
        if s >= len(sn):
            stats["no snapshot"] += 1
            continue
        I, F = touched(repo, lk["ind"]), touched(repo, lk["fix"])
        if not I or not F:
            stats["no function in a commit"] += 1
            continue
        if len(I) > 60 or len(F) > 30:
            stats["sweep (too many functions)"] += 1
            continue
        nodes, loc, args, fwd, rev, by_file, dec, by_dec = graph(sn[s]["db"])
        Im, Fm = I & set(nodes), F & set(nodes)
        if not Im or not Fm:
            stats["not found in the snapshot"] += 1
            continue
        callers = bfs(Im, rev, max(K))
        callees = bfs(Im, fwd, max(K))
        same_func = bool(Fm & Im)
        Fo = Fm - Im  # fixed functions outside the changed set: the only ones a ripple can be read from
        obs = indicators(Fo, Im, callers, callees) if Fo else None
        nullA, nullB, okB = collections.defaultdict(float), collections.defaultdict(float), True
        if Fo:
            for _ in range(M):
                FA, FB = set(), set()
                for f in Fo:
                    pool = [g for g in by_dec[dec[f]] if g not in Im]
                    if pool:
                        FA.add(pool[rng.integers(len(pool))])
                    mates = [g for g in by_file[f[0]] if g != f and g not in Im and abs(dec[g] - dec[f]) <= 1]
                    if mates:
                        FB.add(mates[rng.integers(len(mates))])
                if not FB:
                    okB = False
                for FF, acc in ((FA, nullA), (FB, nullB)):
                    if FF:
                        for k, v in indicators(FF, set(), callers, callees).items():
                            acc[k] += v / M
                        # same-file relation with the changed functions, and callers/callees (the changed set is excluded from the draws)
                        for k, v in indicators(FF, Im, callers, callees).items():
                            if k == "same_file":
                                acc[k] += 0  # computed below
                    for k in ("same_file",):
                        acc[k] += (1.0 / M) if (FF and {f for f, _ in FF} & {f for f, _ in Im}) else 0.0
            if not okB:
                stats["no file-mates"] += 1
        sig = False
        if s >= 1:
            _, _, args0, *_ = graph(sn[s - 1]["db"])
            sig = any(k in args0 and k in args and args0[k] != args[k] for k in Im)
        res.append({"fix": lk["fix"], "ind": lk["ind"], "Im": Im, "Fm": Fm, "Fo": Fo, "graph": (nodes, loc, args, fwd, rev, by_file, dec, by_dec), "lag": lk["lag"], "same_func": same_func, "obs": obs, "A": dict(nullA) if obs else None, "B": dict(nullB) if (obs and okB) else None, "sig": sig, "nI": len(Im), "nF": len(Fm), "nFo": len(Fo)})
    return res, stats, len(L)


def summarise(res_all, label):
    print(f"  {label}: {len(res_all)} links; fixed function also changed by the inducing commit in {100 * np.mean([r['same_func'] for r in res_all]) if res_all else float('nan'):.0f}%; fix touches a function outside the changed set in {sum(1 for r in res_all if r['obs'])} ({100 * np.mean([bool(r['obs']) for r in res_all]) if res_all else float('nan'):.0f}%)")
    res = [r for r in res_all if r["obs"]]
    if len(res) < 15:
        print("    too few links with a fixed function outside the changed set")
        return
    keys = ["same_file"] + [f"{d}{k}" for k in K for d in ("callers", "callees", "either")]
    print(f"    {'relation':12s} {'observed':>9s} {'repo null':>10s} {'ratio':>6s} {'[95%]':>14s}   {'file-mate null':>14s} {'ratio':>6s} {'[95%]':>14s}")
    for k in keys:
        o = np.array([r["obs"][k] for r in res], float)
        a = np.array([r["A"][k] for r in res], float)
        rb = [r for r in res if r["B"] is not None]
        ob = np.array([r["obs"][k] for r in rb], float)
        b = np.array([r["B"][k] for r in rb], float)

        def boot(x, y):
            vals = []
            for _ in range(300):
                i = rng.integers(0, len(x), len(x))
                if y[i].mean() > 0:
                    vals.append(x[i].mean() / y[i].mean())
            return (np.percentile(vals, 2.5), np.percentile(vals, 97.5)) if len(vals) > 50 else (np.nan, np.nan)

        ra = o.mean() / a.mean() if a.mean() > 0 else np.nan
        rbv = ob.mean() / b.mean() if len(rb) and b.mean() > 0 else np.nan
        lo, hi = boot(o, a)
        lo2, hi2 = boot(ob, b) if len(rb) > 20 else (np.nan, np.nan)
        print(f"    {k:12s} {100 * o.mean():8.1f}% {100 * a.mean():9.1f}% {ra:6.2f} [{lo:5.2f},{hi:5.2f}]   {100 * b.mean() if len(rb) else float('nan'):13.1f}% {rbv:6.2f} [{lo2:5.2f},{hi2:5.2f}]")


def main():
    for name in sys.argv[1:]:
        res, stats, n = analyse(name)
        print(f"\n=== {name}: {n} regression fixes naming their inducing commit (reverts out); usable pairs {len(res)}; dropped: {dict(stats)} ===")
        summarise(res, "all pairs")
        summarise([r for r in res if r["lag"] < 2], "fix within 2 days of the change")
        summarise([r for r in res if r["lag"] >= 2], "fix 2 or more days later")
        diff_file = [r for r in res if r["obs"] and not r["obs"]["same_file"]]
        summarise(diff_file, "fix in a different file from every changed function")
        summarise([r for r in res if r["sig"]], "inducing change altered a parameter count")
        summarise([r for r in res if not r["sig"]], "inducing change did not alter a parameter count")


if __name__ == "__main__":
    main()
