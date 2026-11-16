#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Layer 3, the cell map (docs/process/comparison_scorer_spec.md, section 5).

The reference's result file and the comparison scorer's result, both read as JSON, are compared key by key,
every leaf a cell. Equality is exact: the same JSON type (a whole number is not equal to a real, true is not 1)
and, for a real, the same 64 bits; a missing number (NaN) equals a missing number, null equals null, and a key
present on one side only is "not equal" (a cell of "which cells exist"). An empty object or list is a cell of
its own. Key ORDER is not compared: "which cells exist" is a set (the order of `repos` follows the stream and is
seen through the R cells).

Classes (the spec's table; the review's table of result keys):

  W  words, sets and whole numbers that use no random draw: a cell's status; which cells exist; n, files
     dropped; summaries' n / positive / negative / reading; the bookkeeping keys sealed, engine, not_run,
     unavailable, valid
  D  real numbers that use no random draw: bauc, residual, nonzero_share, the sensitivity statistics, minus the
     surrogate, the bootstrap interval, every summary of these; holm_level; the sign test's p
  R  anything that uses the shared stream: null_sd, perm_p, specificity (the matched control) and its
     summaries, random_effects, side_counts above / below / across, the confirmatory tests' readings and
     minus_control, allreverts_reading

The existence of a cell is class W, except under an R container (specificity, random_effects, minus_control
summaries, the optional allreverts_reading), where it is R.

Every not-equal cell counts and fails; none is excused. The first not-equal R cell in loop order (per repo: its
outcome cells in loop order, then its control; then the study-level cells) is named by position (repo, outcome,
predictor); later ones are marked "may follow from the first" and still counted; and "R cells equal after it"
are counted (all equal after it: a local fault; none equal: a slip of the stream).
"""
from __future__ import annotations

import json
import math
import struct
from pathlib import Path

EMPTY_DICT, EMPTY_LIST = ("<empty object>",), ("<empty list>",)
SUMMARY_WORDS = ("n", "positive", "negative", "reading")
CELL_D = ("bauc", "nonzero_share", "residual", "S4_replaces", "S6_sauc_minus", "S9_logistic_z", "S7_tight", "ci95",
          "minus_surrogate")
CELL_R = ("null_sd", "perm_p")
CELL_W = ("status", "dropped_null")


def flatten(obj, path=()) -> list[tuple[tuple, object]]:
    """(path, leaf) in the object's own order; an empty container is a leaf of its own"""
    out = []
    if isinstance(obj, dict):
        if not obj:
            out.append((path, EMPTY_DICT))
        for k, v in obj.items():
            out += flatten(v, path + (k,))
    elif isinstance(obj, list):
        if not obj:
            out.append((path, EMPTY_LIST))
        for i, v in enumerate(obj):
            out += flatten(v, path + (i,))
    else:
        out.append((path, obj))
    return out


def classify(path: tuple) -> str:
    """the class of a cell by its path (W, D or R)"""
    if not path:
        return "W"
    top = path[0]
    if top in ("valid", "unavailable", "sealed", "engine", "not_run"):
        return "W"
    if top == "repos":
        if len(path) < 3 or path[2] == "n":
            return "W"
        if path[2] == "specificity":
            return "R"
        if path[2] == "outcomes":
            if len(path) < 6:
                return "W"
            k = path[5]
            if k in CELL_R:
                return "R"
            if k in CELL_D:
                return "D"
            return "W"
        return "W"
    if top == "tests":
        if len(path) < 3:
            return "W"
        p, k = path[1], path[2]
        if p == "in_degree":
            if k in ("exploratory", "reading"):
                return "W"
            return "W" if len(path) > 3 and path[3] in SUMMARY_WORDS else ("D" if len(path) > 3 else "W")
        if k in ("minus_control", "reading", "allreverts_reading"):
            return "R"
        if k == "holm_level":
            return "D"
        if k in ("bauc", "residual", "allreverts"):
            return "W" if len(path) > 3 and path[3] in SUMMARY_WORDS else ("D" if len(path) > 3 else "W")
        return "W"
    if top == "side_counts":
        if len(path) > 2 and path[2] == "sign_test_p":
            return "D"
        return "R"
    if top == "random_effects":
        return "R"
    if top == "summaries":
        if len(path) < 2:
            return "W"
        stat = str(path[1]).split("|")[2] if str(path[1]).count("|") == 3 else ""
        if stat == "minus_control":
            return "R"
        if len(path) < 3:
            return "W"
        return "W" if path[2] in SUMMARY_WORDS else "D"
    return "W"


def existence_class(path: tuple) -> str:
    return "R" if classify(path) == "R" else "W"


def same(a, b) -> bool:
    """exact equality of two JSON leaves"""
    if type(a) is not type(b):
        return False
    if isinstance(a, float):
        if math.isnan(a) and math.isnan(b):
            return True
        return struct.pack("<d", a) == struct.pack("<d", b)
    return a == b


def position(path: tuple) -> tuple:
    """(repo, outcome, predictor) for a repo's cells; (repo, "control", predictor) for its matched control;
    ("study", section, key) for the study-level cells"""
    if path and path[0] == "repos" and len(path) > 1:
        if len(path) > 2 and path[2] == "outcomes":
            return (path[1],) + tuple(str(x) for x in path[3:5])
        if len(path) > 2 and path[2] == "specificity":
            return (path[1], "control") + tuple(str(x) for x in path[3:4])
        return (path[1],) + tuple(str(x) for x in path[2:3])
    return ("study",) + tuple(str(x) for x in path[:2])


def cell_map(ref: dict, cmp: dict) -> dict:
    a, b = flatten(ref), flatten(cmp)
    da, db = dict(a), dict(b)
    order = [p for p, _ in a] + [p for p, _ in b if p not in da]
    counts = {c: {"equal": 0, "not_equal": 0} for c in "WDR"}
    per_repo: dict = {}
    cells = []
    for p in order:
        if p in da and p in db:
            cls, ok, kind = classify(p), same(da[p], db[p]), "value"
        else:
            cls, ok, kind = existence_class(p), False, "only in the reference" if p in da else "only in the comparison"
        counts[cls]["equal" if ok else "not_equal"] += 1
        if p and p[0] == "repos" and len(p) > 1:
            pr = per_repo.setdefault(p[1], {c: {"equal": 0, "not_equal": 0} for c in "WDR"})
            pr[cls]["equal" if ok else "not_equal"] += 1
        cells.append((p, cls, ok, kind))
    first_r, after_eq, after_ne = None, 0, 0
    not_equal = []
    for p, cls, ok, kind in cells:
        if cls == "R" and first_r is not None:
            if ok:
                after_eq += 1
            else:
                after_ne += 1
        if not ok:
            note = None
            if cls == "R":
                if first_r is None:
                    first_r = position(p)
                    note = "first not-equal R cell"
                else:
                    note = "may follow from the first"
            not_equal.append({"cell": [str(x) for x in p], "position": list(position(p)), "class": cls,
                              "kind": kind, "note": note})
    return {"classes": counts, "per_repo": per_repo, "cells": len(cells),
            "all_equal": not not_equal, "first_R": list(first_r) if first_r else None,
            "R_after_first": {"equal": after_eq, "not_equal": after_ne}, "not_equal": not_equal}


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def render(m: dict, max_cells: int = 40) -> str:
    """counts per class and per repo; the first not-equal R cell by position; the not-equal cells by position
    (keys only, never a value)"""
    L = [f"cells {m['cells']}: " + ", ".join(f"{c} {v['equal']} equal / {v['not_equal']} not equal"
                                              for c, v in m["classes"].items())]
    for r, v in m["per_repo"].items():
        L.append(f"  {r}: " + ", ".join(f"{c} {x['equal']}/{x['not_equal']}" for c, x in v.items()))
    if m["first_R"]:
        L.append(f"first not-equal R cell at {' / '.join(m['first_R'])}; R cells after it: "
                 f"{m['R_after_first']['equal']} equal, {m['R_after_first']['not_equal']} not equal")
    for c in m["not_equal"][:max_cells]:
        L.append(f"  not equal [{c['class']}] {'.'.join(c['cell'])} ({c['kind']}){'; ' + c['note'] if c['note'] else ''}")
    if len(m["not_equal"]) > max_cells:
        L.append(f"  ... and {len(m['not_equal']) - max_cells} more")
    L.append("ALL EQUAL" if m["all_equal"] else "NOT ALL EQUAL")
    return "\n".join(L) + "\n"
