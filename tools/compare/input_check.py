#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Layer 1, the input check (docs/process/comparison_scorer_spec.md, section 3).

Predictor side, before scoring, no label present. Per repo of the marginals file with status `ok`:

  1. phase B's copy stage (tools/tables/phase_b.py, unchanged), in tools/harness/sandbox_ro.py's sandbox with the
     repo's declared inputs: the two databases copied, checkpointed, set to rollback mode;
  2. this module's `stage`, in a second such sandbox: the copies, the sidecar and the nesting file at their study
     paths, a STUB outcome file at sa3_outcomes/<repo>.json (tools/tables/silence.stub: every list empty), no
     clone, no label: the reference `sa3_score.load(repo, True)` is called unchanged from a copy of the tree under
     test, and its arrays are written to the stage's scratch directory;
  3. outside any sandbox, in this process: the same arrays from the tables (derive.py), and the comparison.

Compared, each "equal" or "not equal" (null: not compared, when the universe differs): the universe's paths and
order; size; every file's band; the band count; every predictor element by element, missing values in the same
places (`x:<name>`); its silence (`silent:<name>`, the reference's `silent` against section 2's rule); and the
files in use with their recomputed bands (`in_use:<name>`, the reference's `design_for` against section 2).
Equality is numpy's array_equal with equal_nan: exact, NaN equal to NaN, 0.0 equal to -0.0.

The public output is, per repo, that fixed list of items and the count of flagged `flux` rows among the
universe's files, and a stage code; nothing else. It is validated by tools/owner/report.py's `check` (imported by
file, not edited) against this module's schema before it is written: no path, no value, no free text.

Label side (at scoring time; on decoys here): the loader called with the decoy's outcome file bound, against the
label tables: every outcome's positive flags, the primary outcome's commits (their order and their files) and the
control pool likewise. If the universes differ the label comparison reads "not comparable" and nothing else. It
compares a re-encoding of the outcome file with the loader reading the same file: it shows an encoder fault only.

    python3 tools/compare/input_check.py --decoy DIR --tables PB --compare-tables CT --sealed SC --ref TREE --out F
    python3 tools/compare/input_check.py --real --i-am-the-reviewer-session ...     (never run by its builder)
    python3 tools/compare/input_check.py stage --repo R --ref TREE --rundir D       (inside the sandbox only)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
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

PREDICTOR_NAMES = (
    "in_degree", "in_degree_per_loc", "out_degree", "pagerank_score", "betweenness_score", "struct_branch",
    "struct_branch_per_loc", "state_danger", "state_pointers_alloc", "def_safety", "state_flux", "nest_max",
    "nest_mean", "risk_safety_score", "risk_tech_debt", "risk_cognitive_load", "risk_state_flux", "risk_concurrency",
    "risk_safety_nonzero", "risk_safety_among_nonzero", "amplified_cascading_flux",
    "amplified_cascading_flux_per_loc", "state_heat_triggers")
OUTCOMES = ("HP", "HP_allreverts", "HP_revert", "HP_cve", "HP_fixref", "KW")
PRED_ITEMS = (("universe", "size", "band", "band_count") + tuple(f"x:{p}" for p in PREDICTOR_NAMES)
              + tuple(f"silent:{p}" for p in PREDICTOR_NAMES) + tuple(f"in_use:{p}" for p in PREDICTOR_NAMES))
LABEL_ITEMS = tuple(f"y:{o}" for o in OUTCOMES) + ("hp_commits", "pool")

# the public shapes, in tools/owner/report.py's schema language (fixed-key dicts, yes/no leaves, repo names
# from the marginals file, stage codes from its fixed list)
PRED_REPO = {"code": "word:stage_code", "items": {i: "yesno?" for i in PRED_ITEMS}, "flux_flagged": "count?"}
PRED_PUBLIC = {"repos": ("map", "repo", PRED_REPO), "repos_checked": "count", "all_equal": "yesno"}
LABEL_REPO = {"code": "word:stage_code", "comparable": "yesno?", "items": {i: "yesno?" for i in LABEL_ITEMS}}
LABEL_PUBLIC = {"repos": ("map", "repo", LABEL_REPO), "repos_checked": "count", "all_equal": "yesno"}


def code_of(e: BaseException) -> str:
    """an exception's TYPE mapped to the owner job's fixed codes (its message is never looked at)"""
    if isinstance(e, KeyError):
        return "key_error"
    if isinstance(e, AssertionError):
        return "assertion"
    if isinstance(e, sqlite3.Error):
        return "database_error"
    if isinstance(e, MemoryError):
        return "memory"
    if isinstance(e, ImportError):
        return "import_error"
    if isinstance(e, OSError):
        return "os_error"
    if isinstance(e, ValueError):
        return "value_error"
    if isinstance(e, TypeError):
        return "type_error"
    return "unclassified"


# =============================================================================================== the stage
def _arr(a) -> list:
    return [U.enc(v) for v in np.asarray(a, dtype=np.float64)]


def stage(argv: list[str]) -> int:
    """inside sandbox_ro only: the reference loader, unchanged, from the tree under test's copy"""
    SR = U.sandbox_ro()
    SR.assert_inside_ro()                                  # the mount table first
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--ref", type=Path, required=True)
    ap.add_argument("--rundir", type=Path, required=True)
    ap.add_argument("--labels", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    res: dict = {}
    try:
        sys.path.insert(0, str(a.ref / "tools"))
        import sa3_score as SC                             # the tree under test's own file, unchanged
        assert Path(SC.__file__).resolve().parent == (a.ref / "tools").resolve(), "loaded the wrong sa3_score"
        d = SC.load(a.repo, with_predictors=True)
        out = {"paths": d["paths"], "loc": _arr(d["loc"]), "band": [int(b) for b in d["band"]], "k": int(d["k"]),
               "x": {p: _arr(v) for p, v in d["x"].items()},
               "silent": {p: bool(SC.silent(d["x"][p], p)) for p in SC.PREDICTORS},
               "in_use": {}, "predictors": {p: list(v) for p, v in SC.PREDICTORS.items()}}
        for p in SC.PREDICTORS:
            valid = ~np.isnan(d["x"][p])
            _des, band, k, idx = SC.design_for(d, d["y"]["HP"], valid)
            out["in_use"][p] = {"idx": [int(i) for i in idx], "band": [int(b) for b in band], "k": int(k)}
        if a.labels:
            out["y"] = {o: [int(v) for v in d["y"][o]] for o in OUTCOMES}
            out["hp_commits"] = [[s, sorted(int(i) for i in v)] for s, v in d["hp_commits"].items()]
            out["pool"] = [[s, sorted(int(i) for i in v)] for s, v in d["pool"].items()]
        (a.rundir / "loader.json").write_text(json.dumps(out) + "\n")
        res = {"status": "ok"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        res = {"status": "failed", "code": code_of(e)}
    res["seconds"] = round(time.time() - t0, 1)
    (a.rundir / "result.json").write_text(json.dumps(res) + "\n")
    return 0 if res["status"] == "ok" else 1


# =========================================================================================== the comparison
def _eq(a, b) -> bool:
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    return a.shape == b.shape and bool(np.array_equal(a, b, equal_nan=True))


def compare_predictor(ld: dict, d: dict, stats) -> dict:
    """items: True equal, False not equal, None not compared (the universe differs). ld: the loader's arrays as
    the stage wrote them; d: derive.derive's result"""
    D = U.sibling("derive")
    items = {i: None for i in PRED_ITEMS}
    items["universe"] = ld["paths"] == d["paths"]
    if not items["universe"]:
        return items
    items["size"] = _eq([U.dec(v) for v in ld["loc"]], d["loc"])
    items["band"] = ld["band"] == [int(b) for b in d["band"]]
    items["band_count"] = ld["k"] == int(d["k"])
    for p in PREDICTOR_NAMES:
        lx = np.array([U.dec(v) for v in ld["x"][p]]) if p in ld["x"] else None
        items[f"x:{p}"] = lx is not None and _eq(lx, d["x"][p])
        items[f"silent:{p}"] = p in ld["silent"] and ld["silent"][p] == D.silent(d["x"][p], p)
        idx, band, k = D.in_use(d, p, stats)
        u = ld["in_use"].get(p)
        items[f"in_use:{p}"] = (u is not None and u["idx"] == [int(i) for i in idx]
                                and u["band"] == [int(b) for b in band] and u["k"] == int(k))
    return items


def compare_label(ld: dict, d: dict) -> dict:
    """the label-side items, or not comparable when the universes differ"""
    if ld["paths"] != d["paths"]:
        return {"comparable": False, "items": {i: None for i in LABEL_ITEMS}}
    items = {f"y:{o}": ld["y"][o] == [int(v) for v in d["y"][o]] for o in OUTCOMES}
    items["hp_commits"] = ld["hp_commits"] == [[s, sorted(int(i) for i in v)] for s, v in d["hp_commits"].items()]
    items["pool"] = ld["pool"] == [[s, sorted(int(i) for i in v)] for s, v in d["pool"].items()]
    return {"comparable": True, "items": items}


# ============================================================================================= the launcher
class Layout:
    """where one check reads and writes: the study's inputs (bound into sandboxes only), the tree under test, the
    stored tables, the sealed copies, the scratch directory"""

    def __init__(self, study: Path, ref_tree: Path, pb_tables: Path, cmp_tables: Path, sealed: Path, scratch: Path,
                 label_tables: Path | None = None, linguist: Path | None = None):
        SR = U.sandbox_ro()
        P = U.phase_b()
        self.study, self.ref_tree = Path(study), Path(ref_tree)
        self.pb, self.cmp, self.labels = Path(pb_tables), Path(cmp_tables), label_tables
        self.sealed = Path(sealed)
        self.scratch = SR.check_rw(Path(scratch))
        self.linguist = Path(linguist or P.LINGUIST_HOST)


def _prepare(L: Layout) -> tuple[Path, Path, Path]:
    """this worktree's tools/ (the stage's code) and the tree under test's tools/, each copied once per scratch
    directory; the second under a name that carries the tree's path, so one scratch never serves two trees"""
    import hashlib
    T = U.sibling("tables")
    code = T.code_copy(L.scratch)
    ref = L.scratch / ("ref-" + hashlib.sha256(str(L.ref_tree.resolve()).encode()).hexdigest()[:12])
    if not (ref / "tools").is_dir():
        shutil.copytree(L.ref_tree / "tools", ref / "tools", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    stubs = L.scratch / "stubs"
    stubs.mkdir(exist_ok=True)
    return code, ref, stubs


def run_loader(L: Layout, repo: str, outcome_src: Path | None = None) -> tuple[dict | None, str]:
    """the copy stage and the loader stage for one repo; (the loader's arrays, a stage code)"""
    SR = U.sandbox_ro()
    P = U.phase_b()
    SL = U.load_path(U.TOOLS / "tables" / "silence.py", "tools_compare_tables_silence")
    code, ref, stubs = _prepare(L)
    tag = "labels" if outcome_src is not None else "stub"
    rd = L.scratch / repo / f"copy_{tag}"                 # copied afresh on every call: never a stale copy
    if rd.exists():
        shutil.rmtree(rd)
    rd.mkdir(parents=True)
    cp = P.run_stage("copy", repo, L.scratch, P.stage_spec(code, rd, P.declared(L.study, repo), None), rd, code)
    if cp.get("status") != "ok":
        return None, "no_result" if "reason" not in cp else "unclassified"
    copies = rd / "db"
    if outcome_src is None:
        src = stubs / f"{repo}.json"
        if not src.exists():
            src.write_text(json.dumps(SL.stub(repo), indent=1) + "\n")
    else:
        src = Path(os.path.abspath(outcome_src))
        if any(src == b or b in src.parents for b in SR.FORBIDDEN + (SR.PROJECTS,)) or \
                not any(a in src.parents for a in SR.ALLOWED_RW_ROOTS):
            raise SR.SandboxError("an outcome file may be bound here only from a decoy; refused")
    rl = L.scratch / repo / f"loader_{tag}"
    if rl.exists():
        shutil.rmtree(rl)
    rl.mkdir(parents=True)
    inputs = P.declared(L.study, repo, copies) + [(str(src), SR.STUDY / "sa3_outcomes" / f"{repo}.json")]
    inputs += [(str(L.linguist / n), P.LINGUIST_DST / n) for n in ("vendor.yml", "documentation.yml")]
    spec = SR.Spec(rw=[rl], code=[code, ref], inputs=inputs, clone=None,
                   env={"LAWS_LINGUIST_DIR": str(P.LINGUIST_DST)}, cwd=rl)
    home, tmp = rl / "home", rl / "tmp"
    home.mkdir()
    tmp.mkdir()
    P.write_gitconfig(home)
    argv = ["/usr/bin/python3", "-I", "-B", str(code / "tools" / "compare" / "input_check.py"), "stage",
            "--repo", repo, "--ref", str(ref), "--rundir", str(rl)] + (["--labels"] if outcome_src else [])
    with open(rl / "stage.log", "w") as log:
        try:
            p = SR.run(argv, spec, home, tmp, timeout=P.STAGE_TIMEOUT, stdout=log)
            rc = p.returncode
        except subprocess.TimeoutExpired:
            return None, "timeout"
    rf = rl / "result.json"
    if not rf.exists():
        return None, "sandbox_refused" if rc == 3 else "no_result"
    res = json.loads(rf.read_text())
    if res.get("status") != "ok":
        return None, res.get("code", "unclassified")
    return json.loads((rl / "loader.json").read_text()), "none"


def _derived(L: Layout, repo: str, stats, labels: bool):
    D = U.sibling("derive")
    pb, cmp, lab = D.load_dirs(L.pb / repo, L.cmp / repo, (Path(L.labels) / repo) if labels else None)
    return D.derive(repo, pb, cmp, stats, lab)


def ok_repos(L: Layout) -> list[str]:
    marg = json.loads((L.sealed / "docs" / "sa3_outcome_marginals.json").read_text())
    return [r["repo"] for r in marg if r["status"] == "ok"]


def predictor_check(L: Layout, repos: list[str] | None = None, loaders: dict | None = None) -> dict:
    """the public predictor-side result (validated by the caller's writer). loaders: already-computed loader
    arrays by repo (tests reuse one run against many planted tables)"""
    stats = U.load_sealed_stats(L.sealed)
    out = {"repos": {}, "repos_checked": 0, "all_equal": True}
    for r in (repos or ok_repos(L)):
        ld, code = (loaders[r], "none") if loaders and r in loaders else run_loader(L, r)
        rec = {"code": code, "items": {i: None for i in PRED_ITEMS}, "flux_flagged": None}
        try:
            d = _derived(L, r, stats, labels=False)
            rec["flux_flagged"] = int(d["flux_flagged"])     # reported even when the loader stopped
            if ld is not None:
                rec["items"] = compare_predictor(ld, d, stats)
        except Exception as e:                            # a table that cannot be read: its type, never its text
            if rec["code"] == "none":
                rec["code"] = code_of(e)
        out["repos"][r] = rec
        out["repos_checked"] += 1
        out["all_equal"] = out["all_equal"] and rec["code"] == "none" and all(v is True for v in rec["items"].values())
    return out


def label_check(L: Layout, outcomes_dir: Path, repos: list[str] | None = None, loaders: dict | None = None) -> dict:
    """decoys only (on real data this runs inside the scoring job): the loader with the decoy's outcome files"""
    stats = U.load_sealed_stats(L.sealed)
    out = {"repos": {}, "repos_checked": 0, "all_equal": True}
    for r in (repos or ok_repos(L)):
        ld, code = (loaders[r], "none") if loaders and r in loaders else \
            run_loader(L, r, Path(outcomes_dir) / f"{r}.json")
        rec = {"code": code, "comparable": None, "items": {i: None for i in LABEL_ITEMS}}
        if ld is not None:
            try:
                rec.update(compare_label(ld, _derived(L, r, stats, labels=True)))
            except Exception as e:
                rec["code"] = code_of(e)
        out["repos"][r] = rec
        out["repos_checked"] += 1
        out["all_equal"] = out["all_equal"] and rec["code"] == "none" and rec["comparable"] is True and \
            all(v is True for v in rec["items"].values())
    return out


# ============================================================================================ public output
def vocab(L: Layout):
    R = U.owner_report()
    marg = json.loads((L.sealed / "docs" / "sa3_outcome_marginals.json").read_text())
    return R.Vocab(repos=frozenset(r["repo"] for r in marg))


def validate(obj: dict, schema: dict, voc, field: str) -> None:
    """tools/owner/report.py's check, unchanged; raises ReportError naming the field only"""
    U.owner_report().check(schema, obj, field, voc)


def render(obj: dict, label: bool = False) -> str:
    """the terminal lines, from validated values only, with fixed words"""
    word = {True: "equal", False: "not equal", None: "not compared"}
    lines = []
    for r, rec in obj["repos"].items():
        lines.append(f"{r} stage {rec['code']}")
        if label and rec["comparable"] is False:
            lines.append(f"{r} not comparable: universe differs")
            continue
        for i, v in rec["items"].items():
            lines.append(f"{r} {i} {word[v]}")
        if not label:
            lines.append(f"{r} flux_flagged {'n/a' if rec['flux_flagged'] is None else rec['flux_flagged']}")
    lines.append("ALL EQUAL" if obj["all_equal"] else "NOT ALL EQUAL")
    return "\n".join(lines) + "\n"


def write_public(out_file: Path, obj: dict, voc, label: bool = False) -> str:
    """validate first, then write the JSON and its text rendering; nothing is written if a value does not fit"""
    validate(obj, LABEL_PUBLIC if label else PRED_PUBLIC, voc, "label_check" if label else "input_check")
    text = render(obj, label)
    out_file = Path(out_file)
    out_file.write_text(json.dumps(obj, indent=1) + "\n")
    out_file.with_suffix(".txt").write_text(text)
    return text


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["stage"]:
        return stage(argv[1:])
    ap = argparse.ArgumentParser()
    ap.add_argument("--decoy")
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--i-am-the-reviewer-session", action="store_true")
    ap.add_argument("--real-study", default=None, help="default: the study path every SA3 tool has compiled in")
    ap.add_argument("--tables", required=True, help="phase B's output directory (<repo>/index.json)")
    ap.add_argument("--compare-tables", required=True, help="tools/compare/tables.py predictor output")
    ap.add_argument("--sealed", required=True, help="the sealed copies: tools/sa3_stats.py, docs/")
    ap.add_argument("--ref", required=True, help="the tree under test (tools/)")
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--out", required=True, help="the public JSON file (a .txt beside it)")
    a = ap.parse_args(argv)
    SR = U.sandbox_ro()
    if bool(a.decoy) == bool(a.real) or (a.real and not a.i_am_the_reviewer_session):
        print("input_check: --decoy DIR, or --real --i-am-the-reviewer-session; refused", file=sys.stderr)
        return 2
    if a.real:
        study = Path(a.real_study or SR.STUDY)
    else:
        d = Path(os.path.abspath(a.decoy))
        if any(d == b or b in d.parents for b in SR.FORBIDDEN + (SR.PROJECTS,)):
            print("input_check: a decoy may not be inside a data root; refused", file=sys.stderr)
            return 2
        study = d / "study"
    try:
        L = Layout(study, Path(a.ref), Path(a.tables), Path(a.compare_tables), Path(a.sealed), Path(a.scratch))
        out = SR.check_rw(Path(a.out).parent) / Path(a.out).name
    except SR.SandboxError as e:
        print(f"input_check: {e}", file=sys.stderr)
        return 2
    obj = predictor_check(L)
    sys.stdout.write(write_public(out, obj, vocab(L)))
    return 0 if obj["all_equal"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
