#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The stored tables' columns, types and key order (docs/process/tables_spec.md, phase A). Pure: imports no SA3
module and holds no rule. Key columns come first in every table; every key column is a string and never null;
every other column may be null.

Types: "str"; "int" (a real with no fractional part is accepted and written as an integer); "real" (written as
the string of float.hex()); "bool" (written as the integer 0 or 1).
"""
from __future__ import annotations

SCHEMA_VERSION = 1

# The closed reason list for file.reason. The order is the order the reasons are decided in by build.py: the
# language test of sa3_outcomes.universe first, then laws_units.Excluder.why (whose own order is vendored,
# documentation, generated, test, example), then the archive, the scan and the LOC (DECISIONS.md 3).
REASONS = ("language", "vendored", "documentation", "generated", "test", "example", "tutorial", "gitattributes",
           "not_in_archive", "not_scanned", "zero_loc")
PATTERN_REASONS = ("vendored", "documentation")      # the row carries the GitHub pattern that matched

OUTCOMES = ("HP", "HP_allreverts", "HP_revert", "HP_cve", "HP_fixref", "KW", "control_pool")
WITH_COMMIT_LISTS = ("HP", "HP_allreverts", "HP_revert", "HP_cve", "HP_fixref", "control_pool")
TIERS = ("revert", "cve", "issue_fix")               # the exclusive tier's names, as the outcome file names them
TIER_OUTCOME = {"HP_revert": "revert", "HP_cve": "cve", "HP_fixref": "issue_fix"}
HOW = ("own", "inherited")                           # null: the outcome file does not say (DECISIONS.md 9)

# The measures the scorer reads (sa3_score.load): sa3_score.COLS without mitigation_telemetry (checked against
# the module itself inside the sandbox at every build), the branch-state value amplified_cascading_flux (read
# from mitigation_telemetry; absent reads as 0), and the nesting file's two values.
SCAN_COLS = ("total_loc", "coding_loc", "pagerank_score", "betweenness_score", "struct_branch", "state_danger",
             "state_pointers", "state_memory_alloc", "def_safety", "state_flux", "state_heat_triggers",
             "risk_safety_score", "risk_tech_debt", "risk_cognitive_load", "risk_state_flux", "risk_concurrency")
TELEMETRY_COLS = ("amplified_cascading_flux",)
NEST_COLS = ("nest_max", "nest_mean")
SCORER_MEASURES = SCAN_COLS + TELEMETRY_COLS + NEST_COLS
# how sa3_score.load reads an absent value: a NULL column becomes NaN (missing); an absent telemetry key
# becomes 0 (zero); a file absent from the nesting file stays NaN (missing)
ABSENT_MEANS = {**{c: "missing" for c in SCAN_COLS}, **{c: "zero" for c in TELEMETRY_COLS},
                **{c: "missing" for c in NEST_COLS}}
ABSENT_VALUES = ("zero", "missing")


def _t(key, cols, protected=False):
    return {"key": tuple(k for k, _ in key), "columns": tuple(key) + tuple(cols), "protected": protected,
            "version": SCHEMA_VERSION}


TABLES = {
    "repo": _t([("repo", "str")],
               [("language", "str"), ("langs", "str"), ("units", "str"), ("unit_rule", "str"),
                ("first_parent", "bool"), ("status", "str"), ("why", "str"), ("pool_tip", "str"),
                ("history_head", "str"), ("engine", "str"), ("hashseed", "str"), ("commits", "int"),
                ("bots", "int"), ("merges", "int"), ("first_parent_commits", "int"), ("merge_share", "real"),
                ("walk_out_of_time_order", "int"), ("pipeline_complete", "real"),
                ("pipeline_unit_files", "int"), ("pipeline_tree_unit_files", "int"),
                ("scanned_not_in_tree", "int")]),
    "snapshot": _t([("repo", "str")],
                   [("sha", "str"), ("ct", "int"), ("cut_ct", "int"), ("window_start", "int"),
                    ("window_end", "int"), ("usable_commits", "int")]),
    "file": _t([("repo", "str"), ("path", "str")],
               [("in_universe", "bool"), ("reason", "str"), ("pattern", "str"), ("loc", "int"),
                ("language", "str"), ("scanned", "bool"), ("in_archive", "bool"), ("history_can_touch", "bool")]),
    "measure": _t([("repo", "str"), ("path", "str"), ("name", "str")],
                  [("value", "real"), ("absent_means", "str"), ("instrument", "str"), ("version", "str")]),
    "touch": _t([("repo", "str"), ("sha", "str"), ("path", "str")],
                [("ct", "int"), ("walk_pos", "int")]),
    "link": _t([("repo", "str"), ("sha", "str"), ("kind", "str"), ("value", "str")],
               [("n", "int")], protected=True),
    "event": _t([("repo", "str"), ("sha", "str"), ("path", "str")],
                [("hp", "bool"), ("hp_allreverts", "bool"), ("tier", "str"), ("how", "str")], protected=True),
    "pool": _t([("repo", "str"), ("sha", "str"), ("path", "str")], [], protected=True),
    "marginal": _t([("repo", "str"), ("outcome", "str")],
                   [("n_files", "int"), ("n_commits", "int"), ("largest_commit_share", "real"),
                    ("clears_floor", "bool")]),
}
PROTECTED = tuple(n for n, t in TABLES.items() if t["protected"])
TYPES = ("str", "int", "real", "bool")

for _n, _t_ in TABLES.items():                       # the schema's own consistency, checked at import
    assert all(t in TYPES for _, t in _t_["columns"]), _n
    assert all(dict(_t_["columns"])[k] == "str" for k in _t_["key"]), f"{_n}: key columns must be strings"
    assert len({c for c, _ in _t_["columns"]}) == len(_t_["columns"]), _n


def columns(table: str) -> tuple[str, ...]:
    return tuple(c for c, _ in TABLES[table]["columns"])
