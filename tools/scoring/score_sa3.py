#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The SA3 scoring job (docs/process/scoring_step_spec.md, Revision 2): Amendment 5's step (g), the reference
`lock`, then the reference `score`, once, with the comparison scorer, the corrected readings and the sensitivities
beside it.

    python3 tools/scoring/score_sa3.py --real --i-am-the-owner --commit C --seal RUN2/seal.json \
        --protected /srv/storage_16tb/projects/temporal-crucible-protected/score-1 --out ~/sa3-score-1
    python3 tools/scoring/score_sa3.py --resume --real --i-am-the-owner --commit C2 --receipt SHA256 \
        --protected <the first run's> --out <the first run's>
    python3 tools/scoring/score_sa3.py --decoy DIR --ledger L ... (what tests use: DIR holds study/, pool/, docs/)

The launcher runs on the host from this checkout. Every stage runs from code taken from a fresh clone at C made
inside the protected directory, in tools/harness/sandbox_ro.py's read-only sandbox (its guard reads the mount
table first). Steps 1 to 8 stop on any failure with nothing scored and no ledger entry; step 9 writes `started`
to the ledger and runs the reference `score` once; step 10 writes `completed`, publishes the result byte for byte
and prints the receipt; steps 11 to 13 end as done or `failed` with a code and never stop the report; step 14
always writes it. `--resume` runs steps 11 to 14 again from the published result: it checks the receipt and has
no path to the reference `score` (the function that runs it, `step9_score`, is reached only from `run_full`).

The terminal gets `step N name repo ok|failed code` lines, the receipt line, the fixed sentences of section 6
that apply, the report's path, and last one line: `SCORED` (with the parts that failed, if any) or
`STOPPED <code>`. No value of a stage reaches it, and nothing a stage writes is read but its result file.
Choices the spec did not make: tools/scoring/DECISIONS.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
WORKTREE = TOOLS.parent


def _load(path: Path, name: str):
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


def owner(name: str):
    return _load(TOOLS / "owner" / f"{name}.py", f"tools_owner_{name}")


def scoring(name: str):
    return _load(HERE / f"{name}.py", f"tools_scoring_{name}")


sys.modules.setdefault("tools_scoring_score_sa3", sys.modules[__name__])
P = owner("prepare")                    # the owner job: Target, refusals, the copy stage, code_of, write_gitconfig
SR = P.SR                               # tools/harness/sandbox_ro.py, as the owner job loaded it
RP = P.RP
TX = scoring("texts")
SC = scoring("schema")
LG = scoring("ledger")

TAG = "sa3-score-C"
LEDGER_NAME = "sa3_score_ledger.jsonl"
PREDICTOR_CHECK = "docs/sa3_predictor_check.json"      # committed in step 2 of section 2 (a fixed path)
DEVIATION_TABLE = "docs/sa3_deviation_table.md"        # committed in step 3 of section 2 (a fixed path)
SCORE_TIMEOUT = 86400                                  # section 3, step 9: a day
STAGE_TIMEOUT = P.STAGE_TIMEOUT
TEST_FAIL_ENV = "SCORE_SA3_TEST_FAIL"
VERIFY_NAME = __import__("re").compile(r"[A-Za-z0-9_.<>/+-]{1,200}")                  # TESTS ONLY, decoys only: plant an exception in one stage
PY = "/usr/bin/python3"
GIT_ENV = {"GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"}
GIT_C = ["-c", "gc.auto=0", "-c", "maintenance.auto=false", "-c", "core.autocrlf=false", "-c",
         "core.hooksPath=/dev/null"]


class Stop(Exception):
    """a step failed: (step, code); `field` names an invalid value's field (validator only)"""

    def __init__(self, step: int, code: str, field: str | None = None):
        super().__init__(f"step {step}: {code}")
        self.step, self.code, self.field = step, code, field


class Refused(Exception):
    pass


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return P.sha256_file(Path(p))


def blob(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def now() -> int:
    return int(time.time())


# ================================================================================================= in the sandbox
def stage_main(argv: list[str]) -> int:
    """`score_sa3.py stage NAME --rundir D --args F`: inside the sandbox only. The result holds the stage's values
    and the SHA-256 of every module loaded from this tree, or {"status": "failed", "code": ...}; the traceback goes
    to stderr, which is the stage's log in the protected directory."""
    SR.assert_inside_ro()                                      # first: the mount table, before any path is touched
    ST = scoring("stages")
    ap = argparse.ArgumentParser()
    ap.add_argument("name", choices=sorted(ST.STAGES))
    ap.add_argument("--rundir", type=Path, required=True)
    ap.add_argument("--args", type=Path, required=True)
    a = ap.parse_args(argv)
    try:
        res = {"status": "ok", "code": "none", **ST.STAGES[a.name](json.loads(a.args.read_text()), a.rundir)}
    except ST.StageFailed as e:
        traceback.print_exc()
        res = {"status": "failed", "code": e.code}
    except BaseException as e:                                 # noqa: BLE001  the message is never written
        traceback.print_exc()
        res = {"status": "failed", "code": P.code_of(e)}
    res["modules"] = loaded_modules()
    tmp = a.rundir / ".result.json.part"
    tmp.write_text(json.dumps(res, indent=1) + "\n")
    os.replace(tmp, a.rundir / "result.json")
    return 0


def loaded_modules() -> dict[str, str]:
    """every module in sys.modules whose file lies in this tree's tools/: its path from the tree's root, and the
    SHA-256 of that file now (the launcher compares each with `git ls-tree` of the commit)"""
    root = TOOLS.resolve()
    out = {}
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if not f:
            continue
        p = Path(f).resolve()
        if root in p.parents and p.suffix == ".py":
            out["tools/" + str(p.relative_to(root))] = sha256_file(p)
    return dict(sorted(out.items()))


# =================================================================================================== on the host
def git(cwd: Path, *args: str, check: bool = True, timeout: int = 3600) -> subprocess.CompletedProcess:
    p = subprocess.run(["git", "-C", str(cwd), *GIT_C, *args], capture_output=True, text=True,
                       env={**os.environ, **GIT_ENV}, timeout=timeout)
    if check and p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, args[0])
    return p


def pin_problems(checkout: Path, commit: str, need_tag: bool = True) -> str | None:
    """section 3, step 1: HEAD is the commit; nothing untracked, modified or ignored but __pycache__; the tag
    points at it. Returns a stop code or None"""
    head = git(checkout, "rev-parse", "HEAD").stdout.strip()
    if head != commit:
        return "head_differs"
    st = git(checkout, "status", "--porcelain", "--ignored", "--untracked-files=all").stdout.splitlines()
    for line in st:
        path = line[3:]
        if not (line.startswith("!! ") and ("/__pycache__/" in "/" + path or path.endswith(".pyc"))):
            return "checkout_dirty"
    if need_tag:
        t = git(checkout, "rev-parse", "-q", "--verify", f"refs/tags/{TAG}^{{commit}}", check=False)
        if t.returncode != 0 or t.stdout.strip() != commit:
            return "tag_differs"
    return None


def ls_tree(clone: Path, commit: str) -> dict[str, str]:
    out = {}
    for rec in git(clone, "ls-tree", "-r", "-z", commit).stdout.split("\0"):
        if not rec:
            continue
        meta, path = rec.split("\t", 1)
        mode, kind, obj = meta.split()
        if kind == "blob":
            out[path] = obj
    return out


class Places:
    """where one run reads and writes. Host strings only: nothing is opened, listed or statted here"""

    def __init__(self, tgt, prot: Path, out: Path, ledger: Path):
        self.tgt, self.prot, self.out, self.ledger = tgt, prot, out, ledger
        self.clone = prot / "clone"


class Job:
    def __init__(self, a, pl: Places, mode: str, echo=print):
        self.a, self.pl, self.mode, self.echo = a, pl, mode, echo
        self.tgt = pl.tgt
        self.commit = a.commit
        self.started = now()
        self.vocab = SC.Vocab(commit=a.commit)
        self.steps: list[dict] = []
        self.modules: dict[str, dict[str, str]] = {}
        self.tree: dict[str, str] = {}
        self.repos: list[str] = []
        self.seal: dict = {}
        self.seal_sha = ""
        self.runs = pl.prot / "runs"
        self.code_root = pl.clone                   # the tree the stages run from
        self.sealed_root = pl.clone                 # the comparison scorer's sealed copies
        self.later: str | None = None               # "run later, on <date>" when a resume runs other code
        self.fail_stage = a.test_fail if not self.tgt.real else None

    # ------------------------------------------------------------------------------------------- the run log
    def record(self, step: int, name: str, repo: str, status: str, code: str, seconds: int) -> None:
        self.steps.append({"step": step, "name": name, "repo": repo, "status": status, "code": code,
                           "seconds": seconds})
        self.echo(f"step {step} {name} {repo} {status}" + ("" if code == "none" else f" {code}"))
        self.save_log(False)

    def save_log(self, complete: bool) -> None:
        log = {"target": "real" if self.tgt.real else "decoy", "mode": self.mode, "started": self.started,
               "finished": now() if complete else None, "complete": complete, "steps": self.steps}
        try:
            SC.check(SC.RUN_LOG, log, "run_log", self.vocab)
        except RP.ReportError:
            return
        atomic(self.pl.out / "run_log.json", json.dumps(log, indent=1) + "\n")

    # ------------------------------------------------------------------------------------------ stage runner
    def run_stage(self, step: int, name: str, repo: str, args: dict, inputs: list, rw: list[Path] = (),
                  code: list[Path] | None = None, timeout: int = STAGE_TIMEOUT, runs: Path | None = None,
                  sub: str | None = None) -> dict:
        """one of this job's stages (stages.py), from the code root, in the read-only sandbox"""
        rundir = (runs or self.runs) / name / (repo if repo != "*" else "all") / (sub or "")
        rundir = Path(os.path.normpath(rundir))
        home, tmp = rundir / "home", rundir / "tmp"
        for d in (home, tmp):
            d.mkdir(parents=True, exist_ok=True)
        P.write_gitconfig(home)
        if self.fail_stage == name:
            args = {**args, "planted_failure": True}
        (rundir / "args.json").write_text(json.dumps(args) + "\n")
        cr = self.code_root
        argv = [PY, "-I", "-B", str(cr / "tools" / "harness" / "sandbox_ro.py"), "exec", "--",
                PY, "-I", "-B", str(cr / "tools" / "scoring" / "score_sa3.py"), "stage", name, "--rundir",
                str(rundir), "--args", str(rundir / "args.json")]
        spec = SR.Spec(rw=[rundir, *rw], code=code if code is not None else [cr], inputs=list(inputs),
                       env={"LAWS_LINGUIST_DIR": str(P.LINGUIST_DST)}, cwd=rundir)
        t0 = time.time()
        with open(rundir / "stage.log", "w") as log:      # written by the stage; never read by the launcher
            try:
                rc = SR.run(argv, spec, home, tmp, timeout=timeout, guard=False, stdout=log).returncode
            except subprocess.TimeoutExpired:
                rc = "timeout"
        rf = rundir / "result.json"
        if rf.is_file():
            try:
                res = json.loads(rf.read_text())
            except ValueError:
                raise RP.ReportError(f"{name}.result") from None
            mods = res.get("modules") if isinstance(res, dict) else None
            if isinstance(mods, dict) and not set(mods) <= set(self.vocab.codepaths):
                res = {"status": "failed", "code": "modules_differ", "modules": {}}
            res = SC.validate_stage(name, res, self.vocab)
            if res["status"] == "ok" and not self.modules_match(res["modules"]):
                res = {"status": "failed", "code": "modules_differ", "modules": res["modules"]}
            self.modules.setdefault(name, {}).update(res["modules"])
        else:
            res = {"status": "failed", "modules": {},
                   "code": "timeout" if rc == "timeout" else "sandbox_refused" if rc == 3 else "no_result"}
        res["rundir"] = rundir
        self.record(step, name, repo, res["status"], res["code"], int(time.time() - t0))
        return res

    def modules_match(self, mods: dict[str, str]) -> bool:
        """each module a stage loaded has, in the code root, the bytes `git ls-tree` gives for the commit"""
        for path, h in mods.items():
            f = self.code_root / path
            data = f.read_bytes()
            if self.tree.get(path) != blob(data) or sha256_bytes(data) != h:
                return False
        return True

    # ------------------------------------------------------------------------------------- the inputs bound
    def study(self, r: str) -> dict:
        return P.study_files(self.tgt.study, r)

    def lists(self) -> list:
        return P.lists_inputs(self.tgt.linguist)

    def loader_inputs(self, r: str) -> list:
        """what the reference loader reads for one repo, exactly as the owner job's placebo stage binds it: the
        history and scan COPIES (checked against the seal in step 4), the sidecar, the nesting file, the outcome
        file, the clone; GitHub's lists are added by the caller"""
        F = self.study(r)
        db = self.runs / "copy" / r / "db"
        return [(str(db / "history.db"), F["history"][1]), (str(db / "scan_db.db"), F["scan_db"][1]),
                F["scan_sidecar"], F["nesting"], F["outcome"], (str(self.tgt.pool / r), SR.POOL / r)]

    def tables_inputs(self) -> list:
        return [(str(self.pb), Path(self.pb)), (str(self.ct), Path(self.ct))]


def atomic(path: Path, text: str) -> None:
    tmp = path.with_name("." + path.name + ".part")
    tmp.write_text(text)
    os.replace(tmp, path)


# =========================================================================================== steps 1 to 8
def step1_pin(job: Job) -> None:
    """the pin, run-2's report, seal.py verify (the ledger was decided before the plan was printed)"""
    t0 = time.time()
    try:
        bad = pin_problems(WORKTREE, job.commit)
    except (subprocess.SubprocessError, OSError):
        bad = "git_error"
    job.record(1, "pin", "*", "failed" if bad else "ok", bad or "none", int(time.time() - t0))
    if bad:
        raise Stop(1, bad)
    seal_file = Path(os.path.abspath(job.a.seal))
    try:
        rep = json.loads((seal_file.parent / "owner_report.json").read_text())
        job.seal = json.loads(seal_file.read_text())
        RP.check(RP.SEAL, job.seal, "seal", RP.Vocab(repos=frozenset(job.seal.get("inputs", {})),
                                                     modules=frozenset(job.seal.get("code", {})),
                                                     packages=frozenset((job.seal.get("runtime") or {})
                                                                        .get("packages", {})),
                                                     sealed=frozenset(job.seal.get("lock_expected", {}))))
    except (OSError, ValueError, RP.ReportError):
        job.record(1, "run2_report", "*", "failed", "run2_not_pass", 0)
        raise Stop(1, "run2_not_pass") from None
    target = "real" if job.tgt.real else "decoy"
    if not isinstance(rep, dict) or (rep.get("placebo") or {}).get("verdict") != "bytes_equal":
        job.record(1, "run2_report", "*", "failed", "run2_placebo", 0)       # section 6, first row
        raise Stop(1, "run2_placebo")
    ok = rep.get("first_line") == "PASS" and rep.get("verdict") == "PASS" and rep.get("codes") == [] and \
        rep.get("target") == target and job.seal.get("target") == target
    if not ok:
        job.record(1, "run2_report", "*", "failed", "run2_not_pass", 0)
        raise Stop(1, "run2_not_pass")
    job.record(1, "run2_report", "*", "ok", "none", 0)
    job.seal_sha = sha256_file(seal_file)
    verify(job, 1, WORKTREE, job.pl.prot / "verify-1", after_lock=False)


def verify(job: Job, step: int, code_tree: Path, prot: Path, after_lock: bool) -> None:
    """tools/owner/seal.py verify, unchanged, from `code_tree`, into its own new protected directory; on decoys
    after the lock through a view whose docs/ is the clone's"""
    t0 = time.time()
    prot = fresh(prot)
    argv = [PY, "-I", "-B", str(code_tree / "tools" / "owner" / "seal.py"), "verify", "--seal",
            str(Path(os.path.abspath(job.a.seal))), "--protected", str(prot)]
    docs = job.pl.clone / "docs" if after_lock else Path(job.tgt.docs)
    if job.tgt.real:
        argv += ["--real", "--i-am-the-owner", "--real-study", str(job.tgt.study), "--real-pool", str(job.tgt.pool),
                 "--real-docs", str(docs), "--linguist", str(job.tgt.linguist)]
    else:
        view = fresh(job.pl.prot / f"view-{step}")
        view.mkdir()
        for n, src in (("study", job.tgt.study), ("pool", job.tgt.pool), ("docs", docs)):
            (view / n).symlink_to(src)
        argv += ["--decoy", str(view), "--linguist", str(job.tgt.linguist)]
    if after_lock:
        argv.append("--after-lock")
    env = {k: v for k, v in os.environ.items() if k != TEST_FAIL_ENV}
    p = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=4 * STAGE_TIMEOUT)
    (prot.parent / f"{prot.name}.log").write_text(p.stdout + p.stderr)          # protected directory only
    lines = p.stdout.splitlines()
    ok = p.returncode == 0 and lines[-1:] == ["VERIFIED"]
    code = "none" if ok else ("after_lock_differs" if after_lock else "seal_not_verified")
    job.record(step, "seal_verify", "*", "ok" if ok else "failed", code, int(time.time() - t0))
    if not ok:
        for line in lines:                                  # seal.py's own lines: names of entries, never values
            if line.startswith("differs: ") and VERIFY_NAME.fullmatch(line[9:]):
                job.echo("  " + line)
        raise Stop(step, code)


def fresh(p: Path) -> Path:
    """p, or p-1, p-2, ... : a name not yet taken (seal.py verify needs a new protected directory each call)"""
    q, i = p, 0
    while q.exists():
        i += 1
        q = p.with_name(f"{p.name}-{i}")
    return q


def step2_clone(job: Job) -> None:
    t0 = time.time()
    clone = job.pl.clone
    try:
        src = git(WORKTREE, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()
        git(job.pl.prot, "clone", "-q", "--no-hardlinks", "--no-checkout", "--template=", src, str(clone))
        git(clone, "checkout", "-q", "--detach", job.commit)
    except (subprocess.SubprocessError, OSError):
        job.record(2, "clone", "*", "failed", "clone_failed", int(time.time() - t0))
        raise Stop(2, "clone_failed") from None
    ok = (clone / ".git").is_dir() and not (clone / ".git" / "commondir").exists() and \
        not (clone / ".git" / "objects" / "info" / "alternates").exists() and \
        git(clone, "rev-parse", "HEAD").stdout.strip() == job.commit and \
        git(clone, "status", "--porcelain", "--ignored", "--untracked-files=all").stdout == "" and \
        all(os.stat(os.path.join(d, f)).st_nlink == 1 for d, _ds, fs in os.walk(clone / ".git" / "objects")
            for f in fs)
    job.record(2, "clone", "*", "ok" if ok else "failed", "none" if ok else "clone_not_clean", int(time.time() - t0))
    if not ok:
        raise Stop(2, "clone_not_clean")
    job.tree = ls_tree(clone, job.commit)
    job.vocab.codepaths = frozenset(p for p in job.tree if p.startswith("tools/") and p.endswith(".py"))


def step3_sealed(job: Job) -> None:
    """every sealed file in the clone has the seal's hash: the code modules, the job's own code, the six
    documents, the nine files the reference lock will hash"""
    t0 = time.time()
    c, s = job.pl.clone, job.seal
    want = []
    for m, v in s["code"].items():
        want.append((c / "tools" / f"{m}.py", "sha256", v["sha256"]))
    for f, h in s["job_code"].items():
        want.append((c / f, "sha256", h))
    for n, v in s["documents"].items():
        want.append((c / "docs" / n, "sha256", v["sha256"]))
    for f, b in s["lock_expected"].items():
        want.append((c / f, "blob", b))
    ok = True
    for f, kind, h in want:
        data = f.read_bytes() if f.is_file() else None
        got = None if data is None else (sha256_bytes(data) if kind == "sha256" else blob(data))
        ok = ok and h is not None and got == h
    job.record(3, "sealed_files", "*", "ok" if ok else "failed", "none" if ok else "sealed_file_differs",
               int(time.time() - t0))
    if not ok:
        raise Stop(3, "sealed_file_differs")


def owner_job(job: Job):
    """the owner job's launcher object, pointed at this job's places: its `copy` and `seal_inputs` stages run
    unchanged from the clone's tools/owner/prepare.py (Job.run binds the code root read-only)"""
    oj = P.Job(job.tgt, job.pl.prot, None, job.pl.clone, echo=lambda line: None)
    oj.code = job.pl.clone
    oj.vocab = RP.Vocab(repos=frozenset(job.repos))
    oj.repos = list(job.repos)
    return oj


def step4_copies(job: Job) -> None:
    t0 = time.time()
    marg = json.loads((job.pl.clone / "docs" / "sa3_outcome_marginals.json").read_text())
    for row in marg:
        if not RP.REPO_NAME.fullmatch(str(row.get("repo", ""))):
            raise Stop(4, "input_differs")
    job.repos = [r["repo"] for r in marg if r.get("status") == "ok"]
    job.marg_repos = frozenset(r["repo"] for r in marg)
    job.vocab.repos = job.marg_repos
    if set(job.repos) != set(job.seal["inputs"]):
        job.record(4, "copy", "*", "failed", "input_differs", int(time.time() - t0))
        raise Stop(4, "input_differs")
    oj = owner_job(job)
    for r in job.repos:
        t1 = time.time()
        cp = oj.run("copy", r, P.originals(job.tgt.study, r), {"repo": r})
        code = cp["code"] if cp["status"] != "ok" else \
            "input_differs" if cp["sha256"] != job.seal["inputs"][r] else "none"
        if code == "none":
            detail = json.loads((job.runs / "copy" / r / "detail.json").read_text())
            for role in P.DB_ROLES:
                d = detail.get(role)
                if d != "absent" and not (isinstance(d, dict) and d.get("quick_check") == "ok"
                                          and d.get("side_files_left") == []):
                    code = "copy_unusable"
        job.record(4, "copy", r, "ok" if code == "none" else "failed", code, int(time.time() - t1))
        if cp["status"] != "ok":
            raise Stop(4, "copy_failed")
        if code != "none":
            raise Stop(4, code)
    t1 = time.time()
    si = oj.run("seal_inputs", "*", oj.everything(), {"repos": job.repos})
    job.record(4, "seal_inputs", "*", si["status"], si["code"], int(time.time() - t1))
    if si["status"] != "ok" or si["inputs"] != job.seal["inputs"] or si["lists"] != job.seal["lists"] or \
            si["clones"] != job.seal["clones"]:
        job.record(4, "seal_inputs", "*", "failed", "input_differs", int(time.time() - t0))
        raise Stop(4, "input_differs")


def tree_files(d: Path) -> dict[str, str]:
    return {str(p.relative_to(d)): sha256_file(p) for p in sorted(Path(d).rglob("*")) if p.is_file()}


def allowed_tables_dir(job: Job, d: str) -> Path:
    p = Path(os.path.abspath(d))
    if job.tgt.real:                     # the stored tables root; in tests only, a test-named protected root
        if not any(r in p.parents for r in (P.TABLES_ROOT,) + SR.protected_roots()[1:]):
            raise Stop(5, "predictor_check_missing")
    else:
        try:
            SR.check_rw(p)
        except SR.SandboxError:
            raise Stop(5, "predictor_check_missing") from None
    return p


def step5_tables(job: Job) -> None:
    """the predictor-side tables (step 2 of section 2) against the hashes committed at C; the deviation table
    present. The committed file names the two table directories and every file's SHA-256 per ok repo"""
    t0 = time.time()
    try:
        chk = json.loads((job.pl.clone / PREDICTOR_CHECK).read_text())
        dev = (job.pl.clone / DEVIATION_TABLE).read_text()
        if set(chk) != {"verdict", "phase_b", "compare"} or "|" not in dev:
            raise ValueError
        job.pb = allowed_tables_dir(job, chk["phase_b"]["dir"])
        job.ct = allowed_tables_dir(job, chk["compare"]["dir"])
    except (OSError, ValueError, KeyError, TypeError):
        job.record(5, "tables", "*", "failed", "predictor_check_missing", int(time.time() - t0))
        raise Stop(5, "predictor_check_missing") from None
    if chk["verdict"] != "all_equal":
        job.record(5, "tables", "*", "failed", "predictor_check_not_equal", int(time.time() - t0))
        raise Stop(5, "predictor_check_not_equal")
    for key, d in (("phase_b", job.pb), ("compare", job.ct)):
        want = chk[key]["files"]
        if set(want) != set(job.repos) or any(tree_files(d / r) != want[r] for r in job.repos):
            job.record(5, "tables", "*", "failed", "table_hash_differs", int(time.time() - t0))
            raise Stop(5, "table_hash_differs")
    job.record(5, "tables", "*", "ok", "none", int(time.time() - t0))


def step6_rehearse(job: Job) -> None:
    for r in job.repos:
        res = job.run_stage(6, "rehearse", r, {"repo": r, "ref": str(job.pl.clone)},
                            job.loader_inputs(r) + job.lists())
        if res["status"] != "ok":
            raise Stop(6, "rehearsal_failed")


def lock_layout(job: Job) -> tuple[list[Path], list[Path]]:
    """section 3, step 7: the clone's docs/ the only writable directory; its .git and tools/ read-only"""
    c = job.pl.clone
    return [c / "docs"], [c / ".git", c / "tools"]


def clone_status(job: Job) -> list[str]:
    return git(job.pl.clone, "status", "--porcelain", "--ignored", "--untracked-files=all").stdout.splitlines()


def step7_lock(job: Job) -> None:
    rw, code = lock_layout(job)
    res = job.run_stage(7, "lock", "*", {"tools": str(job.pl.clone / "tools")}, job.lists(), rw=rw, code=code)
    if res["status"] != "ok":
        raise Stop(7, res["code"] if res["code"] == "modules_differ" else "lock_failed")
    if res["rc"] != 0:
        raise Stop(7, "lock_refused")


def step8_after_lock(job: Job) -> None:
    verify(job, 8, job.pl.clone, job.pl.prot / "verify-8", after_lock=True)
    t0 = time.time()
    try:
        lock = json.loads((job.pl.clone / "docs" / "sa3_lock.json").read_text())
        SC.check_lock(lock, frozenset(job.seal["lock_expected"]))
    except (OSError, ValueError, SC.ResultShapeError):
        job.record(8, "after_lock", "*", "failed", "lock_commit_differs", int(time.time() - t0))
        raise Stop(8, "lock_commit_differs") from None
    if lock["sealed_at_commit"] != job.commit:
        job.record(8, "after_lock", "*", "failed", "lock_commit_differs", int(time.time() - t0))
        raise Stop(8, "lock_commit_differs")
    if clone_status(job) != ["?? docs/sa3_lock.json"]:
        job.record(8, "after_lock", "*", "failed", "clone_status_after_lock", int(time.time() - t0))
        raise Stop(8, "clone_status_after_lock")
    job.lock = lock
    job.record(8, "after_lock", "*", "ok", "none", int(time.time() - t0))


# ================================================================================================ the score
def step9_score(job: Job, rerun: str | None) -> dict:
    """the ledger entry `started` (written and flushed), then the reference `score`, unchanged, once"""
    LG.append(job.pl.ledger, LG.entry("started", job.commit, job.seal_sha, rerun=rerun))
    rw, code = lock_layout(job)
    ins = [x for r in job.repos for x in job.loader_inputs(r)] + job.lists()
    return job.run_stage(9, "score", "*", {"tools": str(job.pl.clone / "tools")}, ins, rw=rw, code=code,
                         timeout=SCORE_TIMEOUT)


def step10_publish(job: Job, res: dict) -> None:
    """When the reference score returned 0 and wrote its file: the result is published byte for byte, `completed`
    is written with its SHA-256 and the receipt printed, ALWAYS; only then is its shape checked, and an unexpected
    shape is a verdict for the report (`result_shape_unexpected`, with a schema position), never a stop. `stopped`
    is written only when the score produced no result (time-out, crash, exit 2, no file): a start with no
    completion, so a second start needs --rerun"""
    t0 = time.time()
    rf = job.pl.clone / "docs" / "sa3_result.json"
    code = "none"
    if res["status"] != "ok":
        code = {"timeout": "score_timeout", "result_exists": "result_exists"}.get(res["code"], "score_crashed")
    elif res["rc"] == 2:
        code = "locked"
    elif res["rc"] != 0:
        code = "score_crashed"
    elif not rf.is_file():
        code = "no_result"
    if code == "none":
        data = rf.read_bytes()
    if code != "none":
        LG.append(job.pl.ledger, LG.entry("stopped", job.commit, job.seal_sha, code=code))
        job.record(10, "publish", "*", "failed", code, int(time.time() - t0))
        raise Stop(10, code)
    out = job.pl.out / "sa3_result.json"
    tmp = out.with_name(".sa3_result.json.part")
    tmp.write_bytes(data)
    os.replace(tmp, out)
    lock_bytes = (job.pl.clone / "docs" / "sa3_lock.json").read_bytes()
    (job.pl.out / "sa3_lock.json").write_bytes(lock_bytes)
    job.result_sha = sha256_bytes(data)
    published = out.read_bytes() == rf.read_bytes()
    LG.append(job.pl.ledger, LG.entry("completed", job.commit, job.seal_sha, result_sha256=job.result_sha))
    job.echo(f"keep this line somewhere other than this machine: receipt sa3_result.json sha256 {job.result_sha} "
             f"commit {job.commit} seal sha256 {job.seal_sha}")
    job.record(10, "publish", "*", "ok" if published else "failed", "none" if published else "no_result",
               int(time.time() - t0))
    try:
        st = clone_status(job)
        job.after_score_status = sorted(st) == ["?? docs/sa3_lock.json", "?? docs/sa3_result.json"]
    except (subprocess.SubprocessError, OSError):
        job.after_score_status = False
    shape_check(job, data)


def shape_check(job: Job, data: bytes) -> None:
    """after publication: the result by shape. A failure is recorded (step 10, result_shape) with the position in
    the result's schema where it failed (fixed words and placeholders only, validated); it never stops the job"""
    t0 = time.time()
    job.result_shape, job.result_shape_at = "expected", None
    try:
        SC.check_result(json.loads(data), job.marg_repos, frozenset(job.seal["lock_expected"]))
    except SC.ResultShapeError as e:
        job.result_shape, job.result_shape_at = "unexpected", str(e)
    except Exception:                                            # noqa: BLE001  not JSON, or not the expected types
        job.result_shape, job.result_shape_at = "unexpected", "result"
    if job.result_shape_at is not None:
        try:
            SC.leaf("shapepos", job.result_shape_at, "result_shape", job.vocab)
        except RP.ReportError:
            job.result_shape_at = "result"
    ok = job.result_shape == "expected"
    job.record(10, "result_shape", "*", "ok" if ok else "failed", "none" if ok else "result_shape_unexpected",
               int(time.time() - t0))


# ============================================================================================ after the score
def after_score(job: Job, runs: Path) -> dict:
    """steps 11 to 13: each part ends as done or failed with a code; nothing here can stop the report. Runs the
    stages from job.code_root (the clone at C, or a resume's clone), reading the sealed copies from job.sealed_root
    (always the clone at C, with its lock and result)"""
    parts: dict[str, dict] = {}
    sealed = str(job.sealed_root)
    tabs = job.tables_inputs()
    outcomes = [job.study(r)["outcome"] for r in job.repos]
    base = {"repos": job.repos, "sealed": sealed, "pb": str(job.pb), "ct": str(job.ct)}

    if job.sealed_root != job.code_root:                 # a resume from other code: bind the sealed copies too
        extra = [(sealed, Path(sealed))]
    else:
        extra = []

    def part(step, name, repo, args, inputs, **kw):
        try:
            res = job.run_stage(step, name, repo, args, list(inputs) + extra, runs=runs, **kw)
        except RP.ReportError:
            res = {"status": "failed", "code": "invalid_value", "modules": {}}
            job.record(step, name, repo, "failed", "invalid_value", 0)
        except Exception:                                    # noqa: BLE001  the launcher's own fault, this part only
            with open(job.pl.prot / "launcher.log", "a") as fh:
                traceback.print_exc(file=fh)
            res = {"status": "failed", "code": "unclassified", "modules": {}}
            job.record(step, name, repo, "failed", "unclassified", 0)
        return res

    def skipped(step, name, repo="*"):
        job.record(step, name, repo, "failed", "dependency_failed", 0)
        return {"status": "failed", "code": "dependency_failed"}

    # ---- step 11: label tables and the label side of the input check
    lab = part(11, "labels", "*", {**base, "rehearse": str(job.runs / "rehearse")},
               outcomes + tabs + [(str(job.runs / "rehearse"), job.runs / "rehearse")])
    parts["labels"] = lab
    lt = lab["rundir"] / "labels" if lab["status"] == "ok" else None
    lt_in = [(str(lt), lt)] if lt else []
    # ---- step 12: the comparison scorer and the cell map
    loop = {"timeout": SCORE_TIMEOUT}                     # a full scoring loop: the score's time-out
    parts["compare"] = part(12, "compare", "*", {**base, "lt": str(lt)}, tabs + lt_in, **loop) if lt else \
        skipped(12, "compare")
    # ---- step 13: corrected readings; named streams; the two harvest variants
    parts["readings"] = part(13, "readings", "*", base, [])
    parts["named"] = part(13, "named", "*", {**base, "lt": str(lt)}, tabs + lt_in, **loop) if lt else \
        skipped(13, "named")
    prep = {}
    for r in job.repos:
        prep[r] = part(13, "hv_prepare", r, {"repo": r}, P.originals(job.tgt.study, r) +
                       [(str(job.tgt.pool / r), SR.POOL / r)] + job.lists())
    for w in ("case", "late"):
        name = {"case": "PU_tracker_keys_case_sensitive", "late": "PU_late_revert_ticket_dropped"}[w]
        if parts["named"]["status"] != "ok" or any(p["status"] != "ok" for p in prep.values()):
            parts[name] = skipped(13, "variant", "*")
            continue
        repos, ok = {}, True
        for r in job.repos:
            n = prep[r]["deleted"][w]
            rec = {"deleted": n, "plain": None, "rebuilt": None}
            if n:
                for which in ("plain", w):
                    built = job_build(job, part, runs, prep[r]["rundir"], r, which)
                    if built is None:
                        ok = False
                        break
                    rec["plain" if which == "plain" else "rebuilt"] = str(built)
            repos[r] = rec
            if not ok:
                break
        if not ok:
            parts[name] = skipped(13, "variant", "*")
            continue
        ins = tabs + lt_in + outcomes + [(str(parts["named"]["rundir"]), parts["named"]["rundir"])]
        ins += [(v[k], Path(v[k])) for v in repos.values() for k in ("plain", "rebuilt") if v[k]]
        parts[name] = part(13, "variant", "*", {**base, "lt": str(lt), "which": w, "repos": repos,
                                                "named": str(parts["named"]["rundir"] / "named.json")}, ins, sub=w,
                            **loop)
    parts["hv_prepare"] = {"status": "ok" if all(p["status"] == "ok" for p in prep.values()) else "failed",
                           "code": next((p["code"] for p in prep.values() if p["status"] != "ok"), "none")}
    return parts


def job_build(job: Job, part, runs: Path, prep_dir: Path, r: str, which: str) -> Path | None:
    """the reference outcome builder on one of the harvest copies of hv_prepare (built once per repo and copy)"""
    HARVEST = {"plain": "harvest.db", "case": "harvest_aprime.db", "late": "harvest_late.db"}
    done = runs / "hv_build" / r / which / "outcome.json"
    if done.is_file() and (runs / "hv_build" / r / which / "result.json").is_file():
        res = json.loads((runs / "hv_build" / r / which / "result.json").read_text())
        return done if res.get("status") == "ok" else None
    F = job.study(r)
    db = prep_dir / "db"
    ins = [(str(db / "history.db"), F["history"][1]), (str(db / "scan_db.db"), F["scan_db"][1]), F["scan_sidecar"],
           (str(db / HARVEST[which]), SR.STUDY / "meta_sa3" / f"{r}.db"), (str(job.tgt.pool / r), SR.POOL / r)]
    res = part(13, "hv_build", r, {"repo": r, "ref_tools": str(job.code_root / "tools")}, ins + job.lists(),
               sub=which)
    return done if res["status"] == "ok" and done.is_file() else None


# =============================================================================================== the report
def report_values(job: Job, parts: dict) -> dict:
    """the report's values, every one validated before anything is written"""
    rd = parts.get("readings", {})
    rd_ok = rd.get("status") == "ok"
    try:
        if getattr(job, "result_shape", "expected") != "expected":
            raise ValueError("not read: the result's shape is unexpected")
        tests, expl, gate = result_lines(json.loads((job.pl.out / "sa3_result.json").read_text()), rd, rd_ok)
    except Exception:                                            # noqa: BLE001  an unexpected shape: nothing read
        tests, expl, gate = {}, None, None
    lab, cm = parts.get("labels", {}), parts.get("compare", {})
    sentences = sentences_after(parts)
    return report_rest(job, parts, rd, rd_ok, tests, expl, gate, lab, cm, sentences)


def result_lines(res: dict, rd: dict, rd_ok: bool) -> tuple[dict, dict, bool]:
    """the first lines' numbers and words, from the published result"""
    tests = {}
    for n in SC.CONFIRMATORY:
        t = res["tests"][n]
        b = t["bauc"]
        tests[n] = {"holm_level": float(t["holm_level"]), "n": int(b.get("n", 0)), "mean": SC.finite_or_none(b.get("mean")),
                    "ci": [SC.finite_or_none(x) for x in b["ci"]] if "ci" in b and all(
                        SC.finite_or_none(x) is not None for x in b["ci"]) else None,
                    "coded": t["reading"], "corrected": rd["beside"][n]["corrected"] if rd_ok else None,
                    "status": rd["beside"][n]["status"] if rd_ok else None}
    a = res["tests"]["in_degree"]["bauc"]
    expl = {"n": int(a.get("n", 0)), "mean": SC.finite_or_none(a.get("mean")),
            "ci": [SC.finite_or_none(x) for x in a["ci"]] if "ci" in a and all(
                SC.finite_or_none(x) is not None for x in a["ci"]) else None,
            "reading": res["tests"]["in_degree"]["reading"]}
    return tests, expl, bool(res["valid"])


def report_rest(job, parts, rd, rd_ok, tests, expl, gate, lab, cm, sentences) -> dict:
    variants = []
    for name in SC.VARIANT_NAMES:
        p = parts.get("named" if name == "PU_named_streams" else name, {"status": "failed", "code": "not_run"})
        variants.append({"name": name, "status": p["status"], "code": p.get("code", "none"),
                         "block": p.get("block") if p["status"] == "ok" else None,
                         "inputs": p.get("inputs") if p["status"] == "ok" and name != "PU_named_streams" else None})
    part_rows = {}
    for key, step, label in (("labels", 11, "labels"), ("compare", 12, "compare"), ("readings", 13, "readings"),
                             ("named", 13, "named"), ("hv_prepare", 13, "hv_prepare"),
                             ("PU_tracker_keys_case_sensitive", 13, "variant"),
                             ("PU_late_revert_ticket_dropped", 13, "variant")):
        p = parts.get(key, {"status": "failed", "code": "not_run"})
        part_rows[key] = {"step": step, "status": p["status"], "code": p.get("code", "none")}
    entries = LG.read(job.pl.ledger)
    att = LG.read(LG.attempts_path(job.pl.ledger))
    return {
        "target": "real" if job.tgt.real else "decoy", "mode": job.mode, "made": now(),
        "label_addition": "w_or_d" in sentences or "not_computed" in sentences,
        "check_code": check_not_computed(parts),
        "result_shape": getattr(job, "result_shape", "expected"),
        "result_shape_at": getattr(job, "result_shape_at", None),
        "rerun_reasons": [e["rerun_reason"] for e in entries if e["event"] == "started" and e["rerun_reason"]],
        "tests": tests, "exploratory": expl, "gate_valid": gate,
        "label_check": {"status": lab.get("status", "failed"), "code": lab.get("code", "not_run"),
                        "check": lab.get("label_check") if lab.get("status") == "ok" else None},
        "cellmap": {"status": cm.get("status", "failed"), "code": cm.get("code", "not_run"),
                    "map": cm.get("cellmap") if cm.get("status") == "ok" else None},
        "allreverts": rd.get("allreverts") if rd_ok else None,
        "applies": rd.get("applies") if rd_ok else None,
        "sentences": sentences, "variants": variants, "parts": part_rows,
        "later": job.later,
        "ledger": entries, "attempts": att,
        "provenance": {"commit": job.a.commit_of_result, "code_commit": job.commit, "tag": TAG,
                       "tools_tree": job.tools_tree, "seal_sha256": job.seal_sha, "result_sha256": job.result_sha,
                       "lock": job.lock, "after_score_status_ok": bool(getattr(job, "after_score_status", True)),
                       "deviation_table_sha256": sha256_file(job.sealed_root / DEVIATION_TABLE),
                       "modules": job.modules},
    }


REPORT = {
    "target": "word:target", "mode": "word:mode", "made": "time", "label_addition": "yesno",
    "check_code": "word:code?", "result_shape": "word:result_shape", "result_shape_at": "shapepos?",
    "rerun_reasons": ("list", "reason"),
    "tests": ("map", "word:confirmatory", {"holm_level": "real", "n": "count", "mean": "real?",
                                           "ci": ("opt", ("pair", "real")), "coded": "word:test_word",
                                           "corrected": "word:test_word?", "status": "word:same?"}),
    "exploratory": ("opt", {"n": "count", "mean": "real?", "ci": ("opt", ("pair", "real")),
                            "reading": "word:exploratory_word"}),
    "gate_valid": "yesno?",
    "label_check": {"status": "word:status", "code": "word:code", "check": ("opt", SC.LABEL_CHECK)},
    "cellmap": {"status": "word:status", "code": "word:code", "map": ("opt", SC.CELLMAP)},
    "allreverts": ("opt", SC.ALLREV), "applies": ("opt", {"change1": "yesno", "change2": "yesno"}),
    "sentences": ("list", "word:sentence"),
    "variants": ("list", {"name": "word:variant_name", "status": "word:status", "code": "word:code",
                          "block": ("opt", SC.BLOCK), "inputs": ("opt", ("map", "repo", SC.VINPUT))}),
    "parts": ("map", "word:part", {"step": "count", "status": "word:status", "code": "word:code"}),
    "later": "time?",
    "ledger": ("list", SC.LEDGER_ENTRY), "attempts": ("list", SC.ATTEMPT),
    "provenance": {"commit": "anycommit", "code_commit": "anycommit", "tag": "word:tag", "tools_tree": "anycommit",
                   "seal_sha256": "hex64", "result_sha256": "hex64",
                   "lock": {"sealed_at_commit": "anycommit", "files": ("map", "sealed", "hex40")},
                   "after_score_status_ok": "yesno", "deviation_table_sha256": "hex64",
                   "modules": ("map", "word:step_name", SC.MODULES)},
}


STOPPED = {"target": "word:target", "mode": "word:mode", "made": "time", "step": "count", "code": "word:code",
           "attempts": ("list", SC.ATTEMPT), "ledger": ("list", SC.LEDGER_ENTRY)}


def check_not_computed(parts: dict) -> str | None:
    """owner ruling of 2026-11-15: the code that kept the check from being computed (the label tables, the
    label-side input check or the comparison scorer ended failed), or None when the cell map is complete"""
    lab, cm = parts.get("labels", {"status": "failed", "code": "not_run"}), \
        parts.get("compare", {"status": "failed", "code": "not_run"})
    if lab.get("status") != "ok":
        return lab.get("code", "not_run")
    bad = [v["code"] for v in lab["label_check"]["repos"].values() if v["code"] != "none"]
    if bad:
        return bad[0]
    if cm.get("status") != "ok":
        return cm.get("code", "not_run")
    return None


def sentences_after(parts: dict) -> list[str]:
    """section 6's sentences that apply after the score, in the table's order; the gate's always"""
    out = ["gate"]
    lab, cm = parts.get("labels", {}), parts.get("compare", {})
    if lab.get("status") == "ok" and not lab["label_check"]["all_equal"]:
        out.append("label_check")
    if cm.get("status") == "ok" and not cm["cellmap"]["all_equal"]:
        by = cm["cellmap"]["not_equal_by_class"]
        out.append("w_or_d" if by["W"] or by["D"] else "r_only")
    if check_not_computed(parts) is not None:
        out.append("not_computed")
    if any(parts.get(k, {}).get("status") != "ok" for k in ("readings", "named", "hv_prepare",
                                                             "PU_tracker_keys_case_sensitive",
                                                             "PU_late_revert_ticket_dropped")):
        out.append("part_failed")
    return out


def write_report(job: Job, parts: dict) -> Path:
    MD = scoring("report_md")
    vals = report_values(job, parts)
    voc = SC.Vocab(repos=job.marg_repos, codepaths=job.vocab.codepaths, commit=job.commit,
                   rp=RP.Vocab(repos=job.marg_repos, sealed=frozenset(job.seal["lock_expected"])))
    SC.check(REPORT, vals, "report", voc)
    md = MD.render(vals, (job.sealed_root / DEVIATION_TABLE).read_text(), variant_table(job))
    out = job.pl.out
    for f in ("report.md", "report.json", "ledger.jsonl"):
        if (out / f).exists() and job.mode == "resume":
            i = 0
            while (out / f"{f}.superseded-{i}").exists():
                i += 1
            os.replace(out / f, out / f"{f}.superseded-{i}")
    atomic(out / "report.json", json.dumps(vals, indent=1) + "\n")
    atomic(out / "report.md", md)
    atomic(out / "ledger.jsonl", "".join(json.dumps(e, sort_keys=True) + "\n" for e in vals["ledger"]))
    return out / "report.md"


def variant_table(job: Job) -> list:
    """variants.py's TABLE (names, how each is reported, the fixed text of the ones not scored), read from the
    clone's source by ast: code constants, never executed here"""
    import ast
    src = (job.sealed_root / "tools" / "compare" / "variants.py").read_text()
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "TABLE" for t in node.targets):
            return list(ast.literal_eval(node.value))
    return []


def write_stopped(job: Job, stop: Stop) -> None:
    """before the score: a short public record (the job stopped, nothing scored), validated"""
    vals = {"target": "real" if job.tgt.real else "decoy", "mode": job.mode, "made": now(), "step": stop.step,
            "code": stop.code, "attempts": LG.read(LG.attempts_path(job.pl.ledger)), "ledger": LG.read(job.pl.ledger)}
    voc = SC.Vocab(repos=getattr(job, "marg_repos", frozenset()), commit=job.commit)
    SC.check(STOPPED, vals, "stopped", voc)
    MD = scoring("report_md")
    atomic(job.pl.out / "report.json", json.dumps(vals, indent=1) + "\n")
    atomic(job.pl.out / "report.md", MD.render_stopped(vals))
    atomic(job.pl.out / "ledger.jsonl", "".join(json.dumps(e, sort_keys=True) + "\n" for e in vals["ledger"]))


# =========================================================================================== the two routes
def stop_sentence(stop: Stop) -> str | None:
    if stop.step == 1 and stop.code == "run2_placebo":
        return "run2_placebo"
    if stop.step == 6:
        return "rehearsal"
    if stop.step <= 8:
        return "before_score"
    return None


def run_full(job: Job, decision: str) -> int:
    """steps 1 to 14 of section 3"""
    rerun = job.a.rerun if decision == "rerun" else None
    try:
        step1_pin(job)
        step2_clone(job)
        step3_sealed(job)
        step4_copies(job)
        step5_tables(job)
        step6_rehearse(job)
        step7_lock(job)
        step8_after_lock(job)
        job.tools_tree = git(job.pl.clone, "rev-parse", f"{job.commit}:tools").stdout.strip()
        res = step9_score(job, rerun)
        step10_publish(job, res)
    except Stop as e:
        return stopped(job, e)
    job.a.commit_of_result = job.commit
    parts = safe_after(job, job.runs)
    return finish(job, parts)


def stopped(job: Job, e: Stop) -> int:
    LG.append(LG.attempts_path(job.pl.ledger), LG.attempt("attempt_ended", job.mode, job.commit, e.step, e.code))
    if e.field:
        job.echo(f"invalid report value: {e.field}")
    s = stop_sentence(e)
    job.echo(f"stopped at step {e.step} ({TX.STEPS.get(e.step, '')}): {e.code}: {TX.STOP_CODES.get(e.code, '')}")
    if s:
        job.echo(TX.SENTENCES[s])
    if e.step >= 9:
        job.echo("A start is recorded in the ledger and no result was published: a second start needs "
                 "--rerun REASON.")
    try:
        write_stopped(job, e)
        job.echo(f"report: {job.pl.out / 'report.md'}")
    except Exception:                                            # noqa: BLE001
        with open(job.pl.prot / "launcher.log", "a") as fh:
            traceback.print_exc(file=fh)
    job.save_log(True)
    job.echo(f"STOPPED {e.code}")
    return 1


def safe_after(job: Job, runs: Path) -> dict:
    try:
        return after_score(job, runs)
    except Exception:                                            # noqa: BLE001  the launcher's own fault
        with open(job.pl.prot / "launcher.log", "a") as fh:
            traceback.print_exc(file=fh)
        return {}


def finish(job: Job, parts: dict) -> int:
    """step 14: the report, always"""
    t0 = time.time()
    LG.append(LG.attempts_path(job.pl.ledger), LG.attempt("attempt_ended", job.mode, job.commit, 14, "none"))
    try:
        path = write_report(job, parts)
        job.record(14, "report", "*", "ok", "none", int(time.time() - t0))
    except RP.ReportError as e:
        job.echo(str(e))
        job.record(14, "report", "*", "failed", "invalid_report_value", int(time.time() - t0))
        path = None
    except Exception:                                            # noqa: BLE001
        with open(job.pl.prot / "launcher.log", "a") as fh:
            traceback.print_exc(file=fh)
        job.record(14, "report", "*", "failed", "launcher_error", int(time.time() - t0))
        path = None
    failed = [k for k, v in parts.items() if v.get("status") != "ok"] if parts else ["after_score"]
    if getattr(job, "result_shape", "expected") != "expected":
        job.echo(f"result_shape: unexpected ({TX.STOP_CODES['result_shape_unexpected']})")
    code = check_not_computed(parts) if parts else "not_run"
    for s in sentences_after(parts) if parts else ["not_computed", "part_failed"]:
        job.echo(TX.sentence(s, code))
    if path is None:
        minimal_report(job)
    job.echo(f"report: {job.pl.out / 'report.md'}")
    job.save_log(True)
    job.echo("SCORED" + (f"; parts failed: {' '.join(sorted(failed))}" if failed else ""))
    return 0


def minimal_report(job: Job) -> None:
    """the report could not be built: the result is published; say so with fixed words only"""
    try:
        atomic(job.pl.out / "report.md", f"{TX.LABEL}\n\nThe result is published (sa3_result.json, byte for byte). "
               "The report could not be built from validated values; run --resume.\n")
    except OSError:
        pass


def resume(job: Job) -> int:
    """steps 11 to 14 again, from the published result. It checks the receipt and never starts the reference
    score: nothing here, nor in what it calls, names the score stage"""
    entries = LG.read(job.pl.ledger)
    done = LG.state(entries)["completed"]
    try:
        out_res = job.pl.out / "sa3_result.json"
        clone_res = job.pl.clone / "docs" / "sa3_result.json"
        got = {sha256_file(out_res), sha256_file(clone_res), done["result_sha256"]}
        if got != {job.a.receipt}:
            raise Stop(1, "receipt_differs")
        bad = pin_problems(WORKTREE, job.commit, need_tag=False)
        if bad:
            raise Stop(1, bad)
    except (OSError, subprocess.SubprocessError):
        return stopped(job, Stop(1, "receipt_differs"))
    except Stop as e:
        return stopped(job, e)
    LG.append(job.pl.ledger, LG.entry("resume", job.commit, done["seal_sha256"]))
    job.a.commit_of_result = done["commit"]
    job.seal_sha = done["seal_sha256"]
    job.result_sha = done["result_sha256"]
    job.lock = json.loads((job.pl.out / "sa3_lock.json").read_text())
    job.seal = {"lock_expected": dict.fromkeys(job.lock["files"])}
    marg0 = json.loads((job.pl.clone / "docs" / "sa3_outcome_marginals.json").read_text())
    job.marg_repos = frozenset(r["repo"] for r in marg0)
    job.vocab.repos = job.marg_repos
    shape_check(job, (job.pl.out / "sa3_result.json").read_bytes())
    n = 0
    while (job.pl.prot / f"resume-{n}").exists():
        n += 1
    base = job.pl.prot / f"resume-{n}"
    base.mkdir()
    job.sealed_root = job.pl.clone
    if job.commit != done["commit"]:                       # other code: a fresh clone of it; parts labelled later
        job.pl.clone = base / "clone"
        try:
            step2_clone(job)
        except Stop as e:
            return stopped(job, e)
        job.code_root = job.pl.clone
        job.later = now()
        job.pl.clone = job.sealed_root
    else:
        job.code_root = job.pl.clone
    job.tree = ls_tree(job.code_root, job.commit)
    job.vocab.codepaths = frozenset(p for p in job.tree if p.startswith("tools/") and p.endswith(".py"))
    job.tools_tree = git(job.code_root, "rev-parse", f"{job.commit}:tools").stdout.strip()
    marg = json.loads((job.sealed_root / "docs" / "sa3_outcome_marginals.json").read_text())
    job.repos = [r["repo"] for r in marg if r.get("status") == "ok"]
    job.marg_repos = frozenset(r["repo"] for r in marg)
    job.vocab.repos = job.marg_repos
    chk = json.loads((job.sealed_root / PREDICTOR_CHECK).read_text())
    job.pb, job.ct = Path(chk["phase_b"]["dir"]), Path(chk["compare"]["dir"])
    parts = safe_after(job, base / "runs")
    return finish(job, parts)


# ============================================================================================= the command
def default_reader(prompt: str) -> str:
    if not sys.stdin.isatty():
        raise EOFError("standing input is not a terminal")
    return input(prompt)


def places(a) -> Places:
    """string tests only: nothing is opened, listed or statted"""
    P.test_root_from_env()
    if os.environ.get(TEST_FAIL_ENV) and a.real:
        raise Refused(f"{TEST_FAIL_ENV} is for decoy tests only; refused")
    a.test_fail = os.environ.get(TEST_FAIL_ENV) or None
    a.code_root, a.reference_git = None, None
    try:
        tgt = P.resolve_target(a)
    except P.Refused as e:
        raise Refused(str(e)) from None
    if not a.commit or not RP.HEX40.fullmatch(a.commit):
        raise Refused("--commit must be the commit's full 40-character hash; refused")
    if not a.protected or not a.out:
        raise Refused("--protected and --out are both required; refused")
    if not a.resume and not a.seal:
        raise Refused("--seal (run-2's seal.json) is required; refused")
    if a.resume and not (a.receipt and RP.HEX64.fullmatch(a.receipt)):
        raise Refused("--resume needs --receipt with the 64-character SHA-256 of the receipt line; refused")
    if a.rerun is not None and (a.resume or not SC.REASON.fullmatch(a.rerun)):
        raise Refused("--rerun REASON: letters, digits, spaces and . , ; : ( ) - / only, 1 to 200 characters, and "
                      "not with --resume; refused")
    try:
        prot, out = P.check_places(Path(a.protected), Path(a.out), tgt.real)
    except P.Refused as e:
        raise Refused(str(e)) from None
    if tgt.real:
        if a.ledger:
            raise Refused("--ledger is for decoys only: a real run's ledger is the fixed one; refused")
        root = next(r for r in SR.protected_roots() if r in prot.parents)
        ledger = root / LEDGER_NAME
    else:
        if not a.ledger:
            raise Refused("--ledger is required on a decoy; refused")
        ledger = Path(os.path.abspath(a.ledger))
        try:
            SR.check_rw(ledger.parent)
        except SR.SandboxError as e:
            raise Refused(f"ledger: {e}") from None
    for d in (prot, out):
        if ledger.parent == d or d in ledger.parents:
            raise Refused("the ledger must lie outside every run directory; refused")
    return Places(tgt, prot, out, ledger)


def main(argv: list[str] | None = None, reader=default_reader, echo=print) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["stage"]:
        return stage_main(argv[1:])
    if argv[:1] == ["predictor-check"]:
        return scoring("predictor_check").main(argv[1:])
    ap = argparse.ArgumentParser(description="the SA3 scoring job: the reference lock, then score, once")
    ap.add_argument("--decoy")
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--i-am-the-owner", action="store_true")
    ap.add_argument("--real-study", default=str(SR.STUDY))
    ap.add_argument("--real-pool", default=str(SR.POOL))
    ap.add_argument("--real-docs", default=str(WORKTREE / "docs"))
    ap.add_argument("--linguist", default=str(P.LINGUIST_HOST))
    ap.add_argument("--commit")
    ap.add_argument("--seal")
    ap.add_argument("--protected")
    ap.add_argument("--out")
    ap.add_argument("--ledger", help="decoys only")
    ap.add_argument("--rerun", metavar="REASON")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--receipt", metavar="SHA256")
    a = ap.parse_args(argv)
    try:
        pl = places(a)
        decision = LG.decide(LG.read(pl.ledger), a.resume, a.rerun)
        if pl.tgt.real:
            echo(TX.plan("real", str(pl.tgt.study), str(pl.tgt.pool), str(pl.prot), str(pl.out), str(pl.ledger),
                         a.commit))
            try:
                answer = reader("> ")
            except (EOFError, KeyboardInterrupt):
                raise Refused("no answer; refused") from None
            if answer.strip() != "":
                raise Refused("not confirmed; refused")
        if a.resume:
            for d, w in ((pl.prot, "protected"), (pl.out, "public")):
                if not d.is_dir():
                    raise Refused(f"--resume needs the first run's {w} directory; refused")
        else:
            P.new_or_empty(pl.prot, "protected")
            P.new_or_empty(pl.out, "public")
    except (Refused, P.Refused) as e:
        print(f"score_sa3: {e}", file=sys.stderr)
        return 2
    except LG.LedgerError as e:
        print(f"score_sa3: {e.code}: {TX.STOP_CODES[e.code]}; refused", file=sys.stderr)
        return 2
    for root in SR.protected_roots():
        if root in pl.prot.parents and not root.exists():
            root.mkdir(parents=True, mode=0o700)
    pl.prot.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(pl.prot, 0o700)
    pl.out.mkdir(parents=True, exist_ok=True)
    job = Job(a, pl, "resume" if a.resume else "score", echo)
    LG.append(LG.attempts_path(pl.ledger), LG.attempt("attempt_started", job.mode, a.commit))
    try:
        return resume(job) if a.resume else run_full(job, decision)
    except RP.ReportError as e:
        return stopped(job, Stop(job.steps[-1]["step"] if job.steps else 1, "invalid_report_value", e.field))
    except Exception:                                            # noqa: BLE001  the launcher's own fault
        with open(pl.prot / "launcher.log", "a") as fh:
            traceback.print_exc(file=fh)
        return stopped(job, Stop(job.steps[-1]["step"] if job.steps else 1, "launcher_error"))


if __name__ == "__main__":
    raise SystemExit(main())
