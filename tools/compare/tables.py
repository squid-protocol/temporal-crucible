#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The comparison scorer's own tables (docs/process/comparison_scorer_spec.md, section 1).

Predictor side, built from a repo's scan database and sidecar by the rules of section 2:

  call_degree  (repo, path)  in_degree, out_degree        every scanned path
  flux         (repo, path)  value, special, loader_stops, case

Label side, built from a parsed outcome file (json.loads: a repeated key keeps its first position and its last
value, as the loader reads it):

  outcome_file      (repo, outcome, path)          one row per path of each scored outcome's `files` list
  hp_commit         (repo, position)  sha, n_paths  the primary outcome's commits in the file's order, 0-based
  hp_commit_file    (repo, position, path)
  pool_commit       (repo, position)  sha, n_paths  the control pool, likewise
  pool_commit_file  (repo, position, path)

`position` is a whole-number key: tools/tables/canon.py sorts it as a number. A commit with no path keeps its
commit row (n_paths 0) and has no file row. Label tables are protected (written under protected/) and are
built on real data only inside the scoring job (a later specification); this module's label CLI refuses a real
target.

    python3 tools/compare/tables.py predictor --decoy DIR --out OUT [--scratch S] [--repos a,b]
    python3 tools/compare/tables.py predictor --real --i-am-the-reviewer-session --out OUT [...]
    python3 tools/compare/tables.py labels --decoy DIR --out OUT          (decoys only)
    python3 tools/compare/tables.py stage --repo R --rundir D --out O     (inside the read-only sandbox only)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
import time
from collections import Counter, defaultdict
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

SCHEMA_VERSION = 1
KEY = "amplified_cascading_flux"
SCORED = ("HP", "HP_allreverts", "HP_revert", "HP_cve", "HP_fixref", "KW")    # sa3_score.load's six outcomes
# the flux table's cases, in the order of section 2's table
CASES = ("empty_record", "key_absent", "falsy_value", "number", "numeric_text", "unreadable_value", "not_json",
         "not_object")


def _t(key, cols, protected=False):
    return {"key": tuple(k for k, _ in key), "columns": tuple(key) + tuple(cols), "protected": protected,
            "version": SCHEMA_VERSION}


TABLES = {
    "call_degree": _t([("repo", "str"), ("path", "str")], [("in_degree", "int"), ("out_degree", "int")]),
    "flux": _t([("repo", "str"), ("path", "str")],
               [("value", "real"), ("special", "str"), ("loader_stops", "bool"), ("case", "str")]),
    "outcome_file": _t([("repo", "str"), ("outcome", "str"), ("path", "str")], [], True),
    "hp_commit": _t([("repo", "str"), ("position", "int")], [("sha", "str"), ("n_paths", "int")], True),
    "hp_commit_file": _t([("repo", "str"), ("position", "int"), ("path", "str")], [], True),
    "pool_commit": _t([("repo", "str"), ("position", "int")], [("sha", "str"), ("n_paths", "int")], True),
    "pool_commit_file": _t([("repo", "str"), ("position", "int"), ("path", "str")], [], True),
}
PREDICTOR_TABLES = ("call_degree", "flux")
LABEL_TABLES = ("outcome_file", "hp_commit", "hp_commit_file", "pool_commit", "pool_commit_file")


class TableError(ValueError):
    """a table cannot be built or read; the message never names a path, a commit or a value"""


# ============================================================================================ predictor side
def scan_path(stored: str, root: str) -> str:
    """section 2's path rule: the scan root and one slash removed from the front if the stored path starts with
    them; otherwise every leading slash removed (sa3_score.load, sa3_outcomes.universe)"""
    return stored[len(root):] if stored.startswith(root) else stored.lstrip("/")


def flux_of(rec) -> tuple[float | None, str]:
    """one telemetry record by the loader's expression: (value, case). value None: the loader would stop here
    (valid JSON that is not an object: `.get` raises AttributeError, which the loader does not catch);
    NaN: missing (the loader's `except (ValueError, TypeError): pass` leaves the slot as it was)"""
    try:
        obj = json.loads(rec) if rec else {}
    except (ValueError, TypeError):
        return math.nan, "not_json"
    if not rec:
        return 0.0, "empty_record"
    if not isinstance(obj, dict):
        return None, "not_object"
    if KEY not in obj:
        return 0.0, "key_absent"
    v = obj[KEY]
    try:
        f = float(obj.get(KEY, 0) or 0)                 # the loader's own expression, sa3_score.py:103
    except (ValueError, TypeError):
        return math.nan, "unreadable_value"
    if not v:
        return f, "falsy_value"
    if isinstance(v, str):
        return f, "numeric_text"
    return f, "number"


def predictor_rows(repo: str, scan_db: Path, side: dict) -> dict:
    """call_degree and flux rows for every scanned path, with the loader's semantics: a call row counts when its
    target function is resolved, toward the file of its target (in) and of its source (out), whatever the other
    end; when two file_data rows map to one path, both ids count, and the later record that parses wins (a later
    unreadable one leaves the earlier value, as the loader's `pass` does). Returns {"rows": {table: [...]},
    "duplicate_paths": n}"""
    root = side["src_root"].rstrip("/") + "/"
    con = sqlite3.connect(f"file:{scan_db}?mode=ro", uri=True)
    try:
        ids: dict[str, list[int]] = defaultdict(list)
        val: dict[str, float] = {}
        case: dict[str, str] = {}
        stops: dict[str, bool] = defaultdict(bool)
        order: list[str] = []
        for fid, stored, rec in con.execute("select id, file_path, mitigation_telemetry from file_data"):
            p = scan_path(stored, root)
            if p not in ids:
                order.append(p)
                val[p] = math.nan
                case[p] = None
            ids[p].append(fid)
            v, c = flux_of(rec)
            if v is None:                          # the loader would stop on this row
                stops[p] = True
                case[p] = c
            elif c not in ("not_json", "unreadable_value"):
                val[p], case[p] = v, c             # the loader assigns (a NaN that parsed is assigned too)
            elif case[p] is None:
                case[p] = c                        # the loader passes: the slot keeps what it had
        path_of = {i: p for p, xs in ids.items() for i in xs}
        indeg, outdeg = Counter(), Counter()
        for sf, df in con.execute("select src_file_id, dst_file_id from fcall_data where dst_func_id is not null"):
            if df in path_of:
                indeg[path_of[df]] += 1
            if sf in path_of:
                outdeg[path_of[sf]] += 1
    finally:
        con.close()
    cd = [{"repo": repo, "path": p, "in_degree": indeg[p], "out_degree": outdeg[p]} for p in order]
    fl = []
    for p in order:
        v = val[p]
        special = None
        if math.isinf(v):
            special, v = ("inf" if v > 0 else "-inf"), None
        elif math.isnan(v):
            v = None
        fl.append({"repo": repo, "path": p, "value": v, "special": special, "loader_stops": stops[p],
                   "case": case[p]})
    return {"rows": {"call_degree": cd, "flux": fl},
            "duplicate_paths": sum(1 for xs in ids.values() if len(xs) > 1)}


# ================================================================================================ label side
def label_rows(repo: str, outcome: dict) -> dict:
    """the five label tables from one parsed outcome file. Refuses (by count, never by name) a commit whose
    hash appears at two positions; a path repeated inside one commit's list is stored once (the loader's flags
    are the same either way) and counted"""
    o = outcome["outcomes"]
    rows = {n: [] for n in LABEL_TABLES}
    for oc in SCORED:
        for p in dict.fromkeys(o[oc]["files"]):
            rows["outcome_file"].append({"repo": repo, "outcome": oc, "path": p})
    repeated = 0
    for src, ct, cft in (("HP", "hp_commit", "hp_commit_file"), ("control_pool", "pool_commit", "pool_commit_file")):
        commits = o[src]["commits"]
        for pos, (sha, paths) in enumerate(commits.items()):
            uniq = list(dict.fromkeys(paths))
            repeated += len(paths) - len(uniq)
            rows[ct].append({"repo": repo, "position": pos, "sha": sha, "n_paths": len(uniq)})
            for p in uniq:
                rows[cft].append({"repo": repo, "position": pos, "path": p})
    return {"rows": rows, "repeated_paths": repeated,
            "repeated_files": sum(len(o[oc]["files"]) - len(set(o[oc]["files"])) for oc in SCORED)}


# ==================================================================================================== storage
def write(out_dir: Path, rows: dict) -> dict:
    """write each table with the canonical writer; returns {table: {file, hash, rows, ...}}"""
    C = U.canon()
    return {n: C.write_table(out_dir, n, r, TABLES[n]) for n, r in rows.items()}


def table_hash(name: str, rows: list[dict]) -> str:
    return U.canon().table_hash(name, rows, TABLES[name])


def decode(name: str, rows: list[dict]) -> list[dict]:
    reals = [c for c, t in TABLES[name]["columns"] if t == "real"]
    return [{**r, **{c: (None if r[c] is None else float.fromhex(r[c])) for c in reals}} for r in rows]


def read_dir(d: Path) -> dict:
    """every table an index.json in d names, decoded"""
    C = U.canon()
    idx = json.loads((Path(d) / "index.json").read_text())
    out = {}
    for n, t in idx["tables"].items():
        out[n] = decode(n, C.read_rows(Path(d) / t["file"])) if n in TABLES else C.read_rows(Path(d) / t["file"])
    return out


def write_index(d: Path, meta: dict, written: dict) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.json").write_text(json.dumps({**meta, "tables": written}, indent=1, sort_keys=True) + "\n")


def commits_in_order(commit_rows: list[dict], file_rows: list[dict]) -> list[tuple[str, list[str]]]:
    """(sha, paths) by position as a number; refuses a gap, a repeated position or a hash at two positions"""
    by = sorted(commit_rows, key=lambda r: r["position"])
    if [r["position"] for r in by] != list(range(len(by))):
        raise TableError("commit positions are not 0..n-1")
    shas = Counter(r["sha"] for r in by)
    if any(c > 1 for c in shas.values()):
        raise TableError(f"{sum(1 for c in shas.values() if c > 1)} commit hash(es) at two positions")
    files = defaultdict(list)
    for r in sorted(file_rows, key=lambda r: (r["position"], r["path"].encode("utf-8", "surrogateescape"))):
        files[r["position"]].append(r["path"])
    out = []
    for r in by:
        ps = files.get(r["position"], [])
        if len(ps) != r["n_paths"]:
            raise TableError("a commit's path count differs from its file rows")
        out.append((r["sha"], ps))
    if set(files) - {r["position"] for r in by}:
        raise TableError("file rows with no commit row")
    return out


# ============================================================================ the sandboxed predictor stage
def stage(argv: list[str]) -> int:
    """inside tools/harness/sandbox_ro.py's sandbox only: copy the scan database (phase B's copy stage), build
    call_degree and flux from the copy, write them to --out/<repo>/"""
    SR = U.sandbox_ro()
    SR.assert_inside_ro()                          # the mount table first, before any path
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--rundir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    t0 = time.time()
    res: dict = {}
    try:
        P = U.phase_b()
        cp = P.stage_copy(a.repo, a.rundir)
        side = json.loads(P.roles(a.repo)["scan_sidecar"].read_text())
        built = predictor_rows(a.repo, a.rundir / "db" / "scan.db", side)
        od = a.out / a.repo
        written = write(od, built["rows"])
        write_index(od, {"repo": a.repo, "inputs_sha256": cp["sha256"], "duplicate_paths": built["duplicate_paths"],
                         "built_by": "tools/compare/tables.py"}, written)
        res = {"status": "ok", "tables": {n: t["hash"] for n, t in written.items()},
               "duplicate_paths": built["duplicate_paths"]}
    except Exception as e:                         # recorded by type; the message stays in the stage log
        import traceback
        traceback.print_exc()
        res = {"status": "failed", "code": type(e).__name__}
    res["seconds"] = round(time.time() - t0, 1)
    (a.rundir / "result.json").write_text(json.dumps(res, indent=1) + "\n")
    return 0 if res["status"] == "ok" else 1


def code_copy(scratch: Path) -> Path:
    """this worktree's tools/ copied into scratch (the worktree is hidden inside every sandbox)"""
    import shutil
    code = scratch / "code"
    if not (code / "tools").is_dir():
        shutil.copytree(U.TOOLS, code / "tools", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return code


def build_predictor_tables(study: Path, repos: list[str], out: Path, scratch: Path) -> dict:
    """per repo, one read-only sandbox with that repo's declared inputs (phase B's `declared`): the tables land
    in out/<repo>/. Never opens the study directory from outside the sandbox."""
    SR = U.sandbox_ro()
    P = U.phase_b()
    out, scratch = SR.check_rw(out), SR.check_rw(scratch)
    out.mkdir(parents=True, exist_ok=True)
    code = code_copy(scratch)
    res = {}
    for r in repos:
        rd = scratch / r / "compare_tables"
        rd.mkdir(parents=True, exist_ok=True)
        (out / r).mkdir(parents=True, exist_ok=True)
        spec = SR.Spec(rw=[rd, out / r], code=[code], inputs=P.declared(study, r), clone=None, cwd=rd)
        home, tmp = rd / "home", rd / "tmp"
        home.mkdir(exist_ok=True)
        tmp.mkdir(exist_ok=True)
        P.write_gitconfig(home)
        argv = ["/usr/bin/python3", "-I", "-B", str(code / "tools" / "compare" / "tables.py"), "stage", "--repo", r,
                "--rundir", str(rd), "--out", str(out)]
        with open(rd / "stage.log", "w") as log:
            p = SR.run(argv, spec, home, tmp, timeout=P.STAGE_TIMEOUT, stdout=log)
        rf = rd / "result.json"
        res[r] = json.loads(rf.read_text()) if rf.exists() else {"status": "failed", "code": f"rc {p.returncode}"}
        print(f"{r} compare_tables {res[r]['status']}", flush=True)
    return res


def build_label_tables(outcomes_dir: Path, repos: list[str], out: Path) -> dict:
    """decoys only: the five label tables of each repo from <outcomes_dir>/<repo>.json"""
    res = {}
    for r in repos:
        f = Path(outcomes_dir) / f"{r}.json"
        built = label_rows(r, json.loads(f.read_text()))
        od = Path(out) / r
        written = write(od, built["rows"])
        write_index(od, {"repo": r, "repeated_paths": built["repeated_paths"],
                         "repeated_files": built["repeated_files"], "built_by": "tools/compare/tables.py"}, written)
        res[r] = {n: t["hash"] for n, t in written.items()}
    return res


def _decoy_dir(d: str) -> Path:
    SR = U.sandbox_ro()
    p = Path(os.path.abspath(d))
    for bad in SR.FORBIDDEN + (SR.PROJECTS,):
        if p == bad or bad in p.parents:
            raise SystemExit(f"tables: a decoy may not be inside {bad}; refused")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["stage"]:
        return stage(argv[1:])
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("predictor", "labels"))
    ap.add_argument("--decoy")
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--i-am-the-reviewer-session", action="store_true")
    ap.add_argument("--real-study", default=None)
    ap.add_argument("--real-docs", default=str(U.WORKTREE / "docs"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--scratch")
    ap.add_argument("--repos")
    a = ap.parse_args(argv)
    SR = U.sandbox_ro()
    if bool(a.decoy) == bool(a.real):
        print("tables: exactly one of --decoy DIR or --real; refused", file=sys.stderr)
        return 2
    if a.real and (a.what == "labels" or not a.i_am_the_reviewer_session):
        print("tables: label tables are built on real data only inside the scoring job; --real needs "
              "--i-am-the-reviewer-session; refused", file=sys.stderr)
        return 2
    try:
        if a.real:
            study, docs = Path(a.real_study or SR.STUDY), Path(a.real_docs)
        else:
            d = _decoy_dir(a.decoy)
            study, docs = d / "study", d / "docs"
        out = SR.check_rw(Path(a.out))
    except (SystemExit, SR.SandboxError) as e:
        print(str(e), file=sys.stderr)
        return 2
    if out.exists():
        print(f"tables: {out} exists; refused", file=sys.stderr)
        return 2
    marg = json.loads((docs / "sa3_outcome_marginals.json").read_text())
    repos = [r["repo"] for r in marg if r["status"] == "ok" and (not a.repos or r["repo"] in a.repos.split(","))]
    if a.what == "labels":
        build_label_tables(study / "sa3_outcomes", repos, out)
        return 0
    res = build_predictor_tables(study, repos, out, SR.check_rw(Path(a.scratch or str(out) + ".scratch")))
    return 0 if all(v["status"] == "ok" for v in res.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
