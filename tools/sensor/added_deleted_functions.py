#!/usr/bin/env python3
"""Do repairs follow functions that are added or deleted? Hypotheses AD1-AD3, DL1-DL3: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.

    python tools/sensor/added_deleted_functions.py dpdk mesa      (needs links_<repo>.json, blast/<repo>/touched_all.pkl and snapshot_cts.npy, the quarterly scans)"""
import collections
import json
import pickle
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from tree_sitter_language_pack import get_parser

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import repair_structure as RS  # noqa: E402
import verify_functions as VF  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
LINKS = {"dpdk": f"{B}/argl/links_dpdk.json", "mesa": f"{B}/argl/links_mesa.json"}
GROUPS = ["ADD", "NEWFILE", "DEL", "DELFILE"]
rng = np.random.default_rng(2982)
_P = None


def all_funcs(src):
    """{name: token set of the function} for every function definition (first definition of a name wins)."""
    global _P
    if _P is None:
        _P = get_parser("c")
    tree = _P.parse(src)
    out = {}
    stack = [tree.root_node]
    while stack:
        n = stack.pop()
        if n.type == "function_definition":
            nm = RS.func_name(n, src)
            if nm and nm not in out:
                out[nm] = frozenset(re.findall(rb"\w+", src[n.start_byte:n.end_byte]))
            continue
        stack.extend(n.children)
    return out


def event_worker(job):
    repo, shas = job
    res = []
    for sha in shas:
        st = subprocess.run(["git", "-C", repo, "diff-tree", "-r", "-M", "--no-commit-id", "--name-status", sha], capture_output=True, text=True, errors="replace").stdout.splitlines()
        files = []
        for l in st:
            p = l.split("\t")
            if len(p) >= 2 and p[-1].endswith((".c", ".h")):
                files.append((p[0][0], p[1], p[-1]))
        if not files or len(files) > 60:
            res.append((sha, None if files else [], len(files)))
            continue
        added, deleted = [], []
        for status, old, new in files:
            try:
                if status == "A":
                    src = VF.get(repo, f"{sha}:{new}")
                    for n, t in (all_funcs(src) if src else {}).items():
                        added.append(("NEWFILE", new, n, t))
                elif status == "D":
                    src = VF.get(repo, f"{sha}^:{old}")
                    for n, t in (all_funcs(src) if src else {}).items():
                        deleted.append(("DELFILE", old, n, t))
                else:
                    a, b = VF.get(repo, f"{sha}:{new}"), VF.get(repo, f"{sha}^:{old}")
                    if a is None or b is None:
                        continue
                    fa, fb = all_funcs(a), all_funcs(b)
                    for n in set(fa) - set(fb):
                        added.append(("ADD", new, n, fa[n]))
                    for n in set(fb) - set(fa):
                        deleted.append(("DEL", old, n, fb[n]))
            except Exception:  # noqa: BLE001
                continue
        # moves and renames: a deleted and an added function with similar token sets
        moved = set()
        if len(added) <= 300 and len(deleted) <= 300:
            for i, d in enumerate(deleted):
                for j, a in enumerate(added):
                    if j in moved:
                        continue
                    inter = len(d[3] & a[3])
                    if inter and inter / max(len(d[3] | a[3]), 1) >= 0.7:
                        moved.add(j)
                        moved.add(-1 - i)
                        break
        ev = [(k, p, n) for j, (k, p, n, _) in enumerate(added) if j not in moved] + [(k, p, n) for i, (k, p, n, _) in enumerate(deleted) if -1 - i not in moved]
        res.append((sha, ev, len(files), len([m for m in moved if m >= 0])))
    return res


def fan_worker(args):
    db, items = args
    g = BR.Graph(db)
    fan = np.asarray(g.callers_m.sum(axis=0)).ravel()
    out = {}
    for it in items:
        idx = [g.index[k] for k in it["I"] if k in g.index]
        out[it["pid"]] = (float(fan[idx].sum()) if idx else np.nan)
    return out


def main():
    all_rows = {}
    for repo in sys.argv[1:]:
        path = f"{BR.POOL}/{repo}"
        pairs = json.load(open(LINKS[repo]))
        sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
        cts = np.load(f"{B}/blast/{repo}/snapshot_cts.npy")
        touched = pickle.load(open(f"{B}/blast/{repo}/touched_all.pkl", "rb"))
        causes = list(dict.fromkeys(p["ind"] for p in pairs))
        fixes = list(dict.fromkeys(p["fix"] for p in pairs))
        print(f"\n########## {repo}: {len(pairs)} pairs, {len(causes)} cause commits, {len(fixes)} fix commits ##########", flush=True)
        # verified function sets of the fixes
        todo = [(s, [tuple(k) for k in touched.get(s, [])]) for s in fixes]
        ver = {}
        with ProcessPoolExecutor(max_workers=6) as ex:
            for res in ex.map(VF.work, [(path, todo[i : i + 40]) for i in range(0, len(todo), 40)]):
                for sha, kept, _ in res:
                    ver[sha] = kept
        print("  fix commits verified", flush=True)
        events = {}
        skipped = nmoved = 0
        with ProcessPoolExecutor(max_workers=6) as ex:
            for res in ex.map(event_worker, [(path, causes[i : i + 20]) for i in range(0, len(causes), 20)]):
                for r in res:
                    if r[1] is None:
                        skipped += 1
                    else:
                        events[r[0]] = r[1]
                        nmoved += r[3] if len(r) > 3 else 0
        cnt = collections.Counter()
        for ev in events.values():
            for g in {k for k, _, _ in ev}:
                cnt[g] += 1
        print(f"  cause commits with events: " + ", ".join(f"{g} {cnt[g]}" for g in GROUPS) + f"; skipped (more than 60 C/H files) {skipped}; added functions matched to a deletion (moves, renames) {nmoved}", flush=True)
        by_group = {g: collections.defaultdict(list) for g in GROUPS}
        meta = {}
        for pid, p in enumerate(pairs):
            ev = events.get(p["ind"])
            if not ev or p["fix"] not in ver or not ver[p["fix"]]:
                continue
            for g in GROUPS:
                keys = [(pth, n) for k, pth, n in ev if k == g]
                if not keys:
                    continue
                s = int(np.searchsorted(cts, p["ind_ct"], side="left"))
                if g in ("DEL", "DELFILE"):
                    s -= 1
                if s < 0 or s >= len(sn):
                    continue
                by_group[g][s].append({"pid": pid, "I": keys, "F": ver[p["fix"]]})
                meta[(g, pid)] = p["lag"]
        rows = {}
        for g in GROUPS:
            jobs = [(sn[s]["db"], None, it) for s, it in sorted(by_group[g].items())]
            out, rel, fan = [], [], {}
            with ProcessPoolExecutor(max_workers=6) as ex:
                for r in ex.map(BR.measure_snapshot, jobs):
                    out += r
                for r in ex.map(RS.rel_worker, [(sn[s]["db"], it) for s, it in sorted(by_group[g].items())]):
                    rel += r
                for r in ex.map(fan_worker, [(sn[s]["db"], it) for s, it in sorted(by_group[g].items())]):
                    fan.update(r)
            df = pd.DataFrame(out)
            if len(df):
                df["ncallers"] = df.pid.map(fan)
            rows[g] = (df, pd.DataFrame(rel))
        all_rows[repo] = rows
        report(repo, rows)
    verdicts(all_rows)


def report(repo, rows):
    for g in GROUPS:
        df, rel = rows[g]
        if not len(df):
            print(f"\n  {g}: no pairs")
            continue
        ok = df[df.status == "ok"]
        o = ok[ok.nFo > 0]
        print(f"\n  {g}: {len(df)} pairs; measured {len(ok)}; with a repaired function outside the event set {len(o)}; the fix edits an event function itself in {100 * ok.same_func.mean():.0f}% of measured pairs")
        if len(o) >= 30:
            print("    " + "  ".join(f"{rl} {BR.fmt(BR.ratio(o, rl, 'eB', rng))}" for rl in ("either1", "either2", "callers1", "callees1")))
        if len(rel):
            print("    relation of the repaired functions to the event: " + ", ".join(f"{r} {100 * (rel.rel == r).mean():.0f}%" for r in RS.RELS) + f" (n {len(rel)})")


def verdicts(all_rows):
    print("\n=== VERDICTS ===")
    repos = list(all_rows)

    def stat(repo, g, rl="either2"):
        df = all_rows[repo][g][0]
        if not len(df):
            return None
        o = df[(df.status == "ok") & (df.nFo > 0)]
        return BR.ratio(o, rl, "eB", rng) if len(o) >= 100 else None

    ad1 = {r: (all_rows[r]["ADD"][0][all_rows[r]["ADD"][0].status == "ok"].same_func.mean() if len(all_rows[r]["ADD"][0]) else np.nan) for r in repos}
    print("  AD1 the fix edits the new function itself: " + ", ".join(f"{r} {100 * v:.0f}%" for r, v in ad1.items()) + f" (needs 60% in both): {'supported' if all(v >= 0.6 for v in ad1.values()) else 'not supported'}")
    a2 = {r: stat(r, "ADD") for r in repos}
    print("  AD2 radius around added functions (within 2 calls): " + ", ".join(f"{r} {v[0]:.2f}" if v else f"{r} untestable (under 100 pairs)" for r, v in a2.items()) + f" (needs 1.5 in both): {'supported' if all(v and v[0] >= 1.5 for v in a2.values()) else 'not supported'}")
    a3 = {r: (stat(r, "ADD", "callers1"), stat(r, "ADD", "callees1")) for r in repos}
    print("  AD3 added functions, callers1 against callees1: " + ", ".join(f"{r} " + (f"{c[0]:.2f} vs {e[0]:.2f}" if c and e else "untestable") for r, (c, e) in a3.items()) + f": {'supported' if all(c and e and c[0] > e[0] for c, e in a3.values()) else 'not supported'}")
    d1 = {r: stat(r, "DEL") for r in repos}
    print("  DL1 radius around deleted functions (previous graph, within 2 calls): " + ", ".join(f"{r} {v[0]:.2f}" if v else f"{r} untestable (under 100 pairs)" for r, v in d1.items()) + f" (needs 1.5 in both): {'supported' if all(v and v[0] >= 1.5 for v in d1.values()) else 'not supported'}")
    d2 = {r: (stat(r, "DEL", "callers1"), stat(r, "DEL", "callees1")) for r in repos}
    print("  DL2 deleted functions, former callers1 against callees1: " + ", ".join(f"{r} " + (f"{c[0]:.2f} vs {e[0]:.2f}" if c and e else "untestable") for r, (c, e) in d2.items()) + f": {'supported' if all(c and e and c[0] > e[0] for c, e in d2.values()) else 'not supported'}")
    lo, hi = [], []
    for r in repos:
        df = all_rows[r]["DEL"][0]
        if len(df):
            o = df[(df.status == "ok") & (df.nFo > 0)]
            lo += list(o[o.ncallers <= 1].o_either2.dropna())
            hi += list(o[o.ncallers >= 3].o_either2.dropna())
    if len(lo) >= 30 and len(hi) >= 30:
        print(f"  DL3 share of deleted-function pairs with a repair within 2 calls: 3+ former callers {100 * np.mean(hi):.0f}% (n {len(hi)}) against at most 1 {100 * np.mean(lo):.0f}% (n {len(lo)}) = {np.mean(hi) / np.mean(lo):.2f} (needs 1.2): {'supported' if np.mean(hi) / np.mean(lo) >= 1.2 else 'not supported'}")
    else:
        print(f"  DL3 untestable (3+ former callers n {len(hi)}, at most 1 n {len(lo)})")
    vals = [v[0] for v in list(a2.values()) + list(d1.values()) if v]
    print(f"  surprise bar (radius at or below 1.2 around both added and deleted functions): {'MET' if vals and all(x <= 1.2 for x in vals) else 'not met'} (ratios {', '.join(f'{x:.2f}' for x in vals)})")


if __name__ == "__main__":
    main()
