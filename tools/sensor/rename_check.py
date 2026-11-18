#!/usr/bin/env python3
"""How well do three matchers recognise a moved or renamed function? M1 token-set Jaccard, M2 the engine-style structural match (fingerprint of keyword families + call set + size,
from the scan databases), M3 reference: git line-origin tracking (blame -w -M -C -C -C). Hypotheses RC1-RC4: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.

    python tools/sensor/rename_check.py dpdk [N_COMMITS]"""
import json
import random
import re
import sqlite3
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from tree_sitter_language_pack import get_parser

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import repair_structure as RS  # noqa: E402
import verify_functions as VF  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
FAM = ["struct_branch", "state_pointers", "state_memory_alloc", "bitwise_ops", "def_sync_locks", "def_cleanup", "def_safety", "state_safety_neg", "arch_io", "arch_api", "state_flux", "arch_concurrency", "arch_globals", "state_cast_hits", "state_bailout_hits", "state_print_hits", "state_heat_triggers", "struct_macros"]
_P = None


def funcs_full(src):
    global _P
    if _P is None:
        _P = get_parser("c")
    tree = _P.parse(src)
    out, stack = {}, [tree.root_node]
    while stack:
        n = stack.pop()
        if n.type == "function_definition":
            nm = RS.func_name(n, src)
            if nm and nm not in out:
                text = src[n.start_byte:n.end_byte]
                out[nm] = {"start": n.start_point[0] + 1, "end": n.end_point[0] + 1, "tokens": frozenset(re.findall(rb"\w+", text)), "lines": {l.strip() for l in text.decode("utf8", "replace").splitlines() if len(l.strip()) > 3}}
            continue
        stack.extend(n.children)
    return out


def events_full(repo, sha):
    st = subprocess.run(["git", "-C", repo, "diff-tree", "-r", "-M", "--no-commit-id", "--name-status", sha], capture_output=True, text=True, errors="replace").stdout.splitlines()
    added, deleted = [], []
    for l in st:
        p = l.split("\t")
        if len(p) < 2 or not p[-1].endswith((".c", ".h")) or p[0][0] not in "MR":
            continue
        a, b = VF.get(repo, f"{sha}:{p[-1]}"), VF.get(repo, f"{sha}^:{p[1]}")
        if a is None or b is None:
            continue
        fa, fb = funcs_full(a), funcs_full(b)
        added += [{"path": p[-1], "name": n, **fa[n]} for n in set(fa) - set(fb)]
        deleted += [{"path": p[1], "name": n, **fb[n]} for n in set(fb) - set(fa)]
    return added, deleted


def snap_row(con, path, name):
    r = con.execute(f"SELECT {', '.join('d.' + c for c in FAM)}, d.calls_out_to, d.loc FROM function_data d JOIN file_data f ON f.id = d.file_id WHERE f.file_path = ? AND d.func_name = ? LIMIT 1", (path, name)).fetchone()
    if not r:
        return None
    try:
        calls = set(json.loads(r[len(FAM)] or "[]"))
    except Exception:  # noqa: BLE001
        calls = set()
    return tuple(int((x or 0) > 0) for x in r[: len(FAM)]), calls, int(r[len(FAM) + 1] or 0)


def blame_lines(repo, sha, path, a, b):
    try:
        out = subprocess.run(["git", "-C", repo, "blame", "-w", "-M", "-C", "-C", "-C", "--line-porcelain", "-L", f"{a},{b}", sha, "--", path], capture_output=True, text=True, errors="replace", timeout=240).stdout
    except subprocess.TimeoutExpired:
        return None
    res, cur = [], None
    for l in out.splitlines():
        if re.match(r"^[0-9a-f]{40} \d+ \d+", l):
            cur = l[:40]
        elif l.startswith("\t") and cur:
            res.append((cur, l[1:].strip()))
    return res


def worker(job):
    repo, sha, ct, snaps, cts = job
    added, deleted = events_full(repo, sha)
    if not added or not deleted:
        return []
    s_prev, s_next = int(np.searchsorted(cts, ct, side="left")) - 1, int(np.searchsorted(cts, ct, side="left"))
    cons = {}
    for s in (s_prev, s_next):
        if 0 <= s < len(snaps):
            cons[s] = sqlite3.connect(f"file:{snaps[s]['db']}?mode=ro", uri=True)
    rows = []
    for a in added[:12]:
        if a["end"] - a["start"] > 400:
            continue
        bl = blame_lines(repo, sha, a["path"], a["start"], a["end"])
        if not bl:
            continue
        body = [(s, t) for s, t in bl if len(t) > 3]
        if len(body) < 3:
            continue
        f_old = sum(1 for s, _ in body if s != sha) / len(body)
        ov = [(len(a["lines"] & d["lines"]) / max(len(a["lines"]), 1), i) for i, d in enumerate(deleted)]
        best_ov, best_i = max(ov)
        ref = "move" if (f_old >= 0.5 and best_ov >= 0.5) else "new" if f_old <= 0.1 else "ambiguous"
        # M1
        jac = [(len(a["tokens"] & d["tokens"]) / max(len(a["tokens"] | d["tokens"]), 1), i) for i, d in enumerate(deleted)]
        j, ji = max(jac)
        m1 = ji if j >= 0.7 else None
        # M2
        ra = snap_row(cons[s_next], a["path"], a["name"]) if s_next in cons else None
        m2, avail = None, False
        if ra is not None and s_prev in cons:
            best = (-1, None)
            any_row = False
            for i, d in enumerate(deleted):
                rd = snap_row(cons[s_prev], d["path"], d["name"])
                if rd is None:
                    continue
                any_row = True
                cj = len(ra[1] & rd[1]) / max(len(ra[1] | rd[1]), 1) if (ra[1] or rd[1]) else 1.0
                ratio = (ra[2] + 1) / (rd[2] + 1)
                if ra[0] == rd[0] and cj >= 0.5 and 0.5 <= ratio <= 2 and cj > best[0]:
                    best = (cj, i)
            avail = any_row
            m2 = best[1]
        rows.append({"sha": sha, "name": a["name"], "path": a["path"], "ref": ref, "f_old": f_old, "ref_partner": best_i if ref == "move" else None, "m1": m1, "m2": m2, "m2_avail": avail, "partner_name": deleted[best_i]["name"], "partner_path": deleted[best_i]["path"], "m1_name": deleted[m1]["name"] if m1 is not None else None, "m2_name": deleted[m2]["name"] if m2 is not None else None})
    return rows


def main():
    repo = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    path = f"{BR.POOL}/{repo}"
    pairs = json.load(open(f"{B}/argl/links_{repo}.json"))
    snaps = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
    cts = np.load(f"{B}/blast/{repo}/snapshot_cts.npy")
    ct_of = {p["ind"]: p["ind_ct"] for p in pairs}
    causes = sorted(ct_of)
    random.Random(7).shuffle(causes)
    rows, tried = [], 0
    with ProcessPoolExecutor(max_workers=6) as ex:
        for i in range(0, len(causes), 60):
            jobs = [(path, c, ct_of[c], snaps, cts) for c in causes[i : i + 60]]
            for r in ex.map(worker, jobs):
                rows += r
            tried += 60
            ncommits = len({r["sha"] for r in rows})
            print(f"  scanned {tried} cause commits; {ncommits} with both added and deleted functions; {len(rows)} added functions blamed", flush=True)
            if ncommits >= n:
                break
    import pandas as pd
    df = pd.DataFrame(rows)
    df.to_pickle(f"{B}/blast/{repo}/rename_check.pkl")
    pos, new, amb = df[df.ref == "move"], df[df.ref == "new"], df[df.ref == "ambiguous"]
    print(f"\n{repo}: {df.sha.nunique()} commits, {len(df)} added functions: reference says move {len(pos)}, new code {len(new)}, ambiguous {len(amb)}")
    for nm, col in (("M1 token overlap", "m1"), ("M2 fingerprint + call set + size", "m2")):
        if nm.startswith("M2"):
            p_, n_ = pos[pos.m2_avail], new[new.m2_avail]
            print(f"  {nm}: snapshot data available for {len(p_)} of {len(pos)} moves and {len(n_)} of {len(new)} new functions")
        else:
            p_, n_ = pos, new
        rec = p_[col].notna().mean() if len(p_) else float("nan")
        corr = (p_[col] == p_.ref_partner).mean() if len(p_) else float("nan")
        fpr = n_[col].notna().mean() if len(n_) else float("nan")
        print(f"    recall of moves {100 * rec:.0f}% (right partner {100 * corr:.0f}%), calls new code a move {100 * fpr:.0f}% of the time")
    both = df[df.m2_avail]
    dis = (both.m1.notna() != both.m2.notna()).mean() if len(both) else float("nan")
    print(f"  M1 and M2 disagree on whether an added function is a move: {100 * dis:.0f}% (of {len(both)} with snapshot data)")
    miss = pos[pos.m1.isna() & pos.m2.isna()]
    print(f"  reference moves matched by neither method: {len(miss)} of {len(pos)} ({100 * len(miss) / max(len(pos), 1):.0f}%)")
    print("\n  examples the reference calls moves that M1 missed (name in the new place <- partner):")
    for r in pos[pos.m1.isna()].head(8).itertuples():
        print(f"    {r.name} ({r.path}) <- {r.partner_name} ({r.partner_path}); M2: {r.m2_name}")
    print("  examples M2 calls a move that M1 did not (and what the reference says):")
    for r in df[df.m2.notna() & df.m1.isna()].head(6).itertuples():
        print(f"    {r.name} <- {r.m2_name}; reference {r.ref} (lines older than the commit {100 * r.f_old:.0f}%)")
    r1 = pos.m1.notna().mean() if len(pos) else float("nan")
    p2 = pos[pos.m2_avail]
    r2 = p2.m2.notna().mean() if len(p2) else float("nan")
    fp1, fp2 = new.m1.notna().mean(), new[new.m2_avail].m2.notna().mean() if new.m2_avail.any() else float("nan")
    print("\n=== VERDICTS ===")
    print(f"  RC1 recall: M2 {100 * r2:.0f}% (needs 70%), M1 {100 * r1:.0f}% (needs 60%): {'supported' if r2 >= 0.7 and r1 >= 0.6 else 'not supported'}")
    print(f"  RC2 new code called a move: M1 {100 * fp1:.0f}%, M2 {100 * fp2:.0f}% (needs 10% or less for both): {'supported' if fp1 <= 0.1 and fp2 <= 0.1 else 'not supported'}")
    print(f"  RC3 disagreement {100 * dis:.0f}% (needs 15% or more): {'supported' if dis >= 0.15 else 'not supported'}")
    print(f"  RC4 moves neither finds {100 * len(miss) / max(len(pos), 1):.0f}% (needs 15% or less): {'supported' if len(miss) / max(len(pos), 1) <= 0.15 else 'not supported'}")
    print(f"  surprise bar (M1 recall under 40%): {'MET' if r1 < 0.4 else 'not met'}")


if __name__ == "__main__":
    main()
