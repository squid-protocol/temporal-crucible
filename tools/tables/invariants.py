#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The eight invariants of tables_spec.md. Pure: tables in, failures out; each failure names its invariant and
the row(s) by key. The build fails when `check` returns anything.

    check(tables, tree_paths) -> [str]     tables: {name: [row dict]}; tree_paths: every path of the snapshot's
                                           tree as `git ls-tree -r` lists it (duplicates kept, to be caught)
"""
from __future__ import annotations

from collections import Counter, defaultdict

import schema as S

MAX_NAMED = 25            # rows named per invariant; the count of the rest is given


def _key(table: str, row: dict) -> str:
    return f"{table}{tuple(row[k] for k in S.TABLES[table]['key'])}"


def _cap(num: int, bad: list[str]) -> list[str]:
    out = [f"invariant {num}: {b}" for b in bad[:MAX_NAMED]]
    if len(bad) > MAX_NAMED:
        out.append(f"invariant {num}: ... and {len(bad) - MAX_NAMED} more rows")
    return out


def recount(event: list[dict], pool: list[dict]) -> dict[str, dict]:
    """per outcome with a commit list: (positive files, qualifying commits, files of the largest commit) from the
    event and pool rows"""
    per: dict[str, dict[str, set]] = {o: defaultdict(set) for o in S.WITH_COMMIT_LISTS}
    for e in event:
        if e["hp"]:
            per["HP"][e["sha"]].add(e["path"])
        if e["hp_allreverts"]:
            per["HP_allreverts"][e["sha"]].add(e["path"])
        for oc, tier in S.TIER_OUTCOME.items():
            if e["hp"] and e["tier"] == tier:
                per[oc][e["sha"]].add(e["path"])
    for p in pool:
        per["control_pool"][p["sha"]].add(p["path"])
    out = {}
    for oc, by in per.items():
        files = set().union(*by.values()) if by else set()
        out[oc] = {"n_files": len(files), "n_commits": len(by), "largest": max((len(v) for v in by.values()), default=0)}
    return out


def check(t: dict[str, list[dict]], tree_paths: list[str]) -> list[str]:
    fail: list[str] = []
    file_rows = t.get("file", [])
    by_path: dict[str, list[dict]] = defaultdict(list)
    for r in file_rows:
        by_path[r["path"]].append(r)

    # 1. every path of the snapshot's tree is in `file` exactly once (and `file` holds nothing else)
    tc = Counter(tree_paths)
    bad = [f"tree path {p!r} is listed {n} times by the tree" for p, n in sorted(tc.items()) if n > 1]
    bad += [f"tree path {p!r} has no file row" for p in sorted(tc) if p not in by_path]
    bad += [f"{_key('file', rs[0])} appears {len(rs)} times" for p, rs in sorted(by_path.items()) if len(rs) > 1]
    bad += [f"{_key('file', rs[0])} is not a path of the snapshot's tree" for p, rs in sorted(by_path.items())
            if p not in tc]
    fail += _cap(1, bad)

    # 2. in_universe = 1 implies reason null, loc > 0, scanned = 1
    bad = [f"{_key('file', r)}: in_universe=1 with reason={r['reason']!r} loc={r['loc']!r} scanned={r['scanned']!r}"
           for r in file_rows if r["in_universe"]
           and not (r["reason"] is None and (r["loc"] or 0) > 0 and r["scanned"])]
    fail += _cap(2, bad)

    # 3. in_universe = 0 implies a reason from the closed list
    bad = [f"{_key('file', r)}: in_universe=0 with reason={r['reason']!r}" for r in file_rows
           if not r["in_universe"] and r["reason"] not in S.REASONS]
    bad += [f"{_key('file', r)}: reason {r['reason']!r} carries no pattern" for r in file_rows
            if r["reason"] in S.PATTERN_REASONS and not r["pattern"]]
    fail += _cap(3, bad)

    # 4. every touch, event and pool path is in `file` with in_universe = 1
    uni = {p for p, rs in by_path.items() if any(r["in_universe"] for r in rs)}
    bad = [f"{_key(tn, r)}: path not a universe file" for tn in ("touch", "event", "pool") for r in t.get(tn, [])
           if r["path"] not in uni]
    fail += _cap(4, bad)

    # 5. every event and pool commit has a touch row for each of its paths
    touched = {(r["sha"], r["path"]) for r in t.get("touch", [])}
    bad = [f"{_key(tn, r)}: no touch row" for tn in ("event", "pool") for r in t.get(tn, [])
           if (r["sha"], r["path"]) not in touched]
    fail += _cap(5, bad)

    # 6. marginal equals the recount from event (and pool), for every outcome with a commit list
    rc = recount(t.get("event", []), t.get("pool", []))
    marg = {m["outcome"]: m for m in t.get("marginal", [])}
    bad = []
    for oc in S.WITH_COMMIT_LISTS:
        m = marg.get(oc)
        if m is None:
            bad.append(f"marginal row for {oc} is missing")
            continue
        r = rc[oc]
        if m["n_files"] != r["n_files"] or m["n_commits"] != r["n_commits"]:
            bad.append(f"{_key('marginal', m)}: files {m['n_files']} commits {m['n_commits']}, recount from "
                       f"{'pool' if oc == 'control_pool' else 'event'} gives {r['n_files']} and {r['n_commits']}")
        if oc != "control_pool":
            share = r["largest"] / r["n_files"] if r["n_files"] else None
            s = m["largest_commit_share"]
            # the outcome file gives the share to three decimals: equal within half a unit of the third
            if (s is None) != (share is None) or (s is not None and abs(s - share) > 0.0005):
                bad.append(f"{_key('marginal', m)}: largest commit share {s}, recount {share}")
    fail += _cap(6, bad)

    # 7. window_end > window_start; usable commits > 0
    bad = []
    for s in t.get("snapshot", []):
        ws, we, uc = s["window_start"], s["window_end"], s["usable_commits"]
        if ws is None or we is None or not we > ws:
            bad.append(f"{_key('snapshot', s)}: window_end {we} is not after window_start {ws}")
        if not uc or uc <= 0:
            bad.append(f"{_key('snapshot', s)}: usable commits {uc}")
    if not t.get("snapshot"):
        bad.append("no snapshot row")
    fail += _cap(7, bad)

    # 8. every measure row's path is in `file`; a measure the scorer reads has a row for every universe file,
    #    with a value or with absent_means
    bad = [f"{_key('measure', r)}: path not in file" for r in t.get("measure", []) if r["path"] not in by_path]
    bad += [f"{_key('measure', r)}: no value and no absent_means" for r in t.get("measure", [])
            if r["value"] is None and r["absent_means"] not in S.ABSENT_VALUES]
    have = {(r["path"], r["name"]) for r in t.get("measure", [])}
    bad += [f"file('{p}'): no measure row for {name}" for p in sorted(uni) for name in S.SCORER_MEASURES
            if (p, name) not in have]
    fail += _cap(8, bad)
    return fail
