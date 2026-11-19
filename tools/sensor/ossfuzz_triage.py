#!/usr/bin/env python3
"""Reverse triage from real OSS-Fuzz crash sites. Hypotheses OF1-OF5: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.
    python tools/sensor/ossfuzz_triage.py"""
import bisect
import collections
import json
import os
import pickle
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import lang_validation as LV  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
DAY = 86400
YEARS = 5
LV.CFG["ndpi"] = "c"
LV.CFG["harfbuzz"] = "cpp"
SKIP = ("fuzz", "LLVMFuzzer", "_start", "main", "__libc", "libc_start")
RK = ["REC", "FILE", "BLAME", "N1", "N1TOP", "N1FIX", "RRF", "N1R100"]  # RRF and N1R100 are post hoc (added after the registered run)


def dirof(p):
    return p.rsplit("/", 1)[0] if "/" in p else ""


def cts_of(repo, sn):
    cf = f"{B}/blast/lang_{repo}_snapcts.npy"
    if os.path.exists(cf):
        return np.load(cf)
    cts = np.array([int(subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "show", "-s", "--format=%ct", x["commit"]], capture_output=True, text=True).stdout.strip()) for x in sn])
    np.save(cf, cts)
    return cts


def run(repo, entries):
    path = f"{BR.POOL}/{repo}"
    log = subprocess.run(["git", "-C", path, "log", "--no-merges", "--format=%H %ct"], capture_output=True, text=True).stdout.split("\n")
    rows = sorted((int(l.split()[1]), l.split()[0]) for l in log if l.strip())
    times = [t for t, _ in rows]
    shas = [s for _, s in rows]
    ctof = dict(zip(shas, times))
    for e in entries:
        e["fix"] = min(e["fixed"], key=lambda s: ctof.get(s, 1 << 60))
        e["fix_ct"] = ctof.get(e["fix"])
        e["ind"] = e["intro"][0]
        e["ind_ct"] = ctof.get(e["ind"])
    entries = [e for e in entries if e["fix_ct"] and e["ind_ct"] and e["ind_ct"] < e["fix_ct"]]
    need = set()
    for e in entries:
        lo, hi = bisect.bisect_left(times, e["fix_ct"] - YEARS * 365 * DAY), bisect.bisect_left(times, e["fix_ct"])
        e["lo"], e["hi"] = lo, hi
        need.update(shas[lo:hi])
        need.add(e["fix"])
    cache = f"{B}/blast/ossfuzz_{repo}.pkl"
    info = pickle.load(open(cache, "rb")) if os.path.exists(cache) else {}
    todo = [s for s in need if s not in info]
    print(f"{repo}: {len(entries)} entries with usable commits; {len(need):,} commits in the windows, {len(todo):,} to parse", flush=True)
    with ProcessPoolExecutor(max_workers=6) as ex:
        for r in ex.map(LV.commit_worker, [(path, LV.CFG.get(repo, "c"), todo[i : i + 25]) for i in range(0, len(todo), 25)]):
            info.update(r)
    pickle.dump(info, open(cache, "wb"))
    sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
    cts = cts_of(repo, sn)
    ind_count = collections.Counter(e["ind"] for e in entries)
    out, drop = [], collections.Counter()
    by = collections.defaultdict(list)
    for e in entries:
        s = int(np.searchsorted(cts, e["fix_ct"], side="right")) - 1
        if s < 0:
            drop["no earlier scan"] += 1
            continue
        keys_ind = info.get(e["ind"], ([], 0, 0))[0]
        if not (1 <= len(keys_ind) <= 60):
            drop["introduced commit changes no function or is a sweep"] += 1
            continue
        by[s].append(e)
    for s, items in sorted(by.items()):
        g = BR.Graph(sn[s]["db"])
        byname = collections.defaultdict(list)
        for k in g.index:
            byname[k[1]].append(k)
        for e in items:
            frames = [f for f in e["state"] if f and not f.startswith(SKIP)]
            site_all = [k for f in frames for k in byname.get(f, [])]
            site_top = []
            for f in frames:
                if byname.get(f):
                    site_top = list(byname[f])
                    break
            site_fix = [tuple(k) for k in info.get(e["fix"], ([], 0, 0))[0] if tuple(k) in g.index]
            if not site_all:
                drop["no crash frame is a function of the scan"] += 1
                continue
            cand = [i for i in range(e["lo"], e["hi"]) if 1 <= len(info.get(shas[i], ([], 0, 0))[0]) <= 60 and shas[i] != e["fix"]]
            keys_c = [[tuple(k) for k in info[shas[i]][0]] for i in cand]
            if e["ind"] not in {shas[i] for i in cand}:
                drop["introduced commit not among the candidates"] += 1
                continue
            jt = [shas[i] for i in cand].index(e["ind"])
            rec = np.array([e["fix_ct"] - times[i] for i in cand], dtype=float)
            nodes_c = [[g.index[k] for k in ks if k in g.index] for ks in keys_c]

            def score(site):
                if not site:
                    return None
                Gn = [g.index[k] for k in site if k in g.index]
                near = g.near(np.array(Gn, dtype=np.int64))
                dnode = np.full(g.n, 4, dtype=np.int64)
                dnode[near["either3"]] = 3
                dnode[near["either2"]] = 2
                dnode[near["either1"]] = 1
                dnode[Gn] = 0
                Gk, Gp, Gd = set(site), {k[0] for k in site}, {dirof(k[0]) for k in site}
                sf = np.array([any(k in Gk for k in ks) for ks in keys_c], dtype=float)
                sfile = np.array([any(k[0] in Gp for k in ks) for ks in keys_c], dtype=float)
                dist = np.array([dnode[n].min() if n else 4 for n in nodes_c], dtype=float)
                sdir = np.array([any(dirof(k[0]) in Gd for k in ks) for ks in keys_c], dtype=float)
                dsc = np.where(dist <= 3, 4 - dist, 0)
                return {"FILE": sfile * 1e10 - rec, "BLAME": sf * 1e10 - rec, "N1": (sf * 1e4 + sfile * 1e3 + dsc * 1e2 + sdir * 10) * 1e10 - rec}

            a, t, f = score(site_all), score(site_top), score(site_fix)
            rank = {"REC": 1 + int((-rec > -rec[jt]).sum()), "FILE": 1 + int((a["FILE"] > a["FILE"][jt]).sum()), "BLAME": 1 + int((a["BLAME"] > a["BLAME"][jt]).sum()), "N1": 1 + int((a["N1"] > a["N1"][jt]).sum()), "N1TOP": 1 + int((t["N1"] > t["N1"][jt]).sum())}
            rank["N1FIX"] = 1 + int((f["N1"] > f["N1"][jt]).sum()) if f else None
            from scipy.stats import rankdata
            rrf = 1 / (60 + rankdata(rec, method="min")) + 1 / (60 + rankdata(-a["N1"], method="min"))
            rank["RRF"] = 1 + int((rrf > rrf[jt]).sum())
            recent = rec <= np.sort(rec)[min(99, len(rec) - 1)]
            rank["N1R100"] = 1 + int(((recent > recent[jt]) | ((recent == recent[jt]) & (a["N1"] > a["N1"][jt]))).sum())  # exact lexicographic order (an earlier version added 1e30 to float scores, which collapses ties)
            out.append({"repo": repo, "id": e["id"], "rank": rank, "ncand": len(cand), "artifact": ind_count[e["ind"]] >= 3, "frames": len(set(site_all)), "same_func": bool(set(keys_c[jt]) & set(site_all)), "lag": (e["fix_ct"] - e["ind_ct"]) / DAY, "arr": {"rec": rec.astype(np.float32), "base": ((a["N1"] + rec) / 1e10).astype(np.float32), "jt": jt}})
    print(f"  ranked {len(out)}; dropped {dict(drop)}", flush=True)
    return out


def main():
    rows = json.load(open(f"{B}/osv/rows.json"))
    res = []
    repos = sys.argv[1:] or ["curl", "libxml2", "openssl", "libgit2"]
    tag = "_".join(repos) if sys.argv[1:] else "main4"
    for repo in repos:
        ent = [r for r in rows if r["pkg"] == repo and r["intro"] and r["fixed"] and r["intro"][0] != r["fixed"][0]]
        res += run(repo, ent)
    pickle.dump(res, open(f"{B}/osv/ossfuzz_results_{tag}.pkl", "wb"))

    def t(rs, k, n=20):
        v = [x["rank"][k] for x in rs if x["rank"][k] is not None]
        return (100 * np.mean([r <= n for r in v]), len(v)) if v else (float("nan"), 0)

    def table(rs, label):
        print(f"\n  {label} ({len(rs)} entries; median candidates {int(np.median([x['ncand'] for x in rs])) if rs else 0})")
        print(f"    {'ranker':7s} {'top 1':>7s} {'top 5':>7s} {'top 20':>7s} {'top 100':>8s}")
        for k in RK:
            print(f"    {k:7s} " + " ".join(f"{t(rs, k, n)[0]:6.1f}%" for n in (1, 5, 20, 100)) + (f"   (n {t(rs, k)[1]})" if k == "N1FIX" else ""))

    print("\n=== POOLED ===")
    table(res, "all kept entries")
    table([x for x in res if not x["artifact"]], "without artifact entries (introduced commit shared by 3 or more)")
    table([x for x in res if x["artifact"]], "artifact entries only")
    for repo in repos:
        table([x for x in res if x["repo"] == repo], repo)
    print(f"\n  lag from the introduced commit to the fix: median {np.median([x['lag'] for x in res]):.0f} d; share under 30 d {100 * np.mean([x['lag'] < 30 for x in res]):.0f}%; under 180 d {100 * np.mean([x['lag'] < 180 for x in res]):.0f}%; over a year {100 * np.mean([x['lag'] > 365 for x in res]):.0f}%")
    print(f"\n  the introduced commit changed a crash-site function: {100 * np.mean([x['same_func'] for x in res]):.0f}% of entries")
    n1, rec, fl = t(res, "N1")[0], t(res, "REC")[0], t(res, "FILE")[0]
    n1t, n1f = t(res, "N1TOP")[0], t(res, "N1FIX")[0]
    na = t([x for x in res if not x["artifact"]], "N1")[0]
    print("\n=== VERDICTS ===")
    print(f"  OF1 N1 top 20 {n1:.1f}% (needs 35%): {'supported' if n1 >= 35 else 'not supported'}")
    print(f"  OF2 N1 {n1:.1f}% vs REC {rec:.1f}% (needs 3x) and FILE {fl:.1f}% (needs +10): {'supported' if n1 >= 3 * rec and n1 - fl >= 10 else 'not supported'}")
    print(f"  OF3 N1TOP {n1t:.1f}% vs N1 {n1:.1f}% (needs within 10): {'supported' if abs(n1t - n1) <= 10 else 'not supported'}")
    print(f"  OF4 N1FIX {n1f:.1f}% vs N1 {n1:.1f}% (needs +10): {'supported' if n1f - n1 >= 10 else 'not supported'}")
    print(f"  OF5 N1 without artifacts {na:.1f}% vs all {n1:.1f}% (needs +5): {'supported' if na - n1 >= 5 else 'not supported'}")
    print(f"  surprise bar (N1 less than 10 points above REC): {'MET' if n1 - rec < 10 else 'not met'}")


if __name__ == "__main__":
    main()
