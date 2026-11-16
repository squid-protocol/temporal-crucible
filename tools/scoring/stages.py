#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The scoring job's stages (docs/process/scoring_step_spec.md section 3). INSIDE the read-only sandbox only:
`score_sa3.py stage NAME --rundir D --args F` checks the mount table first, then calls one function here.

This file is loaded from the fresh clone at the pinned commit (`<protected>/clone/tools/scoring/stages.py`), and
every module it uses is loaded from the same clone: the reference scorer from `<clone>/tools`, tools/compare/ and
tools/owner/ by file under the names their own loaders give them. Nothing here edits, patches or wraps the
reference; each function calls it, or calls tools/compare/ as a library, and returns counts, words and hashes
for a fixed shape (tools/scoring/schema.py). Arrays, tables, outcome files and the comparison's result stay in the
stage's directory, which lies in the protected directory.

  lock       the reference `stage_lock()`, unchanged (step 7)
  score      the reference `stage_score()`, unchanged, ONCE (step 9)
  rehearse   tools/compare/input_check.py's loader stage: the reference `load(repo, True)` with the real outcome
             file bound; its arrays stay here (step 6)
  labels     the five label tables of every ok repo from its outcome file (tables.label_rows), then the label side
             of the input check against the rehearsal's arrays (step 11)
  compare    the comparison scorer on the tables, reading its sealed copies from the clone; the cell map against
             the clone's result file (step 12)
  readings   the corrected readings beside the result (reading.beside, allreverts_same_repos) (step 13)
  named      PU_named_streams (variants.score_named) against the frozen run (step 13)
  hv_prepare the owner job's copy and the two stripped harvests of one repo (harvest_variant.stage_prepare)
  hv_build   the reference outcome builder, unchanged, on one harvest copy (harvest_variant.stage_build)
  variant    one harvest variant: the rebuilt files where the builder reproduces the frozen file, label tables in
             the frozen order, floors from the rebuilt files, scored on named streams; against PU_named_streams
"""
from __future__ import annotations

import copy
import importlib.util
import json
import math
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent


class StageFailed(Exception):
    """a stage's own refusal, carrying a code of the fixed lists"""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def load_path(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        del sys.modules[name]
        raise
    return mod


def compare(name: str):
    """tools/compare/<name>.py of this tree under the name tools/compare's own loader gives it"""
    load_path(TOOLS / "compare" / "_util.py", "tools_compare__util")
    return load_path(TOOLS / "compare" / f"{name}.py", f"tools_compare_{name}")


def owner(name: str):
    return load_path(TOOLS / "owner" / f"{name}.py", f"tools_owner_{name}")


def reference(tools: Path):
    """the reference scorer from this tree's tools/, imported as itself (its own imports are by bare name)"""
    tools = Path(tools).resolve()
    if tools != TOOLS.resolve():
        raise StageFailed("code_differs")
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    import sa3_score as SC                                      # noqa: PLC0415
    if Path(SC.__file__).resolve().parent != tools:
        raise StageFailed("code_differs")
    return SC


def _planted(a: dict) -> None:
    """TESTS ONLY, decoys only (the launcher refuses the variable on a real run): a planted exception"""
    if a.get("planted_failure"):
        raise RuntimeError("planted failure (decoy test)")


def _f(v):
    return None if v is None or not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) \
        else float(v)


# ================================================================================================ the reference
def st_lock(a: dict, rundir: Path) -> dict:
    SC = reference(Path(a["tools"]))
    return {"rc": int(SC.stage_lock())}


def st_score(a: dict, rundir: Path) -> dict:
    SC = reference(Path(a["tools"]))
    if (SC.DOCS / "sa3_result.json").exists():
        raise StageFailed("result_exists")
    return {"rc": int(SC.stage_score())}


def st_rehearse(a: dict, rundir: Path) -> dict:
    IC = compare("input_check")
    sub = rundir / "loader"
    sub.mkdir()
    IC.stage(["--repo", a["repo"], "--ref", a["ref"], "--rundir", str(sub), "--labels"])
    res = json.loads((sub / "result.json").read_text())
    if res.get("status") != "ok":
        raise StageFailed(res.get("code") or "unclassified")
    return {"loader": "none"}


# ======================================================================================= after the score
def st_labels(a: dict, rundir: Path) -> dict:
    _planted(a)
    SR = owner("prepare").SR
    T, D, IC, U = compare("tables"), compare("derive"), compare("input_check"), compare("_util")
    out = rundir / "labels"
    for r in a["repos"]:
        built = T.label_rows(r, json.loads((SR.STUDY / "sa3_outcomes" / f"{r}.json").read_text()))
        od = out / r
        written = T.write(od, built["rows"])
        T.write_index(od, {"repo": r, "repeated_paths": built["repeated_paths"],
                           "repeated_files": built["repeated_files"], "built_by": "tools/scoring/stages.py"}, written)
    stats = U.load_sealed_stats(Path(a["sealed"]))
    chk = {"repos": {}, "repos_checked": 0, "all_equal": True}
    for r in a["repos"]:
        rec = {"code": "none", "comparable": None, "items": {i: None for i in IC.LABEL_ITEMS}}
        try:
            ld = json.loads((Path(a["rehearse"]) / r / "loader" / "loader.json").read_text())
            pb, cmp, lab = D.load_dirs(Path(a["pb"]) / r, Path(a["ct"]) / r, out / r)
            rec.update(IC.compare_label(ld, D.derive(r, pb, cmp, stats, lab)))
        except Exception as e:                                  # noqa: BLE001  its type, never its text
            rec["code"] = IC.code_of(e)
        chk["repos"][r] = rec
        chk["repos_checked"] += 1
        chk["all_equal"] = chk["all_equal"] and rec["code"] == "none" and rec["comparable"] is True and \
            all(v is True for v in rec["items"].values())
    return {"label_check": chk}


def _data(a: dict, labels: Path | None = None) -> dict:
    SCO = compare("scorer")
    return SCO.load_data(Path(a["pb"]), Path(a["ct"]), Path(labels or a["lt"]), Path(a["sealed"]))


def _result(a: dict) -> dict:
    return json.loads((Path(a["sealed"]) / "docs" / "sa3_result.json").read_text())


def st_compare(a: dict, rundir: Path) -> dict:
    _planted(a)
    SCO, CM = compare("scorer"), compare("cellmap")
    text = SCO.dumps(SCO.Scorer(Path(a["sealed"]), _data(a)).score())
    (rundir / "comparison.json").write_text(text)
    m = CM.cell_map(_result(a), json.loads(text))
    (rundir / "cellmap.json").write_text(json.dumps(m, indent=1) + "\n")      # the cells, protected only
    by = {c: sum(1 for x in m["not_equal"] if x["class"] == c) for c in "WDR"}
    return {"cellmap": {"classes": m["classes"], "per_repo": m["per_repo"], "cells": m["cells"],
                        "all_equal": m["all_equal"], "first_R": m["first_R"], "R_after_first": m["R_after_first"],
                        "not_equal": len(m["not_equal"]), "not_equal_by_class": by}}


def st_readings(a: dict, rundir: Path) -> dict:
    _planted(a)
    R, SCO = compare("reading"), compare("scorer")
    res = _result(a)
    bes = R.beside(res)
    marg = json.loads((Path(a["sealed"]) / "docs" / "sa3_outcome_marginals.json").read_text())
    allr = R.allreverts_same_repos(res, marg, SCO.Scorer.summarize, {n: v["corrected"] for n, v in bes.items()})
    tests, _gate = R.tests_from_result(res)
    ap = R.applies(tests)
    (rundir / "applies.json").write_text(json.dumps(ap) + "\n")
    return {"beside": bes,
            "allreverts": {n: {"repos_where_both_clear": int(v["repos_where_both_clear"]), "n": int(v["n"]),
                               "mean": _f(v["mean"]),
                               "ci": None if v["ci"] is None or any(_f(x) is None for x in v["ci"])
                               else [float(v["ci"][0]), float(v["ci"][1])],
                               "word": v["word"], "tracks_reverts": bool(v["tracks_reverts"])}
                           for n, v in allr.items()},
            "applies": {"change1": bool(ap["change1"]), "change2": bool(ap["change2"])}}


def _block(b: dict) -> dict:
    """a variant block in the fixed shape: every difference carries mean, lo, hi (null where absent); numbers that
    are not finite are null"""
    rows = []
    for r in b["rows"]:
        d = r["difference"]
        rows.append({"outcome": r["outcome"], "predictor": r["predictor"], "n": int(r["n"]), "mean": _f(r["mean"]),
                     "ci": None if r["ci"] is None or any(_f(x) is None for x in r["ci"])
                     else [float(r["ci"][0]), float(r["ci"][1])],
                     "word": r["word"],
                     "difference": {"n": int(d["n"]), "mean": _f(d.get("mean")), "lo": _f(d.get("lo")),
                                    "hi": _f(d.get("hi"))}})
    return {"name": b["name"], "status": b["status"], "baseline": b["baseline"], "rows": rows}


def st_named(a: dict, rundir: Path) -> dict:
    _planted(a)
    V = compare("variants")
    named = V.score_named(Path(a["sealed"]), _data(a))
    (rundir / "named.json").write_text(json.dumps(named, indent=1) + "\n")
    return {"block": _block(V.block("PU_named_streams", named, _result(a), "the frozen run"))}


def st_hv_prepare(a: dict, rundir: Path) -> dict:
    _planted(a)
    HV = compare("harvest_variant")
    res = HV.stage_prepare({"repo": a["repo"]}, rundir)
    return {"deleted": {"case": int(res["aprime"]["deleted_rows"]), "late": int(res["late"]["deleted_rows"])},
            "meta_kept": {"case": bool(res["aprime"]["meta_kept"]), "late": bool(res["late"]["meta_kept"])}}


def st_hv_build(a: dict, rundir: Path) -> dict:
    HV = compare("harvest_variant")
    RP = owner("report")
    s = HV.stage_build({"repo": a["repo"], "ref_tools": a["ref_tools"]}, rundir)["build_status"]
    return {"build_status": s if s in RP.BUILD_STATUSES else "build_status_other"}


def st_variant(a: dict, rundir: Path) -> dict:
    """variants.variant_inputs and the scoring of variants.run, from the outcome files the hv_* stages built"""
    _planted(a)
    SR = owner("prepare").SR
    V, HV, T = compare("variants"), compare("harvest_variant"), compare("tables")
    name = HV.VARIANTS[a["which"]]
    lt = rundir / "labels"
    shutil.copytree(a["lt"], lt)
    od = rundir / "outcomes"
    od.mkdir()
    marg = copy.deepcopy(json.loads((Path(a["sealed"]) / "docs" / "sa3_outcome_marginals.json").read_text()))
    info = {}
    for r, rec in a["repos"].items():
        if not rec["deleted"]:
            info[r] = {"deleted_rows": 0, "applied": False, "reason": V_REASONS[0]}
            continue
        frozen = json.loads((SR.STUDY / "sa3_outcomes" / f"{r}.json").read_text())
        plain = json.loads(Path(rec["plain"]).read_text())
        if HV.comparable(plain) != HV.comparable(frozen):
            info[r] = {"deleted_rows": int(rec["deleted"]), "applied": False, "reason": V_REASONS[1]}
            continue
        new = HV.reorder(frozen, json.loads(Path(rec["rebuilt"]).read_text()))
        (od / f"{r}.json").write_text(json.dumps(new) + "\n")
        shutil.rmtree(lt / r)
        T.build_label_tables(od, [r], lt)
        V.apply_rebuilt(marg, r, new)
        info[r] = {"deleted_rows": int(rec["deleted"]), "applied": True, "reason": V_REASONS[2]}
    named = json.loads(Path(a["named"]).read_text())
    if not any(v["applied"] for v in info.values()):
        result = named                                          # no input changed: the baseline's inputs
    else:
        result = V.score_named(Path(a["sealed"]), _data(a, lt), marg)
    (rundir / "variant.json").write_text(json.dumps(result, indent=1) + "\n")
    return {"block": _block(V.block(name, result, named, "PU_named_streams")), "inputs": info}


# the three reasons variants.variant_inputs gives, in its words
V_REASONS = ("no row deleted: the frozen file stands",
             "the builder does not reproduce the frozen file from the unmodified copy: the frozen file stands",
             "rebuilt")

STAGES = {"lock": st_lock, "score": st_score, "rehearse": st_rehearse, "labels": st_labels, "compare": st_compare,
          "readings": st_readings, "named": st_named, "hv_prepare": st_hv_prepare, "hv_build": st_hv_build,
          "variant": st_variant}
