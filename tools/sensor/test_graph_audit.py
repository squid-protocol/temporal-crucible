#!/usr/bin/env python3
"""Do the call graphs see the tests? Hypotheses TA1-TA4, TE1-TE3: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running."""
import bisect
import collections
import json
import os
import pickle
import random
import subprocess
import sys

import numpy as np

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import lang_validation as LV  # noqa: E402
import test_selection as TS  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
DAY = 86400
AUDIT = ["dpdk", "mesa", "libgit2", "redis", "libxml2", "scapy", "sphinx", "prometheus"]
C5 = ["dpdk", "mesa", "libgit2", "redis", "libxml2"]


def audit_one(repo, maxc):
    os.environ["BLAST_MAXC"] = str(maxc)
    sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
    g = BR.Graph(sn[-1]["db"])
    keys = sorted(g.index, key=g.index.get)
    fpaths = sorted({k[0] for k in keys})
    ist = np.array([TS.is_test(k[0]) for k in keys])
    tfiles = {p for p in fpaths if TS.is_test(p)}
    if not ist.any():
        return None
    # edges from test functions to non-test functions
    coo = g.callers_m.tocoo()  # A[src,dst]
    s, d = coo.row, coo.col
    m = ist[s] & ~ist[d]
    wired_files = {keys[i][0] for i in s[m]}
    v = np.zeros(g.n, dtype=np.int8)
    v[np.nonzero(ist)[0]] = 1
    reach = np.zeros(g.n, dtype=bool)
    front = v.copy()
    seen = v.astype(bool)
    for _ in range(3):
        nxt = (g.callees_m @ front) > 0
        nxt &= ~seen
        seen |= nxt
        front = nxt.astype(np.int8)
        reach |= nxt
    return {"test_files": len(tfiles), "test_funcs": int(ist.sum()), "funcs": g.n, "wired": len(wired_files & tfiles) / max(len(tfiles), 1), "reach": float(reach[~ist].mean())}


def te_part(repo, kind):
    os.environ["BLAST_MAXC"] = "1"
    fixes = TS.load(repo, kind)
    files = TS.files_of(repo, list(fixes))
    n_fix = len(fixes)
    touch = sum(1 for s in fixes if any(TS.is_test(f) for f in files.get(s, [])))
    sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
    cf = f"{B}/blast/{repo}/snapshot_cts.npy" if os.path.exists(f"{B}/blast/{repo}/snapshot_cts.npy") else f"{B}/blast/lang_{repo}_snapcts.npy"
    cts = np.load(cf)
    by = collections.defaultdict(list)
    for sha, (ct, ks) in fixes.items():
        s = int(np.searchsorted(cts, ct, side="right")) - 1
        if s >= 0:
            by[s].append((sha, ks))
    both = within = 0
    for s, items in sorted(by.items()):
        g = BR.Graph(sn[s]["db"])
        keys = sorted(g.index, key=g.index.get)
        fpaths = sorted({k[0] for k in keys})
        tset = {p for p in fpaths if TS.is_test(p)}
        fid_of = {p: i for i, p in enumerate(fpaths)}
        for sha, ks in items:
            src = [k for k in ks if not TS.is_test(k[0]) and k in g.index]
            truth = {f for f in files.get(sha, []) if f in tset}
            if not src or not truth:
                continue
            both += 1
            near = g.near(np.array([g.index[k] for k in src], dtype=np.int64))
            tf = {fid_of[f] for f in truth}
            if any(g.fid[i] in tf for i in np.nonzero(near["either3"])[0]):
                within += 1
    return n_fix, touch, both, within


def te3(repo):
    os.environ["BLAST_MAXC"] = "1"
    path = f"{BR.POOL}/{repo}"
    pairs = json.load(open(f"{B}/argl/links_{repo}.json"))
    random.Random(3).shuffle(pairs)
    pairs = pairs[:1500]
    touched = pickle.load(open(f"{B}/blast/{repo}/touched_all.pkl", "rb"))
    sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
    cts = np.load(f"{B}/blast/{repo}/snapshot_cts.npy")
    log = subprocess.run(["git", "-C", path, "log", "--no-merges", "--name-only", "--format=\x1e%H %ct"], capture_output=True, text=True, errors="replace").stdout
    rows = []
    for blk in log.split("\x1e")[1:]:
        ls = blk.strip().split("\n")
        h, c = ls[0].split()
        rows.append((int(c), h, {f for f in ls[1:] if f and TS.is_test(f)}))
    rows.sort()
    times = [r[0] for r in rows]
    shas = [r[1] for r in rows]
    tfiles_of = [r[2] for r in rows]
    idx_of = {s: i for i, s in enumerate(shas)}
    keys_of = [[tuple(k) for k in touched.get(s, [])] for s in shas]
    ok = [1 <= len(k) <= 60 for k in keys_of]
    fixshas = list(dict.fromkeys(p["fix"] for p in pairs))
    fixinfo = {}
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=6) as ex:
        for r in ex.map(LV.commit_worker, [(path, "c", fixshas[i : i + 25]) for i in range(0, len(fixshas), 25)]):
            fixinfo.update(r)
    by = collections.defaultdict(list)
    for p in pairs:
        G = [k for k in fixinfo.get(p["fix"], ([], 0, 0))[0] if not TS.is_test(k[0])]
        s = int(np.searchsorted(cts, p["fix_ct"], side="right")) - 1
        ci = idx_of.get(p["ind"])
        fi = idx_of.get(p["fix"])
        if G and s >= 0 and ci is not None and fi is not None and tfiles_of[fi] and ok[ci] and p["fix_ct"] - 730 * DAY <= times[ci] < p["fix_ct"]:
            by[s].append((p, G, ci, fi))
    r20 = {"N1": [], "N1T": []}
    for s, items in sorted(by.items()):
        g = BR.Graph(sn[s]["db"])
        for p, G, ci, fi in items:
            Gn = [g.index[k] for k in G if k in g.index]
            if not Gn:
                continue
            near = g.near(np.array(Gn, dtype=np.int64))
            dnode = np.full(g.n, 4, dtype=np.int64)
            dnode[near["either3"]] = 3
            dnode[near["either2"]] = 2
            dnode[near["either1"]] = 1
            dnode[Gn] = 0
            Gk, Gp, Gd = set(G), {k[0] for k in G}, {TS_dir(k[0]) for k in G}
            tf = p["fix_ct"]
            lo, hi = bisect.bisect_left(times, tf - 730 * DAY), bisect.bisect_left(times, tf)
            cand = [i for i in range(lo, hi) if ok[i] and shas[i] != p["fix"]]
            F = np.zeros((len(cand), 6))
            for j, i in enumerate(cand):
                ks = keys_of[i]
                nodes = [g.index[k] for k in ks if k in g.index]
                F[j] = [any(k in Gk for k in ks), any(k[0] in Gp for k in ks), (dnode[nodes].min() if nodes else 4), any(TS_dir(k[0]) in Gd for k in ks), bool(tfiles_of[i] & tfiles_of[fi]), tf - times[i]]
            sf, sfile, dist, sdir, stt, rec = F.T
            dsc = np.where(dist <= 3, 4 - dist, 0)
            base = sf * 1e4 + sfile * 1e3 + dsc * 1e2 + sdir * 10
            sc = {"N1": base * 1e10 - rec, "N1T": (sf * 1e4 + stt * 5e3 + sfile * 1e3 + dsc * 1e2 + sdir * 10) * 1e10 - rec}
            jt = cand.index(ci)
            for k, v in sc.items():
                r20[k].append(1 + int((v > v[jt]).sum()) <= 20)
    return r20


def TS_dir(p):
    return p.rsplit("/", 1)[0] if "/" in p else ""


def main():
    print("=== AUDIT: test files wired into the source, and test reach (latest scan) ===")
    wired = {}
    print(f"  {'repo':10s} {'test files':>10s} {'test funcs':>10s} {'wired (conf.)':>13s} {'wired (all)':>12s} {'test reach 3':>13s}")
    for repo in AUDIT:
        a = audit_one(repo, 1)
        b = audit_one(repo, 100)
        if a is None:
            print(f"  {repo:10s} no test files found")
            continue
        wired[repo] = (a["wired"], b["wired"], a["reach"])
        print(f"  {repo:10s} {a['test_files']:10d} {a['test_funcs']:10d} {100 * a['wired']:12.1f}% {100 * b['wired']:11.1f}% {100 * a['reach']:12.1f}%", flush=True)
    print("\n=== TESTS AS A SIGNAL OF CHANGE ===")
    nf = tt = bo = wi = 0
    for repo, kind in [("dpdk", "trailer"), ("mesa", "trailer"), ("libgit2", "blame"), ("redis", "blame"), ("libxml2", "blame")]:
        a, b, c, d = te_part(repo, kind)
        nf, tt, bo, wi = nf + a, tt + b, bo + c, wi + d
        print(f"  {repo}: fixes {a}, touching a test file {b} ({100 * b / max(a, 1):.0f}%); with source function and graph test file {c}, test file within 3 calls {d} ({100 * d / max(c, 1):.0f}%)", flush=True)
    r20 = {"N1": [], "N1T": []}
    for repo in ("dpdk", "mesa"):
        r = te3(repo)
        for k in r20:
            r20[k] += r[k]
        print(f"  {repo} triage, fixes touching a test file: {len(r['N1'])} pairs; top 20 N1 {100 * np.mean(r['N1']):.1f}%, N1T {100 * np.mean(r['N1T']):.1f}%", flush=True)
    print("\n=== VERDICTS ===")
    c5 = [wired[r] for r in C5 if r in wired]
    print(f"  TA1 repositories with at least 50% wired: {sum(w[0] >= 0.5 for w in c5)} of {len(c5)} (needs 3): {'supported' if sum(w[0] >= 0.5 for w in c5) >= 3 else 'not supported'}")
    print(f"  TA2 repositories where ambiguous edges add 10 points: {sum(w[1] - w[0] >= 0.1 for w in wired.values())} (needs 2): {'supported' if sum(w[1] - w[0] >= 0.1 for w in wired.values()) >= 2 else 'not supported'}")
    print(f"  TA3 redis wired {100 * wired['redis'][0]:.1f}% (needs below 20%): {'supported' if wired['redis'][0] < 0.2 else 'not supported'}")
    med = float(np.median([w[2] for w in wired.values()]))
    print(f"  TA4 median test reach {100 * med:.1f}% (needs 50% or less): {'supported' if med <= 0.5 else 'not supported'}")
    print(f"  TE1 fixes touching a test file {100 * tt / nf:.1f}% (needs 30%): {'supported' if tt / nf >= 0.3 else 'not supported'}")
    print(f"  TE2 touched test file within 3 calls {100 * wi / max(bo, 1):.1f}% of {bo} fixes (needs 50%): {'supported' if wi / max(bo, 1) >= 0.5 else 'not supported'}")
    d = 100 * (np.mean(r20["N1T"]) - np.mean(r20["N1"]))
    print(f"  TE3 N1T minus N1 {d:+.1f} points on {len(r20['N1'])} pairs (needs +3): {'supported' if d >= 3 else 'not supported'}")


if __name__ == "__main__":
    main()
