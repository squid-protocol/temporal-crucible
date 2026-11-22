"""Tests of stored tables, phase B (tools/tables/phase_b.py, tools/harness/sandbox_ro.py; tables_phase_b_spec.md).

Everything runs on DECOYS: control repositories generated (generator 1.3.0, seed 11, --years 10) and run through
the unmodified SA3 pipeline by the existing harness (route manifest, --tables: phase A's builder too), under
pytest's tmp_path, then assembled into a decoy directory (study/, pool/, docs/) with the four cases the review
named (no outcome file; a blobless clone; a write-ahead scan database without side files and with frames but no
-shm; a .gitattributes line switching vendoring off for one directory). Nothing here opens, lists or stats the
real study directory, the corpus, the pool or ~/.blind: the --real path is exercised with throwaway directories
passed as its location parameters, and the production defaults only by the guard, which is shown (under strace)
to refuse before touching any path.

Pipeline tests are skipped, with the reason, when bwrap, tree_sitter_language_pack 1.20.0, linguist's cached
lists or the engine export are unavailable. The whole file takes about four minutes.
"""
from __future__ import annotations

import ast
import builtins
import importlib.metadata as md
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "tools" / "tables"
HARNESS = ROOT / "tools" / "harness"
GEN = ROOT / "tools" / "control_repo" / "generate.py"
sys.path.insert(0, str(TABLES))
sys.path.insert(0, str(HARNESS))
import canon as C  # noqa: E402
import invariants as I  # noqa: E402
import phase_b as P  # noqa: E402
import sandbox as SB  # noqa: E402
import sandbox_ro as SR  # noqa: E402
import schema as S  # noqa: E402
import silence as SL  # noqa: E402

PHASE_B = TABLES / "phase_b.py"
PY = sys.executable
MARK_SHA = "c0ffee" + "5eed" * 8 + "ab"                  # 40 hex, in no clone
MARK_PATH = "zz_marker_dir_q9x7/outcome_only_marker_7f3a.py"
MARK_VAL = "MARKERKEY-424242"
# phase A's four tables for seed 11, --years 10 (route manifest), identical with build.py before and after the
# refactor (DECISIONS.md, phase B): the same hashes for all nine tables, checked by running the old builder on
# the same inputs
PHASE_A = {
    "python-base": {"repo": "6e3ed528b46aa48c97fb8d88ebc250bc068570633b85b3b5ee8f3ee55b2ebfb3",
                    "snapshot": "01f0e9f72d1161e0eb89001a7b56232a97c91ccaecf92325b1bdda87b533b8a9",
                    "file": "54597bbfcd30c25f637ee6f76548a26f2874fd9bd3fa590adf8db2f37a7bfc37",
                    "measure": "73614cd0749d8af3522440141e85879e80bf70efac876519c08b39d231dda785",
                    "touch": "fa84ffaa9172190d730b7d87881ec4b5491b0a286dfb515c25818e22b875489b",
                    "link": "605bd15f31e21c057b8018c73ae1120329270307133d2eaad20e0209c943a35b",
                    "event": "8edd9610b1c04b454a67c6e3b3dd57c8f75447dd2a001c5118191dbea2638391",
                    "pool": "3ee0985b6cb92ee3dd1c6e4e1c72145df5edc2691d524f6206c040ea61f70988",
                    "marginal": "e34b265987400b7b586fabfc60566c139ad19241015979bb11d0d90f444d5b26"},
    "c-base": {"repo": "42076947780a17672d1fefe2063284a1db1c0138acaba326906d2f49d40a2487",
               "snapshot": "e80a3b8bb61e5abad82e589c88cf6e0cef456372661fa1b03ea6a2328677a77c",
               "file": "4391b217ab98616f3f6648f8b04469e722f620f5d9604cdee2709567d9aae984",
               "measure": "52d1445d9e040b30586a23fdd0f3bb997ad15866d23dac69eb8d3d587e0d85c3",
               "touch": "622ed7bf1a70c2f15acdbb432220397b515f274c014d88640b3021f8a8121adb",
               "link": "0765c9f676f0ad17b98aa28f4e9e3d0eb168ecb5c14337723fd3388478b0a2fa",
               "event": "3b0ab18c333dbbbac1b468c995e9795951f4697230611968c2454dbb9bb68618",
               "pool": "d2d9d6cabac9a9091d95202ac0d11d63cbc459c49c8538bb532182bf3f63295b",
               "marginal": "7d3c3bc03443f30cff79a7ff130bf003bc70aaff87d4de2a54cd2da504f9d4fa"},
}
CONTROLS = [("python", None), ("c", None), ("python", "generic_dir_names"), ("python", "vendored_half"),
            ("python", "bot_merges"), ("python", "merge_workflow"), ("python", "mixed_language")]
VARIANTS = ("nooutcome", "blobless", "walnoside", "walframes", "attrs-thirdparty", "marked")   # python-base copies
ATTR_LINE = "**/cache/** -linguist-vendored\n"     # on a copy of generic_dir_names: a directory the engine scans
PUBLIC = ("repo", "snapshot", "file", "measure")


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


def git(repo: Path, *args: str, check: bool = True) -> str:
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1"}
    p = subprocess.run(["git", "-C", str(repo), "-c", "gc.auto=0", *args], capture_output=True, text=True, env=env)
    if check:
        assert p.returncode == 0, p.stderr
    return p.stdout


def phase_a_rows(work: Path, repo: str, table: str) -> list[dict]:
    d = work / "study" / "sa3_tables" / repo
    idx = json.loads((d / "index.json").read_text())
    return decode(table, C.read_rows(d / idx["tables"][table]["file"]))


def decode(table: str, rows: list[dict]) -> list[dict]:
    """stored rows back to values: a real is stored as the string of float.hex()"""
    reals = [c for c, t in S.TABLES[table]["columns"] if t == "real"]
    return [{**r, **{c: (None if r[c] is None else float.fromhex(r[c])) for c in reals}} for r in rows]


def renamed_hash(rows: list[dict], table: str, new: str, change=None) -> str:
    out = []
    for r in rows:
        x = {**r, "repo": new}
        if change:
            x = change(x)
        out.append(x)
    return C.table_hash(table, out)


def all_output_text(*dirs: Path) -> str:
    chunks = []
    for d in dirs:
        for p in sorted(Path(d).rglob("*")):
            if p.is_file():
                chunks.append(p.read_bytes().decode("utf-8", "replace"))
    return "\n".join(chunks)


def listing(root: Path) -> dict:
    return {str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns)
            for p in sorted(root.rglob("*"))}


def wal_frames_copy(src: Path, dst: Path, keep_shm: bool) -> None:
    """dst: a copy of the WAL database src whose -wal holds committed frames (a table created and dropped:
    every row as it was), with or without its -shm. The writer's connection is still open when the files are copied."""
    tmp = dst.parent / (dst.name + ".work")
    shutil.copyfile(src, tmp)
    con = sqlite3.connect(str(tmp))
    con.execute("pragma wal_autocheckpoint=0")
    assert con.execute("pragma journal_mode").fetchone()[0] == "wal"
    con.execute("create table phaseb_frames (x)")            # frames in the -wal; file_data untouched
    con.commit()
    con.execute("drop table phaseb_frames")
    con.commit()
    assert Path(str(tmp) + "-wal").stat().st_size > 0
    shutil.copyfile(tmp, dst)
    shutil.copyfile(str(tmp) + "-wal", str(dst) + "-wal")
    if keep_shm:
        shutil.copyfile(str(tmp) + "-shm", str(dst) + "-shm")
    con.close()
    for f in tmp.parent.glob(tmp.name + "*"):
        f.unlink()


# ------------------------------------------------------------------------------------------- the decoy
class Rehearsal:
    """the controls (harness, phase A tables), one decoy directory with the variants, one phase B run"""

    def __init__(self, base: Path):
        self.base = base
        self.works: dict[str, Path] = {}
        self.decoy = base / "decoy"
        self.out = base / "out"
        self.scratch = base / "out.scratch"
        self.ran: subprocess.CompletedProcess | None = None

    def control(self, language: str, mutation: str | None) -> tuple[str, Path]:
        tag = f"{language}-{mutation or 'base'}"
        if tag in self.works:
            return tag, self.works[tag]
        ctrl = self.base / "controls" / tag
        argv = [PY, "-B", str(GEN), "--out", str(ctrl), "--seed", "11", "--years", "10", "--language", language]
        subprocess.run(argv + (["--mutation", mutation] if mutation else []), check=True, capture_output=True,
                       cwd=str(self.base))
        work = self.base / "work" / tag
        p = subprocess.run([PY, "-B", str(HARNESS / "run.py"), "--control", str(ctrl), "--work", str(work), "--name",
                            tag, "--routes", "manifest", "--no-shim-lock", "--tables"],
                           capture_output=True, text=True, timeout=1800)
        assert p.returncode == 0, p.stdout[-2000:] + p.stderr[-2000:]
        self.works[tag] = work / "manifest"
        return tag, self.works[tag]

    def manifest(self, tag: str) -> dict:
        return json.loads((self.base / "controls" / tag / "manifest.json").read_text())

    def add(self, tag: str, new: str | None = None) -> str:
        w, r = self.works[tag], f"ctrl-{tag}"
        n = new or r
        for sub in ("history", "sa3_scans", "sa3_outcomes", "meta_sa3", "sa3_nesting"):
            for f in (w / "study" / sub).glob(f"{r}*"):
                rest = f.name[len(r):]
                if rest not in (".db", ".json", "_master.db", "_master.db-wal", "_master.db-shm"):
                    continue
                (self.decoy / "study" / sub).mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, self.decoy / "study" / sub / (n + rest))
        shutil.copytree(w / "pool" / r, self.decoy / "pool" / n, symlinks=True)
        rows = json.loads((w / "tree/docs/sa3_outcome_marginals.json").read_text())
        self.marg += [{**row, "repo": n} for row in rows]
        pf = w / "tree/docs/sa3_placebo.json"
        if pf.exists():
            for _k, v in json.loads(pf.read_text()).get("repos", {}).items():
                self.plac["repos"][n] = v
        return n

    def build(self) -> None:
        for lang, mut in CONTROLS:
            self.control(lang, mut)
        self.marg, self.plac = [], {"repos": {}}
        (self.decoy / "docs").mkdir(parents=True)
        for lang, mut in CONTROLS:
            self.add(f"{lang}-{mut or 'base'}")
        st = self.decoy / "study"
        for v in VARIANTS:
            self.add("python-base", f"ctrl-pyb-{v}")
        # 1. a repo with no outcome file (as the six scan-incomplete repos): its marginals row says so
        (st / "sa3_outcomes" / "ctrl-pyb-nooutcome.json").unlink()
        for row in self.marg:
            if row["repo"] == "ctrl-pyb-nooutcome":
                row.update({"status": "scan_incomplete", "why": "imitated: no outcome file"})
        # 2. a blobless clone (tree available, archive not)
        bl = self.decoy / "pool" / "ctrl-pyb-blobless"
        shutil.rmtree(bl)
        src = self.works["python-base"] / "pool" / "ctrl-python-base"
        subprocess.run(["git", "-c", "gc.auto=0", "clone", "-q", "--filter=blob:none", "--no-checkout",
                        "--upload-pack=git -c uploadpack.allowFilter=true upload-pack", f"file://{src}", str(bl)],
                       check=True, capture_output=True, env={**os.environ, "GIT_NO_LAZY_FETCH": "1"})
        # 3. write-ahead scan database: no side files at all; and frames in -wal with no -shm
        db = st / "sa3_scans" / "ctrl-pyb-walnoside_master.db"
        assert Path(str(db) + "-wal").stat().st_size == 0          # nothing is lost by removing it
        Path(str(db) + "-wal").unlink()
        Path(str(db) + "-shm").unlink()
        db = st / "sa3_scans" / "ctrl-pyb-walframes_master.db"
        for sfx in ("-wal", "-shm"):
            Path(str(db) + sfx).unlink()
        wal_frames_copy(self.works["python-base"] / "study/sa3_scans/ctrl-python-base_master.db", db, keep_shm=False)
        # 4. a .gitattributes line that switches vendoring off for one directory (the sidecar the scan wrote)
        #    (a) on generic_dir_names, `cache/`, which the engine scanned: those files join the universe and the
        #    history's own rule still excludes them; (b) on the base, vendor/thirdparty/, which the engine never
        #    scanned: they become `not_scanned`, and the universe does not change
        self.add("python-generic_dir_names", "ctrl-gdn-attrs")
        for name, line in (("ctrl-gdn-attrs", ATTR_LINE),
                           ("ctrl-pyb-attrs-thirdparty", "vendor/thirdparty/** -linguist-vendored\n")):
            sc = st / "sa3_scans" / f"{name}.json"
            side = json.loads(sc.read_text())
            side["attrs"][".gitattributes"] += line
            sc.write_text(json.dumps(side, indent=1) + "\n")
        # markers in the label side only: an outcome file and the link harvest of one repo
        of = st / "sa3_outcomes" / "ctrl-pyb-marked.json"
        o = json.loads(of.read_text())
        o["outcomes"]["HP"]["files"].append(MARK_PATH)
        o["outcomes"]["HP"]["commits"][MARK_SHA] = [MARK_PATH]
        o["outcomes"]["control_pool"]["commits"][MARK_SHA[::-1]] = [MARK_PATH]
        of.write_text(json.dumps(o) + "\n")
        con = sqlite3.connect(str(st / "meta_sa3" / "ctrl-pyb-marked.db"))
        con.execute("insert into link (sha, kind, value) values (?, ?, ?)", (MARK_SHA, "issue_fix", MARK_VAL))
        con.commit()
        con.close()
        (self.decoy / "docs" / "sa3_outcome_marginals.json").write_text(json.dumps(self.marg, indent=1) + "\n")
        (self.decoy / "docs" / "sa3_placebo.json").write_text(json.dumps(self.plac, indent=1) + "\n")

    def run(self) -> subprocess.CompletedProcess:
        if self.ran is None:
            self.build()
            self.bl_before = {"packs": sorted(os.listdir(self.decoy / "pool/ctrl-pyb-blobless/.git/objects/pack")),
                              "logs": listing(self.decoy / "pool/ctrl-pyb-blobless/.git/logs"),
                              "config": (self.decoy / "pool/ctrl-pyb-blobless/.git/config").read_bytes()}
            self.study_before = listing(self.decoy / "study")
            self.ran = subprocess.run([PY, "-B", str(PHASE_B), "--decoy", str(self.decoy), "--out", str(self.out)],
                                      capture_output=True, text=True, timeout=3600)
        return self.ran

    def datacard(self, repo: str) -> dict:
        return json.loads((self.out / repo / "datacard.json").read_text())

    def index(self, repo: str) -> dict:
        return json.loads((self.out / repo / "index.json").read_text())

    def rows(self, repo: str, table: str) -> list[dict]:
        return C.read_rows(self.out / repo / self.index(repo)["tables"][table]["file"])


@pytest.fixture(scope="session")
def rehearsal(tmp_path_factory):
    why = _skip_reason()
    if why:
        pytest.skip(why)
    base = tmp_path_factory.mktemp("phaseb")
    if not _engine_present(base):
        pytest.skip("engine export not present")
    r = Rehearsal(base)
    p = r.run()
    assert p.returncode == 0, p.stdout[-3000:] + p.stderr[-3000:]
    return r


# ====================================================================================== 1. the default and guard
def test_1a_no_target_refuses_before_any_sandbox(tmp_path, monkeypatch):
    """no target, --real alone, --decoy and --real together: exit 2, nothing created, bwrap never started"""
    marker = tmp_path / "bwrap-was-called"
    stub = tmp_path / "bwrap-stub"
    stub.write_text(f"#!/bin/sh\ntouch {marker}\n")
    stub.chmod(0o755)
    monkeypatch.setattr(SR, "BWRAP", str(stub))
    for argv in ([], ["--out", str(tmp_path / "o1")], ["--real", "--out", str(tmp_path / "o2")],
                 ["--decoy", str(tmp_path), "--real", "--i-am-the-reviewer-session", "--out", str(tmp_path / "o3")]):
        assert P.main(argv) == 2, argv
    assert not marker.exists()
    assert not any((tmp_path / n).exists() for n in ("o1", "o2", "o3"))
    p = subprocess.run([PY, "-B", str(PHASE_B)], capture_output=True, text=True)
    assert p.returncode == 2 and "no target" in p.stderr and "refused" in p.stderr
    p = subprocess.run([PY, "-B", str(PHASE_B), "--real", "--out", str(tmp_path / "o4")], capture_output=True,
                       text=True)
    assert p.returncode == 2 and "--i-am-the-reviewer-session" in p.stderr and not (tmp_path / "o4").exists()


def test_1b_out_must_be_new_and_outside_data_roots(tmp_path):
    for bad in (SR.STUDY / "x", SR.POOL / "x", SR.WORKTREE / "x", Path("/nvme-data/x"), SR.HOME / ".blind/x"):
        assert P.main(["--decoy", str(tmp_path), "--out", str(bad)]) == 2
    (tmp_path / "exists").mkdir()
    assert P.main(["--decoy", str(tmp_path), "--out", str(tmp_path / "exists")]) == 2
    with pytest.raises(SystemExit):
        P.resolve_target(type("A", (), {"decoy": str(SR.LAWS / "x"), "real": False})())


def test_1c_production_defaults_guard_refuses_without_touching(tmp_path):
    """The production defaults are what --real resolves to; outside the sandbox the stage's guard refuses, and
    strace shows that no file syscall of that process names the study directory or the pool"""
    a = type("A", (), {"decoy": None, "real": True, "i_am_the_reviewer_session": True,
                       "real_study": str(SR.STUDY), "real_pool": str(SR.POOL), "real_docs": str(ROOT / "docs")})()
    tgt = P.resolve_target(a)
    assert tgt.real and tgt.study == SR.STUDY and tgt.pool == SR.POOL            # strings only
    if not shutil.which("strace"):
        pytest.skip("strace not installed")
    log = tmp_path / "strace.log"
    rd = tmp_path / "rd"
    rd.mkdir()
    for stage in ("tables", "copy", "preflight"):
        p = subprocess.run(["strace", "-f", "-qq", "-e", "trace=%file,%desc", "-o", str(log), PY, "-I", "-B",
                            str(PHASE_B), "stage", stage, "--repo", "django", "--rundir", str(rd)],
                           capture_output=True, text=True, timeout=120)
        assert p.returncode != 0 and "refused" in p.stderr and "read-only sandbox" in p.stderr, p.stderr[-1500:]
        text = log.read_text()
        assert "/proc/self/mountinfo" in text
        for forbidden in (str(SR.LAWS), str(SR.POOL), "/nvme-data", str(SR.HOME / ".blind")):
            assert forbidden not in text, f"{stage}: a syscall named {forbidden}"
        assert not (rd / "result.json").exists()
    # the guard in-process: only the mount table is read before it refuses
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


def _listing_spec(tmp_path: Path, study_files: list[tuple[str, Path]], clone: tuple | None, unsafe=()) -> tuple:
    code = tmp_path / "code"
    if not code.exists():
        shutil.copytree(ROOT / "tools", code / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    rd = tmp_path / f"rd{len(list(tmp_path.glob('rd*')))}"
    rd.mkdir()
    spec = SR.Spec(rw=[rd], code=[code], inputs=study_files, clone=clone, cwd=rd,
                   unsafe_rw_for_tests=list(unsafe))
    return spec, rd, code


def test_1d_guard_refuses_a_writable_study_path_or_clone(tmp_path):
    if not Path(SR.BWRAP).exists():
        pytest.skip("bwrap not installed")
    f = tmp_path / "fake-study" / "history" / "R.db"
    f.parent.mkdir(parents=True)
    f.write_bytes(b"x")
    clone = tmp_path / "fake-pool" / "R"
    clone.mkdir(parents=True)
    cases = {"ok": ([], None), "rw study file": ([(str(f), SR.STUDY / "history" / "R.db")], None),
             "rw study dir": ([(str(f.parent), SR.STUDY / "sa3_scans")], None),
             "rw clone": ([(str(clone), SR.POOL / "R")], ("R", str(clone)))}
    for name, (unsafe, cl) in cases.items():
        spec, rd, code = _listing_spec(tmp_path, [(str(f), SR.STUDY / "history" / "R.db")],
                                       cl or ("R", str(clone)), unsafe)
        if name == "rw clone":
            spec.clone = None                            # bound read-write instead, and still declared as the clone
            spec.env = {"PHASEB_CLONE": str(SR.POOL / "R")}
        p = SR.run(["/usr/bin/python3", "-I", "-B", str(code / "tools/tables/phase_b.py"), "stage", "listing",
                    "--repo", "R", "--rundir", str(rd)], spec, rd, rd, timeout=120)
        if name == "ok":
            assert p.returncode == 0, p.stdout + p.stderr
            assert json.loads((rd / "result.json").read_text())["listing"]["study"] == ["history", "history/R.db"]
        else:
            assert p.returncode == 3 and "refused" in p.stderr, (name, p.stdout, p.stderr)
            assert not (rd / "result.json").exists(), name
    assert f.read_bytes() == b"x"


def test_1e_real_flag_with_throwaway_locations(rehearsal, tmp_path):
    """--real --i-am-the-reviewer-session runs exactly the decoy code path when its location parameters name a
    decoy; the launcher itself (strace without -f: bwrap's own syscalls are not the launcher's) never names the
    study or the pool in a file syscall"""
    d = rehearsal.decoy
    out = tmp_path / "real-out"
    log = tmp_path / "launcher.strace"
    argv = [PY, "-B", str(PHASE_B), "--real", "--i-am-the-reviewer-session", "--real-study", str(d / "study"),
            "--real-pool", str(d / "pool"), "--real-docs", str(d / "docs"), "--repos", "ctrl-python-base",
            "--out", str(out)]
    if shutil.which("strace"):
        argv = ["strace", "-qq", "-e", "trace=%file", "-o", str(log)] + argv
    p = subprocess.run(argv, capture_output=True, text=True, timeout=1200)
    assert p.returncode == 0, p.stdout[-2000:] + p.stderr[-2000:]
    assert json.loads((out / "run_log.json").read_text())["target"] == "real"
    assert P.main([]) == 2
    a = rehearsal.index("ctrl-python-base")["tables"]
    b = json.loads((out / "ctrl-python-base" / "index.json").read_text())["tables"]
    assert {k: v["hash"] for k, v in a.items()} == {k: v["hash"] for k, v in b.items()}
    if shutil.which("strace"):
        text = log.read_text()
        for x in (str(d / "study"), str(d / "pool")):
            bad = [ln for ln in text.splitlines() if x in ln and "execve" not in ln]
            assert not bad, bad[:5]


# ============================================================================= 2. the sandbox, from inside
def _repo_spec(rehearsal, tmp_path, repo: str):
    d = rehearsal.decoy
    spec, rd, code = _listing_spec(tmp_path, P.declared(d / "study", repo), (repo, str(d / "pool" / repo)))
    return spec, rd, code


MISBEHAVE = r"""
import json, os, sqlite3, subprocess, sys
S, POOL, repo, rd = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
clone = os.path.join(POOL, repo)
res = {}
def attempt(name, fn):
    try:
        fn(); res[name] = "SUCCEEDED"
    except Exception as e:
        res[name] = type(e).__name__
def w(p):
    with open(p, "a") as fh: fh.write("x")
attempt("append to the history database", lambda: w(f"{S}/history/{repo}.db"))
attempt("create a file in the study path", lambda: w(f"{S}/new.txt"))
attempt("create a -wal beside the scan database", lambda: w(f"{S}/sa3_scans/{repo}_master.db-journal"))
attempt("mkdir in the study path", lambda: os.mkdir(f"{S}/sa3_outcomes"))
attempt("write a pack into the clone", lambda: w(f"{clone}/.git/objects/pack/pack-evil.pack"))
attempt("write the clone's reflog", lambda: w(f"{clone}/.git/logs/HEAD"))
attempt("chmod a study file", lambda: os.chmod(f"{S}/history/{repo}.db", 0o600))
def sq():
    c = sqlite3.connect(f"{S}/history/{repo}.db"); c.execute("create table evil(x)"); c.commit()
attempt("sqlite write to the original", sq)
def g(*a):
    p = subprocess.run(["git", "-C", clone, *a], capture_output=True, text=True)
    if p.returncode: raise OSError(p.stderr[-200:])
for name, args in (("git gc", ("gc",)), ("git repack", ("repack", "-a", "-d")), ("git fetch", ("fetch", "origin")),
                   ("git update-ref", ("update-ref", "refs/heads/evil", "HEAD")), ("git reflog expire",
                   ("reflog", "expire", "--expire=now", "--all")), ("git config", ("config", "x.y", "z"))):
    attempt(name, lambda a=args: g(*a))
ok = {}
for d in (rd, os.environ["TMPDIR"]):
    try:
        w(os.path.join(d, "ok.txt")); ok[d] = True
    except OSError:
        ok[d] = False
others = {}
for d in ("/etc", "/usr", "/var/tmp", "/srv/storage_16tb", "/srv/storage_16tb/projects", S, POOL, "/nvme-data",
          "/home/joe", "/home/joe/.claude", "/tmp", "/dev", "/dev/shm", "/run/user/1000", "/var/lib/docker"):
    try:
        os.makedirs(d, exist_ok=True); w(os.path.join(d, "phaseb_probe")); others[d] = "WROTE"
    except OSError as e:
        others[d] = type(e).__name__
print(json.dumps({"attempts": res, "rw_ok": ok, "others": others, "lazy": os.environ.get("GIT_NO_LAZY_FETCH")}))
"""


def test_2a_misbehaving_stage_fails_and_manifest_unchanged(rehearsal, tmp_path):
    """spec 'Before the real run' 1: a write to the study path fails, a write to a clone fails, git gc and a fetch
    fail, the output and scratch directories are the only writable places, and the decoy's manifest (taken from
    outside, in its own sandbox) is unchanged"""
    import manifest_stat as MS
    repo = "ctrl-python-base"
    d = rehearsal.decoy
    code = tmp_path / "mcode"
    shutil.copytree(ROOT / "tools", code / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    before = MS.take(d / "study", d / "pool", [repo, "ctrl-pyb-blobless"], tmp_path / "b.json", tmp_path / "mb", code)
    host_before = listing(d / "study")
    spec, rd, _ = _repo_spec(rehearsal, tmp_path, repo)
    (rd / "tmp").mkdir()
    p = SR.run(["/usr/bin/python3", "-I", "-B", "-c", MISBEHAVE, str(SR.STUDY), str(SR.POOL), repo, str(rd)],
               spec, rd, rd / "tmp", timeout=300)
    assert p.returncode == 0, p.stdout + p.stderr
    r = json.loads(p.stdout)
    assert not [k for k, v in r["attempts"].items() if v == "SUCCEEDED"], r["attempts"]
    assert all(r["rw_ok"].values()), r["rw_ok"]
    assert not [k for k, v in r["others"].items() if v == "WROTE"], r["others"]
    assert r["lazy"] == "1"
    after = MS.take(d / "study", d / "pool", [repo, "ctrl-pyb-blobless"], tmp_path / "a.json", tmp_path / "ma", code)
    assert before["ok"] and after["ok"]
    assert not any(MS.compare(before, after).values()), MS.compare(before, after)
    assert listing(d / "study") == host_before


def test_2b_manifest_sees_changes_made_from_outside(rehearsal, tmp_path):
    """touch, a created side file, chmod, a pack added to the clone, an emptied reflog: each is reported"""
    import manifest_stat as MS
    repo = "ctrl-mc"
    d = tmp_path / "decoy"
    for sub in ("history", "sa3_scans", "sa3_nesting"):
        (d / "study" / sub).mkdir(parents=True)
    src = rehearsal.decoy
    for sub, name in (("history", ".db"), ("sa3_scans", ".json"), ("sa3_scans", "_master.db"),
                      ("sa3_nesting", ".json")):
        shutil.copy2(src / "study" / sub / f"ctrl-python-base{name}", d / "study" / sub / f"{repo}{name}")
    shutil.copytree(src / "pool" / "ctrl-python-base", d / "pool" / repo, symlinks=True)
    code = tmp_path / "mcode"
    shutil.copytree(ROOT / "tools", code / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    base = MS.take(d / "study", d / "pool", [repo], tmp_path / "0.json", tmp_path / "m0", code)
    changes = {
        "touch": lambda: os.utime(d / "study/history" / f"{repo}.db"),
        "side file created": lambda: (d / "study/sa3_scans" / f"{repo}_master.db-wal").write_bytes(b""),
        "chmod": lambda: os.chmod(d / "study/sa3_nesting" / f"{repo}.json", 0o600),
        "pack added": lambda: (d / "pool" / repo / ".git/objects/pack/pack-new.pack").write_bytes(b"P"),
        "reflog emptied": lambda: (d / "pool" / repo / ".git/logs/HEAD").write_bytes(b""),
    }
    prev = base
    for i, (name, fn) in enumerate(changes.items()):
        fn()
        now = MS.take(d / "study", d / "pool", [repo], tmp_path / f"{i + 1}.json", tmp_path / f"m{i + 1}", code)
        diff = MS.compare(prev, now)
        assert any(diff.values()), name
        prev = now


def test_2c_declared_inputs_only(rehearsal):
    """from inside every stage's sandbox the study path holds exactly the declared inputs of the one repo"""
    sc = rehearsal.scratch
    for repo in json.loads((rehearsal.out / "run_log.json").read_text())["repos"]:
        pre = json.loads((sc / repo / "preflight" / "result.json").read_text())["listing"]
        want = {f"{s}/{repo}{x}" for s, x in (("history", ".db"), ("sa3_scans", ".json"), ("sa3_scans", "_master.db"),
                                               ("sa3_nesting", ".json"))}
        sides = {f"sa3_scans/{repo}_master.db{s}" for s in ("-wal", "-shm")} | {f"history/{repo}.db-wal"}
        got = set(pre["study"]) - {"history", "sa3_scans", "sa3_nesting"}
        assert want <= got and got - want <= sides, (repo, got ^ want)
        assert pre["pool"] == [repo]
        tb = json.loads((sc / repo / "tables" / "result.json").read_text())["listing"]
        assert set(tb["study"]) - {"history", "sa3_scans", "sa3_nesting"} == want, (repo, tb["study"])
        assert tb["pool"] == [repo]
        for v in SL.VERSIONS:
            sl = json.loads((sc / repo / f"silence_{v}" / "result.json").read_text())
            assert set(sl["listing"]) - {"history", "sa3_scans", "sa3_nesting", "sa3_outcomes"} == \
                want | {f"sa3_outcomes/{repo}.json"}, (repo, v, sl["listing"])
            assert sl["pool"] == []                                       # no clone for silence
        for x in (pre["study"], tb["study"]):
            assert not [p for p in x if p.split("/")[0] in ("sa3_outcomes", "meta_sa3", "meta_mod1", "dbs",
                                                             "sa3_tables")], x
    stub = json.loads((sc / "stubs" / "ctrl-python-base.json").read_text())
    assert all(not v.get("files") and not v.get("commits") for v in stub["outcomes"].values())


# ======================================================================================== 3. SQLite copies
def _db(path: Path, mode: str, rows: int = 50) -> list:
    con = sqlite3.connect(str(path))
    con.execute(f"pragma journal_mode={mode}")
    con.execute("create table file_data (id integer primary key, file_path text, total_loc int)")
    con.executemany("insert into file_data (file_path, total_loc) values (?, ?)",
                    [(f"src/f{i}.py", i + 1) for i in range(rows)])
    con.commit()
    got = con.execute("select * from file_data order by id").fetchall()
    con.close()
    return got


@pytest.mark.parametrize("state", ["wal-with-sides", "wal-no-sides", "wal-frames-shm", "wal-frames-no-shm",
                                   "rollback"])
def test_3_sqlite_copied_then_opened(tmp_path, state):
    if not Path(SR.BWRAP).exists():
        pytest.skip("bwrap not installed")
    repo = "R"
    st = tmp_path / "study"
    (st / "sa3_scans").mkdir(parents=True)
    (st / "history").mkdir()
    db = st / "sa3_scans" / f"{repo}_master.db"
    want = _db(db, "delete" if state == "rollback" else "wal")
    _db(st / "history" / f"{repo}.db", "delete", 3)
    if state == "wal-no-sides":
        for sfx in ("-wal", "-shm"):
            f = Path(str(db) + sfx)
            if f.exists():
                assert sfx == "-shm" or f.stat().st_size == 0
                f.unlink()
    if state == "wal-with-sides":
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)         # leaves -shm and an empty -wal, as readers do
        c.execute("select count(*) from file_data").fetchone()
        c.close()
        assert Path(str(db) + "-shm").exists()
    if state.startswith("wal-frames"):
        tmpd = tmp_path / "w"
        tmpd.mkdir()
        shutil.copyfile(db, tmpd / "x.db")
        con = sqlite3.connect(str(tmpd / "x.db"))
        con.execute("pragma wal_autocheckpoint=0")
        con.executemany("insert into file_data (file_path, total_loc) values (?, ?)", [("late.py", 7)])
        con.commit()
        want = con.execute("select * from file_data order by id").fetchall()
        for f in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
            if f.exists():
                f.unlink()
        shutil.copyfile(tmpd / "x.db", db)
        shutil.copyfile(str(tmpd / "x.db") + "-wal", str(db) + "-wal")
        if state == "wal-frames-shm":
            shutil.copyfile(str(tmpd / "x.db") + "-shm", str(db) + "-shm")
        con.close()
        assert Path(str(db) + "-wal").stat().st_size > 0
    before = listing(st)
    spec, rd, code = _listing_spec(tmp_path, P.declared(st, repo), None)
    (rd / "home").mkdir()
    (rd / "tmp").mkdir()
    p = SR.run(["/usr/bin/python3", "-I", "-B", str(code / "tools/tables/phase_b.py"), "stage", "copy",
                "--repo", repo, "--rundir", str(rd)], spec, rd / "home", rd / "tmp", timeout=120)
    assert p.returncode == 0, p.stdout + p.stderr
    res = json.loads((rd / "result.json").read_text())
    assert res["copies"]["scan_db"]["copy_mode_after"] == "delete" and res["copies"]["scan_db"]["quick_check"] == "ok"
    assert listing(st) == before, "the original's directory listing or stat changed"
    copy = rd / "db" / "scan.db"
    assert not [x for x in copy.parent.iterdir() if x.name.startswith("scan.db-")]
    with open(copy, "rb") as fh:
        h = fh.read(20)
    assert (h[18], h[19]) == (1, 1)                                   # rollback mode: readable from a ro bind
    c = sqlite3.connect(f"file:{copy}?mode=ro", uri=True)
    assert c.execute("select * from file_data order by id").fetchall() == want
    c.close()
    # and the copy is read correctly from a read-only bind with no side file, as the tables stage reads it
    spec2, rd2, _ = _listing_spec(tmp_path, [(str(copy), SR.STUDY / "sa3_scans" / f"{repo}_master.db")], None)
    q = SR.run(["/usr/bin/python3", "-I", "-B", "-c",
                "import sqlite3,sys; c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro', uri=True); "
                "print(c.execute('select count(*) from file_data').fetchone()[0])",
                str(SR.STUDY / "sa3_scans" / f"{repo}_master.db")], spec2, rd2, rd2, timeout=60)
    assert q.returncode == 0 and int(q.stdout) == len(want), q.stderr


# ======================================================================================= 4. the rehearsal
def test_4a_phase_a_hashes_recorded(rehearsal):
    """phase A's nine tables for seed 11 (Python and C) still have the hashes recorded before the refactor"""
    for tag, want in PHASE_A.items():
        idx = json.loads((rehearsal.works[tag] / "study/sa3_tables" / f"ctrl-{tag}" / "index.json").read_text())
        assert {k: v["hash"] for k, v in idx["tables"].items()} == want, tag


def test_4b_tables_equal_phase_a(rehearsal):
    """the four tables equal phase A's, hash for hash, wherever phase A builds them; the variants equal the base
    renamed, except for exactly what their condition changes"""
    for lang, mut in CONTROLS:
        tag = f"{lang}-{mut or 'base'}"
        repo = f"ctrl-{tag}"
        a_dir = rehearsal.works[tag] / "study/sa3_tables" / repo
        if not (a_dir / "index.json").exists():
            assert (a_dir / "build_failed.json").exists() and mut == "bot_merges"
            assert set(rehearsal.index(repo)["tables"]) == set(PUBLIC)         # phase B still builds them
            continue
        a = json.loads((a_dir / "index.json").read_text())["tables"]
        b = rehearsal.index(repo)["tables"]
        assert {n: b[n]["hash"] for n in PUBLIC} == {n: a[n]["hash"] for n in PUBLIC}, tag
    w = rehearsal.works["python-base"]
    base = {t: phase_a_rows(w, "ctrl-python-base", t) for t in PUBLIC}

    def check(new, table, change=None):
        assert rehearsal.index(new)["tables"][table]["hash"] == renamed_hash(base[table], table, new, change), \
            (new, table)
    for v in ("walnoside", "walframes", "marked"):
        for t in PUBLIC:
            check(f"ctrl-pyb-{v}", t)
    n = "ctrl-pyb-nooutcome"
    for t in ("snapshot", "file", "measure"):
        check(n, t)
    check(n, "repo", lambda x: {**x, "status": "scan_incomplete", "why": "imitated: no outcome file"})
    n = "ctrl-pyb-blobless"
    for t in ("snapshot", "measure"):
        check(n, t)
    check(n, "file", lambda x: {**x, "in_archive": None,
                                "reason": "not_scanned" if x["reason"] == "not_in_archive" else x["reason"]})
    check(n, "repo", lambda x: {**x, "pipeline_complete": None, "pipeline_tree_unit_files": None})


def test_4c_blobless_clone(rehearsal):
    """tree only: archive unavailable (not a zero), nothing fetched, the clone's packs, reflog, config unchanged"""
    n = "ctrl-pyb-blobless"
    pre = json.loads((rehearsal.out / "preflight.json").read_text())[n]["clone"]
    assert pre["partial_clone"] and pre["promisor_packs"] >= 1 and pre["snapshot_tree_lists"]
    k = rehearsal.datacard(n)["count_4"]["registered"]
    assert k["complete"] == "archive unavailable" and k["archive"] == "unavailable"
    assert k["universe_returned"]["complete"] == 0.0                   # what universe() itself said
    assert "promisor" in k["archive_error"] and "<object>" in k["archive_error"]
    assert rehearsal.index(n)["archive"] == "unavailable"
    assert rehearsal.index(n)["history_can_touch"] == "computed"
    bl = rehearsal.decoy / "pool" / n / ".git"
    assert sorted(os.listdir(bl / "objects/pack")) == rehearsal.bl_before["packs"]
    assert listing(bl / "logs") == rehearsal.bl_before["logs"]
    assert (bl / "config").read_bytes() == rehearsal.bl_before["config"]
    full = rehearsal.datacard("ctrl-python-base")
    assert rehearsal.datacard(n)["count_4"]["against_tree"]["complete"] == \
        full["count_4"]["against_tree"]["complete"]                     # the new measure needs no archive


def test_4d_no_outcome_file(rehearsal):
    n = "ctrl-pyb-nooutcome"
    assert set(rehearsal.index(n)["tables"]) == set(PUBLIC)
    k = rehearsal.datacard(n)
    for c in ("count_2", "count_3", "count_4", "count_5", "count_6", "count_8", "count_9", "count_10"):
        assert c in k
    assert k["count_3"] == rehearsal.datacard("ctrl-python-base")["count_3"]


def test_4e_wal_cases(rehearsal):
    pre = json.loads((rehearsal.out / "preflight.json").read_text())
    assert pre["ctrl-pyb-walnoside"]["databases"]["scan_db"]["wal"] is None
    assert pre["ctrl-pyb-walnoside"]["databases"]["scan_db"]["shm"] is None
    assert pre["ctrl-pyb-walframes"]["databases"]["scan_db"]["wal"] > 0
    assert pre["ctrl-pyb-walframes"]["databases"]["scan_db"]["shm"] is None
    assert pre["ctrl-python-base"]["databases"]["scan_db"]["mode"] == "wal"
    assert listing(rehearsal.decoy / "study") == rehearsal.study_before, "a decoy input changed"


def test_4f_counts_against_known_values(rehearsal):
    """each count against the value known from the manifest, the clone, or the decoy's own outcome file (read
    here, by the test, never by the job)"""
    st = rehearsal.decoy / "study"
    for lang, mut in CONTROLS:
        tag = f"{lang}-{mut or 'base'}"
        repo = f"ctrl-{tag}"
        k = rehearsal.datacard(repo)
        man = rehearsal.manifest(tag)
        o = json.loads((st / "sa3_outcomes" / f"{repo}.json").read_text())
        side = json.loads((st / "sa3_scans" / f"{repo}.json").read_text())
        assert k["count_2"]["snapshot_time"] == man["points"]["snapshot"]["time"], tag
        assert k["count_2"]["cut"] == o["cut"]
        assert k["count_3"]["window_start"] == o.get("window_start"), tag
        assert k["count_3"]["window_end"] == o["end"] and k["count_3"]["usable_commits"] == o["usable_commits"]
        assert k["count_3"]["window_ends_after_start"] == (mut != "bot_merges"), tag
        assert k["count_2"]["window_start_equals_cut"] == (o["window_start"] == o["cut"])
        assert k["count_4"]["registered"]["complete"] == o["complete"], tag
        assert k["count_4"]["registered"]["unit_files"] == o["unit_files"]
        units = o["unit_files"]
        assert k["count_4"]["against_tree"]["in_universe"] == units, tag
        if mut is None:                    # phase A's test 1: the universe is exactly the manifest's unit files
            assert units == sum(1 for f in man["files"] if f.get("path_at_snapshot") and f["is_unit"]), tag
        assert k["count_6"]["universe_files_history_cannot_touch"] == 0, tag
        assert k["count_6"]["tree_entries_not_regular_files"] == 0
        assert k["count_6"]["scan_paths_not_in_tree"] == 0
        nest = json.loads((st / "sa3_nesting" / f"{repo}.json").read_text())
        assert k["count_8"]["with_nesting_value"] == nest["measured"] and k["count_8"]["universe_files"] == units
        text = git(rehearsal.decoy / "pool" / repo, "show", f"{side['snapshot']}:.gitattributes", check=False)
        assert k["count_9"]["longest_characters"] == len(text) and not k["count_9"]["reaches_cut"], tag
        assert k["count_9"]["gitattributes_files"] == (1 if text else 0)
        assert k["count_10"]["engine"] == side["engine"] and k["count_10"]["grammar_pack"] == nest["pack"]
        assert k["count_10"]["c_family"] == (lang == "c")
        tree = ast.parse((ROOT / "tools" / "laws_units.py").read_text())
        shas = next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n, ast.Assign)
                    and getattr(n.targets[0], "id", "") == "LINGUIST_SHA256")
        assert k["count_10"]["linguist_sha256"] == shas
        gen = k["count_5"]
        if mut == "generic_dir_names":
            sys.path.insert(0, str(ROOT / "tools" / "control_repo"))
            from mutations import GENERIC_DIRS
            moved = [f["generic_dir"] for f in man["files"] if f.get("generic_dir") and f.get("path_at_snapshot")]
            F = {x["path"]: x for x in phase_a_rows(rehearsal.works[tag], repo, "file")}
            for g, pat in GENERIC_DIRS.items():
                mine = [f["path_at_snapshot"] for f in man["files"] if f.get("generic_dir") == g
                        and f.get("path_at_snapshot")]
                assert gen[pat]["excluded_only_by"] == moved.count(g), (g, gen)
                assert gen[pat]["with_scan_rows"] == sum(1 for x in mine if F[x]["scanned"]), (g, gen)
            print("\ncount 5, generic_dir_names:", json.dumps(gen))
            assert gen["_any"]["excluded_only_by"] == len(moved)
        else:
            assert gen["_any"]["excluded_only_by"] == 0, (tag, gen)
    # the .gitattributes re-inclusion: universe files the history's own rule excludes
    k = rehearsal.datacard("ctrl-gdn-attrs")
    base = rehearsal.datacard("ctrl-python-generic_dir_names")
    man = rehearsal.manifest("python-generic_dir_names")
    want = sum(1 for f in man["files"] if f.get("generic_dir") == "cache" and f.get("path_at_snapshot"))
    assert want > 0
    assert k["count_6"]["universe_files_history_cannot_touch"] == want, k["count_6"]
    assert k["count_4"]["against_tree"]["in_universe"] == base["count_4"]["against_tree"]["in_universe"] + want
    assert k["count_5"]["(^|/)cache/"]["excluded_only_by"] == 0              # no longer excluded at all
    assert k["count_9"]["longest_characters"] == base["count_9"]["longest_characters"] + len(ATTR_LINE)
    # the directory the engine never scanned: re-included by rule, absent from the scan, so not in the universe
    k = rehearsal.datacard("ctrl-pyb-attrs-thirdparty")
    b0 = rehearsal.datacard("ctrl-python-base")
    third = sum(1 for f in rehearsal.manifest("python-base")["files"]
                if (f.get("path_at_snapshot") or "").startswith("vendor/thirdparty/"))
    assert k["count_6"]["universe_files_history_cannot_touch"] == 0
    assert k["count_4"]["against_tree"]["by_reason"].get("not_scanned") == third
    assert k["count_4"]["against_tree"]["in_universe"] == b0["count_4"]["against_tree"]["in_universe"]
    print("\n.gitattributes re-inclusion: cache/", want, "files counted by count 6; vendor/thirdparty/", third,
          "files not scanned by the engine")


def test_4g_no_outcome_side_string_in_any_output(rehearsal):
    """markers planted in one decoy's outcome file and link harvest (a path and commit hashes that appear nowhere
    else) occur in no output, run log, preflight, data card, scratch file or terminal line; nothing label-side
    was bound (2c), which is why"""
    text = all_output_text(rehearsal.out, rehearsal.scratch) + rehearsal.ran.stdout + rehearsal.ran.stderr
    for m in (MARK_SHA, MARK_SHA[::-1], MARK_PATH, MARK_VAL, "zz_marker_dir_q9x7", "outcome_only_marker"):
        assert m not in text, m
    assert MARK_PATH in (rehearsal.decoy / "study/sa3_outcomes/ctrl-pyb-marked.json").read_text()   # it was there
    # the terminal: repo, stage, status only
    for line in rehearsal.ran.stdout.splitlines():
        parts = line.split()
        assert (len(parts) == 3 and parts[1] in ("preflight", "copy", "tables")) or \
            (len(parts) == 4 and parts[1] == "silence"), line


def test_4h_run_log_and_study_card(rehearsal):
    log = json.loads((rehearsal.out / "run_log.json").read_text())
    assert log["manifest"]["unchanged"] is True, log["manifest"]
    assert len(log["header"]) == 5
    for repo, rec in log["repos"].items():
        assert rec["tables"]["status"] == "ok", (repo, rec["tables"])
        assert rec["silence_edc5c53"]["status"] == rec["silence_8fb7fe0"]["status"] == "ok", repo
    assert log["repos"]["ctrl-python-bot_merges"]["tables"]["invariants"] == {7: 1} or \
        log["repos"]["ctrl-python-bot_merges"]["tables"]["invariants"] == {"7": 1}
    card = json.loads((rehearsal.out / "study_card.json").read_text())
    assert set(card) == {"what", "run", "count_1", "count_1_placebo_check", "repos"}
    assert card["count_1_placebo_check"]["status"] == "equal", card["count_1_placebo_check"]
    blob = json.dumps(card)
    import re
    k10 = card["repos"]["ctrl-python-base"]["count_10"]
    for known in (k10["engine"], k10["linguist_commit_laws_units"]):    # provenance (count 10), not repo commits
        blob = blob.replace(known, "")
    assert not re.search(r"\b[0-9a-f]{40}\b", blob), "a commit hash in the study card"
    for repo in card["repos"]:
        for row in rehearsal.rows(repo, "file")[:50]:
            assert row["path"] not in blob, row["path"]


# ========================================================================================== 5. count 1
def test_5_silence_stub_equals_real_outcomes(rehearsal, tmp_path):
    """on every control repository, silence with the stub equals silence with the decoy's real outcome file,
    for every cell, under both versions of the scorer; each version is that commit's own file"""
    sc = rehearsal.scratch
    code_sums = json.loads((sc / "code_sha256.json").read_text())
    for v in SL.VERSIONS:
        want = subprocess.run(["git", "-C", str(ROOT), "-c", "gc.auto=0", "rev-parse", f"{v}:tools/sa3_score.py"],
                              capture_output=True, text=True, env={**os.environ, "GIT_NO_LAZY_FETCH": "1"}).stdout.strip()
        got = subprocess.run(["git", "hash-object", str(sc / "code" / v / "tools" / "sa3_score.py")], capture_output=True,
                             text=True).stdout.strip()
        assert got == want, v
        assert "tools/sa3_score.py" in code_sums[v]
    sig = {v: json.loads((sc / "ctrl-python-base" / f"silence_{v}" / "result.json").read_text())["silent_signature"]
           for v in SL.VERSIONS}
    assert sig["edc5c53"].startswith("(x") and "name" not in sig["edc5c53"] and "name" in sig["8fb7fe0"]
    checked = 0
    for lang, mut in CONTROLS:
        repo = f"ctrl-{lang}-{mut or 'base'}"
        real = rehearsal.decoy / "study" / "sa3_outcomes" / f"{repo}.json"
        for v in SL.VERSIONS:
            stubbed = json.loads((sc / repo / f"silence_{v}" / "result.json").read_text())
            rd = tmp_path / f"{repo}-{v}"
            rd.mkdir()
            res = SL.run_one(repo, v, sc, rd, sc / repo / "copy" / "db", rehearsal.decoy / "study",
                             P.LINGUIST_HOST, sc / "stubs", outcome_src=real)
            assert "silent" in res, (repo, v, res.get("error"))
            assert res["listing"] == stubbed["listing"]
            assert res["silent"] == stubbed["silent"], (repo, v)
            assert len(res["silent"]) == 23
            checked += len(res["silent"])
    assert checked == 23 * 2 * len(CONTROLS)
    c1 = json.loads((rehearsal.out / "study_card.json").read_text())["count_1"]
    print("\ncount 1 on the controls:", json.dumps(c1["differ_by_measure"]))
    assert set(c1["differ_by_measure"]) <= {m for m, v in json.loads(
        (sc / "ctrl-python-base" / "silence_8fb7fe0" / "result.json").read_text())["predictors"].items()}


def test_5b_real_outcome_never_bound_from_a_data_root(tmp_path):
    with pytest.raises(SR.SandboxError):
        SL.run_one("x", "8fb7fe0", tmp_path, tmp_path, tmp_path, tmp_path, tmp_path, tmp_path,
                   outcome_src=SR.STUDY / "sa3_outcomes" / "x.json")


# ===================================================================== 6. invariants: protected rows not named
def test_6_protected_rows_reported_by_number_and_count(tmp_path):
    """event and pool rows that fail invariants 4 and 5 are reported as number and count; the planted commit hash
    and path appear in no message (phase A's own check, and phase A's build_failed.json and terminal output on a
    copy of a control repository with a planted outcome row)"""
    sys.path.insert(0, str(ROOT / "tests"))
    import test_tables as TT
    t, tree = TT.valid_tables()
    t["event"].append({"repo": "r", "sha": MARK_SHA, "path": MARK_PATH, "hp": 1, "hp_allreverts": 1,
                       "tier": "issue_fix", "how": "own"})
    t["pool"].append({"repo": "r", "sha": MARK_SHA[::-1], "path": MARK_PATH})
    fails = I.check(t, tree)
    text = "\n".join(fails)
    assert "invariant 4: 1 row of protected table event fail" in text
    assert "invariant 4: 1 row of protected table pool fail" in text
    assert "invariant 5: 1 row of protected table event fail" in text
    assert "invariant 5: 1 row of protected table pool fail" in text
    for m in (MARK_SHA, MARK_SHA[::-1], MARK_PATH, "zz_marker"):
        assert m not in text
    # touch rows (not protected) are still named
    t2, tree2 = TT.valid_tables()
    t2["touch"].append({"repo": "r", "sha": "3" * 40, "path": "README.md", "ct": 1, "walk_pos": 9})
    assert any("touch('r'" in x for x in I.check(t2, tree2))


def test_6b_phase_a_build_does_not_name_a_planted_row(rehearsal, tmp_path):
    w = tmp_path / "w"
    shutil.copytree(rehearsal.works["python-base"].parent / "manifest", w, symlinks=True)
    repo = "ctrl-python-base"
    of = w / "study/sa3_outcomes" / f"{repo}.json"
    o = json.loads(of.read_text())
    o["outcomes"]["HP"]["commits"][MARK_SHA] = [MARK_PATH]
    o["outcomes"]["HP"]["files"].append(MARK_PATH)
    o["outcomes"]["control_pool"]["commits"][MARK_SHA[::-1]] = [MARK_PATH]
    of.write_text(json.dumps(o) + "\n")
    out = w / "study" / "sa3_tables_planted" / repo
    p = SB.run(["/usr/bin/python3", "-B", "tools/tables/build.py", "--repo", repo, "--out", str(out)], w,
               cwd=w / "tree", timeout=600)
    assert p.returncode == 1, p.stdout + p.stderr
    text = (out / "build_failed.json").read_text() + p.stdout + p.stderr
    assert "protected table event" in text and "protected table pool" in text
    for m in (MARK_SHA, MARK_SHA[::-1], MARK_PATH, "zz_marker"):
        assert m not in text, m


# ============================================================================== 7. phase A's import guard
def test_7_build_import_guard(tmp_path):
    """imported (not run) build.py guards too: with PHASEB_SANDBOX=1 outside the sandbox it refuses before any
    SA3 import, and without it the harness guard refuses as before"""
    for env in ({"PHASEB_SANDBOX": "1"}, {}):
        p = subprocess.run([PY, "-B", "-c", f"import sys; sys.path.insert(0, {str(TABLES)!r}); import build"],
                           capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", **env}, timeout=60)
        assert p.returncode != 0 and "SandboxError" in p.stderr and "refused" in p.stderr, p.stderr[-800:]
        assert "mod1_lift" not in p.stderr


# ================================================================================ 8. a symlinked pool entry
def test_8_symlinked_clone(rehearsal, tmp_path):
    """pool/<repo> a symbolic link to a clone elsewhere under scratch (as in the real pool): the same four table
    hashes; the guard sees the clone mounted read-only (it passed, and a listing shows the bound mount ro); the
    manifest covers the linked clone's .git (packs, refs, reflogs)"""
    src = rehearsal.decoy
    repo = "ctrl-python-base"
    d = tmp_path / "decoy"
    for sub in ("history", "sa3_scans", "sa3_nesting"):
        (d / "study" / sub).mkdir(parents=True)
    for sub, name in (("history", ".db"), ("sa3_scans", ".json"), ("sa3_scans", "_master.db"),
                      ("sa3_scans", "_master.db-wal"), ("sa3_scans", "_master.db-shm"), ("sa3_nesting", ".json")):
        if (src / "study" / sub / f"{repo}{name}").exists():
            shutil.copy2(src / "study" / sub / f"{repo}{name}", d / "study" / sub / f"{repo}{name}")
    elsewhere = tmp_path / "clones-elsewhere" / repo
    shutil.copytree(src / "pool" / repo, elsewhere, symlinks=True)
    (d / "pool").mkdir()
    (d / "pool" / repo).symlink_to(elsewhere)
    shutil.copytree(src / "docs", d / "docs")
    marg = [r for r in json.loads((d / "docs/sa3_outcome_marginals.json").read_text()) if r["repo"] == repo]
    (d / "docs/sa3_outcome_marginals.json").write_text(json.dumps(marg) + "\n")
    before = {"packs": sorted(os.listdir(elsewhere / ".git/objects/pack")), "logs": listing(elsewhere / ".git/logs"),
              "refs": listing(elsewhere / ".git/refs")}
    out = tmp_path / "out"
    p = subprocess.run([PY, "-B", str(PHASE_B), "--decoy", str(d), "--out", str(out)], capture_output=True, text=True,
                       timeout=1200)
    assert p.returncode == 0, p.stdout[-2000:] + p.stderr[-2000:]
    got = json.loads((out / repo / "index.json").read_text())["tables"]
    assert {n: got[n]["hash"] for n in PUBLIC} == {n: PHASE_A["python-base"][n] for n in PUBLIC}
    log = json.loads((out / "run_log.json").read_text())
    assert log["repos"][repo]["tables"]["status"] == "ok" and log["manifest"]["unchanged"] is True
    pre = json.loads((out / "preflight.json").read_text())[repo]["clone"]
    assert pre["present"] and pre["git_dir"] == "directory" and pre["snapshot_tree_lists"]
    # the guard's own view: inside a tables-like sandbox the clone is a read-only mount, and the guard passes
    spec, rd, code = _listing_spec(tmp_path, P.declared(d / "study", repo), (repo, str(d / "pool" / repo)))
    q = SR.run(["/usr/bin/python3", "-I", "-B", "-c",
                "import sys; sys.path.insert(0, sys.argv[1]); import sandbox_ro as SR, json; "
                "m = {mp: o for mp, fs, o in SR.mounts()}; print(json.dumps([SR.inside_ro(), m.get(sys.argv[2])]))",
                str(code / "tools/harness"), str(SR.POOL / repo)], spec, rd, rd, timeout=60)
    assert q.returncode == 0, q.stderr
    (ok, why), opts = json.loads(q.stdout)
    assert ok, why
    assert opts is not None and "ro" in opts.split(","), opts
    # the manifest covers the linked clone's .git
    man = json.loads((out.parent / "out.scratch" / "manifest_before.json").read_text())["entries"]
    keys = set(man)
    assert {f"pool/{repo}/.git/objects/pack/{x}" for x in before["packs"]} <= keys
    assert {f"pool/{repo}/.git/logs/{x}" for x in before["logs"]} <= keys
    assert {f"pool/{repo}/.git/refs/{x}" for x in before["refs"]} <= keys
    assert before["packs"] and before["logs"]
    assert sorted(os.listdir(elsewhere / ".git/objects/pack")) == before["packs"]
    assert listing(elsewhere / ".git/logs") == before["logs"] and listing(elsewhere / ".git/refs") == before["refs"]
    assert (d / "pool" / repo).is_symlink()
