"""Tests of the owner-run preparation job (tools/owner/; docs/process/owner_job_spec.md, Revision 2).

Everything runs on DECOYS: two control repositories generated (generator seed 11, --years 10; Python, and Python
with the merge workflow), each with planted commits added to its history BEFORE the unmodified SA3 pipeline is run
on it by the existing harness (route manifest), then assembled into a decoy directory (study/, pool/, docs/) whose
"committed" placebo file is the reference `sa3_score.py placebo` run over the whole decoy inside the harness
sandbox. Nothing here opens, lists or stats the real study directory, the corpus, the pool, the stored tables, the
protected root or ~/.blind: the real code path is exercised with throwaway directories passed as its location
parameters and a test-named protected root, and the production defaults only by the guard, which is shown (under
strace) to refuse before touching any path. Every call into SA3 code runs inside a sandbox.

Skipped, with the reason, when bwrap, tree_sitter_language_pack 1.20.0, linguist's cached lists or the engine
export are unavailable. The whole file takes about two minutes.
"""
from __future__ import annotations

import ast
import builtins
import importlib.metadata as md
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
OWNER = ROOT / "tools" / "owner"
HARNESS = ROOT / "tools" / "harness"
GEN = ROOT / "tools" / "control_repo" / "generate.py"
sys.path.insert(0, str(HARNESS))
import sandbox as SB  # noqa: E402
import sandbox_ro as SR  # noqa: E402


def _load_prepare():
    """tools/owner/prepare.py by its file, under the name its own loader uses (never the bare name `prepare`)"""
    import importlib.util
    if "tools_owner_prepare" not in sys.modules:
        spec = importlib.util.spec_from_file_location("tools_owner_prepare", OWNER / "prepare.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["tools_owner_prepare"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["tools_owner_prepare"]


P = _load_prepare()
RP = P.RP

PREPARE = OWNER / "prepare.py"
SEAL = OWNER / "seal.py"
PY = sys.executable
MARK_SHA = "c0ffee" + "5eed" * 8 + "ab"                   # 40 hex, in no clone
MARK_SHA2 = "d00d" * 10
MARK_PATH = "zz_marker_dir_q9x7/outcome_only_marker_7f3a.py"
MARK_VAL = "markerkey-424242"
MARKERS = (MARK_SHA, MARK_SHA2, MARK_PATH, MARK_VAL, "zz_marker_dir_q9x7", "outcome_only_marker", "markerkey")
REPOS = ("ctrl-base", "ctrl-mw")
# planted commits and whether the count must include them (owner_job_spec.md, "Before the owner runs it", item 1)
BASE_CASES = [("P1_lower_key_alone", "fix x86-64 build\n", True),
              ("P2_with_hash_n", "fix x86-64 build, fixes #12\n", False),
              ("P3_with_upper_key", "fix arm-7 build; resolves PROJ-42\n", False),
              ("P4_with_fixes_trailer", "fix mips-3 build\n\nFixes: the decoder\n", False),
              ("P5_with_cve", "fix sparc-9 build for CVE-2024-12345\n", False),
              # the stated reading: case-insensitively the key alternative takes `deadbeef-1` (it comes before the
              # hash alternative, which would take `deadbeef`), a key with lower-case letters, so it is counted
              ("P8_fixes_colon_deadbeef_1_subject", "Fixes: deadbeef-1\n", True),
              ("P9_upper_key_utf8", "Fix UTF-8 decoding\n", False)]          # review M7: not in the count


# --------------------------------------------------------------------------------------------- helpers
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
    """decided INSIDE the harness sandbox: laws-study is never looked at from outside"""
    w = SB.prepare(base / "engine-probe")
    (w / "tree/tools/harness").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HARNESS / "sandbox.py", w / "tree/tools/harness/sandbox.py")
    p = SB.run(["/usr/bin/python3", "-I", "-B", "-c",
                f"import os; print(os.path.isdir({str(SB.ENGINE / 'gitgalaxy')!r}))"], w, timeout=120)
    return p.stdout.strip() == "True"


def git(repo: Path, *a: str, env: dict | None = None, inp: str | None = None) -> str:
    e = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_CONFIG_NOSYSTEM": "1", "HOME": str(repo.parent),
         "GIT_AUTHOR_NAME": "Planter", "GIT_AUTHOR_EMAIL": "planter@example.invalid",
         "GIT_COMMITTER_NAME": "Planter", "GIT_COMMITTER_EMAIL": "planter@example.invalid", **(env or {})}
    p = subprocess.run(["git", "-C", str(repo), "-c", "gc.auto=0", *a], capture_output=True, text=True, env=e,
                       input=inp)
    assert p.returncode == 0, p.stderr
    return p.stdout.strip()


def unit_paths(ctl: Path) -> list[str]:
    m = json.loads((ctl / "manifest.json").read_text())
    return sorted(x["path_at_snapshot"] for x in m["files"] if x.get("is_unit") and x.get("path_at_snapshot")
                  and x.get("path_final") == x["path_at_snapshot"])


def commit(repo: Path, path: str, msg: str, t: int) -> str:
    with open(repo / path, "a") as fh:
        fh.write(f"# planted {t}\n")
    git(repo, "add", path)
    git(repo, "commit", "-q", "-F", "-", env={"GIT_AUTHOR_DATE": f"@{t} +0000", "GIT_COMMITTER_DATE": f"@{t} +0000"},
        inp=msg)
    return git(repo, "rev-parse", "HEAD")


def plant_base(ctl: Path) -> dict[str, tuple[str, bool]]:
    """sha and expected verdict of each planted commit; all in the window after the snapshot except T7"""
    repo, u = ctl / "repo", unit_paths(ctl)
    t0 = int(git(repo, "log", "-1", "--format=%ct")) + 86400
    early = json.loads((ctl / "manifest.json").read_text())["points"]["snapshot"]["time"] - 200 * 86400
    out, i = {}, 0
    for name, msg, want in BASE_CASES:
        out[name] = (commit(repo, u[i], msg, t0 + i * 3600), want)
        i += 1
    t6 = commit(repo, u[i], "fix sha-1 fallback\n", t0 + i * 3600)
    out["T6_late_target_lower_key"] = (t6, True)
    i += 1
    out["R6_late_revert_quoting_lower_key"] = (commit(repo, u[i], f'Revert "fix sha-1 fallback"\n\nThis reverts '
                                                                f'commit {t6}.\n', t0 + i * 3600), True)
    i += 1
    t7 = commit(repo, u[i], "fix md-5 fallback\n", early)                 # before the cut: not in the window
    out["T7_early_target"] = (t7, False)
    i += 1
    out["R7_early_revert_quoting_lower_key"] = (commit(repo, u[i], f'Revert "fix md-5 fallback"\n\nThis reverts '
                                                                 f'commit {t7}.\n', t0 + i * 3600), False)
    return out


def plant_mw(ctl: Path) -> dict[str, tuple[str, bool]]:
    """two merges at the tip of a merge-workflow history: one inheriting only a lower-case key from its one
    brought-in commit (counted), one inheriting it beside a `Fixes #77` from another brought-in commit (not)"""
    repo, u = ctl / "repo", unit_paths(ctl)
    t0 = int(git(repo, "log", "-1", "--format=%ct")) + 86400
    out = {}

    def merge(branch: str, t: int) -> str:
        git(repo, "checkout", "-q", "main")
        git(repo, "merge", "-q", "--no-ff", "-m", f"Merge branch '{branch}'", branch,
            env={"GIT_AUTHOR_DATE": f"@{t} +0000", "GIT_COMMITTER_DATE": f"@{t} +0000"})
        return git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "-b", "topic-p1")
    out["K1_brought_in_lower_key"] = (commit(repo, u[20], "fix arm-64 alignment\n", t0), False)
    out["M1_merge_inherits_lower_key_only"] = (merge("topic-p1", t0 + 60), True)
    git(repo, "checkout", "-q", "-b", "topic-p2")
    out["K2_brought_in_lower_key"] = (commit(repo, u[21], "fix ppc-32 overflow\n", t0 + 3600), False)
    out["K3_brought_in_hash_n"] = (commit(repo, u[21], "Fixes #77 in the reader\n", t0 + 3700), False)
    out["M2_merge_lower_key_beside_hash_n"] = (merge("topic-p2", t0 + 3800), False)
    git(repo, "branch", "-q", "-D", "topic-p1", "topic-p2")
    return out


def all_text(*dirs: Path) -> str:
    chunks = []
    for d in dirs:
        for p in sorted(Path(d).rglob("*")):
            if p.is_file():
                chunks.append(str(p.relative_to(d)))
                chunks.append(p.read_bytes().decode("utf-8", "replace"))
    return "\n".join(chunks)


def stat_of(p: Path) -> tuple:
    s = p.stat()
    return (p.read_bytes(), s.st_mtime_ns, s.st_size)


class Decoy:
    def __init__(self, base: Path):
        self.base = base
        self.dir = base / "decoy"
        self.planted: dict[str, dict[str, tuple[str, bool]]] = {}

    def build(self) -> None:
        marg = []
        for tag, mut, plant in (("base", None, plant_base), ("mw", "merge_workflow", plant_mw)):
            ctl = self.base / "controls" / tag
            argv = [PY, "-B", str(GEN), "--out", str(ctl), "--seed", "11", "--years", "10", "--language", "python"]
            subprocess.run(argv + (["--mutation", mut] if mut else []), check=True, capture_output=True,
                           cwd=str(self.base))
            self.planted[f"ctrl-{tag}"] = plant(ctl)
            work = self.base / "work" / tag
            p = subprocess.run([PY, "-B", str(HARNESS / "run.py"), "--control", str(ctl), "--work", str(work),
                                "--name", tag, "--routes", "manifest", "--no-shim-lock"],
                               capture_output=True, text=True, timeout=1800)
            w, r = work / "manifest", f"ctrl-{tag}"
            assert (w / "study/sa3_outcomes" / f"{r}.json").is_file(), p.stdout[-3000:] + p.stderr[-3000:]
            for sub in ("history", "sa3_scans", "sa3_outcomes", "meta_sa3", "sa3_nesting"):
                for f in (w / "study" / sub).glob(f"{r}*"):
                    (self.dir / "study" / sub).mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, self.dir / "study" / sub / f.name)
            shutil.copytree(w / "pool" / r, self.dir / "pool" / r, symlinks=True)
            marg += json.loads((w / "tree/docs/sa3_outcome_marginals.json").read_text())
        docs = self.dir / "docs"
        docs.mkdir(parents=True)
        (docs / "sa3_outcome_marginals.json").write_text(json.dumps(marg, indent=1) + "\n")
        for n in ("sa3_registration_consolidated.md", "sa3_power.md", "sa3_code_review.md", "sa3_registration.md"):
            shutil.copyfile(ROOT / "docs" / n, docs / n)
        self.committed_placebo(self.dir)

    def committed_placebo(self, d: Path) -> None:
        """docs/sa3_placebo.json: the reference placebo stage over the whole decoy, in the harness sandbox"""
        w = SB.prepare(self.base / f"placebo-work-{d.name}")
        shutil.copytree(d / "study", w / "study", dirs_exist_ok=True)
        for c in (d / "pool").iterdir():
            shutil.copytree(c, w / "pool" / c.name, symlinks=True)
        shutil.copytree(ROOT / "tools", w / "tree/tools", ignore=shutil.ignore_patterns("__pycache__"))
        (w / "tree/docs").mkdir()
        shutil.copyfile(d / "docs/sa3_outcome_marginals.json", w / "tree/docs/sa3_outcome_marginals.json")
        assert SB.copy_linguist_cache(w)
        p = SB.run(["/usr/bin/python3", "-B", "tools/sa3_score.py", "placebo"], w, cwd=w / "tree", timeout=900)
        assert p.returncode == 0, p.stdout[-2000:] + p.stderr[-2000:]
        shutil.copyfile(w / "tree/docs/sa3_placebo.json", d / "docs/sa3_placebo.json")

    def variant(self, name: str) -> Path:
        d = self.base / "variants" / name
        shutil.copytree(self.dir, d, symlinks=True)
        return d


def run_job(decoy: Path, prot: Path, out: Path, *extra: str, strace: Path | None = None,
            timeout: int = 1800) -> subprocess.CompletedProcess:
    argv = [PY, "-B", str(PREPARE), "--decoy", str(decoy), "--protected", str(prot), "--out", str(out), *extra]
    if strace is not None:
        argv = ["strace", "-qq", "-e", "trace=open,openat,openat2,stat,newfstatat,statx,access,readlink",
                "-o", str(strace)] + argv
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)


def report(out: Path) -> dict:
    return json.loads((out / "owner_report.json").read_text())


@pytest.fixture(scope="session")
def decoy(tmp_path_factory):
    why = _skip_reason()
    if why:
        pytest.skip(why)
    base = tmp_path_factory.mktemp("ownerjob")
    if not _engine_present(base):
        pytest.skip("engine export not present")
    d = Decoy(base)
    d.build()
    return d


@pytest.fixture(scope="session")
def run1(decoy):
    """the ordinary run on the untouched decoy, the launcher under strace (no -f: its own syscalls only)"""
    b = decoy.base / "run1"
    st = b / "launcher.strace" if shutil.which("strace") else None
    b.mkdir()
    before = {"decoy": stat_of(decoy.dir / "docs/sa3_placebo.json"),
              "worktree": stat_of(ROOT / "docs/sa3_placebo.json")}
    p = run_job(decoy.dir, b / "prot", b / "pub", strace=st)
    return {"p": p, "prot": b / "prot", "pub": b / "pub", "strace": st, "before": before}


# ================================================================================ 1. refusals and the guard
def test_1a_refusals_before_anything(tmp_path, monkeypatch):
    """no target; --real without --i-am-the-owner; --decoy with --real; a protected directory that is not empty;
    one outside the protected root on a real run; a public directory inside the protected root, a data root or the
    protected directory; a decoy inside a data root; --code-root with --real; no answer or a wrong answer to the
    real run's question: exit 2, nothing created, bwrap never started"""
    marker = tmp_path / "bwrap-was-called"
    stub = tmp_path / "bwrap-stub"
    stub.write_text(f"#!/bin/sh\ntouch {marker}\n")
    stub.chmod(0o755)
    monkeypatch.setattr(SR, "BWRAP", str(stub))
    d = tmp_path / "decoy"
    for sub in ("study", "pool", "docs"):
        (d / sub).mkdir(parents=True)
    full = tmp_path / "full"
    full.mkdir()
    (full / "x").write_text("x")
    tp = tmp_path / "troot"
    tp.mkdir()
    prot, pub = tmp_path / "prot", tmp_path / "pub"
    asked = []

    def no(prompt):
        asked.append(prompt)
        raise EOFError

    cases = [[], ["--protected", str(prot), "--out", str(pub)],
             ["--real", "--protected", str(prot), "--out", str(pub)],
             ["--decoy", str(d), "--real", "--i-am-the-owner", "--protected", str(prot), "--out", str(pub)],
             ["--decoy", str(d), "--protected", str(full), "--out", str(pub)],
             ["--decoy", str(d), "--protected", str(prot), "--out", str(full)],
             ["--real", "--i-am-the-owner", "--protected", str(prot), "--out", str(pub)],       # not in the root
             ["--decoy", str(d), "--protected", str(prot), "--out", str(SR.PROTECTED_ROOT / "pub")],
             ["--decoy", str(d), "--protected", str(prot), "--out", str(tp / "pub")],
             ["--decoy", str(d), "--protected", str(prot), "--out", str(prot / "pub")],
             ["--decoy", str(d), "--protected", str(pub / "p"), "--out", str(pub)],
             ["--decoy", str(SR.LAWS / "x"), "--protected", str(prot), "--out", str(pub)],
             ["--decoy", str(d), "--protected", str(prot)],
             ["--real", "--i-am-the-owner", "--code-root", str(tmp_path), "--protected", str(tp / "r"),
              "--out", str(pub)],
             ["--real", "--i-am-the-owner", "--reference-git", str(tmp_path), "--protected", str(tp / "r"),
              "--out", str(pub)]]
    for bad in (SR.STUDY / "x", SR.POOL / "x", Path("/nvme-data/x"), SR.HOME / ".blind/x", P.TABLES_ROOT / "x"):
        cases.append(["--decoy", str(d), "--protected", str(prot), "--out", str(bad)])
    for bad in (SR.STUDY / "x", SR.WORKTREE / "x", SR.PROJECTS / "x", SR.PROTECTED_ROOT):
        cases.append(["--decoy", str(d), "--protected", str(bad), "--out", str(pub)])
    SR.name_protected_root_for_tests(tp)
    try:
        for argv in cases:
            assert P.main(argv, reader=no) == 2, argv
        assert not asked                                    # all refused before the question
        real = ["--real", "--i-am-the-owner", "--real-study", str(d / "study"), "--real-pool", str(d / "pool"),
                "--real-docs", str(d / "docs"), "--protected", str(tp / "run"), "--out", str(pub)]
        assert P.main(real, reader=no, echo=lambda *a: None) == 2 and len(asked) == 1
        assert P.main(real, reader=lambda _p: "no", echo=lambda *a: None) == 2
    finally:
        SR.name_protected_root_for_tests(None)
    assert not marker.exists()
    assert not prot.exists() and not pub.exists() and not (tp / "run").exists() and list(full.iterdir()) == [full / "x"]
    p = subprocess.run([PY, "-B", str(PREPARE)], capture_output=True, text=True)
    assert p.returncode == 2 and "no target" in p.stderr and "refused" in p.stderr
    p = subprocess.run([PY, "-B", str(PREPARE), "--real", "--protected", str(prot), "--out", str(pub)],
                       capture_output=True, text=True)
    assert p.returncode == 2 and "--i-am-the-owner" in p.stderr and not prot.exists()
    p = subprocess.run([PY, "-B", str(PREPARE), "--real", "--i-am-the-owner", "--protected",
                        str(SR.PROTECTED_ROOT / "x"), "--out", str(pub)], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL)               # no terminal: the question is never answered
    assert p.returncode == 2 and "refused" in p.stderr and not pub.exists()


def test_1b_production_defaults_guard_refuses_without_touching(tmp_path):
    """--real resolves to the production paths (strings only); a stage run outside the sandbox refuses first,
    and under strace no file syscall names the study directory, the pool, the protected root, /nvme-data or
    ~/.blind; in-process the guard opens /proc/self/mountinfo and nothing else"""
    a = type("A", (), {"decoy": None, "real": True, "i_am_the_owner": True, "code_root": None, "reference_git": None,
                       "real_study": str(SR.STUDY), "real_pool": str(SR.POOL), "real_docs": str(ROOT / "docs"),
                       "linguist": str(P.LINGUIST_HOST)})()
    tgt = P.resolve_target(a)
    assert tgt.real and tgt.study == SR.STUDY and tgt.pool == SR.POOL
    prot, _ = P.check_places(SR.PROTECTED_ROOT / "run-x", tmp_path / "pub", True)     # a string test
    assert prot == SR.PROTECTED_ROOT / "run-x"
    if not shutil.which("strace"):
        pytest.skip("strace not installed")
    rd = tmp_path / "rd"
    rd.mkdir()
    (rd / "args.json").write_text(json.dumps({"repo": "django", "repos": ["django"]}))
    log = tmp_path / "strace.log"
    for stage in sorted(P.STAGE_FUNCS):
        p = subprocess.run(["strace", "-f", "-qq", "-e", "trace=%file,%desc", "-o", str(log), PY, "-I", "-B",
                            str(PREPARE), "stage", stage, "--rundir", str(rd), "--args", str(rd / "args.json")],
                           capture_output=True, text=True, timeout=120)
        assert p.returncode != 0 and "refused" in p.stderr and "read-only sandbox" in p.stderr, p.stderr[-1500:]
        text = log.read_text()
        assert "/proc/self/mountinfo" in text
        for forbidden in (str(SR.LAWS), str(SR.POOL), str(SR.PROTECTED_ROOT), "/nvme-data", str(SR.HOME / ".blind"),
                          str(P.TABLES_ROOT)):
            assert forbidden not in text, f"{stage}: a syscall named {forbidden}"
        assert not (rd / "result.json").exists()
    opened = []
    real_open = builtins.open

    def spy(f, *k, **kw):
        opened.append(str(f))
        return real_open(f, *k, **kw)
    builtins.open = spy
    try:
        with pytest.raises(SR.SandboxError):
            SR.assert_inside_ro()
    finally:
        builtins.open = real_open
    assert opened == ["/proc/self/mountinfo"], opened


def test_1c_protected_root_in_sandbox_ro(tmp_path):
    """the listed change: the production root is a constant outside every data root and session scratch root;
    directories strictly inside it are writable locations (strings only: it is never created here); a test may
    name another root only under a session scratch root; a test root's directory is writable inside a sandbox
    that binds it and invisible to one that does not"""
    R = SR.PROTECTED_ROOT
    assert R == Path("/srv/storage_16tb/projects/temporal-crucible-protected")
    for bad in SR.FORBIDDEN + (SR.WORKTREE,) + SR.ALLOWED_RW_ROOTS:
        assert not (R == bad or bad in R.parents or R in bad.parents), bad
    assert SR.check_rw(R / "run-1") == R / "run-1"
    for bad in (R, SR.PROJECTS / "elsewhere", SR.STUDY / "x", SR.WORKTREE / "x", SR.POOL / "x"):
        with pytest.raises(SR.SandboxError):
            SR.check_rw(bad)
    argv = SR.bwrap_argv(SR.Spec(rw=[R / "run-1"], code=[]), {})
    i = argv.index("--bind")
    assert argv[i:i + 3] == ["--bind", str(R / "run-1"), str(R / "run-1")]
    assert argv.index("--bind") > argv.index(str(SR.PROJECTS))             # bound after the projects tmpfs
    for bad in (SR.STUDY, SR.WORKTREE / "t", Path("/srv/storage_16tb/x"), R / "t"):
        with pytest.raises(SR.SandboxError):
            SR.name_protected_root_for_tests(bad)
    assert SR.protected_roots() == (R,)
    if not Path(SR.BWRAP).exists():
        pytest.skip("bwrap not installed")
    root = tmp_path / "proot"
    run = root / "run"
    run.mkdir(parents=True)
    other = tmp_path / "other"
    other.mkdir()
    SR.name_protected_root_for_tests(root)
    try:
        assert SR.in_protected_root(run) and not SR.in_protected_root(root)
        code = tmp_path / "code"
        shutil.copytree(ROOT / "tools", code / "tools", ignore=shutil.ignore_patterns("__pycache__"))
        probe = ("import os,sys,json; p=sys.argv[1]; open(os.path.join(p,'w.txt'),'w').write('x'); "
                 "print(json.dumps(sorted(os.listdir(p))))")
        q = SR.run(["/usr/bin/python3", "-I", "-B", "-c", probe, str(run)],
                   SR.Spec(rw=[run, other], code=[code], cwd=other), other, other, timeout=60)
        assert q.returncode == 0 and json.loads(q.stdout) == ["w.txt"], q.stdout + q.stderr
        hid = ("import os,sys; print(os.path.exists(sys.argv[1]), os.path.exists(sys.argv[2]))")
        q = SR.run(["/usr/bin/python3", "-I", "-B", "-c", hid, str(run), str(run / "w.txt")],
                   SR.Spec(rw=[other], code=[code], cwd=other), other, other, timeout=60)
        assert q.returncode == 0 and q.stdout.split() == ["False", "False"], q.stdout + q.stderr
    finally:
        SR.name_protected_root_for_tests(None)


# ===================================================================================== 2. the decoy run
def test_2a_pass_on_the_untouched_decoy(run1, decoy):
    """PASS as the last terminal line and the report's first line; the terminal holds stage, repo, ok|failed
    lines and the report's path only; the public directory holds the four files"""
    p = run1["p"]
    assert p.returncode == 0, p.stdout[-3000:] + p.stderr[-3000:]
    lines = p.stdout.splitlines()
    assert lines[-1] == "PASS"
    assert lines[-2] == f"report: {run1['pub'] / 'owner_report.md'}"
    for ln in lines[:-2]:
        stage, repo, status = ln.split(" ")
        assert stage in RP.STAGES and (repo == "*" or repo in REPOS) and status in ("ok", "failed"), ln
    assert p.stderr == ""
    assert sorted(os.listdir(run1["pub"])) == ["owner_report.json", "owner_report.md", "run_log.json", "seal.json"]
    assert (run1["pub"] / "owner_report.md").read_text().splitlines()[0] == "PASS"
    rep = report(run1["pub"])
    assert rep["verdict"] == "PASS" and rep["codes"] == [] and rep["placebo"]["verdict"] == "bytes_equal"
    assert set(rep["repos"]) == set(REPOS)
    log = json.loads((run1["pub"] / "run_log.json").read_text())
    assert log["complete"] and log["last_stage"] == "report" and all(s["status"] == "ok" for s in log["stages"])
    assert oct(run1["prot"].stat().st_mode & 0o777) == "0o700"
    print(f"\ndecoy run: {rep['seconds']} s; terminal:\n" + p.stdout)


def test_2b_count_against_planted_commits(run1, decoy):
    """every planted case has its expected verdict (A - A', read here from the protected directory of a decoy
    run); the published counts are those numbers; A equals the stored file; no pattern disagreement"""
    rep = report(run1["pub"])
    for r in REPOS:
        det = json.loads((run1["prot"] / "runs/count" / r / "count_detail.json").read_text())
        got = set(det["a_minus_aprime"])
        stored = json.loads((decoy.dir / "study/sa3_outcomes" / f"{r}.json").read_text())["outcomes"]["HP"]["commits"]
        for name, (sha, want) in decoy.planted[r].items():
            assert (sha in got) == want, (r, name)
            if not name.startswith(("K", "T7")):
                assert sha in stored, (r, name, "planted commit is not a positive at all")
        assert got <= {s for s, w in decoy.planted[r].values() if w}, "a generated commit is in the count"
        assert det["aprime_minus_a"] == [] and det["a_equals_stored"]
        row = rep["repos"][r]
        assert row == {"determined": True, "reason": "none", "count": sum(w for _s, w in decoy.planted[r].values()),
                       "a_equals_stored": True, "disagreements": 0}, row
        print(f"\n{r}:", {n: ("counted" if s in got else "not counted") for n, (s, _w) in decoy.planted[r].items()})
    cp = json.loads((run1["prot"] / "runs/copy/ctrl-base/detail.json").read_text())["aprime"]
    assert cp["meta_kept"] and cp["left_rows"] == 0 and cp["deleted_rows"] >= 5


def test_2c_hyphen_rule_against_the_reference_pattern(tmp_path):
    """inside a sandbox: the reference extract_links and RX themselves (imported, not copied): a stored fix
    reference has a hyphen exactly when the pattern's key alternative matched, on made-up messages of every
    alternative; and tools/owner holds no copy of hist_meta's patterns"""
    if not Path(SR.BWRAP).exists():
        pytest.skip("bwrap not installed")
    code = tmp_path / "code"
    shutil.copytree(ROOT / "tools", code / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    script = r"""
import sys, json
sys.path.insert(0, sys.argv[1] + "/tools/harness"); import sandbox_ro as SR; SR.assert_inside_ro()
sys.path.insert(0, sys.argv[1] + "/tools/owner"); sys.path.insert(0, sys.argv[1] + "/tools")
import hist_meta as HM, tracker_keys as TK
msgs = ["fix x86-64 build", "Fixes #12", "fixed GH-7", "resolves bug #9", "fix bpo-3311", "Fixes PR 1234",
        "Resolves: PROJ-42", "Fix UTF-8 decoding", "Fixed sha-1 fallback", "GnuPG-bug-id: 5512", "Fixes: deadbeef",
        "Fixes: deadbeef-1", "fix i_8-9 and fixes #3", "x\n\nFixes: 0123abcd\n", "x\n\nFixes: utf-8 handling\n"]
bad, rows = 0, []
for i, m in enumerate(msgs):
    subj, _, body = m.partition("\n")
    for _s, kind, v in HM.extract_links(str(i), subj, body.strip(), sa3_links=True):
        if kind == "issue_fix":
            rows.append(v)
    for mm in HM.RX["issue_fix_sa3"].finditer(subj + "\n" + body.strip()):
        val = next(g for g in mm.groups() if g is not None)
        bad += ("-" in val) != (mm.lastindex == 2)
print(json.dumps({"bad": bad, "lower": sorted(v for v in rows if TK.is_lower_key(v)), "rows": sorted(rows)}))
"""
    q = SR.run(["/usr/bin/python3", "-I", "-B", "-c", script, str(code)], SR.Spec(rw=[tmp_path], code=[code],
               cwd=tmp_path), tmp_path, tmp_path, timeout=60)
    assert q.returncode == 0, q.stdout + q.stderr
    r = json.loads(q.stdout)
    assert r["bad"] == 0
    assert r["lower"] == ["deadbeef-1", "i_8-9", "sha-1", "utf-8", "x86-64"], r
    assert "UTF-8" in r["rows"] and "PROJ-42" in r["rows"]          # capitals stay in A'
    tree = ast.parse((ROOT / "tools" / "hist_meta.py").read_text())
    pats = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and len(n.value) > 12 and "\\" in n.value}
    assert len(pats) >= 5
    for f in OWNER.glob("*.py"):
        strs = {n.value for n in ast.walk(ast.parse(f.read_text())) if isinstance(n, ast.Constant)
                and isinstance(n.value, str)}
        assert not [s for s in strs for x in pats if x in s], f.name


def test_2d_placebo_twice_and_the_committed_file_never_written(run1, decoy):
    """bytes_equal on the untouched decoy, twice in a row; the committed file (the decoy's, and this checkout's)
    keeps its bytes and its modification time; the copy the stage ran from was byte-identical to the code root"""
    b = decoy.base / "run2"
    p = run_job(decoy.dir, b / "prot", b / "pub")
    assert p.returncode == 0 and p.stdout.splitlines()[-1] == "PASS", p.stdout[-2000:]
    for out in (run1["pub"], b / "pub"):
        pl = report(out)["placebo"]
        assert pl["verdict"] == "bytes_equal" and pl["numbers_differing"] == 0 and pl["integer_fields_equal"]
    assert stat_of(decoy.dir / "docs/sa3_placebo.json") == run1["before"]["decoy"]
    assert stat_of(ROOT / "docs/sa3_placebo.json") == run1["before"]["worktree"]
    regen = run1["prot"] / "ref/docs/sa3_placebo.json"
    assert regen.read_bytes() == (decoy.dir / "docs/sa3_placebo.json").read_bytes()
    want = P.tree_hashes(ROOT / "tools")
    assert P.tree_hashes(run1["prot"] / "ref/tools") == want and P.tree_hashes(run1["prot"] / "code/tools") == want
    seal = json.loads((run1["pub"] / "seal.json").read_text())
    for m, v in seal["code"].items():
        assert v["sha256"] == want[f"{m}.py"] and v["unchanged_since_8fb7fe0"], m


def test_2e_import_recorder_and_seal_contents(run1, decoy):
    rep = report(run1["pub"])
    seal = json.loads((run1["pub"] / "seal.json").read_text())
    found = rep["seal"]["code_modules_found"]
    print("\nmodules the import recorder found:", found)
    assert set(found) == set(P.EXPECTED_MODULES), found
    assert set(seal["code"]) == set(found) | {"hist_meta"}
    assert set(seal["inputs"]) == set(REPOS)
    for r in REPOS:
        x = seal["inputs"][r]
        assert set(x) == set(RP.ROLES) and "scan_db-shm" not in x
        assert all(x[k] for k in ("history", "scan_db", "scan_db-wal", "scan_sidecar", "harvest", "outcome",
                                  "nesting")), x
        assert seal["clones"][r]["head_sha256"]
    sealed = P.sealed_list(ROOT / "tools/sa3_score.py")
    assert len(sealed) == 9 and set(seal["lock_expected"]) == set(sealed)
    for f, h in seal["lock_expected"].items():                 # as `git hash-object` (the reference blob()) gives
        src = ROOT / f if f.startswith("tools/") else decoy.dir / f
        assert h == subprocess.run(["git", "hash-object", str(src)], capture_output=True, text=True).stdout.strip(), f
    assert set(seal["documents"]) == set(RP.DOCUMENTS) and all(v["sha256"] for v in seal["documents"].values())
    rt = seal["runtime"]
    assert rt["python"] and "numpy" in rt["packages"] and rt["libraries"] and rt["git"] and rt["tar"]
    assert rep["manifest"]["unchanged"] is True and rep["manifest"]["entries"] > 0
    assert rep["seal"]["written"] and rep["seal"]["modules_unchanged_since_8fb7fe0"] is True
    text = json.dumps(seal)
    for r in REPOS:                     # no size of a label-side file anywhere public
        for role in ("outcome", "harvest"):
            f = decoy.dir / "study" / ("sa3_outcomes" if role == "outcome" else "meta_sa3") / \
                (f"{r}.json" if role == "outcome" else f"{r}.db")
            assert not re.search(rf"\b{f.stat().st_size}\b", all_text(run1["pub"])), (r, role)
    assert not re.search(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])",
                         json.dumps({k: v for k, v in seal.items() if k not in ("code", "documents", "lock_expected")}))
    assert "/" not in json.dumps(report(run1["pub"])).replace("docs/sa3", "")


# ===================================================================================== 3. failure verdicts
def test_3a_not_determined(decoy):
    """a repo whose clone cannot serve the archive (build() says scan_incomplete) and a repo whose harvest copy
    has no meta rows (build() tries to re-harvest and the read-only bind refuses): not determined, with a code,
    never zero; FAIL count_not_determined; the placebo (on the other repos) still bytes_equal"""
    d = decoy.variant("notdet")
    st = d / "study"
    marg = json.loads((d / "docs/sa3_outcome_marginals.json").read_text())
    base = next(r for r in marg if r["repo"] == "ctrl-base")
    for new in ("ctrl-blobless", "ctrl-nometa"):
        for sub, sfx in (("history", ".db"), ("sa3_scans", ".json"), ("sa3_scans", "_master.db"),
                         ("sa3_scans", "_master.db-wal"), ("sa3_scans", "_master.db-shm"),
                         ("sa3_outcomes", ".json"), ("meta_sa3", ".db"), ("sa3_nesting", ".json")):
            if (st / sub / f"ctrl-base{sfx}").exists():
                shutil.copy2(st / sub / f"ctrl-base{sfx}", st / sub / f"{new}{sfx}")
        marg.append({**base, "repo": new, "HP": {**base["HP"], "clears_floor": False}})
    shutil.copytree(d / "pool/ctrl-base", d / "pool/ctrl-nometa", symlinks=True)
    subprocess.run(["git", "-c", "gc.auto=0", "clone", "-q", "--filter=blob:none", "--no-checkout",
                    "--upload-pack=git -c uploadpack.allowFilter=true upload-pack", f"file://{d / 'pool/ctrl-base'}",
                    str(d / "pool/ctrl-blobless")], check=True, capture_output=True,
                   env={**os.environ, "GIT_NO_LAZY_FETCH": "1"})
    con = sqlite3.connect(str(st / "meta_sa3/ctrl-nometa.db"))
    con.execute("delete from meta")
    con.commit()
    con.close()
    (d / "docs/sa3_outcome_marginals.json").write_text(json.dumps(marg, indent=1) + "\n")
    b = decoy.base / "run-notdet"
    p = run_job(d, b / "prot", b / "pub")
    assert p.returncode == 1 and p.stdout.splitlines()[-1] == "FAIL count_not_determined", p.stdout[-2000:]
    rep = report(b / "pub")
    assert rep["repos"]["ctrl-blobless"] == {"determined": False, "reason": "scan_incomplete", "count": None,
                                             "a_equals_stored": None, "disagreements": None}
    assert rep["repos"]["ctrl-nometa"]["determined"] is False and rep["repos"]["ctrl-nometa"]["count"] is None
    assert rep["repos"]["ctrl-nometa"]["reason"] == "write_refused", rep["repos"]["ctrl-nometa"]
    assert rep["repos"]["ctrl-base"]["count"] == 4 and rep["placebo"]["verdict"] == "bytes_equal"
    assert (st / "meta_sa3/ctrl-nometa.db").exists()                     # the refused unlink: nothing deleted


def test_3b_placebo_differs_when_one_scan_value_changes(decoy):
    d = decoy.variant("differs")
    db = d / "study/sa3_scans/ctrl-base_master.db"
    con = sqlite3.connect(str(db))
    fid = con.execute("select id from file_data where total_loc > 0 and file_path like 'src/%.py' order by id "
                      "limit 1").fetchone()[0]
    con.execute("update file_data set total_loc = total_loc + 997 where id = ?", (fid,))
    con.commit()
    con.close()
    b = decoy.base / "run-differs"
    p = run_job(d, b / "prot", b / "pub")
    assert p.returncode == 1 and p.stdout.splitlines()[-1] == "FAIL placebo_differs", p.stdout[-2000:]
    pl = report(b / "pub")["placebo"]
    assert pl["verdict"] == "differs" and pl["numbers_differing"] > 0 and pl["largest_difference"] > 1e-9
    assert report(b / "pub")["repos"]["ctrl-base"]["count"] == 4             # the count does not read the value
    assert (b / "pub/owner_report.md").read_text().splitlines()[0] == "FAIL"


def test_3c_placebo_failed_when_an_input_is_missing(decoy):
    d = decoy.variant("missing")
    (d / "study/sa3_outcomes/ctrl-mw.json").unlink()
    b = decoy.base / "run-missing"
    p = run_job(d, b / "prot", b / "pub")
    assert p.returncode == 1, p.stdout[-2000:]
    assert p.stdout.splitlines()[-1] == "FAIL count_not_determined placebo_failed"
    rep = report(b / "pub")
    assert rep["placebo"]["verdict"] == "failed" and rep["placebo"]["code"] == "input_missing"
    assert rep["repos"]["ctrl-mw"]["reason"] == "input_missing" and rep["repos"]["ctrl-mw"]["count"] is None
    assert rep["seal"]["written"]                                            # an absent input is sealed as absent
    assert json.loads((b / "pub/seal.json").read_text())["inputs"]["ctrl-mw"]["outcome"] is None


# ============================================================================================ 4. the seal
def _verify(decoy_dir: Path, seal: Path, prot: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run([PY, "-B", str(SEAL), "verify", "--seal", str(seal), "--protected", str(prot), "--decoy",
                           str(decoy_dir), *extra], capture_output=True, text=True, timeout=600)


def _reference_lock(tmp: Path, decoy_dir: Path, as_git: bool) -> Path:
    """the reference `sa3_score.py lock`, unchanged, inside the read-only sandbox, from a throwaway root holding
    tools/ and the decoy's documents: committed to a git repository (a correct lock), or carrying the `.git` file
    of a linked worktree whose main repository is not there, as this checkout's would be in a sandbox that does
    not bind it: git then fails, and `blob()` returns empty strings (defect 57)"""
    r = tmp / ("lockroot-git" if as_git else "lockroot-broken")
    shutil.copytree(ROOT / "tools", r / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(decoy_dir / "docs", r / "docs")
    if as_git:
        git(r, "init", "-q")
        git(r, "add", "-A")
        git(r, "commit", "-q", "-m", "lock root")
    else:
        (r / ".git").write_text(f"gitdir: {tmp / 'no-such-main-repository' / 'worktrees' / 'x'}\n")
    h = tmp / ("home-" + r.name)
    h.mkdir()
    P.write_gitconfig(h)
    guard = tmp / "guard-code"
    if not guard.exists():
        shutil.copytree(ROOT / "tools", guard / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    q = SR.run(["/usr/bin/python3", "-I", "-B", str(r / "tools/sa3_score.py"), "lock"],
               SR.Spec(rw=[r, h], code=[guard], cwd=r), h, h, timeout=300)
    assert q.returncode == 0, q.stdout + q.stderr
    return r / "docs/sa3_lock.json"


def test_4_seal_verify(run1, decoy, tmp_path):
    """verifies on unchanged inputs; after a -shm is touched by an ordinary read; a changed input, module or
    document is named; --after-lock passes against the reference lock written in a git checkout and fails
    against the one it writes where git fails (empty hashes)"""
    d = decoy.variant("seal")
    b = decoy.base / "run-seal"
    assert run_job(d, b / "prot", b / "pub").returncode == 0
    s = b / "pub/seal.json"
    v = _verify(d, s, tmp_path / "v0")
    assert v.returncode == 0 and v.stdout.splitlines()[-1] == "VERIFIED", v.stdout + v.stderr
    db = d / "study/sa3_scans/ctrl-base_master.db"
    shm = Path(str(db) + "-shm")
    before = (shm.read_bytes(), shm.stat().st_mtime_ns) if shm.exists() else None
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)                 # as SA3 readers open it
    con.execute("select count(*) from file_data").fetchone()
    con.close()
    assert shm.exists() and (shm.read_bytes(), shm.stat().st_mtime_ns) != before    # the read touched it
    v = _verify(d, s, tmp_path / "v1")
    assert v.returncode == 0 and v.stdout.splitlines()[-1] == "VERIFIED", v.stdout
    # the reference lock: correct in a git checkout, empty hashes where git fails
    good = _reference_lock(tmp_path, d, True)
    empty = _reference_lock(tmp_path, d, False)
    assert set(json.loads(empty.read_text())["files"].values()) == {""}
    assert json.loads(empty.read_text())["sealed_at_commit"] == ""
    assert json.loads(good.read_text())["files"] == json.loads(s.read_text())["lock_expected"]
    shutil.copyfile(good, d / "docs/sa3_lock.json")
    v = _verify(d, s, tmp_path / "v2", "--after-lock")
    assert v.returncode == 0 and v.stdout.splitlines()[-1] == "VERIFIED", v.stdout
    shutil.copyfile(empty, d / "docs/sa3_lock.json")
    v = _verify(d, s, tmp_path / "v3", "--after-lock")
    assert v.returncode == 1 and v.stdout.splitlines()[-1] == "DIFFERS 9", v.stdout
    assert {ln for ln in v.stdout.splitlines() if ln.startswith("differs: ")} == \
        {f"differs: lock.{f}" for f in P.sealed_list(ROOT / "tools/sa3_score.py")}
    (d / "docs/sa3_lock.json").unlink()
    # a changed input, a changed document, a changed module: each named
    of = d / "study/sa3_outcomes/ctrl-mw.json"
    of.write_text(of.read_text() + " ")
    v = _verify(d, s, tmp_path / "v4")
    assert v.returncode == 1 and "differs: inputs.ctrl-mw.outcome" in v.stdout.splitlines(), v.stdout
    pw = d / "docs/sa3_power.md"
    pw.write_text(pw.read_text() + "\n")
    v = _verify(d, s, tmp_path / "v5")
    out = v.stdout.splitlines()
    assert "differs: documents.sa3_power.md.sha256" in out and "differs: lock_expected.docs/sa3_power.md" in out
    cr = tmp_path / "coderoot"
    shutil.copytree(ROOT / "tools", cr / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    f = cr / "tools/sa3_stats.py"
    f.write_text(f.read_text() + "\n# one changed line\n")
    v = _verify(d, s, tmp_path / "v6", "--code-root", str(cr))
    out = v.stdout.splitlines()
    for name in ("code.sa3_stats.sha256", "code.sa3_stats.blob", "code.sa3_stats.unchanged_since_8fb7fe0",
                 "lock_expected.tools/sa3_stats.py"):
        assert f"differs: {name}" in out, v.stdout


# ======================================================================== 5. no way out for label-side text
PATCHES = {
    "raise": "    raise RuntimeError(_marks(stored_file))\n",
    "print": "    print(_marks(stored_file)); print(_marks(stored_file), file=sys.stderr)\n"
             "    _probe(rest[-1])\n    return _orig(repo, a_file, ap_file, stored_file, *rest)\n",
    "write": "    r = _orig(repo, a_file, ap_file, stored_file, *rest)\n    r['count'] = _marks(stored_file)[:40]\n"
             "    return r\n",
}


def _patched_code_root(tmp: Path, mode: str, public: Path) -> Path:
    """a copy of tools/ whose count stage misbehaves with text read from the label side; the reference files are
    untouched (only tools/owner/tracker_keys.py differs)"""
    cr = tmp / f"code-{mode}"
    shutil.copytree(ROOT / "tools", cr / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    f = cr / "tools/owner/tracker_keys.py"
    f.write_text(f.read_text() + f"""

_orig = count_stage


def _marks(stored_file):
    o = json.loads(Path(stored_file).read_text())["outcomes"]
    keys = [k for k in o["HP"]["commits"] if k.startswith("c0ffee")] + list(o["control_pool"]["commits"])
    paths = [p for v in o["control_pool"]["commits"].values() for p in v if p.startswith("zz_")]
    return " ".join([k for k in keys if k.startswith(("c0ffee", "d00d"))] + paths)


def _probe(detail_file):
    import os
    pub = {str(public)!r}
    res = {{"public_exists": os.path.exists(pub)}}
    try:
        open(os.path.join(pub, "leak.txt"), "w").write("x")
        res["public_write"] = "SUCCEEDED"
    except OSError as e:
        res["public_write"] = type(e).__name__
    Path(str(detail_file) + ".probe.json").write_text(json.dumps(res))


def count_stage(repo, a_file, ap_file, stored_file, *rest):
{PATCHES[mode]}""")
    return cr


def _marked_decoy(decoy) -> Path:
    d = decoy.variant("marked")
    st = d / "study"
    of = st / "sa3_outcomes/ctrl-base.json"
    o = json.loads(of.read_text())
    real = o["outcomes"]["HP"]["files"][0]
    o["outcomes"]["HP"]["commits"][MARK_SHA] = [real]                        # a commit hash occurring nowhere else
    o["outcomes"]["control_pool"]["commits"][MARK_SHA2] = [MARK_PATH]       # a path no universe holds: KeyError
    of.write_text(json.dumps(o) + "\n")
    con = sqlite3.connect(str(st / "meta_sa3/ctrl-base.db"))
    con.execute("insert into link (sha, kind, value) values (?, 'issue_fix', ?)", (MARK_SHA, MARK_VAL))
    con.execute("insert into body (sha, subject, body) values (?, ?, ?)", (MARK_SHA, f"fix {MARK_VAL}", MARK_PATH))
    con.commit()
    con.close()
    return d


def _no_marker(p: subprocess.CompletedProcess, pub: Path) -> None:
    text = all_text(pub) + p.stdout + p.stderr
    for m in MARKERS:
        assert m not in text, m


def _launcher_never_reads_logs_nor_touches_study(strace: Path | None, d: Path) -> None:
    if strace is None:
        return
    lines = strace.read_text().splitlines()
    logs = [ln for ln in lines if "stage.log" in ln]
    assert logs and all("O_WRONLY" in ln for ln in logs if "open" in ln), logs[:5]
    assert not [ln for ln in logs if not ln.startswith(("open", "openat"))], logs[:5]
    for x in (str(d / "study"), str(d / "pool")):
        bad = [ln for ln in lines if x in ln and "execve" not in ln]
        assert not bad, bad[:5]


@pytest.fixture(scope="session")
def marked(decoy):
    return _marked_decoy(decoy)


def test_5a_markers_normal_run(decoy, marked):
    """markers in a decoy's outcome file and harvest: the run fails (A no longer equals the stored file; the
    reference loader raises a KeyError whose text is the marker path) and no marker reaches the public
    directory or the terminal; the marker path is in the protected stage log, so the test is live"""
    d = marked
    b = decoy.base / "run-marked"
    st = b / "launcher.strace" if shutil.which("strace") else None
    b.mkdir()
    p = run_job(d, b / "prot", b / "pub", strace=st)
    assert p.returncode == 1, p.stdout[-2000:]
    rep = report(b / "pub")
    assert rep["repos"]["ctrl-base"]["a_equals_stored"] is False and rep["repos"]["ctrl-base"]["count"] is None
    assert rep["placebo"] == {**rep["placebo"], "verdict": "failed", "code": "key_error"}
    assert p.stdout.splitlines()[-1] == "FAIL a_differs_from_stored placebo_failed"
    _no_marker(p, b / "pub")
    assert MARK_PATH in (b / "prot/runs/placebo/all/stage.log").read_text()
    _launcher_never_reads_logs_nor_touches_study(st, d)


@pytest.mark.parametrize("mode", ["raise", "print", "write"])
def test_5b_markers_misbehaving_stage(decoy, marked, tmp_path, mode):
    """a stage that raises an exception whose message is the markers, one that prints them (stdout and stderr)
    and probes the public directory, one that writes a marker where an integer is expected: no marker in the
    public directory or on the terminal; the last is stopped with 'invalid report value' and the field name"""
    d = marked
    b = tmp_path / "run"
    b.mkdir()
    st = b / "launcher.strace" if shutil.which("strace") else None
    cr = _patched_code_root(tmp_path, mode, b / "pub")
    p = run_job(d, b / "prot", b / "pub", "--code-root", str(cr), strace=st)
    assert p.returncode == 1, p.stdout[-2000:] + p.stderr[-2000:]
    _no_marker(p, b / "pub")
    _launcher_never_reads_logs_nor_touches_study(st, d)
    log = (b / "prot/runs/count/ctrl-base/stage.log").read_text()
    rep = report(b / "pub")
    if mode == "raise":
        assert MARK_SHA in log and MARK_PATH in log                         # in the protected log only
        assert rep["repos"]["ctrl-base"]["reason"] == "unclassified"
    elif mode == "print":
        assert log.count(MARK_SHA) >= 2
        probe = json.loads((b / "prot/runs/count/ctrl-base/count_detail.json.probe.json").read_text())
        assert probe == {"public_exists": False, "public_write": probe["public_write"]}
        assert probe["public_write"] != "SUCCEEDED" and not (b / "pub/leak.txt").exists()
    else:
        assert "invalid report value: count.result.count" in p.stdout
        assert p.stdout.splitlines()[-1] == "FAIL invalid_report_value"
        assert rep["codes"] == ["invalid_report_value"]
        assert json.loads((b / "pub/run_log.json").read_text())["invalid_in_stage"] == ["count"]


def test_5c_validator_rejects_paths_hashes_free_text():
    """the validator alone: a path, a 40-character hash, free text, an unknown key, a marker as a repo name, a
    boolean as a count; each rejected with the field's name and never the value"""
    vocab = RP.Vocab(repos=frozenset(REPOS), modules=frozenset({"sa3_score"}), packages=frozenset({"numpy"}),
                     sealed=frozenset({"tools/sa3_score.py"}))
    good = {"determined": True, "reason": "none", "count": 3, "a_equals_stored": True, "disagreements": 0}
    RP.check(("map", "repo", RP.REPO_ROW), {"ctrl-base": good}, "repos", vocab)
    bad = [({"ctrl-base": {**good, "reason": "/srv/x/" + MARK_PATH}}, "repos.<repo>.reason"),
           ({"ctrl-base": {**good, "count": MARK_SHA}}, "repos.<repo>.count"),
           ({"ctrl-base": {**good, "reason": "the file was not found"}}, "repos.<repo>.reason"),
           ({"ctrl-base": {**good, "extra": 1}}, "repos.<repo>"),
           ({MARK_PATH: good}, "repos.<repo>"),
           ({MARK_VAL: good}, "repos.<repo>"),
           ({"ctrl-base": {**good, "count": True}}, "repos.<repo>.count"),
           ({"ctrl-base": {**good, "count": -1}}, "repos.<repo>.count")]
    for value, field in bad:
        with pytest.raises(RP.ReportError) as e:
            RP.check(("map", "repo", RP.REPO_ROW), value, "repos", vocab)
        assert str(e.value) == f"invalid report value: {field}"
        for m in MARKERS:
            assert m not in str(e.value)
    for kind, v in (("hex64", MARK_SHA), ("hex64", "/x"), ("version", MARK_VAL), ("lib", MARK_PATH),
                    ("real", float("nan")), ("module", "evil"), ("package", MARK_VAL), ("sealed", "tools/x.py"),
                    ("envval", MARK_PATH), ("word:stage_code", "KeyError: " + MARK_PATH)):
        with pytest.raises(RP.ReportError):
            RP.leaf(kind, v, "f", vocab)
    with pytest.raises(RP.ReportError):          # a 40-character hash is allowed only under the seal's blob keys
        RP.check(RP.SEAL["clones"], {"ctrl-base": {"head_sha256": MARK_SHA}}, "seal.clones", vocab)


# ========================================================================= 6. the real path on throwaways
def test_6_real_path_with_throwaway_locations(decoy, run1, tmp_path, capsys):
    """--real --i-am-the-owner with the location parameters naming the decoy and a test-named protected root:
    it prints what it will bind and write, waits for Enter (an injected reader), then runs exactly the decoy
    code path and passes"""
    d = decoy.dir
    root = tmp_path / "proot"
    root.mkdir()
    asked = []
    SR.name_protected_root_for_tests(root)
    try:
        rc = P.main(["--real", "--i-am-the-owner", "--real-study", str(d / "study"), "--real-pool", str(d / "pool"),
                     "--real-docs", str(d / "docs"), "--protected", str(root / "run1"), "--out", str(tmp_path / "pub")],
                    reader=lambda prompt: asked.append(prompt) or "")
    finally:
        SR.name_protected_root_for_tests(None)
    out = capsys.readouterr().out.splitlines()
    assert rc == 0 and out[-1] == "PASS" and len(asked) == 1, out[-5:]
    assert "It does not score SA3." in out[0] and any("Press Enter" in x for x in out)
    assert report(tmp_path / "pub")["target"] == "real"
    a = json.loads((tmp_path / "pub/seal.json").read_text())
    b = json.loads((run1["pub"] / "seal.json").read_text())
    assert a["inputs"] == b["inputs"] and a["code"] == b["code"] and a["lock_expected"] == b["lock_expected"]


# ================================================================ 7. the frozen reference code (owner ruling)
def test_7a_one_byte_of_a_reference_module_changed(decoy, run1, tmp_path):
    """a code root whose sa3_stats.py differs from 8fb7fe0 by one byte (in its docstring, so the placebo output
    does not move): FAIL reference_code_changed; the seal section says no; no module name is added to the report"""
    cr = tmp_path / "coderoot"
    shutil.copytree(ROOT / "tools", cr / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    f = cr / "tools/sa3_stats.py"
    data = f.read_bytes()
    i = data.index(b'"""') + 3
    f.write_bytes(data[:i] + (b"X" if data[i:i + 1] != b"X" else b"Y") + data[i + 1:])
    assert len(f.read_bytes()) == len(data)
    b = tmp_path / "run"
    p = run_job(decoy.dir, b / "prot", b / "pub", "--code-root", str(cr))
    assert p.returncode == 1 and p.stdout.splitlines()[-1] == "FAIL reference_code_changed", p.stdout[-2000:]
    rep = report(b / "pub")
    assert rep["seal"]["modules_unchanged_since_8fb7fe0"] is False and rep["placebo"]["verdict"] == "bytes_equal"
    assert "Unchanged since 8fb7fe0: no." in (b / "pub/owner_report.md").read_text()
    assert rep["seal"]["code_modules_found"] == report(run1["pub"])["seal"]["code_modules_found"]
    seal = json.loads((b / "pub/seal.json").read_text())
    assert [m for m, v in seal["code"].items() if not v["unchanged_since_8fb7fe0"]] == ["sa3_stats"]


def test_7b_reference_code_cannot_be_checked(decoy, tmp_path):
    """the reference commit cannot be looked up (a directory that is no git checkout): FAIL
    reference_code_unchecked, the seal section says n/a"""
    nogit = tmp_path / "not-a-checkout"
    nogit.mkdir()
    b = tmp_path / "run"
    p = run_job(decoy.dir, b / "prot", b / "pub", "--reference-git", str(nogit))
    assert p.returncode == 1 and p.stdout.splitlines()[-1] == "FAIL reference_code_unchecked", p.stdout[-2000:]
    rep = report(b / "pub")
    assert rep["seal"]["modules_unchanged_since_8fb7fe0"] is None and rep["seal"]["written"]
    assert "Unchanged since 8fb7fe0: n/a." in (b / "pub/owner_report.md").read_text()
    code = json.loads((b / "pub/seal.json").read_text())["code"]
    assert all(v["unchanged_since_8fb7fe0"] is None for v in code.values())


# ================================================================= 8. the real path in a fresh interpreter
def _with_terminal(argv: list[str], env: dict, answer: bytes) -> tuple[int, str, str]:
    """run argv with a pseudo-terminal as standing input, the answer already typed into it"""
    import pty
    master, slave = pty.openpty()
    try:
        os.write(master, answer)
        p = subprocess.run(argv, stdin=slave, capture_output=True, text=True, env=env, timeout=1800)
    finally:
        os.close(slave)
        os.close(master)
    return p.returncode, p.stdout, p.stderr


def test_8_real_path_in_a_fresh_process(decoy, run1, tmp_path):
    """`prepare.py --real --i-am-the-owner` as the owner will type it, in a new interpreter: throwaway locations,
    a protected root named by OWNER_JOB_TEST_PROTECTED_ROOT (honoured only under pytest's temporary directory or
    ~/.claude/jobs), and Enter typed into a pseudo-terminal. Nothing from this process is needed. The protected root
    does not exist beforehand, so the job creates it (mode 700). Then `seal.py verify --real` the same way."""
    d = decoy.dir
    root = tmp_path / "proot"                                         # created by the job
    env = {**os.environ, P.TEST_ROOT_ENV: str(root)}
    real = ["--real", "--i-am-the-owner", "--real-study", str(d / "study"), "--real-pool", str(d / "pool"),
            "--real-docs", str(d / "docs")]
    rc, out, err = _with_terminal([PY, "-B", str(PREPARE), *real, "--protected", str(root / "run1"),
                                   "--out", str(tmp_path / "pub")], env, b"\n")
    lines = out.splitlines()
    assert rc == 0 and lines[-1] == "PASS", out[-3000:] + err[-3000:]
    assert lines[0].startswith("The owner-run preparation job") and "It does not score SA3." in lines[0]
    assert "TEST protected root in force" in err
    assert oct(root.stat().st_mode & 0o777) == "0o700" and oct((root / "run1").stat().st_mode & 0o777) == "0o700"
    rep = report(tmp_path / "pub")
    assert rep["target"] == "real" and rep["codes"] == [] and rep["placebo"]["verdict"] == "bytes_equal"
    assert rep["repos"] == report(run1["pub"])["repos"]
    seal = json.loads((tmp_path / "pub/seal.json").read_text())
    assert seal["target"] == "real" and seal["inputs"] == json.loads((run1["pub"] / "seal.json").read_text())["inputs"]
    assert json.loads((tmp_path / "pub/run_log.json").read_text())["target"] == "real"
    p = subprocess.run([PY, "-B", str(SEAL), "verify", "--seal", str(tmp_path / "pub/seal.json"), "--protected",
                        str(root / "verify1"), *real], capture_output=True, text=True, env=env, timeout=600)
    assert p.returncode == 0 and p.stdout.splitlines()[-1] == "VERIFIED", p.stdout + p.stderr
    # a typed answer other than Enter, and the variable naming a place outside the two allowed: refused
    rc, out, err = _with_terminal([PY, "-B", str(PREPARE), *real, "--protected", str(root / "run2"),
                                   "--out", str(tmp_path / "pub2")], env, b"yes\n")
    assert rc == 2 and "not confirmed" in err and not (root / "run2").exists() and not (tmp_path / "pub2").exists()
    for bad in (str(SR.STUDY / "x"), "/var/tmp/x", str(SR.PROTECTED_ROOT)):
        q = subprocess.run([PY, "-B", str(PREPARE), *real, "--protected", str(root / "run3"), "--out",
                            str(tmp_path / "pub3")], capture_output=True, text=True,
                           env={**os.environ, P.TEST_ROOT_ENV: bad}, stdin=subprocess.DEVNULL, timeout=120)
        assert q.returncode == 2 and P.TEST_ROOT_ENV in q.stderr, (bad, q.stderr)
    assert not (root / "run3").exists()
