"""Tests of the SA3 scoring job (tools/scoring/; docs/process/scoring_step_spec.md, Revision 2, section 9).

Everything runs on DECOYS. Part 1's two decoy studies (tools/compare/decoy_study.py, N and P: 12 control
repositories each, the unmodified pipeline through the harness, the reference placebo / lock / score in a git
checkout, phase B, the comparison tables) are built once, or reused from COMPARE_STUDY_CACHE. From a study,
tools/scoring/decoy.py makes the whole route of section 2 on throwaway directories: a private copy of the study, a
CHECKOUT standing in for this repository at commit C (a fresh clone of this repository with this worktree's
tools/ and the decoy's documents committed, tagged sa3-score-C), the predictor-side check of step 2, the deviation
table draft, and run-2 (the owner preparation job from that checkout: PASS). The scoring job is then run from that
checkout exactly as the owner runs it (section 3), in decoy mode with a throwaway ledger. Routes and the main run
are reused across processes from SCORING_ROUTE_CACHE (a directory under ~/.claude/jobs or /tmp), keyed by the code
under test, so each test can run alone.

Nothing here opens, lists or stats the real study directory, the corpus, the pool, the stored tables, the
protected root, the owner's report directory or ~/.blind. The blind test's faulty copies are READ (copied into
pytest's temporary directory) from the finished blind test's copies directory only. Every call into SA3 code runs
inside a sandbox. Skipped, with the reason, when bwrap, tree_sitter_language_pack 1.20.0, linguist's cached lists
or the engine export are unavailable.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.metadata as md
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
SCORING = ROOT / "tools" / "scoring"
HARNESS = ROOT / "tools" / "harness"
sys.path.insert(0, str(HARNESS))
import sandbox as SB  # noqa: E402
import sandbox_ro as SR  # noqa: E402


def _load(path: Path, name: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, str(path))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


SS = _load(SCORING / "score_sa3.py", "tools_scoring_score_sa3")
DC = _load(SCORING / "decoy.py", "tools_scoring_decoy")
LG, TX, SC, P, MD = SS.LG, SS.TX, SS.SC, SS.P, SS.scoring("report_md")
PY = sys.executable
BLIND = Path.home() / ".claude" / "jobs" / "24bf9d40" / "tmp" / "blind_material" / "copies"
BLIND_KEY = ROOT / "docs" / "process" / "blind_test_run1" / "KEY.json"
MARK_SHA = "c0ffee" + "5eed" * 8 + "ab"
MARK_VAL = "markerkey-424242-zz"
MARKERS = (MARK_SHA, MARK_VAL, "markerkey-424242", "zz_marker_key")
MARK_REPO = "ctrl-early1"            # not drawn, no harvest row deleted by either variant: the marker moves nothing
LINE = re.compile(r"step (\d+) ([a-z_0-9]+) ([A-Za-z0-9._+-]+|\*) (ok|failed)( [a-z_0-9]+)?")


# ============================================================================================== helpers
def _skip_reason() -> str | None:
    if not Path(SB.BWRAP).exists():
        return "bwrap not installed"
    try:
        if md.version("tree_sitter_language_pack") != "1.20.0":
            return "tree_sitter_language_pack is not 1.20.0 in this interpreter"
    except md.PackageNotFoundError:
        return "tree_sitter_language_pack not installed"
    if not (Path.home() / SB.LINGUIST_SUB / "vendor.yml").is_file():
        return "linguist cache absent"
    return None


def _engine_present(base: Path) -> bool:
    w = SB.prepare(base / "engine-probe")
    (w / "tree/tools/harness").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HARNESS / "sandbox.py", w / "tree/tools/harness/sandbox.py")
    p = SB.run(["/usr/bin/python3", "-I", "-B", "-c",
                f"import os; print(os.path.isdir({str(SB.ENGINE / 'gitgalaxy')!r}))"], w, timeout=120)
    return p.stdout.strip() == "True"


def code_key(*extra: str) -> str:
    h = hashlib.sha256("\0".join(extra).encode())
    for f in sorted((ROOT / "tools").rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
            h.update(str(f.relative_to(ROOT)).encode() + b"\0" + f.read_bytes())
    return h.hexdigest()[:16]


def run(cmd: list[str], env: dict | None = None, timeout: int = 7200, **kw) -> subprocess.CompletedProcess:
    e = {k: v for k, v in os.environ.items() if k != SS.TEST_FAIL_ENV}
    return subprocess.run(cmd, capture_output=True, text=True, env={**e, **(env or {})}, timeout=timeout,
                          stdin=subprocess.DEVNULL, **kw)


def ledger_of(d: Path) -> list[dict]:
    return LG.read(d)


def public_text(*dirs: Path) -> str:
    out = []
    for d in dirs:
        for f in sorted(Path(d).rglob("*")):
            if f.is_file():
                out.append(f.read_text(errors="replace"))
    return "\n".join(out)


def plant_markers(decoy: Path) -> None:
    """a pool commit with a marker hash (re-using a path already in the pool: the loader asserts universe paths)
    and a marker value under an extra key, in one repo's outcome file; nothing reads either but the encoders"""
    f = decoy / "study" / "sa3_outcomes" / f"{MARK_REPO}.json"
    o = json.loads(f.read_text())
    pool = o["outcomes"]["control_pool"]["commits"]
    path = next(p for v in pool.values() for p in v)
    pool[MARK_SHA] = [path]
    o["outcomes"]["control_pool"]["n_commits"] = len(pool)
    o["zz_marker_key"] = MARK_VAL
    f.write_text(json.dumps(o) + "\n")


class Run:
    """one scoring job, run as the owner runs it, from the route's checkout"""

    def __init__(self, route: dict, base: Path, *extra: str, env: dict | None = None, ledger: Path | None = None,
                 timeout: int = 7200):
        self.base = Path(base)
        self.prot, self.out = self.base / "prot", self.base / "pub"
        self.ledger = ledger or self.base / "ledger" / "sa3_score_ledger.jsonl"
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.cmd = DC.command(route, self.prot, self.out, self.ledger, *extra)
        p = run(self.cmd, env=env, timeout=timeout)
        self.rc, self.stdout, self.stderr = p.returncode, p.stdout, p.stderr
        self.lines = p.stdout.splitlines()

    def report(self) -> dict:
        return json.loads((self.out / "report.json").read_text())


def resume_cmd(route: dict, prot: Path, out: Path, ledger: Path, receipt: str, commit: str | None = None) -> list:
    return [PY, "-I", "-B", str(Path(route["repo"]) / "tools" / "scoring" / "score_sa3.py"), "--decoy", route["decoy"],
            "--resume", "--commit", commit or route["commit"], "--receipt", receipt, "--protected", str(prot),
            "--out", str(out), "--ledger", str(ledger)]


def receipt_of(lines: list[str]) -> str:
    r = [x for x in lines if x.startswith("keep this line somewhere other than this machine: receipt")]
    assert len(r) == 1, lines
    return r[0].split("sa3_result.json sha256 ")[1].split()[0]


def git(repo: Path, *a: str) -> str:
    return DC.git(repo, *a)


def copy_repo(route: dict, dst: Path) -> Path:
    shutil.copytree(route["repo"], dst, symlinks=True)
    return dst


# ============================================================================================== fixtures
@pytest.fixture(scope="session")
def study_cache(tmp_path_factory) -> Path:
    why = _skip_reason()
    if why:
        pytest.skip(why)
    env = os.environ.get("COMPARE_STUDY_CACHE")
    b = SB.check_work(Path(env)) if env else tmp_path_factory.mktemp("compare")
    b.mkdir(parents=True, exist_ok=True)
    if not _engine_present(b):
        pytest.skip("engine export not present")
    return b


@pytest.fixture(scope="session")
def route_cache(tmp_path_factory) -> Path:
    env = os.environ.get("SCORING_ROUTE_CACHE")
    b = SB.check_work(Path(env)) if env else tmp_path_factory.mktemp("scoring")
    b.mkdir(parents=True, exist_ok=True)
    return b


def _study(study_cache: Path, which: str) -> Path:
    DS = _load(ROOT / "tools" / "compare" / "decoy_study.py", "tools_compare_decoy_study")
    DS.build(study_cache, which)
    return study_cache / which


def _route(study_cache: Path, route_cache: Path, which: str, plant=None, tag: str = "") -> dict:
    d = route_cache / f"route-{which}{tag}-{code_key(which, tag)}"
    done = d / "route.json"
    if done.exists():
        return json.loads(done.read_text())
    if d.exists():
        shutil.rmtree(d)
    rec = DC.build(_study(study_cache, which), d / "b", plant=plant)
    done.write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def _main_run(route: dict, name: str) -> dict:
    """the full decoy run of a route, once per code version (reused from the cache): its terminal and paths"""
    d = Path(route["base"]).parent / name
    done = d / "run.json"
    if done.exists():
        return json.loads(done.read_text())
    if d.exists():
        shutil.rmtree(d)
    t0 = time.time()
    r = Run(route, d)
    rec = {"rc": r.rc, "lines": r.lines, "stderr": r.stderr, "prot": str(r.prot), "out": str(r.out),
           "ledger": str(r.ledger), "seconds": round(time.time() - t0, 1)}
    done.write_text(json.dumps(rec, indent=1) + "\n")
    return rec


@pytest.fixture(scope="session")
def routeP(study_cache, route_cache) -> dict:
    return _route(study_cache, route_cache, "P", plant=plant_markers, tag="m")


@pytest.fixture(scope="session")
def runP(routeP) -> dict:
    return _main_run(routeP, "runP")


# ===================================================================== 1. refusals and the ledger's rule
def _main(argv, monkeypatch=None, reader=None):
    asked = []
    rc = SS.main(argv, reader=reader or (lambda prompt: asked.append(prompt) or ""), echo=lambda line: None)
    return rc, asked


def test_1a_refusals_before_anything(tmp_path, monkeypatch, capsys):
    """string refusals, exit 2, nothing created: no target; --decoy with --real; --real without --i-am-the-owner;
    no or short --commit; no --seal; no --protected; a decoy without --ledger; --ledger on a real run; the test
    variable on a real run; a bad --rerun reason; --rerun with --resume; --resume without a receipt; a protected
    directory that is not empty; a ledger inside a run directory; a real run whose protected directory is outside
    the protected root"""
    d = tmp_path / "decoy"
    (d / "docs").mkdir(parents=True)
    c = "a" * 40
    ok = ["--decoy", str(d), "--commit", c, "--seal", str(tmp_path / "s/seal.json"), "--protected",
          str(tmp_path / "prot"), "--out", str(tmp_path / "pub"), "--ledger", str(tmp_path / "led/l.jsonl")]

    def without(*flags):
        out, skip = [], False
        for x in ok:
            if skip:
                skip = False
                continue
            if x in flags:
                skip = True
                continue
            out.append(x)
        return out

    nonempty = tmp_path / "full"
    nonempty.mkdir()
    (nonempty / "x").write_text("x")
    cases = [
        without("--decoy"),
        ok + ["--real"],
        ["--real", "--commit", c, "--seal", "s", "--protected", str(tmp_path / "p"), "--out", str(tmp_path / "o")],
        without("--commit"),
        without("--commit") + ["--commit", "abc"],
        without("--seal"),
        without("--protected"),
        without("--ledger"),
        ["--real", "--i-am-the-owner", "--commit", c, "--seal", "s", "--protected",
         str(SR.PROTECTED_ROOT / "score-x"), "--out", str(tmp_path / "o"), "--ledger", str(tmp_path / "l")],
        ok + ["--rerun", "because $(rm -rf)"],
        ok + ["--rerun", "fine reason", "--resume", "--receipt", "b" * 64],
        ok + ["--resume"],
        without("--protected") + ["--protected", str(nonempty)],
        without("--ledger") + ["--ledger", str(tmp_path / "prot" / "l.jsonl")],
        ["--real", "--i-am-the-owner", "--commit", c, "--seal", "s", "--protected", str(tmp_path / "p"),
         "--out", str(tmp_path / "o")],
    ]
    for argv in cases:
        rc, asked = _main(argv)
        assert rc == 2 and not asked, argv
    monkeypatch.setenv(SS.TEST_FAIL_ENV, "labels")
    rc, asked = _main(["--real", "--i-am-the-owner", "--commit", c, "--seal", "s", "--protected",
                       str(SR.PROTECTED_ROOT / "score-x"), "--out", str(tmp_path / "o")])
    assert rc == 2 and not asked
    err = capsys.readouterr().err
    assert "decoy tests only" in err
    for p in ("prot", "pub", "led", "p", "o"):
        assert not (tmp_path / p).exists(), p


def test_1b_the_ledger_rule():
    """section 5: any entry refuses a start, whatever directory is named; --rerun only after a start with no
    completion; after a completion, no start ever, only --resume"""
    s = LG.entry("started", "a" * 40, "b" * 64)
    st = LG.entry("stopped", "a" * 40, "b" * 64, code="score_crashed")
    c = LG.entry("completed", "a" * 40, "b" * 64, result_sha256="c" * 64)
    r = LG.entry("resume", "a" * 40, "b" * 64)
    assert LG.decide([], False, None) == "first"
    for entries, resume, rerun, want in (
            ([], False, "why", "rerun_needs_start"), ([], True, None, "nothing_to_resume"),
            ([s], False, None, "ledger_has_entry"), ([s, st], False, None, "ledger_has_entry"),
            ([s, c], False, None, "ledger_completed"), ([s, c], False, "why", "ledger_completed"),
            ([s, c, r], False, "why", "ledger_completed"), ([s], True, None, "nothing_to_resume")):
        with pytest.raises(LG.LedgerError) as e:
            LG.decide(entries, resume, rerun)
        assert e.value.code == want, (entries, resume, rerun)
    assert LG.decide([s], False, "power cut") == "rerun"
    assert LG.decide([s, st], False, "crash") == "rerun"
    assert LG.decide([s, c], True, None) == "resume"
    assert LG.decide([s, c, r], True, None) == "resume"
    assert set(TX.STOP_CODES) >= {"ledger_has_entry", "ledger_completed", "rerun_needs_start", "nothing_to_resume"}


def test_1c_validator_rejects_paths_hashes_and_free_text():
    voc = SC.Vocab(repos=frozenset({"django"}), codepaths=frozenset({"tools/sa3_score.py"}), commit="a" * 40)
    good = {"status": "ok", "code": "none", "modules": {"tools/sa3_score.py": "f" * 64}, "rc": 0}
    SC.validate_stage("lock", good, voc)
    for bad in ({**good, "rc": "0"}, {**good, "extra": 1}, {**good, "modules": {"/etc/passwd": "f" * 64}},
                {**good, "modules": {"tools/other.py": "f" * 64}}, {**good, "code": "free text"},
                {"status": "failed", "code": "none", "modules": {}}):
        with pytest.raises(SC.ReportError) as e:
            SC.validate_stage("lock", bad, voc)
        assert str(e.value).startswith("invalid report value: lock.result")
        assert "passwd" not in str(e.value) and "free text" not in str(e.value)
    lab = {"status": "ok", "code": "none", "modules": {},
           "label_check": {"repos": {"django": {"code": "none", "comparable": True,
                                                "items": {i: True for i in SC.LABEL_REPO["items"]}}},
                           "repos_checked": 1, "all_equal": True}}
    SC.validate_stage("labels", lab, voc)
    lab2 = json.loads(json.dumps(lab))
    lab2["label_check"]["repos"]["/srv/x"] = lab2["label_check"]["repos"]["django"]
    with pytest.raises(SC.ReportError):
        SC.validate_stage("labels", lab2, voc)
    for kind, v in (("reason", "ok reason"), ("cellpos", "django"), ("cellpos", "HP|struct_branch|bauc|all_drawn"),
                    ("commit", "a" * 40)):
        SC.leaf(kind, v, "f", voc)
    for kind, v in (("reason", "x" * 201), ("reason", "rm -rf $HOME"), ("cellpos", "src/a.py"), ("commit", "b" * 40),
                    ("real", float("nan")), ("hex64", "A" * 64)):
        with pytest.raises(SC.ReportError):
            SC.leaf(kind, v, "f", voc)


def test_1d_result_shape_check():
    """the reference's result file by shape: a path, a commit hash or free text anywhere refuses it"""
    sealed = frozenset({"tools/sa3_score.py"})
    res = {"valid": True, "unavailable": SC.UNAVAILABLE, "repos": {"django": {"n": 3, "outcomes": {"HP": {
        "struct_branch": {"status": "ok", "bauc": float("nan"), "ci95": [0.1, 0.2]}}}}},
        "tests": {"struct_branch": {"reading": "supported, defect-specific"}}, "sealed": {"tools/sa3_score.py": "a" * 40},
        "engine": "b" * 40, "not_run": SC.NOT_RUN, "side_counts": {}, "random_effects": {},
        "summaries": {"HP|struct_branch|bauc|all_drawn": {"n": 3, "reading": "supported"}}}
    SC.check_result(res, frozenset({"django"}), sealed)
    for path, val in ((("repos", "django", "outcomes", "HP", "struct_branch", "status"), "src/x.py"),
                      (("engine",), "not a hash"), (("tests", "struct_branch", "reading"), "c" * 40),
                      (("summaries", "HP|struct_branch|bauc|all_drawn", "reading"), "free words")):
        bad = json.loads(json.dumps(res).replace("NaN", "0"))
        x = bad
        for k in path[:-1]:
            x = x[k]
        x[path[-1]] = val
        with pytest.raises(SC.ResultShapeError):
            SC.check_result(bad, frozenset({"django"}), sealed)
    bad = json.loads(json.dumps(res).replace("NaN", "0"))
    bad["repos"]["/abs/path"] = bad["repos"].pop("django")
    with pytest.raises(SC.ResultShapeError):
        SC.check_result(bad, frozenset({"django"}), sealed)
    bad = json.loads(json.dumps(res).replace("NaN", "0"))
    bad["repos"]["django"]["outcomes"]["HP"]["struct_branch"]["zz_new_statistic_77"] = "zz value 88"
    with pytest.raises(SC.ResultShapeError) as e:
        SC.check_result(bad, frozenset({"django"}), sealed)
    assert str(e.value) == "repos.<repo>.outcomes.HP.struct_branch.<key>"
    SC.leaf("shapepos", str(e.value), "f", SC.Vocab())
    for v in ("repos.django.x", "zz_new_statistic_77", "repos.<repo>./etc"):
        with pytest.raises(SC.ReportError):
            SC.leaf("shapepos", v, "f", SC.Vocab())


def test_1e_resume_has_no_path_to_the_score():
    """static half of "resume can never start the reference score": in the launcher's source, the function that
    runs it (step9_score) is called from run_full only, and nothing reachable from resume() names it, the
    'score' stage, or the reference's stage_score"""
    src = (SCORING / "score_sa3.py").read_text()
    tree = ast.parse(src)
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    callers = [f for f, n in funcs.items() if any(isinstance(x, ast.Name) and x.id == "step9_score"
                                                   for x in ast.walk(n))]
    assert callers == ["run_full"], callers

    def reach(name, seen):
        if name in seen or name not in funcs:
            return seen
        seen.add(name)
        for x in ast.walk(funcs[name]):
            if isinstance(x, ast.Name) and x.id in funcs:
                reach(x.id, seen)
            if isinstance(x, ast.Attribute) and x.attr in funcs:
                reach(x.attr, seen)
        return seen

    r = reach("resume", set())
    assert "run_full" not in r and "step9_score" not in r and "step7_lock" not in r, sorted(r)
    for f in r:
        body = ast.get_source_segment(src, funcs[f])
        assert '"score"' not in body.replace('"score" if', "") and "stage_score" not in body, f
    stages = (SCORING / "stages.py").read_text()
    assert stages.count("SC.stage_score()") == 1              # once, in st_score


def test_1f_bind_layout_of_lock_and_score(tmp_path):
    """section 3, step 7: the clone's docs/ is the only writable directory and comes FIRST (sandbox_ro binds
    read-write directories before code), .git and tools/ are read-only binds after it; the clone root itself is
    never bound, so nothing covers docs/"""
    clone = tmp_path / "prot" / "clone"
    for sub in ("docs", ".git", "tools"):
        (clone / sub).mkdir(parents=True)
    job = SimpleNamespace(pl=SimpleNamespace(clone=clone))
    rw, code = SS.lock_layout(job)
    assert rw == [clone / "docs"] and code == [clone / ".git", clone / "tools"]
    rundir = tmp_path / "prot" / "runs" / "lock"
    rundir.mkdir(parents=True)
    spec = SR.Spec(rw=[rundir, *rw], code=code, inputs=[], cwd=rundir)
    argv = SR.bwrap_argv(spec, SR.environment(spec, rundir, rundir))
    binds = [(argv[i], argv[i + 1]) for i in range(len(argv)) if argv[i] in ("--bind", "--ro-bind")]
    assert ("--bind", str(clone / "docs")) in binds
    assert binds.index(("--bind", str(clone / "docs"))) < binds.index(("--ro-bind", str(clone / ".git")))
    assert not any(b[1] == str(clone) for b in binds)


def test_1g_section6_sentences_each_exactly_when_its_case_happens():
    """every case of the table, and only its sentence (plus the gate's, which is always printed)"""
    ok = {"status": "ok", "code": "none"}
    lab_ok = {**ok, "label_check": {"all_equal": True, "repos": {"go": {"code": "none"}}}}
    lab_bad = {**ok, "label_check": {"all_equal": False, "repos": {"go": {"code": "none"}}}}
    lab_err = {**ok, "label_check": {"all_equal": False, "repos": {"go": {"code": "value_error"}}}}

    def cm(w, d, r):
        return {**ok, "cellmap": {"all_equal": not (w or d or r), "not_equal_by_class": {"W": w, "D": d, "R": r}}}

    rest = {k: ok for k in ("readings", "named", "hv_prepare", "PU_tracker_keys_case_sensitive",
                            "PU_late_revert_ticket_dropped")}
    F = {"status": "failed", "code": "unclassified"}
    for parts, want in (({"labels": lab_ok, "compare": cm(0, 0, 0), **rest}, ["gate"]),
                        ({"labels": lab_bad, "compare": cm(0, 0, 0), **rest}, ["gate", "label_check"]),
                        ({"labels": lab_ok, "compare": cm(0, 0, 5), **rest}, ["gate", "r_only"]),
                        ({"labels": lab_ok, "compare": cm(1, 0, 5), **rest}, ["gate", "w_or_d"]),
                        ({"labels": lab_ok, "compare": cm(0, 2, 0), **rest}, ["gate", "w_or_d"]),
                        ({"labels": lab_ok, "compare": cm(0, 0, 0), **rest, "named": F}, ["gate", "part_failed"]),
                        ({"labels": lab_ok, "compare": cm(0, 0, 0), **rest, "readings": F}, ["gate", "part_failed"]),
                        ({"labels": lab_bad, "compare": cm(3, 0, 0), **rest, "PU_late_revert_ticket_dropped": F},
                         ["gate", "label_check", "w_or_d", "part_failed"]),
                        # owner ruling of 2026-11-15: a check that cannot be computed is "not confirmed"
                        ({"labels": F, "compare": {"status": "failed", "code": "dependency_failed"}, **rest},
                         ["gate", "not_computed"]),
                        ({"labels": lab_ok, "compare": {"status": "failed", "code": "value_error"}, **rest},
                         ["gate", "not_computed"]),
                        ({"labels": lab_err, "compare": {"status": "failed", "code": "value_error"}, **rest,
                          "named": F}, ["gate", "label_check", "not_computed", "part_failed"])):
        assert SS.sentences_after(parts) == want, want
    assert SS.check_not_computed({"labels": F, "compare": F}) == "unclassified"
    assert SS.check_not_computed({"labels": lab_err, "compare": cm(0, 0, 0)}) == "value_error"
    assert SS.check_not_computed({"labels": lab_ok, "compare": cm(0, 4, 0)}) is None
    t = TX.sentence("not_computed", "value_error")
    assert "The check could not be computed: value_error." in t and "did not confirm this run" in t
    for step, code, want in ((1, "run2_placebo", "run2_placebo"), (1, "head_differs", "before_score"),
                             (3, "sealed_file_differs", "before_score"), (6, "rehearsal_failed", "rehearsal"),
                             (8, "after_lock_differs", "before_score"), (10, "score_crashed", None)):
        assert SS.stop_sentence(SS.Stop(step, code)) == want
    assert set(TX.SENTENCES) == {"run2_placebo", "before_score", "rehearsal", "gate", "label_check", "r_only",
                                 "w_or_d", "not_computed", "part_failed"}
    assert "the inputs the two routes read were not shown equal" in TX.SENTENCES["label_check"].lower()
    assert "the check did not confirm this run" in TX.SENTENCES["w_or_d"].lower()
    assert TX.LABEL_ADDITION == "the check did not confirm this run"


# ================================================================================ 2. the whole job, study P
def test_2a_whole_job_on_study_P(routeP, runP):
    """section 9, first item: fresh clone, lock, verify, score, comparison, report; the cell map all equal. The
    terminal is step lines, the receipt, the fixed sentences, the report's path, and last SCORED"""
    lines = runP["lines"]
    assert runP["rc"] == 0 and lines[-1] == "SCORED", lines[-12:] + [runP["stderr"][-2000:]]
    receipt = receipt_of(lines)
    for line in lines:
        assert LINE.fullmatch(line) or line.startswith("keep this line somewhere other than this machine: receipt ") \
            or line in TX.SENTENCES.values() or line.startswith("report: ") or line == "SCORED", line
    assert printed(lines) == ["gate"]
    steps = [int(LINE.fullmatch(x).group(1)) for x in lines if LINE.fullmatch(x)]
    assert steps == sorted(steps) and set(steps) == set(range(1, 15)), steps
    assert all(LINE.fullmatch(x).group(4) == "ok" for x in lines if LINE.fullmatch(x))
    out, prot = Path(runP["out"]), Path(runP["prot"])
    pub = (out / "sa3_result.json").read_bytes()
    assert pub == (prot / "clone" / "docs" / "sa3_result.json").read_bytes()
    assert hashlib.sha256(pub).hexdigest() == receipt
    led = ledger_of(Path(runP["ledger"]))
    assert [e["event"] for e in led] == ["started", "completed"] and led[1]["result_sha256"] == receipt
    assert led[0]["commit"] == routeP["commit"] and led[0]["rerun_reason"] is None
    assert led[0]["seal_sha256"] == hashlib.sha256(Path(routeP["seal"]).read_bytes()).hexdigest()
    rep = json.loads((out / "report.json").read_text())
    assert rep["cellmap"]["map"]["all_equal"] is True and rep["cellmap"]["map"]["cells"] > 5000
    assert rep["label_check"]["check"]["all_equal"] is True
    assert rep["sentences"] == ["gate"] and not rep["label_addition"] and rep["check_code"] is None
    assert rep["result_shape"] == "expected" and rep["result_shape_at"] is None
    assert all(p["status"] == "ok" for p in rep["parts"].values())
    md_ = (out / "report.md").read_text().splitlines()
    assert md_[0] == f"**{TX.LABEL}**"
    assert md_[2].startswith("- **SA3-B** (struct_branch): mean ") and "As coded: **" in md_[2]
    assert md_[5].startswith("- **SA3-A** (in_degree), exploratory")
    # the reference's own words match the report's coded words; the decoy plants an effect in branches
    ref = json.loads(pub)
    for n in SC.CONFIRMATORY:
        assert rep["tests"][n]["coded"] == ref["tests"][n]["reading"]
    assert rep["tests"]["struct_branch"]["coded"] == "supported, defect-specific"
    # the clone after the score: exactly the lock and the result
    st = SS.git(prot / "clone", "status", "--porcelain", "--ignored", "--untracked-files=all").stdout.splitlines()
    assert sorted(st) == ["?? docs/sa3_lock.json", "?? docs/sa3_result.json"]
    assert rep["provenance"]["after_score_status_ok"] is True
    lock = json.loads((out / "sa3_lock.json").read_text())
    assert lock["sealed_at_commit"] == routeP["commit"]
    assert lock["files"] == json.loads(Path(routeP["seal"]).read_text())["lock_expected"]
    log = json.loads((out / "run_log.json").read_text())
    assert log["complete"] and log["target"] == "decoy"


def test_2b_each_stage_loaded_the_commits_files(routeP, runP):
    """section 9: each stage's loaded modules equal `git ls-tree` of the clone (the stage records the SHA-256 of
    every module it loaded from the clone's tools/; here each is checked against the blob git holds for C)"""
    prot = Path(runP["prot"])
    tree = SS.ls_tree(prot / "clone", routeP["commit"])
    mods = json.loads((Path(runP["out"]) / "report.json").read_text())["provenance"]["modules"]
    assert {"lock", "score", "rehearse", "labels", "compare", "readings", "named", "hv_prepare", "variant"} <= set(mods)
    git_dir = prot / "clone"
    for stage, m in mods.items():
        assert m, stage
        for path, h in m.items():
            data = subprocess.run(["git", "-C", str(git_dir), "cat-file", "blob", tree[path]], capture_output=True,
                                  check=True).stdout
            assert hashlib.sha256(data).hexdigest() == h, (stage, path)
    assert "tools/sa3_score.py" in mods["score"] and "tools/sa3_stats.py" in mods["score"]
    assert "tools/scoring/score_sa3.py" in mods["score"]
    # and the reference modules are the sealed ones
    seal = json.loads(Path(routeP["seal"]).read_text())
    for m, v in seal["code"].items():
        if f"tools/{m}.py" in mods["score"]:
            assert mods["score"][f"tools/{m}.py"] == v["sha256"], m


def test_2c_markers_absent_from_every_public_output(routeP, runP):
    """planted markers in a decoy's outcome file reach no public file and not the terminal; they were bound (the
    seal hashed the planted file)"""
    f = Path(routeP["decoy"]) / "study" / "sa3_outcomes" / f"{MARK_REPO}.json"
    assert MARK_VAL in f.read_text() and MARK_SHA in f.read_text()
    text = public_text(Path(runP["out"])) + "\n".join(runP["lines"]) + runP["stderr"]
    for m in MARKERS:
        assert m not in text, m
    seal = json.loads(Path(routeP["seal"]).read_text())
    assert seal["inputs"][MARK_REPO]["outcome"] == hashlib.sha256(f.read_bytes()).hexdigest()


def test_2d_lock_and_score_layout_in_the_sandbox(runP, tmp_path):
    """the layout of steps 7 and 9 on a copy of the run's clone: inside the sandbox git reads the commit, the lock
    file can be written into docs/, and writes into tools/ and .git are refused"""
    clone = tmp_path / "prot" / "clone"
    shutil.copytree(Path(runP["prot"]) / "clone", clone, symlinks=True)
    (clone / "docs" / "sa3_lock.json").unlink()
    (clone / "docs" / "sa3_result.json").unlink()
    rundir = tmp_path / "prot" / "runs" / "probe"
    (rundir / "home").mkdir(parents=True)
    (rundir / "tmp").mkdir()
    P.write_gitconfig(rundir / "home")
    rw, code = SS.lock_layout(SimpleNamespace(pl=SimpleNamespace(clone=clone)))
    probe = ("import subprocess, json, os\n"
             f"c = {str(clone)!r}\n"
             "out = {'head': subprocess.run(['git', '-C', c, 'rev-parse', 'HEAD'], capture_output=True, text=True)"
             ".stdout.strip()}\n"
             "for name, p in (('docs', c + '/docs/probe.txt'), ('tools', c + '/tools/probe.txt'),"
             " ('git', c + '/.git/probe.txt')):\n"
             "    try:\n        open(p, 'w').write('x'); out[name] = 'written'\n"
             "    except OSError as e:\n        out[name] = 'refused'\n"
             f"open({str(rundir / 'probe.json')!r}, 'w').write(json.dumps(out))\n")
    spec = SR.Spec(rw=[rundir, *rw], code=code, inputs=[], cwd=rundir)
    p = SR.run(["/usr/bin/python3", "-I", "-B", str(clone / "tools/harness/sandbox_ro.py"), "exec", "--",
                "/usr/bin/python3", "-I", "-B", "-c", probe], spec, rundir / "home", rundir / "tmp", guard=False,
               timeout=120)
    got = json.loads((rundir / "probe.json").read_text())
    assert got == {"head": SS.git(clone, "rev-parse", "HEAD").stdout.strip(), "docs": "written", "tools": "refused",
                   "git": "refused"}, (got, p.stdout, p.stderr)


def test_2e_variants_equal_part2s_route(study_cache, routeP, runP, tmp_path):
    """the job's three scored variants (run as sandbox stages from the clone) equal part 2's own route
    (tools/compare/variants.run on the same decoy study and tables) as parsed JSON, key for key"""
    V = _load(ROOT / "tools" / "compare" / "variants.py", "tools_compare_variants")
    s = _study(study_cache, "P")
    rec = json.loads((s / "built.json").read_text())
    p = rec["paths"]
    T = _load(ROOT / "tools" / "compare" / "tables.py", "tools_compare_tables")
    marg = json.loads((Path(routeP["decoy"]) / "docs" / "sa3_outcome_marginals.json").read_text())
    T.build_label_tables(Path(routeP["decoy"]) / "study" / "sa3_outcomes",
                         [r["repo"] for r in marg if r["status"] == "ok"], tmp_path / "labels")   # part 1's way
    study = {"decoy": routeP["decoy"], "pb": Path(routeP["check"]["phase_b"]["dir"]),
             "ct": Path(routeP["check"]["compare"]["dir"]), "lt": tmp_path / "labels",
             "sealed": Path(runP["prot"]) / "clone"}
    frozen = json.loads((Path(runP["out"]) / "sa3_result.json").read_text())
    got = V.run(study, tmp_path / "v", frozen)
    runs = Path(runP["prot"]) / "runs"
    mine = {"PU_named_streams": json.loads((runs / "named/all/named.json").read_text()),
            "PU_tracker_keys_case_sensitive": json.loads((runs / "variant/all/case/variant.json").read_text()),
            "PU_late_revert_ticket_dropped": json.loads((runs / "variant/all/late/variant.json").read_text())}
    for k, v in mine.items():
        assert json.dumps(got["results"][k], sort_keys=True) == json.dumps(v, sort_keys=True), k
    assert p["decoy"]


def test_2f_whole_job_on_study_N(study_cache, route_cache):
    """section 9, first item, on study N (no planted effect): SCORED, the cell map all equal"""
    route = _route(study_cache, route_cache, "N")
    r = _main_run(route, "runN")
    assert r["rc"] == 0 and r["lines"][-1] == "SCORED", r["lines"][-12:]
    rep = json.loads((Path(r["out"]) / "report.json").read_text())
    assert rep["cellmap"]["map"]["all_equal"] and rep["label_check"]["check"]["all_equal"]
    assert rep["sentences"] == ["gate"]


# ======================================================================== 3. once: the ledger in use
def test_3a_second_run_after_a_completed_one_refuses_with_another_directory(routeP, runP, tmp_path):
    led = Path(runP["ledger"])
    before = led.read_bytes()
    att = LG.attempts_path(led).read_bytes()
    for extra in ((), ("--rerun", "a second look")):
        p = run(DC.command(routeP, tmp_path / "p2", tmp_path / "o2", led, *extra), timeout=300)
        assert p.returncode == 2 and "ledger_completed" in p.stderr, p.stderr
        assert not (tmp_path / "p2").exists() and not (tmp_path / "o2").exists()
    assert led.read_bytes() == before and LG.attempts_path(led).read_bytes() == att


def test_3b_resume_checks_the_receipt_and_never_starts_the_score(routeP, runP, tmp_path, monkeypatch):
    """--resume re-runs steps 11 to 14 from the published result. Run IN-PROCESS here with two traps: the function
    that starts the reference score raises, and so does any stage named "score"; neither may fire. The ledger
    shows one start, one completion, one resume; the result is unchanged byte for byte. A wrong receipt stops it
    before anything runs, with no ledger entry"""
    prot, out = tmp_path / "prot", tmp_path / "pub"
    shutil.copytree(runP["prot"], prot, symlinks=True)
    shutil.copytree(runP["out"], out)
    led = tmp_path / "led" / "sa3_score_ledger.jsonl"
    led.parent.mkdir()
    shutil.copyfile(runP["ledger"], led)
    shutil.copyfile(LG.attempts_path(Path(runP["ledger"])), LG.attempts_path(led))
    receipt = receipt_of(runP["lines"])
    result = (out / "sa3_result.json").read_bytes()

    def boom(*a, **k):
        raise AssertionError("the reference score was started by --resume")

    real_stage = SS.Job.run_stage

    def guarded(self, step, name, *a, **k):
        if name == "score" or step <= 10:
            raise AssertionError(f"--resume ran stage {name} of step {step}")
        return real_stage(self, step, name, *a, **k)

    monkeypatch.setattr(SS, "step9_score", boom)
    monkeypatch.setattr(SS.Job, "run_stage", guarded)
    monkeypatch.setattr(SS, "WORKTREE", Path(routeP["repo"]))      # the launcher's checkout: the route's
    lines = []
    argv = ["--decoy", routeP["decoy"], "--resume", "--commit", routeP["commit"], "--receipt", "0" * 64,
            "--protected", str(prot), "--out", str(out), "--ledger", str(led)]
    rc = SS.main(argv, echo=lines.append)
    assert rc == 1 and lines[-1] == "STOPPED receipt_differs", lines
    assert [e["event"] for e in LG.read(led)] == ["started", "completed"]
    lines = []
    argv[argv.index("0" * 64)] = receipt
    rc = SS.main(argv, echo=lines.append)
    assert rc == 0 and lines[-1] == "SCORED", lines[-10:]
    assert [e["event"] for e in LG.read(led)] == ["started", "completed", "resume"]
    assert (out / "sa3_result.json").read_bytes() == result
    assert (out / "report.md.superseded-0").exists()
    rep = json.loads((out / "report.json").read_text())
    assert rep["mode"] == "resume" and rep["cellmap"]["map"]["all_equal"] and rep["later"] is None
    assert [a["mode"] for a in rep["attempts"] if a["event"] == "attempt_started"] == ["score", "resume", "resume"]
    assert sum(1 for e in rep["ledger"] if e["event"] == "started") == 1


def test_3g_a_result_with_an_unforeseen_key_is_published_and_never_stops(routeP, tmp_path, monkeypatch):
    """build review, 2026-11-15: once the reference score returned 0 and wrote its file, step 10 never stops. The
    launcher's shape check is made to find an unforeseen key (run IN-PROCESS, the check replaced): the result is
    still published byte for byte, `completed` written, the receipt printed; the report's first lines say
    result_shape: unexpected at a schema position; run_log has the verdict; steps 11 to 14 run; the ledger holds
    one start and one completion, so no --rerun is needed"""
    def unforeseen(res, repos, sealed):
        raise SC.ResultShapeError("repos.<repo>.outcomes.HP.struct_branch.<key>")
    monkeypatch.setattr(SC, "check_result", unforeseen)
    monkeypatch.setattr(SS, "WORKTREE", Path(routeP["repo"]))      # the launcher's checkout: the route's
    base = tmp_path / "g"
    led = base / "ledger" / "sa3_score_ledger.jsonl"
    led.parent.mkdir(parents=True)
    lines = []
    rc = SS.main(["--decoy", routeP["decoy"], "--commit", routeP["commit"], "--seal", routeP["seal"],
                  "--protected", str(base / "prot"), "--out", str(base / "pub"), "--ledger", str(led)],
                 echo=lines.append)
    assert rc == 0 and lines[-1] == "SCORED", lines[-10:]
    out = base / "pub"
    data = (out / "sa3_result.json").read_bytes()
    assert data == (base / "prot/clone/docs/sa3_result.json").read_bytes()
    receipt = receipt_of(lines)
    assert hashlib.sha256(data).hexdigest() == receipt
    ev = LG.read(led)
    assert [e["event"] for e in ev] == ["started", "completed"] and ev[1]["result_sha256"] == receipt
    assert "step 10 result_shape * failed result_shape_unexpected" in lines
    assert lines.index("step 10 publish * ok") < lines.index("step 10 result_shape * failed result_shape_unexpected")
    assert any(x.startswith("result_shape: unexpected") for x in lines)
    rep = json.loads((out / "report.json").read_text())
    assert rep["result_shape"] == "unexpected" and rep["result_shape_at"] == "repos.<repo>.outcomes.HP.struct_branch.<key>"
    assert rep["tests"] == {} and rep["exploratory"] is None
    assert all(v["status"] == "ok" for v in rep["parts"].values())          # steps 11 to 13 ran
    md_ = (out / "report.md").read_text().splitlines()
    assert md_[2].startswith("result_shape: unexpected, at repos.<repo>.outcomes.HP.struct_branch.<key>.")
    log = json.loads((out / "run_log.json").read_text())
    assert {"step": 10, "name": "result_shape", "repo": "*", "status": "failed", "code": "result_shape_unexpected"} \
        == {k: v for k, v in next(s for s in log["steps"] if s["name"] == "result_shape").items() if k != "seconds"}
    p = run(DC.command(routeP, base / "p2", base / "o2", led), timeout=300)
    assert p.returncode == 2 and "ledger_completed" in p.stderr               # completed: no second start


@pytest.mark.parametrize("stage", ["labels", "compare", "named"])
def test_3c_split_each_step_after_the_score_fails_in_turn(routeP, tmp_path, stage):
    """steps 11, 12 and 13 made to fail in turn (a planted exception, decoys only): the result is published byte
    for byte, the report exists and names the failure, the ledger shows one start; then --resume completes it"""
    step = {"labels": 11, "compare": 12, "named": 13}[stage]
    r = Run(routeP, tmp_path / "a", env={SS.TEST_FAIL_ENV: stage})
    assert r.rc == 0 and r.lines[-1].startswith("SCORED; parts failed: ") and stage in r.lines[-1], r.lines[-8:]
    assert f"step {step} {stage} * failed unclassified" in r.lines
    want = {"labels": ["gate", "not_computed", "part_failed"], "compare": ["gate", "not_computed"],
            "named": ["gate", "part_failed"]}[stage]
    _only(r.lines, want)
    assert (r.out / "sa3_result.json").read_bytes() == (r.prot / "clone/docs/sa3_result.json").read_bytes()
    rep = r.report()
    assert rep["parts"][stage] == {"step": step, "status": "failed", "code": "unclassified"}
    assert rep["sentences"] == want and rep["label_addition"] == (stage != "named")
    if stage != "named":
        assert rep["check_code"] == "unclassified"
        assert "The check could not be computed: unclassified." in (r.out / "report.md").read_text()
    assert [e["event"] for e in ledger_of(r.ledger)] == ["started", "completed"]
    p = run(resume_cmd(routeP, r.prot, r.out, r.ledger, receipt_of(r.lines)), timeout=7200)
    lines = p.stdout.splitlines()
    assert p.returncode == 0 and lines[-1] == "SCORED", lines[-8:] + [p.stderr[-1500:]]
    assert not any(x.startswith("step 9 ") or x.startswith("step 7 ") for x in lines)
    rep = r.report()
    assert all(v["status"] == "ok" for v in rep["parts"].values()) and rep["cellmap"]["map"]["all_equal"]
    assert [e["event"] for e in ledger_of(r.ledger)] == ["started", "completed", "resume"]


def test_3d_killed_during_the_score_leaves_started_then_rerun_records_its_reason(routeP, tmp_path):
    """a run killed during step 9 (the terminal closed: the process group killed) leaves `started` and no
    completion; a plain new attempt is refused; --rerun REASON completes, and the reason is in the ledger and in
    the report's first lines"""
    base = tmp_path / "k"
    led = base / "ledger" / "sa3_score_ledger.jsonl"
    led.parent.mkdir(parents=True)
    cmd = DC.command(routeP, base / "prot", base / "pub", led)
    e = {k: v for k, v in os.environ.items() if k != SS.TEST_FAIL_ENV}
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                            env=e, start_new_session=True)
    t0 = time.time()
    while time.time() - t0 < 1800:
        try:
            if led.exists() and any(x["event"] == "started" for x in LG.read(led)):
                break
        except LG.LedgerError:
            pass
        if proc.poll() is not None:
            break
        time.sleep(0.2)
    time.sleep(3)                                              # inside the score
    assert proc.poll() is None, "the job ended before it could be killed during the score"
    os.killpg(proc.pid, signal.SIGKILL)
    proc.wait(timeout=60)
    time.sleep(2)
    assert [x["event"] for x in LG.read(led)] == ["started"]
    assert not (base / "pub" / "sa3_result.json").exists()
    p = run(DC.command(routeP, base / "prot2", base / "pub2", led), timeout=300)
    assert p.returncode == 2 and "ledger_has_entry" in p.stderr
    r = Run(routeP, base / "again", "--rerun", "terminal closed during the score (test)", ledger=led)
    assert r.rc == 0 and r.lines[-1] == "SCORED", r.lines[-8:]
    ev = LG.read(led)
    assert [x["event"] for x in ev] == ["started", "started", "completed"]
    assert ev[1]["rerun_reason"] == "terminal closed during the score (test)"
    md_ = (r.out / "report.md").read_text().splitlines()
    assert md_[2] == ('A second start of the reference score was made with --rerun, reason recorded in the ledger: '
                      '"terminal closed during the score (test)".')


def test_3e_a_failure_at_step_3_leaves_no_entry(routeP, tmp_path):
    """a commit C2 whose sealed document differs from run-2's seal (the decoy's own documents unchanged, so the
    seal verifies at step 1): stopped at step 3, nothing scored, no ledger entry; the attempt is listed"""
    repo = copy_repo(routeP, tmp_path / "repo")
    f = repo / "docs" / "sa3_power.md"
    f.write_text(f.read_text() + "\nA changed line.\n")
    git(repo, "commit", "-q", "-am", "a sealed document changed after the seal")
    c2 = git(repo, "rev-parse", "HEAD")
    git(repo, "tag", "-f", "-a", "sa3-score-C", "-m", "moved", c2)
    route = {**routeP, "repo": str(repo), "commit": c2}
    r = Run(route, tmp_path / "a", timeout=1800)
    assert r.rc == 1 and r.lines[-1] == "STOPPED sealed_file_differs", r.lines[-6:]
    assert TX.SENTENCES["before_score"] in r.lines
    assert not r.ledger.exists()
    att = LG.read(LG.attempts_path(r.ledger))
    assert [(a["event"], a["step"], a["code"]) for a in att] == [("attempt_started", 0, "none"),
                                                                 ("attempt_ended", 3, "sealed_file_differs")]
    assert json.loads((r.out / "report.json").read_text())["code"] == "sealed_file_differs"


def test_3f_resume_from_a_later_commit_labels_its_parts_later(routeP, runP, tmp_path):
    """code changed since the first attempt (a later commit C2): --resume runs steps 11 to 13 from a fresh clone of C2
    inside the protected directory, the sealed copies still the first clone's; every part is labelled "run later,
    on <date>"; the result and the ledger's single start are unchanged"""
    prot, out = tmp_path / "prot", tmp_path / "pub"
    shutil.copytree(runP["prot"], prot, symlinks=True)
    shutil.copytree(runP["out"], out)
    led = tmp_path / "led" / "sa3_score_ledger.jsonl"
    led.parent.mkdir()
    shutil.copyfile(runP["ledger"], led)
    repo = copy_repo(routeP, tmp_path / "repo")
    (repo / "docs" / "process").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "process" / "zz_later_note.md").write_text("a later commit\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "decoy: a later commit")
    c2 = git(repo, "rev-parse", "HEAD")
    result = (out / "sa3_result.json").read_bytes()
    p = run(resume_cmd({**routeP, "repo": str(repo)}, prot, out, led, receipt_of(runP["lines"]), commit=c2))
    lines = p.stdout.splitlines()
    assert p.returncode == 0 and lines[-1] == "SCORED", lines[-8:] + [p.stderr[-1500:]]
    rep = json.loads((out / "report.json").read_text())
    assert rep["later"] is not None and rep["provenance"]["code_commit"] == c2
    assert rep["provenance"]["commit"] == routeP["commit"]
    assert SS.git(prot / "resume-0" / "clone", "rev-parse", "HEAD").stdout.strip() == c2
    assert "run later, on " in (out / "report.md").read_text()
    assert (out / "sa3_result.json").read_bytes() == result
    assert [e["event"] for e in LG.read(led)] == ["started", "completed", "resume"]


# ================================================================================================ 4. the pin
def test_4a_the_pin(routeP, tmp_path):
    """a wrong --commit refuses; an untracked file under tools/ refuses; a tag that does not point at C refuses;
    each at step 1, before any copy, with no ledger entry"""
    r = Run({**routeP, "commit": "0" * 40}, tmp_path / "a", timeout=300)
    assert r.rc == 1 and r.lines[-1] == "STOPPED head_differs" and not r.ledger.exists(), r.lines
    repo = copy_repo(routeP, tmp_path / "repo")
    (repo / "tools" / "zz_untracked.py").write_text("x = 1\n")
    r = Run({**routeP, "repo": str(repo)}, tmp_path / "b", timeout=300)
    assert r.rc == 1 and r.lines[-1] == "STOPPED checkout_dirty", r.lines
    (repo / "tools" / "zz_untracked.py").unlink()
    (repo / "tools" / "sa3_score.py").write_bytes((repo / "tools" / "sa3_score.py").read_bytes() + b"\n")
    r = Run({**routeP, "repo": str(repo)}, tmp_path / "c", timeout=300)
    assert r.rc == 1 and r.lines[-1] == "STOPPED checkout_dirty", r.lines
    git(repo, "checkout", "-q", "--", "tools/sa3_score.py")
    git(repo, "tag", "-f", "-a", "sa3-score-C", "-m", "elsewhere", routeP["commit"] + "~1")
    r = Run({**routeP, "repo": str(repo)}, tmp_path / "d", timeout=300)
    assert r.rc == 1 and r.lines[-1] == "STOPPED tag_differs", r.lines
    for x in "abcd":
        assert not (tmp_path / x / "prot" / "runs").exists() and not (tmp_path / x / "prot" / "clone").exists()
        assert not (tmp_path / x / "ledger" / "sa3_score_ledger.jsonl").exists()
    assert TX.SENTENCES["before_score"] in r.lines


def test_4b_step8_lock_where_git_fails_and_a_wrong_lock(runP, routeP, tmp_path):
    """the reference lock run where git cannot read the repository (the clone's .git not bound: every hash is
    real, the commit empty) stops at step 8; so does a lock with empty hashes, and an extra file in the clone"""
    prot = tmp_path / "prot"
    prot.mkdir()
    clone = prot / "clone"
    shutil.copytree(Path(runP["prot"]) / "clone", clone, symlinks=True)
    for f in ("sa3_lock.json", "sa3_result.json"):
        (clone / "docs" / f).unlink()
    tgt = P.Target(Path(routeP["decoy"]) / "study", Path(routeP["decoy"]) / "pool", Path(routeP["decoy"]) / "docs",
                   P.LINGUIST_HOST, False)
    a = SimpleNamespace(commit=routeP["commit"], seal=routeP["seal"], test_fail=None)
    pl = SS.Places(tgt, prot, tmp_path / "pub", tmp_path / "led" / "l.jsonl")
    (tmp_path / "pub").mkdir()
    job = SS.Job(a, pl, "score", echo=lambda line: None)
    job.seal = json.loads(Path(routeP["seal"]).read_text())
    job.tree = SS.ls_tree(clone, routeP["commit"])
    job.vocab.codepaths = frozenset(p for p in job.tree if p.startswith("tools/") and p.endswith(".py"))
    res = job.run_stage(7, "lock", "*", {"tools": str(clone / "tools")}, job.lists(), rw=[clone / "docs"],
                        code=[clone / "tools"])                       # no .git: git fails inside
    assert res["status"] == "ok" and res["rc"] == 0
    lock = json.loads((clone / "docs" / "sa3_lock.json").read_text())
    assert lock["sealed_at_commit"] == "" and all(lock["files"].values())
    with pytest.raises(SS.Stop) as e:
        SS.step8_after_lock(job)
    assert (e.value.step, e.value.code) == (8, "lock_commit_differs")
    (clone / "docs" / "sa3_lock.json").write_text(json.dumps({"sealed_at_commit": "", "files": {
        k: "" for k in lock["files"]}}) + "\n")                      # git failing: empty hashes (defect 57)
    with pytest.raises(SS.Stop) as e:
        SS.step8_after_lock(job)
    assert (e.value.step, e.value.code) == (8, "after_lock_differs")
    good = json.loads((Path(runP["prot"]) / "clone" / "docs" / "sa3_lock.json").read_text())
    (clone / "docs" / "sa3_lock.json").write_text(json.dumps(good, indent=1) + "\n")
    (clone / "docs" / "stray.txt").write_text("x")
    with pytest.raises(SS.Stop) as e:
        SS.step8_after_lock(job)
    assert (e.value.step, e.value.code) == (8, "clone_status_after_lock")


# ============================================================================ 5. inputs against the seal
def test_5a_a_sealed_document_changed_after_run2_stops_at_step_1(routeP, tmp_path):
    def plant(d):
        pass
    fk = DC.fork(routeP, tmp_path / "f", plant)
    f = Path(fk["decoy"]) / "docs" / "sa3_power.md"
    f.write_text(f.read_text() + "\nchanged after the seal\n")
    r = Run(fk, tmp_path / "a", timeout=1800)
    assert r.rc == 1 and r.lines[-1] == "STOPPED seal_not_verified", r.lines[-6:]
    assert "  differs: documents.sa3_power.md.sha256" in r.lines
    assert not r.ledger.exists()


def test_5b_a_scan_database_changed_between_the_seal_and_the_copy_stops_at_step_4(routeP, tmp_path):
    """the database changes after step 1's verify and before the copy stage hashes it again"""
    fk = DC.fork(routeP, tmp_path / "f")
    db = Path(fk["decoy"]) / "study" / "sa3_scans" / "go_master.db"
    base = tmp_path / "a"
    led = base / "ledger" / "sa3_score_ledger.jsonl"
    led.parent.mkdir(parents=True)
    cmd = DC.command(fk, base / "prot", base / "pub", led)
    e = {k: v for k, v in os.environ.items() if k != SS.TEST_FAIL_ENV}
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=e,
                            stdin=subprocess.DEVNULL)
    log = base / "pub" / "run_log.json"
    t0 = time.time()
    while time.time() - t0 < 900:
        try:
            if any(s["name"] == "seal_verify" for s in json.loads(log.read_text())["steps"]):
                break
        except (OSError, ValueError):
            pass
        time.sleep(0.02)
    import sqlite3
    con = sqlite3.connect(str(db))
    con.execute("update file_data set struct_branch = coalesce(struct_branch, 0) + 1 "
                "where rowid = (select min(rowid) from file_data)")
    con.commit()
    con.close()
    out, err = proc.communicate(timeout=1800)
    lines = out.splitlines()
    assert proc.returncode == 1 and lines[-1] == "STOPPED input_differs", lines[-8:]
    assert "step 4 copy go failed input_differs" in lines
    assert not led.exists()


def test_5c_an_outcome_path_outside_the_universe_stops_the_rehearsal(routeP, tmp_path):
    """a path that is no universe file, in the keyword outcome of a repo the placebo does not load (so run-2
    still passes): the loader rehearsal stops the job at step 6, nothing scored, no ledger entry"""
    def plant(d):
        f = d / "study" / "sa3_outcomes" / "ctrl-early2.json"
        o = json.loads(f.read_text())
        o["outcomes"]["KW"]["files"].append("zz/not/in/the/universe.py")
        f.write_text(json.dumps(o) + "\n")
    fk = DC.fork(routeP, tmp_path / "f", plant)
    assert fk["run2_stdout"].strip().endswith("PASS"), fk["run2_stdout"][-800:]
    r = Run(fk, tmp_path / "a", timeout=1800)
    assert r.rc == 1 and r.lines[-1] == "STOPPED rehearsal_failed", r.lines[-6:]
    assert "step 6 rehearse ctrl-early2 failed assertion" in r.lines
    assert TX.SENTENCES["rehearsal"] in r.lines and TX.SENTENCES["before_score"] not in r.lines
    assert not r.ledger.exists()


# ================================================================ 6. section 6 on the blind test's copies
def _blind(n: str) -> Path:
    d = BLIND / n
    if not d.is_dir() or not BLIND_KEY.is_file():
        pytest.skip("the blind test's copies are not on this machine")
    return d


def _key(n: str) -> dict:
    return json.loads(BLIND_KEY.read_text())["copies"][n]


def printed(lines: list[str]) -> list[str]:
    """the section 6 sentences printed on the terminal, in the table's order"""
    out = []
    for k, s in TX.SENTENCES.items():
        if "{code}" in s:
            if any(x.startswith(s.split("{code}")[0]) for x in lines):
                out.append(k)
        elif s in lines:
            out.append(k)
    return out


def _only(lines: list[str], want: list[str]) -> None:
    assert printed(lines) == want, printed(lines)


def test_6a_clean_copy_prints_no_failure_sentence(routeP, runP):
    """blind copy 01 (clean) is byte for byte the decoy study this route was made from; its run printed the gate's
    sentence and no other"""
    d = _blind("01")
    assert _key("01")["kind"] == "clean"
    for f in sorted((d / "study").rglob("*")):
        if f.is_file() and f.name != f"{MARK_REPO}.json" and not f.name.endswith(("-shm", "-wal")):
            rel = f.relative_to(d)
            assert f.read_bytes() == (Path(routeP["decoy"]) / rel).read_bytes(), rel
    _only(runP["lines"], ["gate"])


def test_6b_scan_value_fault_prints_w_or_d_only(routeP, tmp_path):
    """blind copy 05 (one scan value of the risk score, made so the placebo cannot see it): run-2 passes; the
    reference reads the changed scan, the comparison its committed tables: W or D cells differ; the label gains
    the sentence; no other sentence but the gate's"""
    d = _blind("05")
    k = _key("05")
    assert k["kind"] == "risk_score_scan_value"
    src = d / k["change"]["file"]

    def plant(dd):
        shutil.copyfile(src, dd / k["change"]["file"])
    fk = DC.fork(routeP, tmp_path / "f", plant)
    assert fk["run2_stdout"].strip().endswith("PASS"), fk["run2_stdout"][-800:]
    r = Run(fk, tmp_path / "a")
    assert r.rc == 0 and r.lines[-1] == "SCORED", r.lines[-8:]
    _only(r.lines, ["gate", "w_or_d"])
    rep = r.report()
    assert rep["label_addition"] and rep["sentences"] == ["gate", "w_or_d"]
    assert (r.out / "report.md").read_text().splitlines()[0] == \
        f"**{TX.LABEL} The check did not confirm this run.**"


def test_6c_placebo_fault_stops_the_route_before_scoring(routeP, tmp_path):
    """blind copy 13 (a confirmatory count's scan value): run-2's placebo is not bytes_equal; the job stops at
    step 1 with that sentence and no other; nothing scored"""
    d = _blind("13")
    k = _key("13")
    src = d / k["change"]["file"]
    fk = DC.fork(routeP, tmp_path / "f", lambda dd: shutil.copyfile(src, dd / k["change"]["file"]))
    assert "FAIL" in fk["run2_stdout"].splitlines()[-1]
    r = Run(fk, tmp_path / "a", timeout=600)
    assert r.rc == 1 and r.lines[-1] == "STOPPED run2_placebo", r.lines[-5:]
    _only(r.lines, ["run2_placebo"])
    assert not r.ledger.exists()


def test_6d_code_fault_stops_before_scoring(routeP, tmp_path):
    """blind copy 06 (the control's checks before its draws, in the reference scorer): committed as C, run-2 says
    FAIL reference_code_changed with the placebo bytes_equal; the job stops at step 1, sentence "before_score" only"""
    d = _blind("06")
    k = _key("06")
    repo = copy_repo(routeP, tmp_path / "repo")
    shutil.copyfile(d / k["change"]["file"], repo / "tools" / "sa3_score.py")
    git(repo, "commit", "-q", "-am", "decoy: blind copy 06's scorer")
    c2 = git(repo, "rev-parse", "HEAD")
    git(repo, "tag", "-f", "-a", "sa3-score-C", "-m", "moved", c2)
    fk = DC.fork({**routeP, "repo": str(repo)}, tmp_path / "f")
    assert fk["run2_stdout"].splitlines()[-1] == "FAIL reference_code_changed", fk["run2_stdout"][-500:]
    r = Run(fk, tmp_path / "a", timeout=600)
    assert r.rc == 1 and r.lines[-1] == "STOPPED run2_not_pass", r.lines[-5:]
    _only(r.lines, ["before_score"])


def test_6e_encoder_fault_prints_the_label_check_sentence(routeP, tmp_path):
    """no blind copy reaches the label-side check here (the job builds its label tables from the outcome files the
    reference reads), so an encoder fault is made directly: the committed predictor tables drop one universe file
    of one repo, and the commit records them as checked equal. The derivation then refuses that repo's label
    tables (a commit path outside its universe): the label-side check is not equal (code value_error for the repo),
    and the comparison scorer and named streams cannot be computed (failed: value_error). By the owner's ruling of
    2026-11-15 a check that cannot be computed is "not confirmed": printed are the label-check sentence, "The
    check could not be computed: value_error" with the label clause, and "failed to run" for named streams"""
    PC = _load(SCORING / "predictor_check.py", "tools_scoring_predictor_check")
    tabs = tmp_path / "tables"
    for n in ("phase_b", "compare"):
        shutil.copytree(routeP["check"][n]["dir"], tabs / n)
    f = next((tabs / "phase_b" / "go").glob("file.*.jsonl"))
    rows = f.read_text().splitlines()
    i = next(i for i, x in enumerate(rows) if '"in_universe":1' in x)
    rows[i] = rows[i].replace('"in_universe":1', '"in_universe":0')
    f.write_text("\n".join(rows) + "\n")
    marg = json.loads((Path(routeP["decoy"]) / "docs" / "sa3_outcome_marginals.json").read_text())
    rec = PC.record(tabs / "phase_b", tabs / "compare", {"all_equal": True, "repos_checked": 12},
                    [r["repo"] for r in marg if r["status"] == "ok"])
    repo = copy_repo(routeP, tmp_path / "repo")
    (repo / "docs" / "sa3_predictor_check.json").write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    git(repo, "commit", "-q", "-am", "decoy: an encoder fault recorded as equal")
    c2 = git(repo, "rev-parse", "HEAD")
    git(repo, "tag", "-f", "-a", "sa3-score-C", "-m", "moved", c2)
    fk = DC.fork({**routeP, "repo": str(repo)}, tmp_path / "f")
    assert fk["run2_stdout"].strip().endswith("PASS"), fk["run2_stdout"][-800:]
    r = Run(fk, tmp_path / "a")
    assert r.rc == 0 and r.lines[-1].startswith("SCORED; parts failed: "), r.lines[-8:]
    _only(r.lines, ["gate", "label_check", "not_computed", "part_failed"])
    assert TX.sentence("not_computed", "value_error") in r.lines
    rep = r.report()
    assert rep["label_check"]["check"]["all_equal"] is False
    assert rep["label_check"]["check"]["repos"]["go"]["code"] == "value_error"
    assert all(v["code"] == "none" for k, v in rep["label_check"]["check"]["repos"].items() if k != "go")
    assert rep["cellmap"] == {"status": "failed", "code": "value_error", "map": None}
    assert rep["parts"]["named"]["code"] == "value_error" and rep["label_addition"] and rep["check_code"] == "value_error"
    md_ = (r.out / "report.md").read_text()
    assert md_.splitlines()[0] == f"**{TX.LABEL} The check did not confirm this run.**"
    assert "Cell map: failed: value_error." in md_ and "The check could not be computed: value_error." in md_


# ============================================================================================ 7. run time
def test_7_the_timed_loop(runP):
    """one scoring loop timed on the decoy (the reference score, step 9) beside the comparison loop (step 12) and
    the named-streams loop (step 13); the totals are printed for the estimate"""
    log = json.loads((Path(runP["out"]) / "run_log.json").read_text())
    sec = {}
    for s in log["steps"]:
        sec[s["name"]] = sec.get(s["name"], 0) + s["seconds"]
    print(f"\ntimed on decoy P: score {sec['score']} s, compare {sec['compare']} s, named {sec['named']} s, "
          f"variant {sec['variant']} s, whole job {runP['seconds']} s")
    assert sec["score"] > 0 and runP["seconds"] > sec["score"]


# ============================================================ 8. the real path, as the owner types it
def _with_terminal(argv: list[str], env: dict, answer: bytes, timeout: int = 7200) -> tuple[int, str, str]:
    import pty
    master, slave = pty.openpty()
    try:
        os.write(master, answer)
        p = subprocess.run(argv, stdin=slave, capture_output=True, text=True, env=env, timeout=timeout)
    finally:
        os.close(slave)
        os.close(master)
    return p.returncode, p.stdout, p.stderr


def test_8_real_path_in_a_fresh_process(routeP, tmp_path):
    """`score_sa3.py --real --i-am-the-owner` in a new interpreter with Enter typed into a pseudo-terminal, every
    real location a parameter naming the decoy, a protected root named by OWNER_JOB_TEST_PROTECTED_ROOT (created by
    the run-2 job, mode 700), the predictor tables under it, run-2 itself taken with --real the same way. The plan
    is printed first; the ledger is the fixed one of that root; the run scores; a typed answer other than Enter
    refuses with nothing written"""
    d = Path(routeP["decoy"])
    root = tmp_path / "proot"
    env = {**{k: v for k, v in os.environ.items() if k != SS.TEST_FAIL_ENV}, P.TEST_ROOT_ENV: str(root)}
    real = ["--real", "--i-am-the-owner", "--real-study", str(d / "study"), "--real-pool", str(d / "pool"),
            "--real-docs", str(d / "docs")]
    repo = copy_repo(routeP, tmp_path / "repo")
    rc, out, err = _with_terminal([PY, "-B", str(repo / "tools/owner/prepare.py"), *real, "--protected",
                                   str(root / "run-2"), "--out", str(tmp_path / "run2")], env, b"\n")
    assert rc == 0 and out.splitlines()[-1] == "PASS", out[-2000:] + err[-2000:]
    tabs = root / "tables"
    for n in ("phase_b", "compare"):
        shutil.copytree(routeP["check"][n]["dir"], tabs / n)
    chk = {**routeP["check"], "phase_b": {**routeP["check"]["phase_b"], "dir": str(tabs / "phase_b")},
           "compare": {**routeP["check"]["compare"], "dir": str(tabs / "compare")}}
    (repo / "docs" / "sa3_predictor_check.json").write_text(json.dumps(chk, indent=1, sort_keys=True) + "\n")
    git(repo, "commit", "-q", "-am", "the predictor-side record names the test root's tables")
    c = git(repo, "rev-parse", "HEAD")
    git(repo, "tag", "-f", "-a", "sa3-score-C", "-m", "moved", c)
    cmd = [PY, str(repo / "tools/scoring/score_sa3.py"), *real, "--commit", c, "--seal",
           str(tmp_path / "run2" / "seal.json"), "--protected", str(root / "score-1"), "--out", str(tmp_path / "pub")]
    rc, out, err = _with_terminal(cmd[:-4] + ["--protected", str(root / "score-x"), "--out", str(tmp_path / "px")],
                                  env, b"no\n", timeout=300)
    assert rc == 2 and "not confirmed" in err and not (root / "score-x").exists() and not (tmp_path / "px").exists()
    rc, out, err = _with_terminal(cmd, env, b"\n")
    lines = out.splitlines()
    assert rc == 0 and lines[-1] == "SCORED", out[-3000:] + err[-3000:]
    assert lines[0].startswith("The SA3 scoring job") and any("Press Enter" in x for x in lines[:20])
    assert "TEST protected root in force" in err
    led = root / "sa3_score_ledger.jsonl"
    assert [e["event"] for e in LG.read(led)] == ["started", "completed"]
    rep = json.loads((tmp_path / "pub" / "report.json").read_text())
    assert rep["target"] == "real" and rep["cellmap"]["map"]["all_equal"]
    assert oct((root / "score-1").stat().st_mode & 0o777) == "0o700"
    rc, out, err = _with_terminal(cmd[:-4] + ["--protected", str(root / "score-2"), "--out", str(tmp_path / "p2")],
                                  env, b"\n", timeout=300)
    assert rc == 2 and "ledger_completed" in err and not (root / "score-2").exists()
