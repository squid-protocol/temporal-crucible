#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""A decoy of the whole route of docs/process/scoring_step_spec.md section 2, for tests and the timed loop.
DECOYS ONLY: every location is under a session scratch root.

From one of part 1's decoy studies (tools/compare/decoy_study.py, N or P; built or reused from its cache):

  1. BASE/decoy/{study,pool,docs}   a private copy of the decoy study
  2. BASE/tables/{phase_b,compare}  a private copy of its predictor-side tables
  3. BASE/repo                      a CHECKOUT standing in for this repository at commit C: a fresh clone of this
                                    repository (full history, so 8fb7fe0 is there), this worktree's tools/ copied
                                    over it (the build under test, committed or not), the decoy's documents in
                                    docs/, the predictor-side check (step 2: tools/compare/input_check.py on the
                                    decoy, recorded by predictor_check.py) and the deviation table draft (step 3),
                                    committed, with the annotated tag sa3-score-C
  4. BASE/run2, BASE/run2-prot      the owner preparation job run from that checkout on the decoy (step 5): PASS

The scoring job is then run from BASE/repo exactly as the owner runs it from this checkout (section 3).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
WORKTREE = TOOLS.parent
PY = sys.executable
DOCS_FROM_DECOY = ("sa3_registration.md", "sa3_registration_consolidated.md", "sa3_placebo.json",
                   "sa3_outcome_marginals.json", "sa3_power.md", "sa3_code_review.md")
SIX = DOCS_FROM_DECOY
GIT_ENV = {"GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_AUTHOR_NAME": "decoy",
           "GIT_AUTHOR_EMAIL": "decoy@invalid", "GIT_COMMITTER_NAME": "decoy", "GIT_COMMITTER_EMAIL": "decoy@invalid",
           "GIT_AUTHOR_DATE": "@1763200000 +0000", "GIT_COMMITTER_DATE": "@1763200000 +0000"}


def git(repo: Path, *a: str, env: dict | None = None) -> str:
    p = subprocess.run(["git", "-C", str(repo), "-c", "gc.auto=0", "-c", "maintenance.auto=false", *a],
                       capture_output=True, text=True, env={**os.environ, **GIT_ENV, **(env or {})})
    if p.returncode:
        raise RuntimeError(f"git {a[0]}: {p.stderr[-600:]}")
    return p.stdout.strip()


def _scratch(p: Path) -> Path:
    p = Path(os.path.abspath(p))
    roots = (Path.home() / ".claude" / "jobs", Path("/tmp"))
    if not any(r in p.parents for r in roots):
        raise SystemExit(f"{p}: decoys live under ~/.claude/jobs or /tmp only")
    return p


def checkout(base: Path, decoy_docs: Path, check: dict, extra: dict | None = None) -> tuple[Path, str]:
    """BASE/repo at a new commit C with the tag; returns (repo, C)"""
    repo = base / "repo"
    src = git(WORKTREE, "rev-parse", "--path-format=absolute", "--git-common-dir")
    git(base, "clone", "-q", "--no-hardlinks", src, str(repo))
    git(repo, "checkout", "-q", "-b", "decoy-score", git(WORKTREE, "rev-parse", "HEAD"))
    shutil.rmtree(repo / "tools")
    shutil.copytree(TOOLS, repo / "tools", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for n in DOCS_FROM_DECOY:
        shutil.copyfile(decoy_docs / n, repo / "docs" / n)
    for f in ("sa3_lock.json", "sa3_result.json"):
        (repo / "docs" / f).unlink(missing_ok=True)
    (repo / "docs" / "sa3_predictor_check.json").write_text(json.dumps(check, indent=1, sort_keys=True) + "\n")
    shutil.copyfile(HERE / "deviation_table_draft.md", repo / "docs" / "sa3_deviation_table.md")
    for rel, data in (extra or {}).items():
        (repo / rel).write_bytes(data)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "decoy commit C for the scoring job")
    c = git(repo, "rev-parse", "HEAD")
    git(repo, "tag", "-a", "sa3-score-C", "-m", "decoy pin", c)
    return repo, c


def predictor_check(base: Path, study: Path, sealed: Path) -> dict:
    """step 2 of section 2 on the decoy: tools/compare/input_check.py (predictor side, no label), recorded"""
    PC = _load("predictor_check")
    ic = base / "input_check.json"
    p = subprocess.run([PY, "-B", str(TOOLS / "compare" / "input_check.py"), "--decoy", str(base / "decoy"),
                        "--tables", str(base / "tables" / "phase_b"), "--compare-tables",
                        str(base / "tables" / "compare"), "--sealed", str(sealed), "--ref", str(WORKTREE),
                        "--scratch", str(base / "ic-scratch"), "--out", str(ic)],
                       capture_output=True, text=True, timeout=7200, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if not ic.exists():
        raise RuntimeError(f"input check did not run: {p.stdout[-1500:]} {p.stderr[-1500:]}")
    marg = json.loads((base / "decoy" / "docs" / "sa3_outcome_marginals.json").read_text())
    repos = [r["repo"] for r in marg if r["status"] == "ok"]
    return PC.record(base / "tables" / "phase_b", base / "tables" / "compare", json.loads(ic.read_text()), repos)


def _load(name: str):
    import importlib.util
    key = f"tools_scoring_{name}"
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, HERE / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
    return sys.modules[key]


def run2(base: Path, repo: Path) -> subprocess.CompletedProcess:
    """the owner preparation job, from the decoy checkout, on the decoy: run-2"""
    return subprocess.run([PY, "-I", "-B", str(repo / "tools" / "owner" / "prepare.py"), "--decoy",
                           str(base / "decoy"), "--protected", str(base / "run2-prot"), "--out", str(base / "run2")],
                          capture_output=True, text=True, timeout=7200, stdin=subprocess.DEVNULL)


def build(study_base: Path, base: Path, check: dict | None = None, plant=None) -> dict:
    """the whole decoy route up to run-2 (see the module's docstring). study_base: decoy_study.py's BASE/<which>;
    plant(decoy_dir): an edit to the decoy's own study files before the seal is taken (markers, a fault)"""
    base = _scratch(base)
    base.mkdir(parents=True, exist_ok=False)
    rec = json.loads((study_base / "built.json").read_text())
    d = Path(rec["paths"]["decoy"])
    for n in ("study", "pool"):
        shutil.copytree(d / n, base / "decoy" / n, symlinks=True)
    (base / "decoy" / "docs").mkdir()
    for n in DOCS_FROM_DECOY:
        shutil.copyfile(d / "docs" / n, base / "decoy" / "docs" / n)
    for n in ("phase_b", "compare"):
        shutil.copytree(Path(rec["paths"]["tables"]) / n, base / "tables" / n)
    if check is None:
        check = predictor_check(base, d / "study", Path(rec["paths"]["sealed"]))
    else:                                                   # reuse another build's record, re-pointed at this copy
        check = {"verdict": check["verdict"],
                 "phase_b": {"dir": str(base / "tables" / "phase_b"), "files": check["phase_b"]["files"]},
                 "compare": {"dir": str(base / "tables" / "compare"), "files": check["compare"]["files"]}}
    if plant is not None:
        plant(base / "decoy")
    repo, c = checkout(base, d / "docs", check)
    for n in SIX:                                           # the decoy's documents are the commit's
        shutil.copyfile(repo / "docs" / n, base / "decoy" / "docs" / n)
    p = run2(base, repo)
    if not p.stdout.strip().endswith("PASS"):
        raise RuntimeError(f"run-2 on the decoy did not PASS: {p.stdout[-2000:]} {p.stderr[-2000:]}")
    return {"base": str(base), "decoy": str(base / "decoy"), "repo": str(repo), "commit": c,
            "seal": str(base / "run2" / "seal.json"), "check": check}


def fork(b: dict, base: Path, plant=None, repo: Path | None = None) -> dict:
    """another decoy of the same commit's route: a private copy of the decoy study (an edit to it by `plant`), run-2
    taken again from the checkout (or from `repo`, another checkout); the tables and the commit's record shared"""
    base = _scratch(base)
    base.mkdir(parents=True, exist_ok=False)
    shutil.copytree(b["decoy"], base / "decoy", symlinks=True)
    if plant is not None:
        plant(base / "decoy")
    r = Path(repo or b["repo"])
    p = run2(base, r)
    c = git(r, "rev-parse", "HEAD")
    return {**b, "base": str(base), "decoy": str(base / "decoy"), "repo": str(r), "commit": c,
            "seal": str(base / "run2" / "seal.json"), "run2_stdout": p.stdout}


def command(b: dict, prot: Path, out: Path, ledger: Path, *extra: str) -> list[str]:
    """the scoring job as the owner runs it, from the decoy checkout, in decoy mode"""
    return [PY, "-I", "-B", str(Path(b["repo"]) / "tools" / "scoring" / "score_sa3.py"), "--decoy", b["decoy"],
            "--commit", b["commit"], "--seal", b["seal"], "--protected", str(prot), "--out", str(out),
            "--ledger", str(ledger), *extra]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--study-base", required=True, help="decoy_study.py's BASE/<N|P>")
    ap.add_argument("--base", required=True)
    a = ap.parse_args()
    print(json.dumps(build(Path(a.study_base), Path(a.base)), indent=1))
