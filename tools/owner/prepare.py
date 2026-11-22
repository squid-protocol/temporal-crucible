#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The owner-run preparation job (docs/process/owner_job_spec.md, Revision 2): the last count, the placebo
reproduced, and the seal. It does not score SA3.

    python3 tools/owner/prepare.py --decoy DIR --protected P --out O                    # what tests use
    python3 tools/owner/prepare.py --real --i-am-the-owner --protected P --out O

No target: refused. `--real` without `--i-am-the-owner`: refused. A real run first prints what it will bind and
where it will write, and waits for Enter. DIR (a decoy) holds `study/` laid out like the study directory,
`pool/<repo>` clones and `docs/` (the marginals file, the committed placebo file, the sealed documents). The real
locations are parameters (`--real-study`, `--real-pool`, `--real-docs`, `--linguist`) whose defaults are the
production paths; `P` must then lie inside the protected root (tools/harness/sandbox_ro.PROTECTED_ROOT).

Where things go. P (new or empty, mode 700): every stage's directory (`runs/<stage>/<repo>/`, with its HOME,
TMPDIR, stdout and stderr in `stage.log`, its `result.json`), the database copies, the harvest copies, the label-side
manifest, the regenerated placebo file and the code copies. O (new or empty): `owner_report.json`,
`owner_report.md`, `seal.json`, `run_log.json`, written by tools/owner/report.py alone, after every value has been
validated against a fixed shape. No stage's sandbox has O bound. A stage's result is read from P and validated
field by field; a value that does not fit stops the launcher with "invalid report value" and the field's name. A
stage's exception text is never read: a stage that fails returns its name and a code from a fixed list. The
terminal gets `stage repo ok|failed` lines, the report's path, and last one line: PASS or FAIL with codes.

Stages, each in tools/harness/sandbox_ro.py's read-only sandbox, after its guard has read the mount table:

  manifest_before  stat of every declared input (label side included) and every clone's .git
  seal_inputs      SHA-256 of every declared input as it is; SHA-256 of each clone's HEAD; GitHub's two lists
  copy (per repo)  hash each input again; copy the history, scan and harvest databases with their side files, open
                   the COPY, checkpoint it, set it to rollback mode; write the A' harvest (tools/owner/tracker_keys.py)
  build_A, build_Aprime (per repo)   sa3_outcomes.build(repo), unchanged; the harvest bound at the study path is
                   the copy, then the stripped copy
  count (per repo) the count, "A equals the stored file", the pattern disagreements
  placebo          the reference stage_placebo from a copy, compared with the committed file (placebo_check.py)
  runtime          the interpreter, packages, libraries and environment, as the seal records them
  manifest_after   the stat again, compared with the first, inside the sandbox
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata as md
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
WORKTREE = TOOLS.parent
sys.path.insert(0, str(TOOLS / "harness"))
import sandbox_ro as SR  # noqa: E402


def owner_module(name: str):
    """this directory's module `name`, loaded from its file under the unique name `tools_owner_<name>`: never by
    the bare name, which another directory's module (tools/blind/seal.py) may already hold in sys.modules"""
    import importlib.util
    key = f"tools_owner_{name}"
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, Path(__file__).resolve().parent / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
    return sys.modules[key]


sys.modules.setdefault("tools_owner_prepare", sys.modules[__name__])
RP = owner_module("report")

REF_COMMIT = "8fb7fe0"
STAGE_TIMEOUT = 7200
LINGUIST_HOST = Path.home() / ".cache" / "temporal-crucible" / "linguist-e0c78d62c42a"
LINGUIST_DST = SR.HOME / ".owner-job" / "linguist"              # in-sandbox, under the hidden home
SIDE = ("-wal", "-shm", "-journal")
DB_ROLES = ("history", "scan_db", "harvest")
DOCS = Path("docs/")
TABLES_ROOT = SR.PROJECTS / "temporal-crucible-tables"
# the reference scorer's import closure as read from its import lines by the review (M4); used for the seal only
# when the import recorder has nothing (the placebo stage failed); hist_meta is sealed by name (it is not loaded)
EXPECTED_MODULES = ("sa3_score", "sa3_stats", "mod1_lift", "sa3_outcomes", "laws_units", "_engine", "hist_replicate",
                    "label_cascade", "label_card", "hist_fixlabel", "fixlike_v2", "laws_history")
BY_NAME = ("hist_meta",)


# ================================================================================================ declared inputs
def study_files(study: Path, repo: str) -> dict[str, tuple[str, Path]]:
    """role -> (host source, in-sandbox destination) of one repo's study files"""
    S = SR.STUDY
    rel = {"history": f"history/{repo}.db", "scan_db": f"sa3_scans/{repo}_master.db",
           "scan_sidecar": f"sa3_scans/{repo}.json", "harvest": f"meta_sa3/{repo}.db",
           "outcome": f"sa3_outcomes/{repo}.json", "nesting": f"sa3_nesting/{repo}.json"}
    return {k: (str(study / v), S / v) for k, v in rel.items()}


def originals(study: Path, repo: str) -> list[tuple[str, Path]]:
    """every declared original of one repo, each database with the names of its side files"""
    out = []
    for role, (src, dst) in study_files(study, repo).items():
        out.append((src, dst))
        if role in DB_ROLES:
            out += [(src + s, Path(str(dst) + s)) for s in SIDE]
    return out


def lists_inputs(linguist: Path) -> list[tuple[str, Path]]:
    return [(str(linguist / n), LINGUIST_DST / n) for n in RP.LISTS]


# ================================================================================================ in the sandbox
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def code_of(e: BaseException) -> str:
    """an exception's TYPE as one of report.STAGE_CODES; its message is never looked at"""
    import errno
    if isinstance(e, FileNotFoundError):
        return "input_missing"
    if isinstance(e, KeyError):
        return "key_error"
    if isinstance(e, AssertionError):
        return "assertion"
    if isinstance(e, sqlite3.Error):
        return "database_error"
    if isinstance(e, subprocess.TimeoutExpired):
        return "timeout"
    if isinstance(e, subprocess.CalledProcessError):
        return "git_error"
    if isinstance(e, MemoryError):
        return "memory"
    if isinstance(e, ImportError):
        return "import_error"
    if isinstance(e, PermissionError) or (isinstance(e, OSError) and e.errno in (errno.EROFS, errno.EACCES,
                                                                                    errno.EPERM)):
        return "write_refused"
    if isinstance(e, OSError):
        return "os_error"
    if isinstance(e, ValueError):
        return "value_error"
    if isinstance(e, TypeError):
        return "type_error"
    return "unclassified"


def role_hashes(repo: str) -> dict:
    """SHA-256 of each role's file as bound (main file; the -wal of each database), None where absent"""
    out = {}
    for role, (_src, dst) in study_files(Path("/unused"), repo).items():
        out[role] = sha256_file(dst) if dst.is_file() else None
        if role in DB_ROLES:
            w = Path(str(dst) + "-wal")
            out[role + "-wal"] = sha256_file(w) if w.is_file() else None
    return {r: out[r] for r in RP.ROLES}


def stage_manifest(a: dict, rundir: Path) -> dict:
    sys.path.insert(0, str(TOOLS / "tables"))
    from manifest_stat import entry                              # phase B's stat entry: type, size, times, inode
    man: dict[str, list] = {}
    for r in a["repos"]:
        for _src, dst in originals(Path("/unused"), r):
            if os.path.lexists(dst):
                e = entry(dst)
                # a -shm changes on an ordinary read by anyone; only its presence is recorded
                man["study/" + str(dst.relative_to(SR.STUDY))] = ["present"] if str(dst).endswith("-shm") else e
        c = SR.POOL / r
        if not c.exists():
            man[f"pool/{r}"] = ["absent"]
            continue
        man[f"pool/{r}"] = entry(c)
        g = c / ".git" if (c / ".git").is_dir() else c
        for d, dirs, files in os.walk(g, followlinks=False):
            for n in dirs + files:
                man["pool/" + str((Path(d) / n).relative_to(SR.POOL))] = entry(Path(d) / n)
    (rundir / "manifest.json").write_text(json.dumps({"entries": man}, sort_keys=True) + "\n")
    res = {"entries": len(man)}
    if a.get("before"):
        before = json.loads(Path(a["before"]).read_text())["entries"]
        added = set(man) - set(before)
        removed = set(before) - set(man)
        changed = {k for k in set(man) & set(before) if man[k] != before[k]}
        (rundir / "manifest_diff.json").write_text(json.dumps({"added": sorted(added), "removed": sorted(removed),
                                                               "changed": sorted(changed)}, indent=1) + "\n")
        res.update({"unchanged": not (added or removed or changed), "added": len(added), "removed": len(removed),
                    "changed": len(changed)})
    return res


def git_in(clone: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True, timeout=600)


def stage_seal_inputs(a: dict, rundir: Path) -> dict:
    inputs, clones = {}, {}
    for r in a["repos"]:
        inputs[r] = role_hashes(r)
        p = git_in(SR.POOL / r, "rev-parse", "--verify", "-q", "HEAD") if (SR.POOL / r).is_dir() else None
        head = p.stdout.strip() if p is not None and p.returncode == 0 else ""
        clones[r] = {"head_sha256": hashlib.sha256(head.encode()).hexdigest() if head else None}
    lists = {n: (sha256_file(LINGUIST_DST / n) if (LINGUIST_DST / n).is_file() else None) for n in RP.LISTS}
    return {"inputs": inputs, "lists": lists, "clones": clones}


def stage_copy(a: dict, rundir: Path) -> dict:
    """hash each input; copy each database with its side files (plain reads; the original is never opened by
    SQLite); open the COPY, checkpoint it, set it to rollback mode; then the A' harvest from the harvest copy"""
    TK = owner_module("tracker_keys")
    repo = a["repo"]
    res = {"sha256": role_hashes(repo)}
    d = rundir / "db"
    d.mkdir(exist_ok=True)
    files = study_files(Path("/unused"), repo)
    detail = {}
    for role in DB_ROLES:
        src = files[role][1]
        if not src.is_file():
            detail[role] = "absent"
            continue
        dst = d / f"{role}.db"
        shutil.copyfile(src, dst)
        for s in SIDE:
            if Path(str(src) + s).is_file():
                shutil.copyfile(str(src) + s, str(dst) + s)
        con = sqlite3.connect(str(dst))
        try:
            if con.execute("pragma journal_mode").fetchone()[0] == "wal":
                con.execute("pragma wal_checkpoint(TRUNCATE)")
            con.execute("pragma journal_mode=DELETE").fetchone()
            qc = con.execute("pragma quick_check").fetchone()[0]
        finally:
            con.close()
        detail[role] = {"quick_check": qc, "side_files_left": [s for s in SIDE if Path(str(dst) + s).exists()]}
    kept = False
    if (d / "harvest.db").is_file():
        st = TK.strip_harvest(d / "harvest.db", d / "harvest_aprime.db")
        detail["aprime"] = st
        kept = bool(st["meta_kept"])
    (rundir / "detail.json").write_text(json.dumps(detail, indent=1) + "\n")        # protected directory only
    return {**res, "aprime_meta_kept": kept}


def stage_build(a: dict, rundir: Path) -> dict:
    TK = owner_module("tracker_keys")
    return TK.build_stage(a["repo"], Path(a["ref_tools"]), rundir / "build.json")


def stage_count(a: dict, rundir: Path) -> dict:
    TK = owner_module("tracker_keys")
    return TK.count_stage(a["repo"], Path(a["a_file"]), Path(a["ap_file"]), Path(a["stored"]), Path(a["harvest"]),
                          Path(a["ref_tools"]), rundir / "count_detail.json")


def stage_placebo(a: dict, rundir: Path) -> dict:
    PC = owner_module("placebo_check")
    return PC.stage(Path(a["ref_root"]), Path(a["committed"]), rundir)


def stage_runtime(a: dict, rundir: Path) -> dict:
    PC = owner_module("placebo_check")
    PC.exercise(Path(a["ref_tools"]))
    return {"runtime": PC.fingerprint()}


STAGE_FUNCS = {"manifest_before": stage_manifest, "manifest_after": stage_manifest, "seal_inputs": stage_seal_inputs,
               "copy": stage_copy, "build_A": stage_build, "build_Aprime": stage_build, "count": stage_count,
               "placebo": stage_placebo, "runtime": stage_runtime}


def stage_main(argv: list[str]) -> int:
    """`prepare.py stage NAME --rundir D --args FILE`: inside the sandbox only. The result holds the stage's
    values, or {"status": "failed", "code": <type of the exception>}; the traceback goes to stderr, which is the
    stage's log file in the protected directory."""
    SR.assert_inside_ro()                           # first: the mount table, before any path is touched
    ap = argparse.ArgumentParser()
    ap.add_argument("name", choices=sorted(STAGE_FUNCS))
    ap.add_argument("--rundir", type=Path, required=True)
    ap.add_argument("--args", type=Path, required=True)
    a = ap.parse_args(argv)
    try:
        res = {"status": "ok", "code": "none", **STAGE_FUNCS[a.name](json.loads(a.args.read_text()), a.rundir)}
    except BaseException as e:                      # noqa: BLE001  the message is never written to the result
        traceback.print_exc()
        res = {"status": "failed", "code": code_of(e)}
    tmp = a.rundir / ".result.json.part"
    tmp.write_text(json.dumps(res, indent=1) + "\n")
    os.replace(tmp, a.rundir / "result.json")
    return 0


# ================================================================================================= stage results
def stage_schema(name: str) -> dict:
    """the exact shape of an ok result of each stage (a failed one is exactly status + code)"""
    base = {"status": "word:status", "code": "word:stage_code"}
    roles = {r: "hex64?" for r in RP.ROLES}
    s = {"manifest_before": {"entries": "count"},
         "manifest_after": {"entries": "count", "unchanged": "yesno", "added": "count", "removed": "count",
                            "changed": "count"},
         "seal_inputs": {"inputs": ("map", "repo", roles), "lists": {n: "hex64?" for n in RP.LISTS},
                         "clones": ("map", "repo", {"head_sha256": "hex64?"})},
         "copy": {"sha256": roles, "aprime_meta_kept": "yesno"},
         "build_A": {"build_status": "word:build_status"},
         "build_Aprime": {"build_status": "word:build_status"},
         "count": {"determined": "yesno", "reason": "word:repo_reason", "count": "count?",
                   "a_equals_stored": "yesno?", "disagreements": "count?"},
         "placebo": {"verdict": "word:placebo_verdict", "largest_difference": "real?", "numbers_differing": "count?",
                     "integer_fields_equal": "yesno?", "modules": ("map", "module", "hex64"),
                     "libraries": ("map", "lib", "hex64")},
         "runtime": {"runtime": RP.RUNTIME}}[name]
    return {**base, **s}


def validate_result(name: str, res, vocab: RP.Vocab) -> dict:
    f = f"{name}.result"
    if not isinstance(res, dict) or res.get("status") not in RP.STATUSES:
        raise RP.ReportError(f"{f}.status")
    if res["status"] == "failed":
        RP.check({"status": "word:status", "code": "word:stage_code"}, res, f, vocab)
        if res["code"] == "none":
            raise RP.ReportError(f"{f}.code")
        return res
    RP.check(stage_schema(name), res, f, vocab)
    if res["code"] != "none":
        raise RP.ReportError(f"{f}.code")
    return res


# ======================================================================================================= launcher
class Target:
    def __init__(self, study: Path, pool: Path, docs: Path, linguist: Path, real: bool):
        self.study, self.pool, self.docs, self.linguist, self.real = study, pool, docs, linguist, real


class Refused(Exception):
    pass


def _inside(p: Path, root: Path) -> bool:
    return p == root or root in p.parents


def resolve_target(a) -> Target:
    """string tests only: nothing is opened, listed or statted"""
    if a.decoy and a.real:
        raise Refused("--decoy and --real together; refused")
    if a.real:
        if not a.i_am_the_owner:
            raise Refused("--real needs --i-am-the-owner; refused")
        if a.code_root or a.reference_git:
            raise Refused("--code-root and --reference-git are for decoys only; refused")
        return Target(Path(a.real_study), Path(a.real_pool), Path(a.real_docs), Path(a.linguist), True)
    if a.decoy:
        d = Path(os.path.abspath(a.decoy))
        for bad in SR.FORBIDDEN + (SR.PROJECTS,):
            if _inside(d, bad):
                raise Refused(f"a decoy may not be inside {bad}; refused")
        return Target(d / "study", d / "pool", d / DOCS, Path(a.linguist), False)
    raise Refused("no target. Use --decoy DIR (a decoy built from control repositories), or --real "
                  "--i-am-the-owner; refused")


def check_places(protected: Path, out: Path, real: bool) -> tuple[Path, Path]:
    """string tests only"""
    p, o = Path(os.path.abspath(protected)), Path(os.path.abspath(out))
    if real and not SR.in_protected_root(p):
        raise Refused(f"on a real run the protected directory must be inside {SR.PROTECTED_ROOT}; refused")
    try:
        SR.check_rw(p)
    except SR.SandboxError as e:
        raise Refused(f"protected directory: {e}") from None
    for bad in SR.FORBIDDEN + (TABLES_ROOT, SR.WORKTREE / "tools") + SR.protected_roots():
        if _inside(o, bad):
            raise Refused(f"the public directory may not be inside {bad}; refused")
    if _inside(o, p) or _inside(p, o):
        raise Refused("the public and protected directories may not contain one another; refused")
    return p, o


def new_or_empty(d: Path, what: str) -> None:
    if d.exists() and (not d.is_dir() or any(d.iterdir())):
        raise Refused(f"the {what} directory is not empty; a run writes a new one, nothing is resumed or "
                      "overwritten; refused")


TEST_ROOT_ENV = "OWNER_JOB_TEST_PROTECTED_ROOT"


def test_root_from_env() -> None:
    """TESTS ONLY: OWNER_JOB_TEST_PROTECTED_ROOT names a second protected root for a fresh process, honoured only
    under pytest's temporary directory (/tmp/pytest-of-<user>/) or ~/.claude/jobs/, outside every data root;
    anything else is refused. Announced on stderr when in force. A string test."""
    v = os.environ.get(TEST_ROOT_ENV)
    if not v:
        return
    import getpass
    p = Path(os.path.abspath(v))
    if not (Path(f"/tmp/pytest-of-{getpass.getuser()}") in p.parents or SR.HOME / ".claude" / "jobs" in p.parents):
        raise Refused(f"{TEST_ROOT_ENV} must name a directory under pytest's temporary directory or "
                      "~/.claude/jobs; refused")
    try:
        SR.name_protected_root_for_tests(p)
    except SR.SandboxError as e:
        raise Refused(f"{TEST_ROOT_ENV}: {e}") from None
    print(f"prepare: TEST protected root in force: {p}", file=sys.stderr)


def default_reader(prompt: str) -> str:
    if not sys.stdin.isatty():
        raise EOFError("standing input is not a terminal")
    return input(prompt)


def read_marginals(docs: Path) -> list[dict]:
    rows = json.loads((docs / "sa3_outcome_marginals.json").read_text())
    for row in rows:
        if not isinstance(row.get("repo"), str) or not RP.REPO_NAME.fullmatch(row["repo"]):
            raise Refused("a repo name in the marginals file does not fit the pattern; refused")
    return rows


def sealed_list(sa3_score: Path) -> list[str]:
    """the reference scorer's SEALED tuple, read from its source as text (the module is not imported here)"""
    for n in ast.walk(ast.parse(sa3_score.read_text())):
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "SEALED":
            return list(ast.literal_eval(n.value))
    raise Refused("the reference scorer has no SEALED list; refused")


def host_packages() -> frozenset:
    return frozenset(n for n in (d.metadata.get("Name") for d in md.distributions()) if n)


def tree_hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): sha256_file(p) for p in sorted(root.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts}


def write_gitconfig(home: Path) -> None:
    (home / ".gitconfig").write_text("[gc]\n\tauto = 0\n[maintenance]\n\tauto = false\n[user]\n\tname = owner-job\n"
                                     "\temail = owner-job@invalid\n[safe]\n\tdirectory = *\n")


class Job:
    """one run: the places, the vocabulary, the run log, the stage runner"""

    def __init__(self, tgt: Target, prot: Path, out: Path, code_root: Path, echo=print):
        self.tgt, self.prot, self.out, self.code_root, self.echo = tgt, prot, out, code_root, echo
        self.code, self.ref = prot / "code", prot / "ref"
        self.ref_git = WORKTREE                     # where 8fb7fe0 is looked up (decoys may name another)
        self.started = int(time.time())
        self.vocab = RP.Vocab()
        self.log = {"target": "real" if tgt.real else "decoy", "started": self.started, "finished": None,
                    "complete": False, "last_stage": "setup", "invalid_in_stage": [], "stages": []}

    def save_log(self) -> None:
        if self.out is not None:                              # seal.py verify writes nothing public
            RP.write_public(self.out, self.vocab, run_log=self.log)

    def record(self, stage: str, repo: str, status: str, code: str, seconds: int) -> None:
        self.log["stages"].append({"stage": stage, "repo": repo, "status": status, "code": code,
                                   "seconds": seconds})
        self.log["last_stage"] = stage
        self.save_log()
        self.echo(f"{stage} {repo} {status}")

    def spec(self, rundir: Path, inputs: list, clone: tuple | None = None, rw: list[Path] = ()) -> SR.Spec:
        return SR.Spec(rw=[rundir, *rw], code=[self.code], inputs=list(inputs), clone=clone,
                       env={"LAWS_LINGUIST_DIR": str(LINGUIST_DST)}, cwd=rundir)

    def run(self, name: str, repo: str, inputs: list, args: dict, clone: tuple | None = None,
            rw: list[Path] = (), sub: str | None = None) -> dict:
        rundir = self.prot / "runs" / name / (repo if repo != "*" else "all") / (sub or "")
        rundir = Path(os.path.normpath(rundir))
        home, tmp = rundir / "home", rundir / "tmp"
        for d in (home, tmp):
            d.mkdir(parents=True, exist_ok=True)
        write_gitconfig(home)
        (rundir / "args.json").write_text(json.dumps(args) + "\n")
        stage = name
        argv = ["/usr/bin/python3", "-I", "-B", str(self.code / "tools" / "owner" / "prepare.py"), "stage", stage,
                "--rundir", str(rundir), "--args", str(rundir / "args.json")]
        t0 = time.time()
        with open(rundir / "stage.log", "w") as log:         # written by the stage; never read by the launcher
            try:
                rc = SR.run(argv, self.spec(rundir, inputs, clone, rw), home, tmp, timeout=STAGE_TIMEOUT,
                            stdout=log).returncode
            except subprocess.TimeoutExpired:
                rc = "timeout"
        rf = rundir / "result.json"
        if rf.is_file():
            try:
                res = json.loads(rf.read_text())
            except ValueError:
                raise RP.ReportError(f"{stage}.result") from None
            res = validate_result(stage, res, self.vocab)
        else:
            res = {"status": "failed",
                   "code": "timeout" if rc == "timeout" else "sandbox_refused" if rc == 3 else "no_result"}
        self.record(name, repo, res["status"], res["code"], int(time.time() - t0))
        return res

    # ----------------------------------------------------------------------------------------- the steps
    def setup(self) -> list[str]:
        """the code copies (byte-identical to the code root's tools/, checked), the docs copy for the placebo
        stage, the committed placebo file's copy; returns the frozen list"""
        rows = read_marginals(self.tgt.docs)
        self.rows = rows
        self.repos = [r["repo"] for r in rows if r.get("status") == "ok"]
        self.placebo_repos = [r for r in self.repos
                              if ((next(x for x in rows if x["repo"] == r).get("HP") or {}).get("clears_floor"))]
        mods = frozenset(p.stem for p in (self.code_root / "tools").glob("*.py"))
        self.sealed = sealed_list(self.code_root / "tools" / "sa3_score.py")
        self.vocab = RP.Vocab(repos=frozenset(r["repo"] for r in rows), modules=mods, packages=host_packages(),
                              sealed=frozenset(self.sealed))
        self.save_log()
        ign = shutil.ignore_patterns("__pycache__", "*.pyc")
        shutil.copytree(self.code_root / "tools", self.code / "tools", ignore=ign)
        shutil.copytree(self.code_root / "tools", self.ref / "tools", ignore=ign)
        (self.ref / "docs").mkdir(parents=True)
        shutil.copyfile(self.tgt.docs / "sa3_outcome_marginals.json", self.ref / "docs" / "sa3_outcome_marginals.json")
        (self.prot / "committed").mkdir()
        shutil.copyfile(self.tgt.docs / "sa3_placebo.json", self.prot / "committed" / "sa3_placebo.json")
        want = tree_hashes(self.code_root / "tools")
        self.code_hashes = want
        self.copy_ok = tree_hashes(self.code / "tools") == want and tree_hashes(self.ref / "tools") == want and \
            sha256_file(self.ref / "docs" / "sa3_outcome_marginals.json") == \
            sha256_file(self.tgt.docs / "sa3_outcome_marginals.json")
        return self.repos

    def everything(self) -> list:
        ins = [x for r in self.repos for x in originals(self.tgt.study, r)]
        ins += [(str(self.tgt.pool / r), SR.POOL / r) for r in self.repos]
        return ins + lists_inputs(self.tgt.linguist)

    def manifest(self, when: str) -> dict:
        args = {"repos": self.repos}
        ins = self.everything()
        if when == "after":
            b = self.prot / "runs" / "manifest_before" / "all" / "manifest.json"
            args["before"] = str(b)
            ins.append((str(b), b))
        return self.run(f"manifest_{when}", "*", ins, args)

    def per_repo(self, r: str) -> dict:
        """copy, build_A, build_Aprime, count for one repo; returns its report row and the copy's hashes"""
        F = study_files(self.tgt.study, r)
        lists = lists_inputs(self.tgt.linguist)
        cp = self.run("copy", r, originals(self.tgt.study, r), {"repo": r})
        row = {"determined": False, "reason": "not_run", "count": None, "a_equals_stored": None,
               "disagreements": None}
        if cp["status"] != "ok":
            return {**row, "reason": cp["code"]}, None
        db = self.prot / "runs" / "copy" / r / "db"
        S = SR.STUDY
        base = [(str(db / "history.db"), F["history"][1]), (str(db / "scan_db.db"), F["scan_db"][1]),
                F["scan_sidecar"]] + lists
        builds = {}
        ref = (str(self.ref / "tools"), self.ref / "tools")
        for name, harvest in (("build_A", db / "harvest.db"), ("build_Aprime", db / "harvest_aprime.db")):
            b = self.run(name, r, base + [(str(harvest), F["harvest"][1]), ref],
                         {"repo": r, "ref_tools": str(self.ref / "tools")}, clone=(r, str(self.tgt.pool / r)))
            if b["status"] != "ok":
                return {**row, "reason": b["code"]}, cp["sha256"]
            builds[name] = self.prot / "runs" / name / r / "build.json"
        stored = F["outcome"]
        ins = [stored, (str(db / "harvest.db"), S / "meta_sa3" / f"{r}.db"),
               (str(builds["build_A"]), builds["build_A"]), (str(builds["build_Aprime"]), builds["build_Aprime"]),
               (str(self.ref / "tools"), self.ref / "tools")]
        c = self.run("count", r, ins, {"repo": r, "a_file": str(builds["build_A"]),
                                       "ap_file": str(builds["build_Aprime"]), "stored": str(stored[1]),
                                       "harvest": str(S / "meta_sa3" / f"{r}.db"),
                                       "ref_tools": str(self.ref / "tools")})
        if c["status"] != "ok":
            return {**row, "reason": c["code"]}, cp["sha256"]
        return {k: c[k] for k in row}, cp["sha256"]

    def placebo(self) -> dict:
        ins = []
        for r in self.placebo_repos:
            F = study_files(self.tgt.study, r)
            db = self.prot / "runs" / "copy" / r / "db"
            ins += [(str(db / "history.db"), F["history"][1]), (str(db / "scan_db.db"), F["scan_db"][1]),
                    F["scan_sidecar"], F["nesting"], F["outcome"], (str(self.tgt.pool / r), SR.POOL / r)]
        committed = self.prot / "committed" / "sa3_placebo.json"
        ins += [(str(self.ref / "tools"), self.ref / "tools"), (str(committed), committed)]
        ins += lists_inputs(self.tgt.linguist)
        return self.run("placebo", "*", ins, {"ref_root": str(self.ref), "committed": str(committed)},
                        rw=[self.ref / "docs"])

    def runtime(self) -> dict:
        return self.run("runtime", "*", [(str(self.ref / "tools"), self.ref / "tools")],
                        {"ref_tools": str(self.ref / "tools")})


def blank_report(job: Job, codes: list[str]) -> dict:
    now = int(time.time())
    return {"verdict": "FAIL", "codes": codes, "target": job.log["target"], "started": job.started, "finished": now,
            "seconds": now - job.started, "repos": {},
            "placebo": {"verdict": "not_run", "code": "none", "largest_difference": None, "numbers_differing": None,
                        "integer_fields_equal": None, "repos_in_stage": 0},
            "versions": {**{k: None for k in RP.VERSION_KEYS}, "linear_algebra": []},
            "seal": {"written": False, "entries": 0, "code_modules_found": [], "modules_unchanged_since_8fb7fe0": None,
                     "lock_expected_entries": 0},
            "manifest": {"unchanged": None, "entries": None}, "stages_failed": 0}


def finish(job: Job, rep: dict) -> int:
    rep["finished"] = int(time.time())
    rep["seconds"] = rep["finished"] - job.started
    rep["stages_failed"] = sum(1 for s in job.log["stages"] if s["status"] == "failed")
    rep["verdict"] = "FAIL" if rep["codes"] else "PASS"
    RP.write_public(job.out, job.vocab, report=rep)
    job.log.update({"finished": rep["finished"], "complete": True, "last_stage": "report"})
    job.save_log()
    job.echo(f"report: {job.out / 'owner_report.md'}")
    job.echo(rep["verdict"] + ("" if not rep["codes"] else " " + " ".join(rep["codes"])))
    return 0 if rep["verdict"] == "PASS" else 1


def launch(tgt: Target, prot: Path, out: Path, code_root: Path = WORKTREE, echo=print,
           ref_git: Path = WORKTREE) -> int:
    SE = owner_module("seal")
    for root in SR.protected_roots():                         # the protected root itself: mode 700 when made
        if root in prot.parents and not root.exists():
            root.mkdir(parents=True, mode=0o700)
    prot.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(prot, 0o700)
    out.mkdir(parents=True, exist_ok=True)
    job = Job(tgt, prot, out, code_root, echo)
    job.ref_git = ref_git
    try:
        return _launch(job, SE)
    except RP.ReportError as e:
        echo(str(e))                                           # "invalid report value: <field>", nothing else
        stage = e.field.split(".")[0]
        job.log["invalid_in_stage"] = [stage] if stage in RP.STAGES else ["report"]
        job.log["complete"] = False
        try:
            job.save_log()
            RP.write_public(out, job.vocab, report=blank_report(job, ["invalid_report_value"]))
        except RP.ReportError:
            pass
        echo(f"report: {out / 'owner_report.md'}")
        echo("FAIL invalid_report_value")
        return 1
    except Exception:                                          # noqa: BLE001  the launcher's own fault
        with open(prot / "launcher.log", "a") as fh:           # protected directory only
            traceback.print_exc(file=fh)
        try:
            RP.write_public(out, job.vocab, report=blank_report(job, ["launcher_error"]))
            job.save_log()
        except Exception:                                      # noqa: BLE001
            pass
        echo(f"report: {out / 'owner_report.md'}")
        echo("FAIL launcher_error")
        return 1


def _launch(job: Job, SE) -> int:
    t0 = time.time()
    repos = job.setup()
    job.record("setup", "*", "ok" if job.copy_ok else "failed", "none" if job.copy_ok else "code_copy_differs",
               int(time.time() - t0))
    if not job.copy_ok:
        return finish(job, blank_report(job, ["setup_failed"]))
    if not repos:
        return finish(job, blank_report(job, ["no_repos"]))
    codes: list[str] = []
    mb = job.manifest("before")
    si = job.run("seal_inputs", "*", job.everything(),
                 {"repos": repos})
    rows, copies = {}, {}
    for r in repos:
        rows[r], copies[r] = job.per_repo(r)
    pl = job.placebo() if job.placebo_repos else {"status": "failed", "code": "none", "verdict": "not_run"}
    rt = job.runtime()
    ma = job.manifest("after")
    # ---- the seal: written only from validated stage values and the launcher's own code and document hashes
    changed = si["status"] == "ok" and any(copies[r] is not None and copies[r] != si["inputs"][r] for r in repos)
    seal, seal_ok = None, False
    modules = sorted(pl.get("modules", {})) if pl["status"] == "ok" else []
    if si["status"] == "ok" and rt["status"] == "ok" and not changed:
        seal = SE.compose(job, si, rt["runtime"], modules or list(EXPECTED_MODULES),
                          pl.get("libraries", {}) if pl["status"] == "ok" else {})
        RP.write_public(job.out, job.vocab, seal=seal)
        seal_ok = True
    job.record("seal", "*", "ok" if seal_ok else "failed", "none", 0)
    # ---- PASS or FAIL, exactly as the spec defines it
    if any(not x["determined"] for x in rows.values()):
        codes.append("count_not_determined")
    if any(x["a_equals_stored"] is False for x in rows.values()):
        codes.append("a_differs_from_stored")
    if any((x["disagreements"] or 0) > 0 for x in rows.values()):
        codes.append("pattern_disagreements")
    pv = pl.get("verdict", "failed") if pl["status"] == "ok" else ("not_run" if not job.placebo_repos else "failed")
    pcode = pl.get("code", "none")
    if pl["status"] == "ok" and any(h != job.code_hashes.get(f"{m}.py") for m, h in pl["modules"].items()):
        pv, pcode = "failed", "code_copy_differs"          # the placebo did not run the code root's files
    codes += {"differs": ["placebo_differs"], "failed": ["placebo_failed"], "not_run": ["placebo_not_run"]}.get(pv, [])
    if not seal_ok:
        codes.append("seal_not_written")
        if changed:
            codes.append("inputs_changed_during_run")
    # the frozen reference code is what ran (owner ruling: a PASS condition the spec had omitted)
    code = seal["code"] if seal is not None else \
        SE.code_entries(job.code_root, job.ref_git, (modules or list(EXPECTED_MODULES)) + list(BY_NAME))
    vals = [v["unchanged_since_8fb7fe0"] for v in code.values()]
    ref_state = None if any(x is None for x in vals) else all(vals)
    if ref_state is False:
        codes.append("reference_code_changed")
    elif ref_state is None:
        codes.append("reference_code_unchecked")
    if mb["status"] != "ok" or ma["status"] != "ok":
        codes.append("manifest_failed")
    elif not ma["unchanged"]:
        codes.append("manifest_changed")
    runtime = rt.get("runtime") if rt["status"] == "ok" else None
    rep = blank_report(job, codes)
    rep.update({
        "repos": rows,
        "placebo": {"verdict": pv, "code": pcode,
                    "largest_difference": pl.get("largest_difference"),
                    "numbers_differing": pl.get("numbers_differing"),
                    "integer_fields_equal": pl.get("integer_fields_equal"),
                    "repos_in_stage": len(job.placebo_repos)},
        "versions": {"python": runtime["python"] if runtime else None,
                     "numpy": _pkg(runtime, "numpy"), "scipy": _pkg(runtime, "scipy"),
                     "git": runtime["git"] if runtime else None, "tar": runtime["tar"] if runtime else None,
                     "linear_algebra": sorted((runtime or {}).get("libraries", {}))},
        "seal": {"written": seal_ok, "entries": RP.entries(seal) if seal else 0, "code_modules_found": modules,
                 "modules_unchanged_since_8fb7fe0": ref_state,
                 "lock_expected_entries": len(seal["lock_expected"]) if seal else 0},
        "manifest": {"unchanged": ma.get("unchanged") if ma["status"] == "ok" else None,
                     "entries": ma.get("entries") if ma["status"] == "ok" else None},
    })
    return finish(job, rep)


def _pkg(runtime: dict | None, name: str) -> str | None:
    return next((v for k, v in ((runtime or {}).get("packages") or {}).items() if k.lower() == name), None)


def plan_text(tgt: Target, prot: Path, out: Path, code_root: Path) -> str:
    return "\n".join([
        "The owner-run preparation job (docs/process/owner_job_spec.md). It does not score SA3.",
        "It binds, read-only, inside its sandboxes:",
        f"  the study directory {tgt.study}: per repo the history, the scan database, its sidecar, the link harvest,",
        "  the outcome file and the nesting file (databases are copied into the protected directory and the",
        "  copies opened)",
        f"  the clones under {tgt.pool}, GitHub's two lists under {tgt.linguist}, the code under {code_root / 'tools'}",
        f"It reads, as the public files they are, {tgt.docs / 'sa3_outcome_marginals.json'}, "
        f"{tgt.docs / 'sa3_placebo.json'} and the sealed documents.",
        f"It writes the protected directory {prot} (mode 700: copies, logs, manifests) and the public directory",
        f"{out} (owner_report.json, owner_report.md, seal.json, run_log.json). Nothing else is written.",
        "Press Enter to start. Anything else, or end of input, stops it."])


def main(argv: list[str] | None = None, reader=default_reader, echo=print) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["stage"]:
        return stage_main(argv[1:])
    ap = argparse.ArgumentParser(description="the owner-run preparation job (it does not score SA3)")
    ap.add_argument("--decoy")
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--i-am-the-owner", action="store_true")
    ap.add_argument("--real-study", default=str(SR.STUDY))
    ap.add_argument("--real-pool", default=str(SR.POOL))
    ap.add_argument("--real-docs", default=str(WORKTREE / DOCS))
    ap.add_argument("--linguist", default=str(LINGUIST_HOST))
    ap.add_argument("--code-root", help="decoys only: the directory whose tools/ the stages run (default: this "
                                        "checkout)")
    ap.add_argument("--reference-git", help="decoys only: the git checkout where 8fb7fe0 is looked up (default: "
                                            "this checkout)")
    ap.add_argument("--protected")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    try:
        test_root_from_env()
        tgt = resolve_target(a)
        if not a.protected or not a.out:
            raise Refused("--protected and --out are both required; refused")
        prot, out = check_places(Path(a.protected), Path(a.out), tgt.real)
        code_root = Path(os.path.abspath(a.code_root)) if a.code_root else WORKTREE
        if tgt.real:
            echo(plan_text(tgt, prot, out, code_root))
            try:
                answer = reader("> ")
            except (EOFError, KeyboardInterrupt):
                raise Refused("no answer; refused") from None
            if answer.strip() != "":
                raise Refused("not confirmed; refused")
        new_or_empty(prot, "protected")
        new_or_empty(out, "public")
    except Refused as e:
        print(f"prepare: {e}", file=sys.stderr)
        return 2
    return launch(tgt, prot, out, code_root, echo,
                  ref_git=Path(os.path.abspath(a.reference_git)) if a.reference_git else WORKTREE)


if __name__ == "__main__":
    raise SystemExit(main())
