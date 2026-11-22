#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Decoy studies (docs/process/comparison_scorer_spec.md, section 7), and the measured coverage list.

    python3 tools/compare/decoy_study.py build --which N|P --base DIR     # about 6-10 minutes per study
    python3 tools/compare/decoy_study.py coverage --base DIR              # after both are built

A decoy study is 12 control repositories (tools/control_repo/generate.py), each run through the unmodified
pipeline by the harness (tools/harness/run.py, route manifest), laid out as one study directory with one
marginals file. Study N has no planted effect; study P plants `branches=0.5` in every repo. Each condition of
section 7 is obtained either by a generator option or by an edit to the DECOY's files after the pipeline ran
(RECIPE and PLANTS below; DECISIONS.md says which and why). Then, all inside sandboxes:

  reference   one harness WORK for the whole study: the study bound at the study path, every clone under its
              pool, the tree a git checkout (tools/ and docs/, committed); the reference `placebo` (its output
              is committed), `lock` (writes real hashes: a git checkout), `score` (sa3_result.json), and `score`
              again under the standard library's line tracer (`coverage`), unchanged
  tables      phase B (tools/tables/phase_b.py --decoy, unchanged), then tools/compare/tables.py (call_degree,
              flux in the read-only sandbox; the label tables from the decoy's outcome files)
  sealed      the sealed copies the comparison scorer reads: tools/sa3_stats.py, tools/sa3_score.py (read as
              text only), docs/{sa3_outcome_marginals,sa3_placebo,sa3_lock}.json, copied from the pristine tree

Layout under DIR/<which>/: controls/, runs/ (harness), decoy/ (study/, pool/, docs/), work/ (the reference WORK;
work/tree is the reference side's git checkout), tables/{phase_b,compare,labels}, sealed/, built.json.
Nothing here opens the real study directory, the pool, the corpus or ~/.blind; every location is under DIR.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import random
import shutil
import sqlite3
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

PY = sys.executable
GEN = U.TOOLS / "control_repo" / "generate.py"
RUN = U.TOOLS / "harness" / "run.py"
PHASE_B = U.TOOLS / "tables" / "phase_b.py"
SEALED_DOCS = ("sa3_registration_consolidated.md", "sa3_power.md", "sa3_registration.md")
EFFECT = {"N": None, "P": "branches=0.5"}
COVERED = ("stage_score", "control_effects", "churn_any", "summarize")

# name, language, seed, --years, --files, --mutation, drawn, plants. C family drawn: circuitpython, freebsd-src,
# go, bun, ctrl-short; managed drawn: django, mediawiki, racket, ctrl-mw2, ctrl-plain; not drawn: two.
RECIPE = (
    ("django", "python", 41, 12, None, None, True, ()),
    ("circuitpython", "c", 42, 12, None, None, True, ()),
    ("mediawiki", "python", 43, 12, None, "merge_workflow", True, ()),
    ("freebsd-src", "c", 44, 12, 850, None, True, ()),
    ("go", "c", 45, 12, None, None, True, ()),
    ("bun", "c", 46, 12, None, None, True, ("pool_smaller_than_hp",)),
    ("racket", "python", 47, 12, None, None, True, ("telemetry_cases", "nest_sparse")),
    ("ctrl-mw2", "python", 48, 12, None, "merge_workflow", True, ("struct_branch_missing", "pool_mostly_empty")),
    ("ctrl-short", "c", 49, 10, None, None, True, ("window_short",)),
    ("ctrl-plain", "python", 50, 12, None, None, True, ("pool_covers_everything",)),
    ("ctrl-early1", "python", 51, 12, None, None, False, ("pool_under_five",)),
    ("ctrl-early2", "c", 52, 12, None, None, False, ("hp_floor_failed",)),
)
TELEMETRY = (None, "", "{}", '{"amplified_cascading_flux": ""}', '{"amplified_cascading_flux": []}',
             '{"amplified_cascading_flux": {}}', '{"amplified_cascading_flux": true}',
             '{"amplified_cascading_flux": "3.5"}', '{"amplified_cascading_flux": " "}',
             '{"amplified_cascading_flux": "abc"}', '{"amplified_cascading_flux": [1]}', "not json {",
             '{"amplified_cascading_flux": 0}', '{"amplified_cascading_flux": false}',
             '{"amplified_cascading_flux": null}', '{"other": 4}')


def git(repo: Path, *args: str) -> str:
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_AUTHOR_DATE": "@0 +0000",
           "GIT_COMMITTER_DATE": "@0 +0000", "GIT_AUTHOR_NAME": "decoy", "GIT_AUTHOR_EMAIL": "decoy@invalid",
           "GIT_COMMITTER_NAME": "decoy", "GIT_COMMITTER_EMAIL": "decoy@invalid"}
    p = subprocess.run(["git", "-C", str(repo), "-c", "gc.auto=0", "-c", "maintenance.auto=false", *args],
                       capture_output=True, text=True, env=env)
    if p.returncode:
        raise RuntimeError(f"git {args[0]}: {p.stderr[-400:]}")
    return p.stdout


# ===================================================================================== controls and harness
def control(base: Path, which: str, name: str, lang: str, seed: int, years: int, files, mutation) -> Path:
    """one control repository through the harness (route manifest, no placeholder review); its sandbox WORK"""
    tag = f"{which}-{name}"
    work = base / "runs" / tag
    if (work / "manifest" / "probe.json").exists():
        return work / "manifest"
    ctl = base / "controls" / tag
    if ctl.exists():
        shutil.rmtree(ctl)
    argv = [PY, "-B", str(GEN), "--out", str(ctl), "--seed", str(seed), "--years", str(years), "--language", lang]
    if files:
        argv += ["--files", str(files)]
    if mutation:
        argv += ["--mutation", mutation]
    if EFFECT[which]:
        argv += ["--effect", EFFECT[which]]
    subprocess.run(argv, check=True, capture_output=True, cwd=str(base), env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    p = subprocess.run([PY, "-B", str(RUN), "--control", str(ctl), "--work", str(work), "--name", tag, "--routes",
                        "manifest", "--no-shim-lock"], capture_output=True, text=True, timeout=3600,
                       env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    w = work / "manifest"
    if not (w / "probe.json").exists():
        raise RuntimeError(f"harness on {tag} did not finish: {p.stdout[-1500:]} {p.stderr[-1500:]}")
    return w


def assemble(base: Path, which: str) -> Path:
    """the decoy directory: study/, pool/, docs/ with the harness outputs renamed to the recipe's names"""
    d = base / "decoy"
    if d.exists():
        shutil.rmtree(d)
    (d / "docs").mkdir(parents=True)
    marg = []
    for name, lang, seed, years, files, mutation, drawn, _plants in RECIPE:
        w = control(base, which, name, lang, seed, years, files, mutation)
        old = f"ctrl-{which}-{name}"
        for sub in ("history", "sa3_scans", "sa3_outcomes", "meta_sa3", "sa3_nesting"):
            for f in sorted((w / "study" / sub).glob(f"{old}*")):
                rest = f.name[len(old):]
                if rest not in (".db", ".json", "_master.db", "_master.db-wal", "_master.db-shm", ".db-wal", ".db-shm"):
                    continue
                (d / "study" / sub).mkdir(parents=True, exist_ok=True)
                dst = d / "study" / sub / (name + rest)
                shutil.copy2(f, dst)
                if rest == ".json":                        # the sidecar, outcome and nesting files name the repo
                    o = json.loads(dst.read_text())
                    if o.get("repo") == old:
                        o["repo"] = name
                        dst.write_text(json.dumps(o) + "\n")
        shutil.copytree(w / "pool" / old, d / "pool" / name, symlinks=True)
        row = json.loads((w / "tree" / "docs" / "sa3_outcome_marginals.json").read_text())[0]
        marg.append({**row, "repo": name, "drawn": drawn})
    (d / "docs" / "sa3_outcome_marginals.json").write_text(json.dumps(marg, indent=1) + "\n")
    return d


# ================================================================================================== plants
def _universe(base: Path, which: str, name: str) -> list[str]:
    return sorted(json.loads((base / "runs" / f"{which}-{name}" / "manifest" / "probe.json").read_text())["universe"])


def _scan_update(db: Path, side: dict, path: str, sql_set: str, value) -> None:
    root = side["src_root"].rstrip("/") + "/"
    con = sqlite3.connect(str(db))
    try:
        n = con.execute(f"update file_data set {sql_set} = ? where file_path = ? or file_path = ?",
                        (value, root + path, path)).rowcount
        assert n == 1, (path, n)
        con.commit()
    finally:
        con.close()


def _outcome(d: Path, name: str) -> tuple[Path, dict]:
    f = d / "study" / "sa3_outcomes" / f"{name}.json"
    return f, json.loads(f.read_text())


def _fake_sha(tag: str, i: int) -> str:
    return hashlib.sha1(f"decoy-{tag}-{i}".encode()).hexdigest()


def _set_pool(d: Path, name: str, commits: dict) -> None:
    f, o = _outcome(d, name)
    files = set().union(*map(set, commits.values())) if commits else set()
    o["outcomes"]["control_pool"] = {"n_commits": len(commits), "n_files_any": len(files), "commits": commits}
    f.write_text(json.dumps(o) + "\n")


def plant(base: Path, which: str, d: Path, name: str, what: str, marg: list[dict]) -> dict:
    """one edit to the decoy's own files after the pipeline ran; returns what was done (counts only)"""
    st = d / "study"
    side = json.loads((st / "sa3_scans" / f"{name}.json").read_text())
    db = st / "sa3_scans" / f"{name}_master.db"
    uni = _universe(base, which, name)
    if what == "struct_branch_missing":              # 296 files in use: 5 bands, not 10
        k = len(uni) - 296
        for p in uni[:k]:
            _scan_update(db, side, p, "struct_branch", None)
        return {"files": k, "in_use": 296}
    if what == "telemetry_cases":                   # every telemetry case the reference can read without stopping
        for p, rec in zip(uni[20:], TELEMETRY):
            _scan_update(db, side, p, "mitigation_telemetry", rec)
        return {"files": len(TELEMETRY)}
    if what == "nest_sparse":                       # nesting values for 40 files only: a cell under the pair floor
        f = st / "sa3_nesting" / f"{name}.json"
        n = json.loads(f.read_text())
        keep = set(uni[::7][:40])
        n["files"] = {p: v for p, v in n["files"].items() if p in keep}
        f.write_text(json.dumps(n) + "\n")
        return {"files": len(n["files"])}
    if what in ("pool_smaller_than_hp", "pool_under_five"):
        _f, o = _outcome(d, name)
        keep = 15 if what == "pool_smaller_than_hp" else 3
        pool = dict(list(o["outcomes"]["control_pool"]["commits"].items())[:keep])
        assert len(o["outcomes"]["HP"]["commits"]) > keep
        _set_pool(d, name, pool)
        return {"pool": keep, "hp": len(o["outcomes"]["HP"]["commits"])}
    if what == "pool_mostly_empty":
        # 400 commits with no path, 6 that touch only files with no struct_branch value, 2 ordinary ones: so about
        # one draw in six is dropped for every predictor (an empty control) and about half for struct_branch alone
        _f, o = _outcome(d, name)
        real = list(o["outcomes"]["control_pool"]["commits"].items())[:2]
        missing = uni[:10]
        commits = [(_fake_sha(name, i), []) for i in range(400)]
        commits += [(_fake_sha(name, 1000 + i), [missing[i]]) for i in range(6)]
        commits += real
        random.Random(7).shuffle(commits)
        _set_pool(d, name, dict(commits))
        return {"empty": 400, "missing_only": 6, "ordinary": 2}
    if what == "pool_covers_everything":
        # a pool smaller than HP (every pool commit drawn in every draw, then K of HP's) whose union is every
        # universe file: each draw is dropped AFTER both draws used the stream
        _f, o = _outcome(d, name)
        pool = dict(list(o["outcomes"]["control_pool"]["commits"].items())[:12])
        pool[_fake_sha(name, 0)] = list(uni)
        assert len(o["outcomes"]["HP"]["commits"]) > len(pool)
        _set_pool(d, name, pool)
        return {"pool": len(pool), "hp": len(o["outcomes"]["HP"]["commits"])}
    if what == "window_short":                      # stage_score reads window_days from the marginals row only
        f, o = _outcome(d, name)
        o["window_days"] = 671.0
        f.write_text(json.dumps(o) + "\n")
        for row in marg:
            if row["repo"] == name:
                row["window_days"] = 671.0
        return {"window_days": 671.0}
    if what == "hp_floor_failed":                   # status ok, the primary outcome under its floor
        f, o = _outcome(d, name)
        o["outcomes"]["HP"]["clears_floor"] = False
        f.write_text(json.dumps(o) + "\n")
        for row in marg:
            if row["repo"] == name:
                row["HP"]["clears_floor"] = False
        return {}
    raise KeyError(what)


def checkpoint(db: Path) -> None:
    """after an edit, fold the -wal back so the database file alone holds the rows (the -wal/-shm stay empty)"""
    con = sqlite3.connect(str(db))
    try:
        if con.execute("pragma journal_mode").fetchone()[0] == "wal":
            con.execute("pragma wal_checkpoint(TRUNCATE)")
    finally:
        con.close()


# ================================================================================================ reference
def write_docs(docs: Path) -> None:
    for n in SEALED_DOCS:
        shutil.copyfile(U.WORKTREE / "docs" / n, docs / n)
    (docs / "sa3_code_review.md").write_text(
        "# PLACEHOLDER written by tools/compare/decoy_study.py -- not a code review\n\nThis file exists only so "
        "that `sa3_score.py lock` can run on a decoy study (as tools/harness shim 13 does).\n")


def reference_work(base: Path, d: Path) -> Path:
    """the harness WORK for the whole study: study, pool, and the tree as a git checkout"""
    SB = U.harness_sandbox()
    w = base / "work"
    if w.exists():
        shutil.rmtree(w)
    SB.prepare(w)
    shutil.copytree(d / "study", w / "study", dirs_exist_ok=True)
    for c in sorted((d / "pool").iterdir()):
        shutil.copytree(c, w / "pool" / c.name, symlinks=True)
    tree = w / "tree"
    shutil.copytree(U.TOOLS, tree / "tools", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (tree / "docs").mkdir(exist_ok=True)
    for f in ("sa3_outcome_marginals.json", "sa3_code_review.md") + SEALED_DOCS:
        shutil.copyfile(d / "docs" / f, tree / "docs" / f)
    if not SB.copy_linguist_cache(w):
        raise RuntimeError("linguist cache absent")
    git(tree, "init", "-q")
    git(tree, "add", "-A")
    git(tree, "commit", "-q", "-m", "decoy reference tree")
    return w


def sb_run(w: Path, argv: list[str], timeout: int = 7200) -> subprocess.CompletedProcess:
    SB = U.harness_sandbox()
    return SB.run(argv, w, cwd=w / "tree", timeout=timeout)


COV_DRIVER = r'''
import json, os, sys, sysconfig, trace
out = sys.argv[1]
sys.path.insert(0, os.path.abspath("tools"))
import sa3_score as SC
ign = sorted({sys.prefix, sys.exec_prefix, sysconfig.get_paths()["stdlib"], sysconfig.get_paths()["purelib"],
              sysconfig.get_paths()["platlib"], "/usr/lib/python3", "/usr/lib/python3/dist-packages",
              os.path.expanduser("~/.local/lib")})
t = trace.Trace(count=1, trace=0, ignoredirs=ign)
rc = t.runfunc(SC.stage_score)
me = os.path.abspath(SC.__file__)
lines = sorted(l for (f, l), n in t.results().counts.items() if os.path.abspath(f) == me and n)
json.dump({"rc": rc, "executed": lines}, open(out, "w"))
'''


def reference(base: Path, d: Path) -> dict:
    """placebo (committed), lock, score, and score under the line tracer: all unchanged, in the harness sandbox"""
    w = reference_work(base, d)
    tree = w / "tree"
    rec = {}
    t0 = time.time()
    p = sb_run(w, [PY, "-B", "tools/sa3_score.py", "placebo"])
    rec["placebo"] = {"rc": p.returncode, "seconds": round(time.time() - t0, 1), "tail": p.stdout[-600:] + p.stderr[-600:]}
    if p.returncode:
        raise RuntimeError(f"placebo failed: {p.stdout[-2000:]} {p.stderr[-2000:]}")
    shutil.copyfile(tree / "docs" / "sa3_placebo.json", d / "docs" / "sa3_placebo.json")
    git(tree, "add", "-A")
    git(tree, "commit", "-q", "-m", "placebo output")
    p = sb_run(w, [PY, "-B", "tools/sa3_score.py", "lock"])
    rec["lock"] = {"rc": p.returncode, "said": p.stdout.strip()[-300:]}
    if p.returncode:
        raise RuntimeError(f"lock refused: {p.stdout[-1000:]}")
    lock = json.loads((tree / "docs" / "sa3_lock.json").read_text())
    if not lock["sealed_at_commit"] or not all(lock["files"].values()):
        raise RuntimeError("lock wrote empty hashes: the tree is not a working git checkout")
    t0 = time.time()
    p = sb_run(w, [PY, "-B", "tools/sa3_score.py", "score"])
    rec["score"] = {"rc": p.returncode, "seconds": round(time.time() - t0, 1), "said": p.stdout.strip()[-1500:],
                    "err": p.stderr.strip()[-1500:]}
    if p.returncode:
        raise RuntimeError(f"score failed: {p.stdout[-2000:]} {p.stderr[-2000:]}")
    (d / "reference").mkdir(exist_ok=True)
    shutil.copyfile(tree / "docs" / "sa3_result.json", d / "reference" / "sa3_result.json")
    shutil.copyfile(tree / "docs" / "sa3_lock.json", d / "docs" / "sa3_lock.json")
    (w / "cov_driver.py").write_text(COV_DRIVER)
    t0 = time.time()
    p = sb_run(w, [PY, "-B", str(w / "cov_driver.py"), str(w / "coverage.json")])
    rec["coverage"] = {"rc": p.returncode, "seconds": round(time.time() - t0, 1), "err": p.stderr[-1500:]}
    if p.returncode or not (w / "coverage.json").exists():
        raise RuntimeError(f"traced score failed: {p.stdout[-1500:]} {p.stderr[-1500:]}")
    shutil.copyfile(w / "coverage.json", d / "reference" / "coverage.json")
    rec["traced_result_identical"] = (tree / "docs" / "sa3_result.json").read_bytes() == \
        (d / "reference" / "sa3_result.json").read_bytes()
    return rec


def tables(base: Path, d: Path) -> dict:
    """phase B (unchanged) on the decoy, then this directory's predictor and label tables"""
    T = U.sibling("tables")
    tb = base / "tables"
    for x in (tb, base / "scratch"):
        if x.exists():
            shutil.rmtree(x)
    tb.mkdir()
    p = subprocess.run([PY, "-B", str(PHASE_B), "--decoy", str(d), "--out", str(tb / "phase_b"), "--scratch",
                        str(base / "scratch" / "phase_b")], capture_output=True, text=True, timeout=7200,
                       env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if p.returncode:
        raise RuntimeError(f"phase B failed: {p.stdout[-2000:]} {p.stderr[-2000:]}")
    marg = json.loads((d / "docs" / "sa3_outcome_marginals.json").read_text())
    repos = [r["repo"] for r in marg if r["status"] == "ok"]
    res = T.build_predictor_tables(d / "study", repos, tb / "compare", base / "scratch" / "compare_tables")
    if not all(v["status"] == "ok" for v in res.values()):
        raise RuntimeError(f"compare tables failed: {res}")
    T.build_label_tables(d / "study" / "sa3_outcomes", repos, tb / "labels")
    return {"repos": repos}


def sealed_copy(base: Path, d: Path) -> Path:
    """the sealed copies the comparison scorer reads, from the pristine reference tree"""
    s = base / "sealed"
    if s.exists():
        shutil.rmtree(s)
    (s / "tools").mkdir(parents=True)
    (s / "docs").mkdir()
    tree = base / "work" / "tree"
    for f in ("sa3_stats.py", "sa3_score.py"):
        shutil.copyfile(tree / "tools" / f, s / "tools" / f)
    for f in ("sa3_outcome_marginals.json", "sa3_placebo.json", "sa3_lock.json"):
        shutil.copyfile(tree / "docs" / f, s / "docs" / f)
    return s


def recipe_hash() -> str:
    """what a build depends on: the recipe, the source of the building functions (not the coverage report's),
    this directory's table builder, and the generator, harness, phase B and SA3 code it runs"""
    import inspect
    h = hashlib.sha256(json.dumps([RECIPE, TELEMETRY, EFFECT, SEALED_DOCS, COV_DRIVER]).encode())
    for fn in (git, control, assemble, _universe, _scan_update, _outcome, _fake_sha, _set_pool, plant, checkpoint,
               write_docs, reference_work, sb_run, reference, tables, sealed_copy):
        h.update(inspect.getsource(fn).encode())
    for f in [U.HERE / "tables.py"] + sorted((U.TOOLS / "control_repo").glob("*.py")) + \
            sorted((U.TOOLS / "harness").glob("*.py")) + sorted((U.TOOLS / "tables").glob("*.py")) + \
            [U.TOOLS / f"{m}.py" for m in ("sa3_score", "sa3_stats", "sa3_outcomes", "mod1_lift", "sa3_scan",
                                            "sa3_nest_scan", "laws_history", "laws_units", "hist_meta")]:
        h.update(f.name.encode() + b"\0" + f.read_bytes())
    return h.hexdigest()


def gate_variant(base: Path) -> dict:
    """study P with its committed placebo file's `valid` set to false (an edit to the decoy's own document): the
    reference's "NO FINDING" branch. A copy of the reference WORK; lock, score and the traced score again; the
    sealed copies of the variant beside it (base/gate/)"""
    g = base / "gate"
    done = g / "done.json"
    if done.exists():
        return json.loads(done.read_text())
    if g.exists():
        shutil.rmtree(g)
    g.mkdir()
    SB = U.harness_sandbox()
    w = g / "work"
    shutil.copytree(base / "work", w, symlinks=True)
    SB.prepare(w)
    tree = w / "tree"
    pf = tree / "docs" / "sa3_placebo.json"
    pl = json.loads(pf.read_text())
    pl["valid"] = False
    pf.write_text(json.dumps(pl, indent=1) + "\n")
    for f in ("sa3_lock.json", "sa3_result.json"):
        (tree / "docs" / f).unlink(missing_ok=True)
    git(tree, "add", "-A")
    git(tree, "commit", "-q", "-m", "placebo gate failed (decoy variant)")
    rec = {}
    for stage in ("lock", "score"):
        p = sb_run(w, [PY, "-B", "tools/sa3_score.py", stage])
        rec[stage] = p.returncode
        if p.returncode:
            raise RuntimeError(f"gate variant {stage}: {p.stdout[-1000:]} {p.stderr[-1000:]}")
    shutil.copyfile(tree / "docs" / "sa3_result.json", g / "sa3_result.json")
    p = sb_run(w, [PY, "-B", str(w / "cov_driver.py"), str(w / "coverage_gate.json")])   # WORK is the writable place
    if p.returncode:
        raise RuntimeError(f"gate variant traced score: {p.stderr[-1000:]}")
    shutil.copyfile(w / "coverage_gate.json", g / "coverage.json")
    s = g / "sealed"
    (s / "tools").mkdir(parents=True)
    (s / "docs").mkdir()
    for f in ("sa3_stats.py", "sa3_score.py"):
        shutil.copyfile(tree / "tools" / f, s / "tools" / f)
    for f in ("sa3_outcome_marginals.json", "sa3_placebo.json", "sa3_lock.json"):
        shutil.copyfile(tree / "docs" / f, s / "docs" / f)
    shutil.rmtree(w / "study")                       # the variant's inputs are the study's own; keep the tree only
    shutil.rmtree(w / "pool")
    rec.update({"result": str(g / "sa3_result.json"), "sealed": str(s), "coverage": str(g / "coverage.json")})
    done.write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def build(base: Path, which: str) -> dict:
    """the whole study; idempotent: a finished build with the same recipe and code is reused. Study P also gets
    its gate-failed variant (gate_variant)"""
    SB = U.harness_sandbox()
    base = SB.check_work(Path(base)) / which
    done = base / "built.json"
    rh = recipe_hash()
    if done.exists():
        rec = json.loads(done.read_text())
        if rec.get("recipe") == rh:
            if which == "P":
                rec["gate"] = gate_variant(base)
            return rec
    base.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    d = assemble(base, which)
    marg = json.loads((d / "docs" / "sa3_outcome_marginals.json").read_text())
    planted = {}
    for name, *_r, plants in RECIPE:
        for what in plants:
            planted[f"{name}:{what}"] = plant(base, which, d, name, what, marg)
        checkpoint(d / "study" / "sa3_scans" / f"{name}_master.db")
    (d / "docs" / "sa3_outcome_marginals.json").write_text(json.dumps(marg, indent=1) + "\n")
    write_docs(d / "docs")
    t1 = time.time()
    ref = reference(base, d)
    t2 = time.time()
    tb = tables(base, d)
    sealed_copy(base, d)
    rec = {"recipe": rh, "which": which, "planted": planted, "reference": ref, "tables": tb,
           "seconds": {"controls_and_assembly": round(t1 - t0, 1), "reference": round(t2 - t1, 1),
                       "tables": round(time.time() - t2, 1)},
           "paths": {"decoy": str(d), "tree": str(base / "work" / "tree"), "tables": str(base / "tables"),
                     "sealed": str(base / "sealed"), "result": str(d / "reference" / "sa3_result.json")}}
    done.write_text(json.dumps(rec, indent=1) + "\n")
    if which == "P":
        if (base / "gate").exists():                 # a variant of an earlier build is never reused
            shutil.rmtree(base / "gate")
        rec["gate"] = gate_variant(base)
    return rec


# ================================================================================================= coverage
def function_ranges(src: Path) -> dict[str, tuple[int, int]]:
    tree = ast.parse(Path(src).read_text())
    return {n.name: (n.lineno, n.end_lineno) for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in COVERED}


def executable_lines(src: Path) -> dict[str, list[int]]:
    """the lines of the four functions that the standard library's tracer counts as executable"""
    import trace
    exe = set(trace._find_executable_linenos(str(src)))
    return {f: sorted(l for l in exe if a <= l <= b) for f, (a, b) in function_ranges(src).items()}


# why a line no decoy study reaches, by a piece of its text; the coverage test fails on any unexecuted line that
# matches none of these
REASONS = (
    ('print("LOCKED.', "one of the two LOCKED refusals, excepted by the spec: every decoy run is locked correctly"),
    ("return 2", "the exit of a LOCKED refusal (excepted by the spec)"),
    ("not detected (Holm: an earlier test in the family failed)",
     "needs a confirmatory test supported at its Holm level after one ranked before it (a smaller p) was not "
     "supported, for example contradicted; the generator plants one effect (branches, positive) and no decoy has a "
     "contradicted confirmatory test"),
    ('reading = "not robust to the statistic"',
     "needs bAUC supported while the residual statistic is not; with the planted branches effect both are "
     "supported (study P), and with none neither is (study N)"),
    ('"supported, but tracks activity, not defects"',
     "needs a supported test whose matched-control difference is not supported; in study P the planted effect "
     "is in the fixes only, so the control difference is supported too"),
)


def reason_for(text: str) -> str | None:
    return next((why for key, why in REASONS if key in text), None)


def coverage(bases: list[Path], src: Path) -> dict:
    """lines of stage_score, control_effects, churn_any and summarize executed in none of the studies' traced
    runs, with the source text of each. A function's own `def` line runs at import, before the tracer starts, and
    is not listed"""
    lines = Path(src).read_text().splitlines()
    exe = executable_lines(src)
    starts = {a for a, _b in function_ranges(src).values()}
    ran: set[int] = set()
    for b in bases:
        ran |= set(json.loads((Path(b) / "decoy" / "reference" / "coverage.json").read_text())["executed"])
        if (Path(b) / "gate" / "coverage.json").exists():
            ran |= set(json.loads((Path(b) / "gate" / "coverage.json").read_text())["executed"])
    out = {}
    for f, ls in exe.items():
        out[f] = [{"line": l, "text": lines[l - 1].strip()} for l in ls if l not in ran and l not in starts]
    return {"executable": sum(len(v) for v in exe.values()) - len(starts), "unexecuted": out}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("build", "coverage"))
    ap.add_argument("--which", choices=("N", "P"))
    ap.add_argument("--base", required=True)
    a = ap.parse_args(argv)
    if a.what == "build":
        rec = build(Path(a.base), a.which)
        print(json.dumps({k: rec[k] for k in ("which", "planted", "seconds", "paths")}, indent=1))
        return 0
    cov = coverage([Path(a.base) / w for w in ("N", "P")], U.TOOLS / "sa3_score.py")
    print(json.dumps(cov, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
