#!/usr/bin/env python3
"""Sensitivity of the added/deleted function result to the move-and-rename filter. Hypotheses SN1-SN5: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.

    python tools/sensor/added_deleted_sensitivity.py dpdk mesa"""
import collections
import json
import os
import pickle
import sqlite3
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import added_deleted_functions as ADF  # noqa: E402
import blast_radius as BR  # noqa: E402
import rename_check as RC  # noqa: E402
import verify_functions as VF  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
MODES = ["none", "J.5", "J.7", "J.9", "M2", "union"]
rng = np.random.default_rng(2982)


def keep(ev, mode):
    return {"none": True, "J.5": ev["jac"] < 0.5, "J.7": ev["jac"] < 0.7, "J.9": ev["jac"] < 0.9, "M2": not ev["m2"], "union": ev["jac"] < 0.7 and not ev["m2"]}[mode]


def event_worker2(job):
    repo, items, snaps, cts = job
    out = []
    for sha, ct in items:
        st = subprocess.run(["git", "-C", repo, "diff-tree", "-r", "-M", "--no-commit-id", "--name-status", sha], capture_output=True, text=True, errors="replace").stdout.splitlines()
        files = []
        for l in st:
            p = l.split("\t")
            if len(p) >= 2 and p[-1].endswith((".c", ".h")):
                files.append((p[0][0], p[1], p[-1]))
        if not files or len(files) > 60:
            continue
        added, deleted = [], []
        for status, old, new in files:
            try:
                if status == "A":
                    src = VF.get(repo, f"{sha}:{new}")
                    added += [{"kind": "NEWFILE", "path": new, "name": n, "tok": t} for n, t in (ADF.all_funcs(src) if src else {}).items()]
                elif status == "D":
                    src = VF.get(repo, f"{sha}^:{old}")
                    deleted += [{"kind": "DELFILE", "path": old, "name": n, "tok": t} for n, t in (ADF.all_funcs(src) if src else {}).items()]
                else:
                    a, b = VF.get(repo, f"{sha}:{new}"), VF.get(repo, f"{sha}^:{old}")
                    if a is None or b is None:
                        continue
                    fa, fb = ADF.all_funcs(a), ADF.all_funcs(b)
                    added += [{"kind": "ADD", "path": new, "name": n, "tok": fa[n]} for n in set(fa) - set(fb)]
                    deleted += [{"kind": "DEL", "path": old, "name": n, "tok": fb[n]} for n in set(fb) - set(fa)]
            except Exception:  # noqa: BLE001
                continue
        for e in added + deleted:
            e["jac"], e["m2"] = 0.0, False
        if added and deleted and len(added) <= 300 and len(deleted) <= 300:
            for a in added:
                for d in deleted:
                    j = len(a["tok"] & d["tok"]) / max(len(a["tok"] | d["tok"]), 1)
                    if j > a["jac"]:
                        a["jac"] = j
                    if j > d["jac"]:
                        d["jac"] = j
            s_next = int(np.searchsorted(cts, ct, side="left"))
            s_prev = s_next - 1
            if 0 <= s_prev and s_next < len(snaps):
                cn, cp = sqlite3.connect(f"file:{snaps[s_next]['db']}?mode=ro", uri=True), sqlite3.connect(f"file:{snaps[s_prev]['db']}?mode=ro", uri=True)
                ra = {i: RC.snap_row(cn, a["path"], a["name"]) for i, a in enumerate(added) if a["kind"] == "ADD"}
                rd = {i: RC.snap_row(cp, d["path"], d["name"]) for i, d in enumerate(deleted) if d["kind"] == "DEL"}
                used = set()
                for i, x in ra.items():
                    if x is None:
                        continue
                    best = (-1, None)
                    for k, y in rd.items():
                        if y is None or k in used:
                            continue
                        cj = len(x[1] & y[1]) / max(len(x[1] | y[1]), 1) if (x[1] or y[1]) else 1.0
                        ratio = (x[2] + 1) / (y[2] + 1)
                        if x[0] == y[0] and cj >= 0.5 and 0.5 <= ratio <= 2 and cj > best[0]:
                            best = (cj, k)
                    if best[1] is not None:
                        used.add(best[1])
                        added[i]["m2"] = True
                        deleted[best[1]]["m2"] = True
                cn.close()
                cp.close()
        out.append((sha, [{k: v for k, v in e.items() if k != "tok"} for e in added + deleted]))
    return out


def load(repo):
    path = f"{BR.POOL}/{repo}"
    pairs = json.load(open(f"{B}/argl/links_{repo}.json"))
    sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
    cts = np.load(f"{B}/blast/{repo}/snapshot_cts.npy")
    cache = f"{B}/blast/{repo}/ad_sens_cache.pkl"
    if os.path.exists(cache):
        return pairs, sn, cts, pickle.load(open(cache, "rb"))
    touched = pickle.load(open(f"{B}/blast/{repo}/touched_all.pkl", "rb"))
    fixes = list(dict.fromkeys(p["fix"] for p in pairs))
    todo = [(s, [tuple(k) for k in touched.get(s, [])]) for s in fixes]
    ver = {}
    with ProcessPoolExecutor(max_workers=6) as ex:
        for res in ex.map(VF.work, [(path, todo[i : i + 40]) for i in range(0, len(todo), 40)]):
            for sha, kept, _ in res:
                ver[sha] = kept
    ct_of = {p["ind"]: p["ind_ct"] for p in pairs}
    causes = list(ct_of)
    events = {}
    with ProcessPoolExecutor(max_workers=6) as ex:
        for res in ex.map(event_worker2, [(path, [(c, ct_of[c]) for c in causes[i : i + 20]], sn, cts) for i in range(0, len(causes), 20)]):
            for sha, ev in res:
                events[sha] = ev
    pickle.dump((ver, events), open(cache, "wb"))
    return pairs, sn, cts, (ver, events)


def run_mode(pairs, sn, cts, ver, events, mode, with_fan=False):
    res = {}
    for g in ("ADD", "DEL"):
        by = collections.defaultdict(list)
        for pid, p in enumerate(pairs):
            ev = events.get(p["ind"])
            if not ev or not ver.get(p["fix"]):
                continue
            keys = [(e["path"], e["name"]) for e in ev if e["kind"] == g and keep(e, mode)]
            if not keys:
                continue
            s = int(np.searchsorted(cts, p["ind_ct"], side="left")) - (1 if g == "DEL" else 0)
            if 0 <= s < len(sn):
                by[s].append({"pid": pid, "I": keys, "F": ver[p["fix"]]})
        rows, fan = [], {}
        with ProcessPoolExecutor(max_workers=6) as ex:
            for r in ex.map(BR.measure_snapshot, [(sn[s]["db"], None, it) for s, it in sorted(by.items())]):
                rows += r
            if with_fan:
                for r in ex.map(ADF.fan_worker, [(sn[s]["db"], it) for s, it in sorted(by.items())]):
                    fan.update(r)
        df = pd.DataFrame(rows)
        if len(df) and with_fan:
            df["ncallers"] = df.pid.map(fan)
        res[g] = df
    return res


def row(df):
    ok = df[df.status == "ok"]
    o = ok[ok.nFo > 0]
    rr = {k: BR.ratio(o, k, "eB", rng) for k in ("either1", "either2", "callers1", "callees1")}
    return len(ok), len(o), ok.same_func.mean(), rr


def main():
    allres = {}
    repos = sys.argv[1:]
    for repo in repos:
        pairs, sn, cts, (ver, events) = load(repo)
        n_ev = collections.Counter(e["kind"] for ev in events.values() for e in ev)
        add = [e for ev in events.values() for e in ev if e["kind"] == "ADD"]
        print(f"\n########## {repo}: events {dict(n_ev)}; ADD excluded as moves: J.5 {sum(1 for e in add if not keep(e, 'J.5'))}, J.7 {sum(1 for e in add if not keep(e, 'J.7'))}, J.9 {sum(1 for e in add if not keep(e, 'J.9'))}, M2 {sum(1 for e in add if e['m2'])}, union {sum(1 for e in add if not keep(e, 'union'))} (of {len(add)} added functions) ##########", flush=True)
        for mode in MODES:
            r = run_mode(pairs, sn, cts, ver, events, mode, with_fan=(mode == "union"))
            allres[(repo, mode)] = r
            for g in ("ADD", "DEL"):
                if not len(r[g]):
                    print(f"  {mode:6s} {g}: no pairs", flush=True)
                    continue
                nm, no, sf, rr = row(r[g])
                f = lambda k: f"{rr[k][0]:.2f} [{rr[k][1]:.2f},{rr[k][2]:.2f}]" if rr[k] else "n/a"  # noqa: E731
                print(f"  {mode:6s} {g:3s} measured {nm:5d}, with a repaired function outside {no:5d}, same function {100 * sf:3.0f}%  within 1 {f('either1')}  within 2 {f('either2')}  callers1 {f('callers1')}  callees1 {f('callees1')}", flush=True)
    print("\n=== VERDICTS ===")

    def val(repo, mode, g, k="either2"):
        df = allres[(repo, mode)][g]
        if not len(df):
            return None
        rr = row(df)[3][k]
        return rr[0] if rr else None

    for sn_, g, lab in (("SN1", "ADD", "added"), ("SN2", "DEL", "deleted")):
        vs = {(r, m): val(r, m, g) for r in repos for m in MODES}
        ok = all(v is not None and v >= 1.5 for v in vs.values())
        rng_ = ", ".join(f"{r} {min(v for (rr_, m), v in vs.items() if rr_ == r and v):.2f} to {max(v for (rr_, m), v in vs.items() if rr_ == r and v):.2f}" for r in repos)
        print(f"  {sn_} radius around {lab} functions within 2 calls, range over filters: {rng_} (needs 1.5 in all): {'supported' if ok else 'not supported'}")
    dev = []
    for r in repos:
        for g in ("ADD", "DEL"):
            base = val(r, "J.7", g)
            for m in MODES:
                v = val(r, m, g)
                if base and v:
                    dev.append(abs(v / base - 1))
    print(f"  SN3 largest relative deviation from the J.7 value over all filters, groups and repositories: {100 * max(dev):.0f}% (needs 15%): {'supported' if max(dev) <= 0.15 else 'not supported'}")
    ok4 = all((val(r, m, g, "callers1") or 0) > (val(r, m, g, "callees1") or 0) for r in repos for m in MODES for g in ("ADD", "DEL"))
    print(f"  SN4 callers1 above callees1 in every filter, group and repository: {'supported' if ok4 else 'not supported'}")
    lo, hi = [], []
    for r in repos:
        df = allres[(r, "union")]["DEL"]
        if len(df):
            o = df[(df.status == "ok") & (df.nFo > 0)]
            lo += list(o[o.ncallers <= 1].o_either2.dropna())
            hi += list(o[o.ncallers >= 3].o_either2.dropna())
    if len(lo) >= 30 and len(hi) >= 30:
        print(f"  SN5 DL3 under the union filter: 3+ former callers {100 * np.mean(hi):.0f}% (n {len(hi)}) against at most 1 {100 * np.mean(lo):.0f}% (n {len(lo)}) = {np.mean(hi) / np.mean(lo):.2f} (needs 1.2): {'supported' if np.mean(hi) / np.mean(lo) >= 1.2 else 'not supported'}")
    allv = [val(r, m, g) for r in repos for m in MODES for g in ("ADD", "DEL")]
    print(f"  surprise bar (any radius at or below 1.2): {'MET' if any(v is not None and v <= 1.2 for v in allv) else 'not met'} (lowest {min(v for v in allv if v):.2f})")


if __name__ == "__main__":
    main()
