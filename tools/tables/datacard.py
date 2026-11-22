#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The data card of one repo, computed from its finished tables only (tables_spec.md "The data card"). Pure.

It holds counts, shares, times and GitHub linguist pattern strings, and no path, commit hash, link value or repo
name: nothing from any table's key columns is copied into it (tests/test_tables.py test 6 checks this).

    compute(tables) -> dict          markdown(card) -> str
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import PurePosixPath

import schema as S

DAY = 86400
TOP_PATTERNS = 5


def _share(a: int, b: int) -> float | None:
    return round(a / b, 4) if b else None


def _largest_dir(paths: list[str], depth: int | None, touched: set[str]) -> dict:
    """the directory holding the most of `paths`: the file's own directory (depth None), or its first `depth` path
    components (files with fewer components are under no directory at that depth). Its share of `paths`, and the
    share of its files with no touch row in the window. Ties go to the directory first in byte order. The
    directory's name is not given (the card holds no path)."""
    groups: dict[str, list[str]] = defaultdict(list)
    for p in paths:
        parts = PurePosixPath(p).parts[:-1]
        if depth is None:
            groups["/".join(parts)].append(p)
        elif len(parts) >= depth:
            groups["/".join(parts[:depth])].append(p)
    if not groups:
        return {"share": None, "untouched_in_window_share": None}
    _, fs = min(groups.items(), key=lambda kv: (-len(kv[1]), kv[0].encode("utf-8", "surrogateescape")))
    return {"share": _share(len(fs), len(paths)),
            "untouched_in_window_share": _share(sum(1 for p in fs if p not in touched), len(fs))}


def compute(t: dict[str, list[dict]]) -> dict:
    repo = t["repo"][0]
    snap = t["snapshot"][0]
    files = t["file"]
    uni = [f for f in files if f["in_universe"]]
    upaths = [f["path"] for f in uni]
    langs = set((repo["langs"] or "").split(","))
    pats = Counter(f["pattern"] for f in files if f["pattern"])
    lang_files = [f for f in files if f["language"] in langs]
    present: dict[str, int] = defaultdict(int)
    upath_set = set(upaths)
    for m in t["measure"]:
        if m["path"] in upath_set and m["value"] is not None:
            present[m["name"]] += 1
    ws, we = snap["window_start"], snap["window_end"]
    touched = {x["path"] for x in t["touch"]}
    hows = Counter(e["how"] or "undetermined" for e in t["event"])
    return {
        "schema_version": S.SCHEMA_VERSION,
        "files": {"in_tree": len(files), "in_universe": len(uni),
                  "by_reason": dict(sorted(Counter(f["reason"] for f in files if not f["in_universe"]).items()))},
        "github_patterns": {
            "files_excluded_by_a_pattern": sum(pats.values()),
            "top": [{"pattern": p, "files": n} for p, n in sorted(pats.items(), key=lambda kv: (-kv[1], kv[0]))
                    [:TOP_PATTERNS]],
            "by_pattern": dict(sorted(pats.items()))},
        "universe_files_history_cannot_touch": sum(1 for f in uni if not f["history_can_touch"]),
        "scan_completeness_against_tree": {
            "tree_files_in_language": len(lang_files),
            "scanned": sum(1 for f in lang_files if f["scanned"]),
            "in_archive": sum(1 for f in lang_files if f["in_archive"]),
            "in_universe": sum(1 for f in lang_files if f["in_universe"]),
            "scanned_share": _share(sum(1 for f in lang_files if f["scanned"]), len(lang_files)),
            "universe_share": _share(sum(1 for f in lang_files if f["in_universe"]), len(lang_files)),
            "not_in_universe_by_reason": dict(sorted(Counter(f["reason"] for f in lang_files
                                                             if not f["in_universe"]).items())),
            "pipeline_reported_complete": repo["pipeline_complete"],
            "pipeline_unit_files": repo["pipeline_unit_files"],
            "pipeline_tree_unit_files": repo["pipeline_tree_unit_files"],
            "scanned_paths_not_in_tree": repo["scanned_not_in_tree"]},
        "commits": {"walked": repo["commits"], "usable": snap["usable_commits"],
                    "bot_share": _share(repo["bots"] or 0, repo["commits"] or 0),
                    "merge_share": repo["merge_share"], "unit_rule": repo["unit_rule"],
                    "out_of_time_order_in_walk": repo["walk_out_of_time_order"]},
        "window": {"start": ws, "end": we, "length_days": round((we - ws) / DAY, 1) if ws is not None and we is not None
                   else None, "cut": snap["cut_ct"], "snapshot_time": snap["ct"]},
        "marginals": {m["outcome"]: {k: m[k] for k in ("n_files", "n_commits", "largest_commit_share", "clears_floor")}
                      for m in t["marginal"]},
        "status": repo["status"],
        "rows": {"touch": len(t["touch"]), "event": len(t["event"]), "pool": len(t["pool"]), "link": len(t["link"])},
        "event_how": dict(sorted(hows.items())),
        "largest_directory_of_universe": {"own_directory": _largest_dir(upaths, None, touched),
                                          "first_component": _largest_dir(upaths, 1, touched),
                                          "first_two_components": _largest_dir(upaths, 2, touched)},
        "universe_untouched_in_window_share": _share(sum(1 for p in upaths if p not in touched), len(upaths)),
        "measure_present_share": {n: _share(present[n], len(uni)) for n in S.SCORER_MEASURES},
        "nesting_present_share": _share(present["nest_max"], len(uni)),
    }


def markdown(c: dict) -> str:
    L = ["# Data card", "", "Computed from the stored tables only. No path, commit hash or link value appears here.", ""]
    f = c["files"]
    L += [f"**Files in the snapshot's tree:** {f['in_tree']}; in the universe: {f['in_universe']}.", "",
          "| reason not in the universe | files |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in f["by_reason"].items()]
    g = c["github_patterns"]
    L += ["", f"**Files excluded by a GitHub linguist pattern:** {g['files_excluded_by_a_pattern']}", "",
          "| pattern (top five) | files |", "|---|---|"]
    L += [f"| `{x['pattern']}` | {x['files']} |" for x in g["top"]]
    L += ["", f"**Universe files the history walk cannot touch:** {c['universe_files_history_cannot_touch']}", ""]
    s = c["scan_completeness_against_tree"]
    L += ["**Scan completeness against the tree** (files of the repo's language in the snapshot's tree, with the "
          "stored reason of each one left out; not the pipeline's own unit rule)", "",
          f"- in the tree: {s['tree_files_in_language']}; in the archive: {s['in_archive']}; scanned: {s['scanned']} "
          f"({s['scanned_share']}); in the universe: {s['in_universe']} ({s['universe_share']})",
          f"- left out, by reason: {s['not_in_universe_by_reason']}",
          f"- the pipeline's own completeness: {s['pipeline_reported_complete']} ({s['pipeline_unit_files']} of "
          f"{s['pipeline_tree_unit_files']} by its own rule); scanned paths not in the tree: "
          f"{s['scanned_paths_not_in_tree']}", ""]
    k = c["commits"]
    L += [f"**Commits:** {k['walked']} walked ({k['unit_rule']}), {k['usable']} usable; bot share {k['bot_share']}, "
          f"merge share {k['merge_share']}; out of time order in the walk: {k['out_of_time_order_in_walk']}", ""]
    w = c["window"]
    L += [f"**Window:** ({w['start']}, {w['end']}], {w['length_days']} days; cut {w['cut']}, snapshot time "
          f"{w['snapshot_time']} (Unix seconds, UTC)", "", f"**Outcome status:** {c['status']}", "",
          "| outcome | positive files | qualifying commits | largest commit's share | clears floor |",
          "|---|---|---|---|---|"]
    L += [f"| {o} | {m['n_files']} | {m['n_commits']} | {m['largest_commit_share']} | {m['clears_floor']} |"
          for o, m in c["marginals"].items()]
    d = c["largest_directory_of_universe"]
    L += ["", f"**Rows:** {c['rows']}; event rows own / inherited / undetermined: {c['event_how']}", "",
          "**Largest directory of the universe** (share of the universe; share of its files with no touch in the "
          "window)", "", "| directory taken as | share | untouched in window |", "|---|---|---|"]
    L += [f"| {k.replace('_', ' ')} | {v['share']} | {v['untouched_in_window_share']} |" for k, v in d.items()]
    L += ["", f"Universe files with no touch in the window: {c['universe_untouched_in_window_share']}", "",
          f"**Share of universe files with each measure present** (nesting: {c['nesting_present_share']})", "",
          "| measure | share |", "|---|---|"]
    L += [f"| {n} | {v} |" for n, v in c["measure_present_share"].items()]
    return "\n".join(L) + "\n"
