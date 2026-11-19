#!/usr/bin/env python3
"""Data for the repo-evolution report mock-up (DPDK): per-quarter series and tables from the scans, the partition and the measured pairs. Descriptive.
    python tools/sensor/report_data.py dpdk"""
import collections
import json
import pickle
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402

S = "/tmp/gitgalaxy-scratch/claude"
GROUP = {"sweep": "sweeps", "revert": "mechanical", "tests only": "mechanical", "comment or whitespace only": "mechanical", "formatting, docs, licence (subject)": "mechanical"}


def grp(c):
    if c in GROUP:
        return GROUP[c]
    if c.startswith("fix"):
        return "fixes"
    if c == "none":
        return None
    return "organic"


def main():
    repo = sys.argv[1]
    path = f"{BR.POOL}/{repo}"
    sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
    cts = np.load(f"{S}/blast/{repo}/snapshot_cts.npy")
    part = pickle.load(open(f"{S}/partition/{repo}.pkl", "rb"))
    cat, cited = part["cat"], part["cited"]
    touched = pickle.load(open(f"{S}/blast/{repo}/touched_all.pkl", "rb"))
    log = subprocess.run(["git", "-C", path, "log", "--no-merges", "--format=%H\x1f%ct\x1f%s"], capture_output=True, text=True, errors="replace").stdout.splitlines()
    ct, subj = {}, {}
    for l in log:
        p = l.split("\x1f", 2)
        if len(p) == 3:
            ct[p[0]], subj[p[0]] = int(p[1]), p[2]
    out = {"repo": repo, "quarters": []}
    first_seen = {}
    prev_keys = prev_files = None
    edited_by_q = []
    keys_by_q = []
    for i in range(len(sn)):
        g = BR.Graph(sn[i]["db"])
        keys = set(g.index)
        keys_by_q.append(keys)
        for k in keys:
            first_seen.setdefault(k, i)
        q = {"label": sn[i]["label"], "date": sn[i]["date"], "functions": len(keys)}
        if prev_keys is not None:
            lo, hi = cts[i - 1], cts[i]
            names_prev = collections.Counter(k[1] for k in prev_keys)
            names_now = collections.Counter(k[1] for k in keys)
            births, deaths = keys - prev_keys, prev_keys - keys
            q["births_new_code"] = sum(1 for k in births if k[1] not in names_prev)
            q["births_moved"] = sum(1 for k in births if k[1] in names_prev)
            q["deaths_removed"] = sum(1 for k in deaths if k[1] not in names_now)
            q["deaths_moved"] = sum(1 for k in deaths if k[1] in names_now)
            qc = [s for s, t in ct.items() if lo < t <= hi]
            q["commits"] = len(qc)
            e = collections.Counter()
            c = collections.Counter()
            edited = set()
            for s in qc:
                gname = grp(cat.get(s, "none"))
                if gname is None:
                    continue
                n = len(touched.get(s, []))
                e[gname] += n
                c[gname] += 1
                edited.update(tuple(f) for f in touched.get(s, []))
            for gname in ("organic", "sweeps", "fixes", "mechanical"):
                q["edits_" + gname] = e[gname]
                q["commits_" + gname] = c[gname]
            edited_by_q.append(edited)
            q["edited_functions"] = len(edited & keys)
            recent = set().union(*edited_by_q[-4:])
            q["untouched_4q_share"] = 1 - len(recent & keys) / max(len(keys), 1)
        prev_keys = keys
        out["quarters"].append(q)
    # cohort layers: functions present at each quarter by the year they first appeared
    years = sorted({sn[first_seen[k]]["date"][:4] for k in first_seen})
    for i, q in enumerate(out["quarters"]):
        cnt = collections.Counter(sn[first_seen[k]]["date"][:4] for k in keys_by_q[i])
        q["cohorts"] = {y: cnt.get(y, 0) for y in years}
    out["cohort_years"] = years
    # pairs: lag histogram, cause type table
    m = pd.read_pickle(f"{S}/fr_base/measure.pkl")
    m = m[m.status == "ok"].copy()
    tags = pickle.load(open(f"{S}/fix_tags.pkl", "rb"))
    m["cause"] = [tags.get((repo, s), ("", "", "other"))[2] for s in m.fix]
    bins = [(0, 7, "under a week"), (7, 30, "1-4 weeks"), (30, 90, "1-3 months"), (90, 180, "3-6 months"), (180, 365, "6-12 months"), (365, 730, "1-2 years"), (730, 1e9, "over 2 years")]
    out["lag_hist"] = [{"bin": lab, "pairs": int(((m.lag >= a) & (m.lag < b)).sum())} for a, b, lab in bins]
    out["lag_median_days"] = float(m.lag.median())
    rng = np.random.default_rng(2982)
    ct_rows = []
    for k, g in m.groupby("cause"):
        o = g[g.nFo > 0]
        r = BR.ratio(o, "either2", "eB", rng) if len(o) >= 15 else None
        ct_rows.append({"cause": k, "pairs": len(g), "same_function": float(g.same_func.mean()), "radius_2": r[0] if r else None, "median_lag": float(g.lag.median())})
    out["cause_types"] = sorted(ct_rows, key=lambda r: -r["pairs"])
    # sweeps: the 12 largest
    sw = sorted(((len(touched.get(s, [])), s) for s, k in cat.items() if k == "sweep"), reverse=True)[:12]
    out["largest_sweeps"] = [{"date": pd.Timestamp(ct[s], unit="s").strftime("%Y-%m-%d"), "functions": n, "subject": subj[s][:90], "cited_as_cause": s in cited} for n, s in sw]
    # repeat spots
    fixcount = collections.Counter()
    for s, k in cat.items():
        if k.startswith("fix"):
            for f in touched.get(s, []):
                fixcount[tuple(f)] += 1
    tot = sum(fixcount.values())
    out["repeat_spots"] = {"fix_edits": tot, "functions_fixed": len(fixcount), "share_in_fixed_2plus": sum(v for v in fixcount.values() if v >= 2) / tot, "share_in_fixed_5plus": sum(v for v in fixcount.values() if v >= 5) / tot}
    out["most_fixed"] = [{"function": f"{k[1]}", "file": k[0], "fixes": v} for k, v in fixcount.most_common(10)]
    # size bands vs later cited
    end = max(ct.values())
    rows = []
    for s, k in cat.items():
        if (k in ("adds code", "removes code") or k.startswith("modifies")) and ct[s] <= end - 3 * 365 * 86400 and ct[s] >= 1420070400:
            n = len(touched.get(s, []))
            rows.append((n, s in cited))
    bands = [(1, 1, "1 function"), (2, 3, "2-3"), (4, 10, "4-10"), (11, 30, "11-30"), (31, 60, "31-60")]
    out["size_bands"] = [{"band": lab, "commits": sum(1 for n, c in rows if a <= n <= b), "later_repaired": float(np.mean([c for n, c in rows if a <= n <= b])) if any(a <= n <= b for n, c in rows) else None} for a, b, lab in bands]
    # composition over the whole history
    comp = collections.Counter()
    for s, k in cat.items():
        gname = grp(k)
        if gname:
            comp[gname] += len(touched.get(s, []))
    tot_e = sum(comp.values())
    out["composition"] = {k: v / tot_e for k, v in comp.items()}
    out["composition_edits"] = int(tot_e)
    json.dump(out, open(f"docs/sensor-overhaul/report-design/{repo}_report_data.json", "w"), indent=1, default=float)
    q = out["quarters"]
    print(f"{repo}: {len(q)} quarters, composition {out['composition']}, lag median {out['lag_median_days']:.0f} d")
    print("cause types:", out["cause_types"])
    print("size bands:", out["size_bands"])
    print("repeat:", out["repeat_spots"])
    print("sweeps:", out["largest_sweeps"][:3])


if __name__ == "__main__":
    main()
