#!/usr/bin/env python3
"""A complete partition of function edits, with cause-side accounting. Hypotheses RM1-RM5: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.
    python tools/sensor/work_partition.py dpdk mesa"""
import collections
import json
import os
import pickle
import random
import re
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import change_kinds as CK  # noqa: E402
import change_kinds_diff as CDF  # noqa: E402
import lang_validation as LV  # noqa: E402
import test_selection as TS  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
FIX = re.compile(r"\b(fix|fixes|fixed|bug|regression|crash|leak|overflow|race|deadlock|uaf|null)\b", re.I)
FMT = re.compile(r"\b(typo|typos|spelling|whitespace|style|checkpatch|indent(ation)?|licen[cs]e|docs?|documentation|comments?|copyright|spdx)\b", re.I)
CATS = ["sweep", "revert", "fix, named cause", "fix, cause by blame", "fix, no cause found", "tests only", "comment or whitespace only", "formatting, docs, licence (subject)", "adds code", "removes code", "modifies: feature verb", "modifies: restructure verb", "modifies: optimization verb", "modifies: other verb"]
LV.CFG["mesa"] = "c"


def load_log(path):
    out = subprocess.run(["git", "-C", path, "log", "--no-merges", "--name-only", "--format=@@%H%x1f%ct%x1f%s"], capture_output=True, text=True, errors="replace").stdout
    commits = {}
    for blk in out.split("@@")[1:]:
        lines = blk.split("\n")
        p = lines[0].split("\x1f", 2)
        if len(p) == 3:
            commits[p[0]] = (int(p[1]), p[2], [l for l in lines[1:] if l])
    return commits


def main():
    rng = random.Random(5)
    summary = {}
    for repo in sys.argv[1:]:
        t0 = time.time()
        path = f"{BR.POOL}/{repo}"
        CK.REPO = path
        touched = pickle.load(open(f"{B}/blast/{repo}/touched_all.pkl", "rb"))
        commits = load_log(path)
        nf = {s: len(touched.get(s, [])) for s in commits}
        trailer = set(subprocess.run(["git", "-C", path, "log", "--no-merges", "-E", "--grep=^Fixes:", "--format=%H"], capture_output=True, text=True).stdout.split())
        pairs = json.load(open(f"{B}/argl/links_{repo}.json"))
        cited = {p["ind"] for p in pairs}
        total_edits = sum(nf.values())
        cat = {}
        need_blame, need_diff = [], []
        for s, (ct, subj, files) in commits.items():
            if nf[s] == 0:
                cat[s] = "none"
            elif nf[s] > 60:
                cat[s] = "sweep"
            elif subj.lower().startswith("revert"):
                cat[s] = "revert"
            elif s in trailer:
                cat[s] = "fix, named cause"
            elif FIX.search(subj):
                cat[s] = "fix?"
                need_blame.append((s, ct))
            else:
                cfiles = [f for f in files if f.endswith((".c", ".h"))]
                if cfiles and all(TS.is_test(f) for f in cfiles):
                    cat[s] = "tests only"
                elif FMT.search(subj):
                    cat[s] = "formatting, docs, licence (subject)"
                else:
                    cat[s] = "diff?"
                    need_diff.append(s)
        print(f"\n##### {repo}: {len(commits):,} commits, {sum(1 for c in cat.values() if c == 'none'):,} touch no C/H function; blame needed for {len(need_blame):,}, diff features for {len(need_diff):,} ({time.time() - t0:.0f}s)", flush=True)
        cache = f"{B}/blast/partition_blame_{repo}.pkl"
        if os.path.exists(cache):
            bl = pickle.load(open(cache, "rb"))
        else:
            bl = []
            with ProcessPoolExecutor(max_workers=6) as ex:
                for res in ex.map(LV.szz_worker, [(path, "c", need_blame[i : i + 15]) for i in range(0, len(need_blame), 15)]):
                    bl += res
            pickle.dump(bl, open(cache, "wb"))
        found = {}
        for fix, ind, n, t in bl:
            if ind != fix and ind in commits and commits[ind][0] < commits[fix][0]:
                found[fix] = ind
        for s, _ in need_blame:
            cat[s] = "fix, cause by blame" if s in found else "fix, no cause found"
        cited |= set(found.values())
        print(f"  blame: {len(found):,} of {len(need_blame):,} cause found ({time.time() - t0:.0f}s)", flush=True)
        feats = CDF.diff_features(need_diff, f"{B}/blast/partition_feats_{repo}.pkl")
        print(f"  diff features done ({time.time() - t0:.0f}s)", flush=True)
        for s in need_diff:
            f = feats[s]
            na, nr = f["n_add"], f["n_rem"]
            if f["only_comment"]:
                cat[s] = "comment or whitespace only"
            elif na >= 3 * max(nr, 1):
                cat[s] = "adds code"
            elif nr >= 3 * max(na, 1):
                cat[s] = "removes code"
            else:
                v = CK.cause_type(commits[s][1])[0]
                cat[s] = {"feature": "modifies: feature verb", "restructure": "modifies: restructure verb", "optimization": "modifies: optimization verb"}.get(v, "modifies: other verb")
        rows = {}
        n_cm = len(commits)
        print(f"\n  {'category':38s} {'commits':>9s} {'% commits':>9s} {'fn edits':>10s} {'% edits':>8s} {'cited commits':>14s} {'cited edits':>12s} {'cited per edit':>15s}")
        tot_c = tot_e = 0
        for c in ["none"] + CATS:
            ss = [s for s, k in cat.items() if k == c]
            e = sum(nf[s] for s in ss)
            ce = sum(1 for s in ss if s in cited)
            cedit = sum(nf[s] for s in ss if s in cited)
            rows[c] = (len(ss), e, ce, cedit)
            tot_c += len(ss)
            tot_e += e
            print(f"  {c:38s} {len(ss):9,d} {100 * len(ss) / n_cm:8.1f}% {e:10,d} {100 * e / total_edits:7.1f}% {100 * ce / max(len(ss), 1):13.1f}% {100 * cedit / max(e, 1):11.1f}%")
        print(f"  {'TOTAL':38s} {tot_c:9,d} {'':9s} {tot_e:10,d}   (check: commits {n_cm:,}, edits {total_edits:,})")
        os.makedirs(f"{B}/partition", exist_ok=True)
        pickle.dump({"cat": cat, "cited": cited, "rows": rows}, open(f"{B}/partition/{repo}.pkl", "wb"))
        # hand-check sample
        pool = [s for s, k in cat.items() if k in ("adds code", "removes code") or k.startswith("modifies")]
        samp = rng.sample(pool, min(40, len(pool)))
        print(f"\n  HAND CHECK sample ({repo}): subjects of 40 random commits of adds / removes / modifies")
        for s in samp:
            print(f"    [{cat[s][:12]}] {commits[s][1][:110]}")
        summary[repo] = (rows, total_edits)
    print("\n=== VERDICT INPUTS (hand check RM3 is read by eye) ===")
    for repo, (rows, te) in summary.items():
        fixside = sum(rows[c][1] for c in ("fix, named cause", "fix, cause by blame", "fix, no cause found"))
        mech = sum(rows[c][1] for c in ("sweep", "revert", "tests only", "comment or whitespace only", "formatting, docs, licence (subject)"))
        body = sum(rows[c][1] for c in ("adds code", "removes code")) + sum(v[1] for k, v in rows.items() if k.startswith("modifies"))
        org = [k for k in CATS if k not in ("sweep", "revert", "fix, named cause", "fix, cause by blame", "fix, no cause found")]
        oe = sum(rows[k][1] for k in org)
        ocited = sum(rows[k][3] for k in org)
        a, m = rows["adds code"], [sum(rows[k][i] for k in rows if k.startswith("modifies")) for i in range(4)]
        ra, rm = a[3] / max(a[1], 1), m[3] / max(m[1], 1)
        print(f"  {repo}: RM1 fix side {100 * fixside / te:.1f}% (needs 30% or less); RM2 mechanical {100 * mech / te:.1f}% (needs 30% or more); adds+removes+modifies {100 * body / te:.1f}% (surprise below 25%); RM4 cited share of organic non-fix edits {100 * ocited / oe:.1f}% (needs 10 to 40); RM5 cited per edit adds {100 * ra:.1f}% vs modifies {100 * rm:.1f}% (ratio {ra / max(rm, 1e-9):.2f}, needs within 2)")


if __name__ == "__main__":
    main()
