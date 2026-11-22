#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Section 2 of docs/process/comparison_scorer_spec.md: each predictor derived from the stored tables, by the
written rules (transcribed from the reference loader, not derived from the registration).

    d = derive(repo, phase_b_rows, compare_rows, stats, labels=None)

phase_b_rows: {"repo", "file", "measure"} rows of tools/tables/ phase B (decoded: a real is a float);
compare_rows: {"call_degree", "flux"} of tools/compare/tables.py; stats: the sealed statistics module (only its
`bands` is used here); labels: the five label tables, or None (predictor side only).

The result has the reference loader's shape (`sa3_score.load`): paths, loc, lg, n, band, k, x, and with labels
y, hp_commits, pool (ordered: commit -> list of universe indices). Missing values are NaN.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
if "tools_compare__util" not in sys.modules:
    import importlib.util as _iu
    _s = _iu.spec_from_file_location("tools_compare__util", str(HERE / "_util.py"))
    _m = _iu.module_from_spec(_s)
    sys.modules["tools_compare__util"] = _m
    _s.loader.exec_module(_m)
U = sys.modules["tools_compare__util"]
T = U.sibling("tables")

# Copied exactly from tools/sa3_score.py (PREDICTORS): name -> (instrument, role, is a count). The order is the
# order in which predictors are scored; a test compares this literal with the reference's, read by ast.
PREDICTORS = {
    "in_degree": ("A", "primary", True), "in_degree_per_loc": ("A", "secondary", False),
    "out_degree": ("A", "secondary", True), "pagerank_score": ("A", "secondary", False),
    "betweenness_score": ("A", "secondary", False),
    "struct_branch": ("B", "primary", True), "struct_branch_per_loc": ("B", "secondary", False),
    "state_danger": ("B", "secondary", True), "state_pointers_alloc": ("B", "secondary", True),
    "def_safety": ("B", "secondary", True), "state_flux": ("B", "secondary", True),
    "nest_max": ("B", "secondary", True), "nest_mean": ("B", "secondary", False),
    "risk_safety_score": ("C", "primary", False), "risk_tech_debt": ("C", "secondary", False),
    "risk_cognitive_load": ("C", "secondary", False), "risk_state_flux": ("C", "secondary", False),
    "risk_concurrency": ("C", "secondary", False), "risk_safety_nonzero": ("C", "secondary", False),
    "risk_safety_among_nonzero": ("C", "secondary", False),
    "amplified_cascading_flux": ("D", "primary", True), "amplified_cascading_flux_per_loc": ("D", "secondary", False),
    "state_heat_triggers": ("D", "secondary", True),
}
PRIMARIES = [k for k, v in PREDICTORS.items() if v[1] == "primary"]
INDICATOR = "risk_safety_nonzero"
OUTCOMES = T.SCORED


class DeriveError(ValueError):
    """the tables cannot give the arrays; the message carries counts only, never a path or a value"""


def universe(file_rows: list[dict]) -> list[str]:
    """the `file` rows with in_universe = 1, in Python string order"""
    return sorted(r["path"] for r in file_rows if r["in_universe"])


def derive(repo: str, pb: dict, cmp: dict, stats, labels: dict | None = None) -> dict:
    paths = universe([r for r in pb["file"] if r["repo"] == repo])
    ix = {p: i for i, p in enumerate(paths)}
    n = len(paths)
    meas: dict[str, dict[str, float | None]] = {}
    for r in pb["measure"]:
        if r["repo"] == repo and r["path"] in ix:
            meas.setdefault(r["name"], {})[r["path"]] = r["value"]

    def col(name: str) -> np.ndarray:
        """a measure for every universe file: its value, NaN where the value is null or the row is absent"""
        got = meas.get(name, {})
        return np.array([np.nan if got.get(p) is None else float(got[p]) for p in paths], dtype=np.float64)

    loc = col("total_loc")
    if np.isnan(loc).any() or not (loc > 0).all():
        raise DeriveError(f"{int(np.isnan(loc).sum() + (loc <= 0).sum())} universe file(s) with no size above zero")
    indeg, outdeg = np.zeros(n), np.zeros(n)
    for r in cmp["call_degree"]:
        i = ix.get(r["path"]) if r["repo"] == repo else None
        if i is not None:
            indeg[i], outdeg[i] = float(r["in_degree"]), float(r["out_degree"])
    acf = np.full(n, np.nan)
    flagged = 0
    seen_flux = 0
    for r in cmp["flux"]:
        i = ix.get(r["path"]) if r["repo"] == repo else None
        if i is None:
            continue
        seen_flux += 1
        flagged += int(bool(r["loader_stops"]))
        if r["special"] == "inf":
            acf[i] = math.inf
        elif r["special"] == "-inf":
            acf[i] = -math.inf
        elif r["value"] is not None:
            acf[i] = float(r["value"])
    rs = col("risk_safety_score")
    x = {
        "in_degree": indeg,
        "in_degree_per_loc": indeg / loc,
        "out_degree": outdeg,
        "pagerank_score": col("pagerank_score"),
        "betweenness_score": col("betweenness_score"),
        "struct_branch": col("struct_branch"),
        "struct_branch_per_loc": col("struct_branch") / loc,
        "state_danger": col("state_danger"),
        "state_pointers_alloc": col("state_pointers") + col("state_memory_alloc"),   # NaN if either is
        "def_safety": col("def_safety"),
        "state_flux": col("state_flux"),
        "nest_max": col("nest_max"),
        "nest_mean": col("nest_mean"),
        "risk_safety_score": rs,
        "risk_tech_debt": col("risk_tech_debt"),
        "risk_cognitive_load": col("risk_cognitive_load"),
        "risk_state_flux": col("risk_state_flux"),
        "risk_concurrency": col("risk_concurrency"),
        "risk_safety_nonzero": np.array([np.nan if v != v else (1.0 if v > 0 else 0.0) for v in rs]),
        "risk_safety_among_nonzero": np.array([v if v > 0 else np.nan for v in rs]),
        "amplified_cascading_flux": acf,
        "amplified_cascading_flux_per_loc": acf / loc,
        "state_heat_triggers": col("state_heat_triggers"),
    }
    assert list(x) == sorted(x, key=list(PREDICTORS).index)
    band, k = stats.bands(loc, paths)
    repo_row = next((r for r in pb["repo"] if r["repo"] == repo), {})
    d = {"repo": repo, "paths": paths, "loc": loc, "lg": np.log(loc), "n": n, "band": band, "k": k,
         "x": {p: x[p] for p in PREDICTORS}, "engine": repo_row.get("engine"),
         "flux_flagged": flagged, "flux_rows_in_universe": seen_flux}
    if labels is not None:
        d.update(label_side(repo, labels, ix, n))
    return d


def label_side(repo: str, lab: dict, ix: dict, n: int) -> dict:
    """y per outcome, and the primary outcome's commits and the control pool as ordered commit -> indices"""
    y = {oc: np.zeros(n, int) for oc in OUTCOMES}
    bad = 0
    for r in lab["outcome_file"]:
        if r["repo"] != repo:
            continue
        i = ix.get(r["path"])
        if i is None:
            bad += 1
            continue
        y[r["outcome"]][i] = 1
    if bad:
        raise DeriveError(f"{bad} outcome file row(s) are not universe files")

    def ordered(ct: str, cft: str) -> dict:
        rows = T.commits_in_order([r for r in lab[ct] if r["repo"] == repo], [r for r in lab[cft] if r["repo"] == repo])
        out, miss = {}, 0
        for sha, ps in rows:
            idx = []
            for p in ps:
                if p in ix:
                    idx.append(ix[p])
                else:
                    miss += 1
            out[sha] = idx
        if miss:
            raise DeriveError(f"{miss} commit path(s) are not universe files")
        return out

    return {"y": y, "hp_commits": ordered("hp_commit", "hp_commit_file"),
            "pool": ordered("pool_commit", "pool_commit_file")}


def silent(x: np.ndarray, name: str) -> bool:
    """section 2: no present value; or fewer than 10% of present values non-zero; or, for a predictor that is
    not a count and not the yes/no indicator, fewer than 20 distinct present values"""
    v = x[~np.isnan(x)]
    if len(v) == 0:
        return True
    if np.count_nonzero(v) / len(v) < 0.10:
        return True
    continuous = not PREDICTORS[name][2] and name != INDICATOR
    return bool(continuous and len(set(v.tolist())) < 20)


def in_use(d: dict, p: str, stats) -> tuple[np.ndarray, np.ndarray, int]:
    """the files with a value for p, and the bands recomputed on them (5 or 10 by the number in use); with no
    missing value, the universe's own bands"""
    valid = ~np.isnan(d["x"][p])
    if valid.all():
        return np.arange(d["n"]), d["band"], d["k"]
    idx = np.flatnonzero(valid)
    band, k = stats.bands(d["loc"][idx], [d["paths"][i] for i in idx])
    return idx, band, k


def load_dirs(pb_dir: Path, cmp_dir: Path, label_dir: Path | None = None) -> tuple[dict, dict, dict | None]:
    """one repo's tables from phase B's output directory, this module's predictor tables and (optionally) its
    label tables; each directory holds an index.json"""
    import json
    C = U.canon()
    import importlib
    S = sys.modules.get("schema") or importlib.import_module("schema")
    idx = json.loads((Path(pb_dir) / "index.json").read_text())
    pb = {}
    for name in ("repo", "file", "measure"):
        rows = C.read_rows(Path(pb_dir) / idx["tables"][name]["file"])
        reals = [c for c, t in S.TABLES[name]["columns"] if t == "real"]
        pb[name] = [{**r, **{c: (None if r[c] is None else float.fromhex(r[c])) for c in reals}} for r in rows]
    cmp = T.read_dir(cmp_dir)
    lab = T.read_dir(label_dir) if label_dir is not None else None
    return pb, cmp, lab
