#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The runner of the blind test (docs/process/comparison_scorer_spec.md, section 8, "The blind test of the
check"). It runs the check on numbered copies of study P's reference side and prints, per copy and per layer,
"fired" or "silent". It does not make the copies, the faults or the key, and it reads no key: it reads only the
numbered copy directories, the pristine tables, the sealed copies and the seal manifest.

    python3 tools/compare/blind_runner.py seal --side DIR --out SEAL.json       # from the PRISTINE reference side
    python3 tools/compare/blind_runner.py run --copies DIR --tables T --sealed S --seal SEAL.json --work W --out O

A copy (DIR/<number>/) holds the reference side as the fault-writer left it: `tree/` (tools/ and docs/: the tree
under test), `study/` (laid out like the study directory) and `pool/<repo>` (clones). Per copy, five layers:

  seal          SHA-256 of every file of tree/tools, tree/docs (but sa3_lock.json and sa3_result.json, which the
                reference writes), study/ (no -shm: an ordinary read changes it) and each clone's HEAD, against
                the manifest taken from the pristine side: fired when any entry differs, is added or is missing
  placebo       the reference `placebo` stage, unchanged, re-run from a scratch copy of the copy (harness
                sandbox); fired when its output is not exactly the pristine committed placebo file (sealed copy)
  input check   layer 1 with the copy's study and tree under test against the PRISTINE tables: predictor side
                (stub outcome files) and label side (the copy's outcome files); fired when any item is not equal
                or a stage failed
  cell map W/D  the reference `lock` and `score`, unchanged, on a scratch git checkout of the copy's tree as it is
                (so `lock` seals whatever the copy holds: the seal is a layer of its own), against the comparison
                scorer's result, computed once from the pristine tables and the sealed copies; fired when any W or
                D cell is not equal (or the reference wrote no result)
  cell map R    the same comparison; fired when any R cell is not equal (or no result)

Each copy is scored twice, as the spec asks: with the seal, and with the seal's verdict withheld (the four
other layers only). The runner prints both columns; it does not know which copies are faulty.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
if "tools_compare__util" not in sys.modules:
    import importlib.util as _iu
    _s = _iu.spec_from_file_location("tools_compare__util", str(HERE / "_util.py"))
    _m = _iu.module_from_spec(_s)
    sys.modules["tools_compare__util"] = _m
    _s.loader.exec_module(_m)
U = sys.modules["tools_compare__util"]
LAYERS = ("seal", "placebo", "input_check", "cell_map_WD", "cell_map_R")
WRITTEN_BY_REFERENCE = ("tree/docs/sa3_lock.json", "tree/docs/sa3_result.json")


# ===================================================================================================== seal
def manifest(side: Path) -> dict[str, str]:
    """relative path -> SHA-256 for the reference side's files; each clone by the hash of its HEAD"""
    side = Path(side)
    out = {}
    for sub in ("tree/tools", "tree/docs", "study"):
        for p in sorted((side / sub).rglob("*")):
            rel = str(p.relative_to(side))
            if p.is_file() and "__pycache__" not in rel and not rel.endswith("-shm") and rel not in WRITTEN_BY_REFERENCE:
                out[rel] = U.sha256(p)
    for c in sorted((side / "pool").iterdir()) if (side / "pool").is_dir() else []:
        h = subprocess.run(["git", "-C", str(c), "-c", "gc.auto=0", "rev-parse", "HEAD"], capture_output=True,
                           text=True, env={**os.environ, "GIT_NO_LAZY_FETCH": "1"}).stdout.strip()
        out[f"pool/{c.name}@HEAD"] = hashlib.sha256(h.encode()).hexdigest()
    return out


def seal_layer(copy: Path, seal: dict) -> bool:
    return manifest(copy) != seal


# ================================================================================================== placebo
def _work(base: Path, copy: Path, tree_too: bool = True) -> Path:
    SB = U.harness_sandbox()
    w = base
    if w.exists():
        shutil.rmtree(w)
    SB.prepare(w)
    shutil.copytree(copy / "study", w / "study", dirs_exist_ok=True)
    for c in sorted((copy / "pool").iterdir()):
        shutil.copytree(c, w / "pool" / c.name, symlinks=True)
    if tree_too:
        shutil.copytree(copy / "tree", w / "tree", dirs_exist_ok=True, symlinks=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    if not SB.copy_linguist_cache(w):
        raise RuntimeError("linguist cache absent")
    return w


def placebo_layer(copy: Path, sealed: Path, scratch: Path) -> tuple[bool, dict]:
    SB = U.harness_sandbox()
    w = _work(scratch / "placebo", copy)
    p = SB.run(["/usr/bin/python3", "-B", "tools/sa3_score.py", "placebo"], w, cwd=w / "tree", timeout=7200)
    f = w / "tree" / "docs" / "sa3_placebo.json"
    if p.returncode or not f.exists():
        return True, {"rc": p.returncode, "note": "the placebo stage did not complete"}
    got = json.loads(f.read_text())
    want = json.loads((sealed / "docs" / "sa3_placebo.json").read_text())
    C = U.sibling("cellmap")
    m = C.cell_map(want, got)
    return not m["all_equal"], {"rc": 0, "cells_not_equal": len(m["not_equal"])}


# ============================================================================================= input check
def input_check_layer(copy: Path, tables: Path, sealed: Path, scratch: Path) -> tuple[bool, dict]:
    IC = U.sibling("input_check")
    L = IC.Layout(copy / "study", copy / "tree", tables / "phase_b", tables / "compare", sealed, scratch / "ic",
                  label_tables=tables / "labels")
    pred = IC.predictor_check(L)
    IC.validate(pred, IC.PRED_PUBLIC, IC.vocab(L), "input_check")
    lab = IC.label_check(L, copy / "study" / "sa3_outcomes")
    IC.validate(lab, IC.LABEL_PUBLIC, IC.vocab(L), "label_check")
    return (not pred["all_equal"]) or (not lab["all_equal"]), {"predictor_all_equal": pred["all_equal"],
                                                               "label_all_equal": lab["all_equal"]}


# ================================================================================================ cell map
def reference_result(copy: Path, scratch: Path) -> dict | None:
    """lock and score, unchanged, on a fresh git checkout of the copy's tree as it is"""
    SB = U.harness_sandbox()
    DS = U.sibling("decoy_study")
    w = _work(scratch / "score", copy)
    tree = w / "tree"
    for f in WRITTEN_BY_REFERENCE:
        (w / f).unlink(missing_ok=True)
    DS.git(tree, "init", "-q")
    DS.git(tree, "add", "-A")
    DS.git(tree, "commit", "-q", "-m", "copy under test")
    for stage in ("lock", "score"):
        p = SB.run(["/usr/bin/python3", "-B", "tools/sa3_score.py", stage], w, cwd=tree, timeout=7200)
        if p.returncode:
            return None
    f = tree / "docs" / "sa3_result.json"
    return json.loads(f.read_text()) if f.exists() else None


def comparison_result(tables: Path, sealed: Path) -> dict:
    SC = U.sibling("scorer")
    data = SC.load_data(tables / "phase_b", tables / "compare", tables / "labels", sealed)
    return json.loads(SC.dumps(SC.Scorer(sealed, data).score()))


def cell_layers(copy: Path, cmp: dict, scratch: Path) -> tuple[bool, bool, dict]:
    C = U.sibling("cellmap")
    ref = reference_result(copy, scratch)
    if ref is None:
        return True, True, {"note": "the reference wrote no result"}
    m = C.cell_map(ref, cmp)
    wd = m["classes"]["W"]["not_equal"] + m["classes"]["D"]["not_equal"] > 0
    return wd, m["classes"]["R"]["not_equal"] > 0, {"classes": m["classes"], "first_R": m["first_R"]}


# ===================================================================================================== run
def run(copies: Path, tables: Path, sealed: Path, seal: dict, work: Path) -> dict:
    SR = U.sandbox_ro()
    work = SR.check_rw(Path(work))
    work.mkdir(parents=True, exist_ok=True)
    cmp = comparison_result(tables, sealed)
    rows = {}
    for c in sorted(p for p in Path(copies).iterdir() if p.is_dir() and p.name.isdigit()):
        t0 = time.time()
        sc = work / c.name
        if sc.exists():
            shutil.rmtree(sc)
        sc.mkdir()
        fired, detail = {}, {}
        fired["seal"] = seal_layer(c, seal)
        fired["placebo"], detail["placebo"] = placebo_layer(c, sealed, sc)
        fired["input_check"], detail["input_check"] = input_check_layer(c, tables, sealed, sc)
        fired["cell_map_WD"], fired["cell_map_R"], detail["cell_map"] = cell_layers(c, cmp, sc)
        rows[c.name] = {"layers": {k: ("fired" if fired[k] else "silent") for k in LAYERS},
                        "flagged_with_seal": any(fired.values()),
                        "flagged_seal_withheld": any(v for k, v in fired.items() if k != "seal"),
                        "detail": detail, "seconds": round(time.time() - t0, 1)}
        print(line(c.name, rows[c.name]), flush=True)
    return rows


def header() -> str:
    return "copy  " + "  ".join(f"{k:<12}" for k in LAYERS) + "  with seal   seal withheld"


def line(name: str, r: dict) -> str:
    return (f"{name:<5} " + "  ".join(f"{r['layers'][k]:<12}" for k in LAYERS)
            + f"  {'flagged' if r['flagged_with_seal'] else 'clean':<10}  "
            + ("flagged" if r["flagged_seal_withheld"] else "clean"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("seal", "run"))
    ap.add_argument("--side")
    ap.add_argument("--copies")
    ap.add_argument("--tables")
    ap.add_argument("--sealed")
    ap.add_argument("--seal")
    ap.add_argument("--work")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    SR = U.sandbox_ro()
    out = SR.check_rw(Path(a.out).parent) / Path(a.out).name
    if a.what == "seal":
        out.write_text(json.dumps(manifest(Path(a.side)), indent=1, sort_keys=True) + "\n")
        return 0
    print(header(), flush=True)
    rows = run(Path(a.copies), Path(a.tables), Path(a.sealed), json.loads(Path(a.seal).read_text()), Path(a.work))
    out.write_text(json.dumps(rows, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
