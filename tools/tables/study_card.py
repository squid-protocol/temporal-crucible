#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The counts of SA3 Amendment 5 section 7 that phase B publishes (tables_phase_b_spec.md, counts 1-6 and 8-10;
count 7 belongs to the owner-run job), per repo and for the study. Pure: imports no SA3 module and reads no file.

    repo_counts(...)   -> one repo's counts 2-6 and 8-10 (its data card), from the predictor-side tables and
                          values computed inside the sandbox by phase_b.py
    card(...)          -> the study card: every repo's counts, count 1 from silence.py, and nothing else
    markdown(card)     -> the same as a page

A card holds numbers, booleans, Unix times, the four registered pattern strings, measure names, repo names and
the provenance strings of count 10 (hashes, engine id, unit rule). It holds no file path and no commit hash.
"""
from __future__ import annotations

from collections import Counter

ATTR_CUT = 200_000          # sa3_scan.py keeps each .gitattributes text as text[:200000] (characters, not bytes)
RULE_REASONS = ("not_in_archive", "not_scanned", "zero_loc")   # file reasons decided after the unit rule


def _share(a: int, b: int):
    return round(a / b, 4) if b else None


def repo_counts(repo: str, *, file_rows: list[dict], measure_rows: list[dict], repo_row: dict, snap_row: dict,
                frame: dict, universe_meta: dict, archive_ok: bool, archive_error: str | None,
                touch_ok: bool, tree_modes: Counter, side: dict, hmeta: dict, nest: dict,
                linguist_sha256: dict, laws_units_linguist: str, generic: dict, marginal: dict | None) -> dict:
    """One repo's counts. generic: {pattern: {"excluded_only_by": n, "with_scan_rows": n}} plus "_any" (computed
    inside the sandbox with laws_units' own Excluder, phase_b.py). marginal: the repo's row of the public frozen
    marginals file (status, drawn, HP clears_floor), or None."""
    langs = set(frame["langs"])
    uni = [r for r in file_rows if r["in_universe"]]
    drawn15 = bool(marginal and marginal.get("drawn") and marginal.get("status") == "ok"
                   and (marginal.get("HP") or {}).get("clears_floor"))
    ws, we, cut, sct = snap_row["window_start"], snap_row["window_end"], snap_row["cut_ct"], snap_row["ct"]
    c2 = {"drawn_ok_clearing_HP": drawn15, "cut": cut, "snapshot_time": sct,
          "snapshot_minus_cut_seconds": None if sct is None else sct - cut,
          "window_start_equals_cut": None if ws is None else ws == cut}
    c3 = {"window_start": ws, "window_end": we, "usable_commits": snap_row["usable_commits"],
          "window_ends_after_start": None if ws is None or we is None else we > ws,
          "usable_commits_positive": bool(snap_row["usable_commits"]) and snap_row["usable_commits"] > 0}
    # 4. completeness: the registered measure (universe()'s own figure, or "archive unavailable"), and against
    #    the snapshot's tree with the stored reasons
    lang_rows = [r for r in file_rows if r["language"] in langs]
    by_reason = Counter(r["reason"] if r["reason"] is not None else "in_universe" for r in lang_rows)
    rule_files = [r for r in lang_rows if r["reason"] is None or r["reason"] in RULE_REASONS]
    scanned_rule = [r for r in rule_files if r["scanned"]]
    reg = {"measure": "scanned unit files / unit files of `git archive` (sa3_outcomes.universe)",
           "unit_files": universe_meta.get("unit_files")}
    if archive_ok:
        reg.update({"complete": universe_meta.get("complete"), "tree_unit_files": universe_meta.get("tree_unit_files"),
                    "archive": "available"})
    else:
        reg.update({"complete": "archive unavailable", "tree_unit_files": "archive unavailable",
                    "archive": "unavailable", "archive_error": archive_error,
                    "universe_returned": {"complete": universe_meta.get("complete"),
                                          "tree_unit_files": universe_meta.get("tree_unit_files"),
                                          "note": "universe() does not check git's exit code; not a zero"}})
    c4 = {"registered": reg,
          "against_tree": {"measure": "scanned files / files of the snapshot's tree (`git ls-tree`) that pass the "
                                      "unit rule (language and laws_units.Excluder), from the file table",
                           "tree_files_in_language": len(lang_rows), "unit_rule_files": len(rule_files),
                           "unit_rule_files_scanned": len(scanned_rule), "in_universe": len(uni),
                           "complete": _share(len(scanned_rule), len(rule_files)),
                           "in_archive": (sum(1 for r in lang_rows if r["in_archive"]) if archive_ok
                                          else "archive unavailable"),
                           "by_reason": dict(sorted(by_reason.items()))}}
    c5 = generic
    c6 = {"universe_files_history_cannot_touch": (sum(1 for r in uni if not r["history_can_touch"])
                                                  if touch_ok else "history walk not run"),
          "tree_entries_not_regular_files": sum(n for m, n in tree_modes.items() if m not in ("100644", "100755")),
          "tree_entry_modes": dict(sorted(tree_modes.items())),
          "scan_paths_not_in_tree": repo_row["scanned_not_in_tree"]}
    nm = {r["path"] for r in measure_rows if r["name"] == "nest_max" and r["value"] is not None}
    c8 = {"universe_files": len(uni), "with_nesting_value": sum(1 for r in uni if r["path"] in nm),
          "share": _share(sum(1 for r in uni if r["path"] in nm), len(uni)),
          "nesting_file": ({k: nest.get(k) for k in ("measured", "not_measured", "parse_errors", "pack")}
                           if nest else "no nesting file")}
    attrs = side.get("attrs") or {}
    lens = [len(t) for t in attrs.values()]
    c9 = {"gitattributes_files": len(attrs), "longest_characters": max(lens, default=0),
          "exactly_at_cut": sum(1 for n in lens if n == ATTR_CUT), "cut_characters": ATTR_CUT,
          "reaches_cut": any(n >= ATTR_CUT for n in lens),
          "note": "a text of exactly the cut cannot be told from a truncated one"}
    c10 = {"linguist_sha256": linguist_sha256, "linguist_commit_laws_units": laws_units_linguist,
           "linguist_commit_history_meta": hmeta.get("linguist"), "history_unit_rule": hmeta.get("unit"),
           "history_units": hmeta.get("units"), "c_family": hmeta.get("units") == "c+cpp",
           "engine": side.get("engine"), "hashseed": side.get("hashseed"),
           "grammar_pack": nest.get("pack") if nest else None,
           "archive_files_in_sidecar": side.get("archive_files")}
    return {"repo": repo, "count_2": c2, "count_3": c3, "count_4": c4, "count_5": c5, "count_6": c6,
            "count_8": c8, "count_9": c9, "count_10": c10}


def count_1(silence: dict[str, dict], marginals: dict[str, dict], predictors: dict, confirmatory: tuple,
            outcomes: tuple) -> dict:
    """silence: {repo: {version: {"silent": {measure: bool}} or {"error": ...}}}. Cells (repo, measure); and the
    (repo, outcome, measure) cells the scorer would reach before its silence test, from the frozen marginals file's
    clears_floor (the scorer's own loop: non-primary predictors on HP and KW only). No outcome is read."""
    versions = ("edc5c53", "8fb7fe0")
    cells, differ, by_measure, errors = [], [], Counter(), {}
    for repo in sorted(silence):
        got = silence[repo]
        if any("silent" not in got.get(v, {}) for v in versions):
            errors[repo] = {v: got.get(v, {}).get("error", "not run") for v in versions
                            if "silent" not in got.get(v, {})}
            continue
        a, b = got["edc5c53"]["silent"], got["8fb7fe0"]["silent"]
        m = marginals.get(repo) or {}
        for p in predictors:
            oc_cells = [oc for oc in outcomes if m.get("status") == "ok" and (m.get(oc) or {}).get("clears_floor")
                        and (oc in ("HP", "KW") or predictors[p][1] == "primary")]
            row = {"repo": repo, "measure": p, "silent_edc5c53": a.get(p), "silent_8fb7fe0": b.get(p),
                   "confirmatory": p in confirmatory, "role": predictors[p][1], "is_count": predictors[p][2],
                   "scored_outcomes": oc_cells}
            cells.append(row)
            if a.get(p) != b.get(p):
                differ.append(row)
                by_measure[p] += 1
    expected = {"risk_safety_nonzero", "nest_max"}   # Amendment 4's two (the indicator; nesting depth, a count)
    return {"cells_silent_under_either": [c for c in cells if c["silent_edc5c53"] or c["silent_8fb7fe0"]],
            "cells_total": len(cells),
            "differ": differ, "differ_by_measure": dict(sorted(by_measure.items())),
            "differ_repo_outcome_measure": sum(len(c["scored_outcomes"]) for c in differ),
            "differ_outside_the_two_disclosed": [c for c in differ if c["measure"] not in expected],
            "differ_outside_the_two_disclosed_repo_outcome_measure":
                sum(len(c["scored_outcomes"]) for c in differ if c["measure"] not in expected),
            "differ_outside_count_measures_and_the_two": sorted({c["measure"] for c in differ
                                                                 if c["measure"] not in expected
                                                                 and not c["is_count"]}),
            "expected": "Amendment 4: risk_safety_nonzero and nest_max differ in most repos; defect log 46: three "
                        "count measures in 14 (repo, outcome, measure) cells besides. Anything else is unexpected.",
            "errors": errors}


def placebo_check(silence: dict[str, dict], placebo: dict | None) -> dict:
    """the 8fb7fe0 column against the `silent` values published in docs/sa3_placebo.json (primaries)"""
    if not placebo:
        return {"status": "no placebo file"}
    rows, bad = 0, []
    for repo, info in sorted(placebo.get("repos", {}).items()):
        got = silence.get(repo, {}).get("8fb7fe0", {}).get("silent")
        for p, want in sorted((info.get("silent") or {}).items()):
            rows += 1
            if got is None or got.get(p) != want:
                bad.append({"repo": repo, "measure": p, "published": want,
                            "computed": None if got is None else got.get(p)})
    return {"status": "equal" if not bad and rows else ("no rows" if not rows else "DIFFERS"), "compared": rows,
            "differ": bad}


def card(per_repo: dict[str, dict], c1: dict | None, placebo: dict | None, run: dict) -> dict:
    return {"what": "SA3 Amendment 5 section 7 counts, phase B (predictor side only); count 7 is the owner-run "
                    "job's", "run": run, "count_1": c1, "count_1_placebo_check": placebo,
            "repos": per_repo}


def markdown(c: dict) -> str:
    out = ["# SA3 counts before scoring, phase B (predictor side)", "",
           "Counts 1-6 and 8-10 of Amendment 5 section 7 (tables_phase_b_spec.md). Count 7 is produced by the "
           "owner-run job. No outcome was bound into any sandbox that produced these numbers.", ""]
    out += ["| repo | cut | window start = cut | window ends after start | usable commits | registered complete | "
            "against tree | generic dirs restorable (with scan rows) | universe untouchable | not regular | "
            "nesting share | .gitattributes longest |", "|" + "---|" * 12]
    for repo, k in sorted(c["repos"].items()):
        if "count_2" not in k:
            out.append(f"| {repo} | {k.get('status', 'not built')} |" + " |" * 10)
            continue
        g = k["count_5"].get("_any", {})
        out.append(f"| {repo} | {k['count_2']['cut']} | {k['count_2']['window_start_equals_cut']} | "
                   f"{k['count_3']['window_ends_after_start']} | {k['count_3']['usable_commits']} | "
                   f"{k['count_4']['registered']['complete']} | {k['count_4']['against_tree']['complete']} | "
                   f"{g.get('excluded_only_by')} ({g.get('with_scan_rows')}) | "
                   f"{k['count_6']['universe_files_history_cannot_touch']} | "
                   f"{k['count_6']['tree_entries_not_regular_files']} | {k['count_8']['share']} | "
                   f"{k['count_9']['longest_characters']} |")
    c1 = c.get("count_1")
    if c1:
        out += ["", "## Count 1: silence under the rule as at edc5c53 and as at 8fb7fe0", "",
                f"(repo, measure) cells: {c1['cells_total']}; silent under either rule: "
                f"{len(c1['cells_silent_under_either'])}; differing: {len(c1['differ'])} "
                f"({c1['differ_repo_outcome_measure']} (repo, outcome, measure) cells); outside the two disclosed "
                f"measures: {len(c1['differ_outside_the_two_disclosed'])} "
                f"({c1['differ_outside_the_two_disclosed_repo_outcome_measure']} (repo, outcome, measure) cells)", "",
                "| measure | repos where the two rules differ |", "|---|---|"]
        out += [f"| {m} | {n} |" for m, n in c1["differ_by_measure"].items()]
        if c1["errors"]:
            out += ["", f"not computed: {c1['errors']}"]
    pc = c.get("count_1_placebo_check")
    if pc:
        out += ["", f"Placebo check (8fb7fe0 column against docs/sa3_placebo.json): {pc.get('status')}, "
                    f"{pc.get('compared', 0)} values compared, {len(pc.get('differ', []))} differ"]
    return "\n".join(out) + "\n"
