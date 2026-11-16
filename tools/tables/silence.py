#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Count 1 of tables_phase_b_spec.md: which (repo, measure) cells the scorer's "instrument silent" rule silences
as at edc5c53 and as at 8fb7fe0. The reference scorer's own `load()` and `silent()` are called unchanged, each
version from a copy of that commit's tools/*.py placed in the scratch directory (`extract`; the working tree's
tools/sa3_score.py is never edited), each in its own sandbox and process (`run_one`).

`load()` reads the outcome file as well as the predictors. No outcome file is bound: in its place, at the study
path's sa3_outcomes/<repo>.json, the sandbox holds a STUB the job writes (`stub`): every outcome with the keys
`load()` reads (and those of the real file's outcome entries), every list empty. Silence is computed on the
predictor over all universe files before any outcome is used, so the stub cannot change it; tests/
test_tables_phase_b.py checks that on control repositories for every cell under both versions.

    python3 tools/tables/silence.py stage --repo R --vdir DIR --rundir D     # inside the sandbox only
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS / "harness"))
import sandbox_ro as SR  # noqa: E402

VERSIONS = ("edc5c53", "8fb7fe0")
SCORED_OUTCOMES = ("HP", "HP_allreverts", "HP_revert", "HP_cve", "HP_fixref", "KW")   # sa3_score.stage_score's loop
LISTS = SCORED_OUTCOMES


def stub(repo: str) -> dict:
    """an outcome file with the real one's outcome keys and every list empty: no file, no commit"""
    outs = {k: {"files": [], "n_files": 0, "n_commits": 0, "largest_commit_share": None, "clears_floor": False,
                "commits": {}} for k in LISTS}
    outs["control_pool"] = {"n_commits": 0, "n_files_any": 0, "commits": {}}
    return {"repo": repo, "status": "stub written by tools/tables/silence.py: no outcome", "outcomes": outs}


def extract(worktree: Path, commit: str, dst: Path) -> dict[str, str]:
    """every tools/*.py as at `commit` into dst/tools/, by `git show` (no lazy fetch, no gc); {name: sha256}"""
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"}

    def g(*args: str) -> bytes:
        p = subprocess.run(["git", "-C", str(worktree), "-c", "gc.auto=0", "-c", "maintenance.auto=false", *args],
                           capture_output=True, env=env, timeout=600)
        if p.returncode:
            raise SystemExit(f"silence: git {args[0]} at {commit}: {p.stderr.decode('utf-8', 'replace')[:300]}")
        return p.stdout

    names = [n for n in g("ls-tree", "--name-only", f"{commit}:tools").decode().splitlines() if n.endswith(".py")]
    (dst / "tools").mkdir(parents=True, exist_ok=True)
    out = {}
    for n in names:
        data = g("show", f"{commit}:tools/{n}")
        (dst / "tools" / n).write_bytes(data)
        out[f"tools/{n}"] = hashlib.sha256(data).hexdigest()
    return out


def run_one(repo: str, version: str, scratch: Path, rundir: Path, copies: Path, study: Path, linguist: Path,
            stubs: Path, outcome_src: Path | None = None) -> dict:
    """One version's silence for one repo, in its own sandbox: the database copies, the sidecar and the nesting
    file at their study paths, the stub at sa3_outcomes/<repo>.json, no clone. outcome_src is for the tests on
    control repositories only (stub against real): it must lie under /tmp or ~/.claude/jobs, never in a data root."""
    import phase_b as P
    code_wt, vdir = scratch / "code" / "wt", scratch / "code" / version
    if outcome_src is None:
        sf = stubs / f"{repo}.json"
        if not sf.exists():
            sf.write_text(json.dumps(stub(repo), indent=1) + "\n")
        src = sf
    else:
        src = Path(os.path.abspath(outcome_src))
        if any(src == b or b in src.parents for b in SR.FORBIDDEN + (SR.PROJECTS,)) or \
                not any(a in src.parents for a in SR.ALLOWED_RW_ROOTS):
            raise SR.SandboxError(f"{src}: a real outcome file may be bound only from a decoy; refused")
    inputs = P.declared(study, repo, copies) + [(str(src), SR.STUDY / "sa3_outcomes" / f"{repo}.json")]
    inputs += [(str(linguist / n), P.LINGUIST_DST / n) for n in ("vendor.yml", "documentation.yml")]
    spec = SR.Spec(rw=[rundir], code=[code_wt, vdir], inputs=inputs, clone=None,
                   env={"LAWS_LINGUIST_DIR": str(P.LINGUIST_DST)}, cwd=rundir)
    home, tmp = rundir / "home", rundir / "tmp"
    home.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    P.write_gitconfig(home)
    argv = ["/usr/bin/python3", "-I", "-B", str(code_wt / "tools" / "tables" / "silence.py"), "stage",
            "--repo", repo, "--vdir", str(vdir), "--rundir", str(rundir)]
    with open(rundir / "stage.log", "w") as log:
        try:
            rc = SR.run(argv, spec, home, tmp, timeout=P.STAGE_TIMEOUT, stdout=log).returncode
        except subprocess.TimeoutExpired:
            rc = "timeout"
    rf = rundir / "result.json"
    res = json.loads(rf.read_text()) if rf.exists() else {"error": f"stage wrote no result (rc {rc})"}
    res["rc"] = rc
    return res


def stage(argv: list[str]) -> int:
    SR.assert_inside_ro()                              # the mount table first
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--vdir", type=Path, required=True)
    ap.add_argument("--rundir", type=Path, required=True)
    a = ap.parse_args(argv)
    t0 = time.time()
    res: dict = {"repo": a.repo, "listing": sorted(str(p.relative_to(SR.STUDY)) for p in SR.STUDY.rglob("*")),
                 "pool": sorted(os.listdir(SR.POOL))}
    try:
        sys.path.insert(0, str(a.vdir / "tools"))
        import sa3_score as SC                     # the version's own file, unchanged
        assert Path(SC.__file__).resolve().parent == (a.vdir / "tools").resolve(), SC.__file__
        res["scorer_sha256"] = hashlib.sha256(Path(SC.__file__).read_bytes()).hexdigest()
        d = SC.load(a.repo, with_predictors=True)
        two = len(inspect.signature(SC.silent).parameters) >= 2      # silent(x) at edc5c53, silent(x, name) later
        res["silent"] = {p: bool(SC.silent(d["x"][p], p) if two else SC.silent(d["x"][p])) for p in SC.PREDICTORS}
        res["n"] = int(d["n"])
        res["predictors"] = {p: list(v) for p, v in SC.PREDICTORS.items()}
        res["confirmatory"] = list(getattr(SC, "CONFIRMATORY", ()))
        res["silent_signature"] = str(inspect.signature(SC.silent))
    except Exception as e:
        import traceback
        traceback.print_exc()
        res["error"] = f"{type(e).__name__}: {str(e)[:300]}"
    res["seconds"] = round(time.time() - t0, 1)
    (a.rundir / "result.json").write_text(json.dumps(res, indent=1) + "\n")
    return 0 if "silent" in res else 1


if __name__ == "__main__":
    if sys.argv[1:2] == ["stage"]:
        raise SystemExit(stage(sys.argv[2:]))
    print(__doc__)
    raise SystemExit(2)
