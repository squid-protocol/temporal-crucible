#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The read-only, declared-inputs sandbox of stored tables phase B (docs/process/tables_phase_b_spec.md), and its
guard. tools/harness/sandbox.py is not changed and not used for this: there the study path is a writable WORK;
here it is an empty read-only tmpfs into which only one repo's declared files are bound, read-only.

    python tools/harness/sandbox_ro.py exec -- CMD...     # the in-sandbox guard: refuses outside it, then execs

Mount order (bwrap applies its arguments in order; bind sources are resolved on the host by bwrap itself):

  1. --ro-bind / /, --dev /dev, --proc /proc
  2. --tmpfs over each hidden root: /nvme-data, /srv/storage_16tb/projects (laws-study, the clone pool, every
     checkout), /home/joe (~/.blind, ~/.ssh, ~/.claude, ~/.cache), /tmp
  3. --tmpfs at the study path (laws-study/pilot) and at the pool path (temporal-crucible-pool): empty
  4. --bind each read-write directory (one output directory, one scratch directory) at its own path
  5. --ro-bind each required read-only source (the code), then --ro-bind-try each declared input: a repo's
     files at their study paths, its clone at <pool>/<repo>, GitHub's two lists. A declared file that does not
     exist is simply absent inside (the launcher never stats it; the in-sandbox preflight reports it)
  6. --remount-ro every tmpfs of steps 2 and 3, and /dev
  7. --unshare-net --unshare-ipc --unshare-pid --unshare-uts --die-with-parent --new-session --clearenv, an
     explicit environment (git: GIT_NO_LAZY_FETCH=1, gc.auto=0, maintenance.auto=false, no system config)

The engine export is not bound: nothing in phase B runs it (DECISIONS.md, phase B).

One more allowed read-write root (docs/process/owner_job_spec.md, "Where things are written"): directories
strictly inside PROTECTED_ROOT, the owner-run job's protected root, outside the study directory, this repository
and every session scratch root. It is under the projects root, so every sandbox hides it unless it binds one of
its directories. Tests name another root with `name_protected_root_for_tests`, which accepts only a directory
under a session scratch root, so it can never widen where a real run may write.

The guard (`inside_ro`, `assert_inside_ro`, `exec`) reads /proc/self/mountinfo and /proc/net/dev and nothing
else; it never stats, opens or lists a target path. It passes only when: / is read-only; each hidden root is a
read-only tmpfs; the study path and the pool path are read-only tmpfs mounts; every mount at or under a hidden
root is read-only except exactly the declared read-write directories (PHASEB_RW), none of which may lie in the
study path, the pool, laws-study, /nvme-data or ~/.blind; the declared clone mount (PHASEB_CLONE), if any, is
read-only; and no network interface but `lo` exists.
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sandbox as SB  # noqa: E402   constants only; SB.run / SB.bwrap_argv are never called from here

BWRAP = SB.BWRAP
PROJECTS = SB.PROJECTS
LAWS = SB.LAWS
STUDY = SB.PILOT                          # mod1_lift.STUDY: the study path every SA3 tool has compiled in
POOL = SB.POOL_REAL                       # the pool path inside (EXPOSURE_POOL); a repo's clone is POOL/<repo>
HOME = SB.HOME
HIDDEN = SB.HIDDEN                        # /nvme-data, projects root, home, /tmp
FORBIDDEN = (STUDY, LAWS, Path("/nvme-data"), POOL, HOME / ".blind")
WORKTREE = SB.WORKTREE
ALLOWED_RW_ROOTS = (HOME / ".claude" / "jobs", Path("/tmp"))
PROTECTED_ROOT = PROJECTS / "temporal-crucible-protected"     # the owner-run job's protected root (a constant)
_test_protected_root: Path | None = None
SandboxError = SB.SandboxError


def _under(p: Path, root: Path) -> bool:
    return p == root or root in p.parents


def protected_roots() -> tuple[Path, ...]:
    """the production protected root, and the one a test has named, if any"""
    return (PROTECTED_ROOT,) + ((_test_protected_root,) if _test_protected_root is not None else ())


def name_protected_root_for_tests(p: Path | None) -> None:
    """TESTS ONLY: name a throwaway directory as a second protected root (None forgets it). It must lie under a
    session scratch root and outside every data root and this repository. A string test."""
    global _test_protected_root
    if p is None:
        _test_protected_root = None
        return
    p = Path(os.path.abspath(p))
    if any(_under(p, b) for b in FORBIDDEN + (WORKTREE, PROTECTED_ROOT)) or \
            not any(a in p.parents for a in ALLOWED_RW_ROOTS):
        raise SandboxError(f"{p}: a test protected root must be under {' or '.join(map(str, ALLOWED_RW_ROOTS))}")
    _test_protected_root = p


def in_protected_root(p: Path) -> bool:
    """strictly inside a protected root (the root itself is never a read-write directory). A string test."""
    p = Path(os.path.abspath(p))
    return any(r in p.parents for r in protected_roots())


def check_rw(p: Path) -> Path:
    """A read-write directory: absolute, under ~/.claude/jobs or /tmp, or strictly inside the protected root;
    outside every data root and this repository. A string test: nothing is opened or statted."""
    p = Path(os.path.abspath(p))
    if PROTECTED_ROOT in p.parents:
        for bad in FORBIDDEN + (WORKTREE,):
            if _under(p, bad):
                raise SandboxError(f"{p} is inside {bad}; refused")
        return p
    for bad in FORBIDDEN + (PROJECTS, WORKTREE):
        if _under(p, bad):
            raise SandboxError(f"{p} is inside {bad}; refused")
    if not any(a in p.parents for a in ALLOWED_RW_ROOTS):
        raise SandboxError(f"{p} must be under {' or '.join(map(str, ALLOWED_RW_ROOTS))}")
    return p


def check_dst(p: Path) -> Path:
    """An in-sandbox destination of a read-only bind: under the study path, the pool path or a hidden root."""
    p = Path(os.path.abspath(p))
    if not (_under(p, STUDY) or _under(p, POOL) or any(_under(p, h) for h in HIDDEN)):
        raise SandboxError(f"bind destination {p} is outside the study path, the pool and the hidden roots")
    return p


@dataclass
class Spec:
    rw: list[Path]                                     # read-write directories (must exist; bound at their path)
    code: list[Path] = field(default_factory=list)     # read-only, required (--ro-bind), each at its own path
    inputs: list[tuple[str, Path]] = field(default_factory=list)   # (host source, in-sandbox dst), --ro-bind-try
    clone: tuple[str, str] | None = None               # (repo name, host source): bound read-only at POOL/<repo>
    env: dict = field(default_factory=dict)
    cwd: Path | None = None
    # TESTS ONLY: (host source, dst) bound READ-WRITE, to prove the guard refuses a writable study path or clone
    unsafe_rw_for_tests: list[tuple[str, Path]] = field(default_factory=list)


def environment(spec: Spec, home: Path, tmp: Path) -> dict:
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(home), "TMPDIR": str(tmp),
        "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TZ": "UTC",
        "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(home / ".gitconfig"),
        "GIT_CONFIG_COUNT": "3", "GIT_CONFIG_KEY_0": "gc.auto", "GIT_CONFIG_VALUE_0": "0",
        "GIT_CONFIG_KEY_1": "maintenance.auto", "GIT_CONFIG_VALUE_1": "false",
        "GIT_CONFIG_KEY_2": "safe.directory", "GIT_CONFIG_VALUE_2": "*",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CEILING_DIRECTORIES": str(POOL),
        "EXPOSURE_POOL": str(POOL),
        "PHASEB_SANDBOX": "1",
        "PHASEB_RW": ":".join(str(p) for p in spec.rw),
        "PHASEB_CLONE": str(POOL / spec.clone[0]) if spec.clone else "",
    }
    env.update(spec.env)
    return env


def bwrap_argv(spec: Spec, env: dict) -> list[str]:
    rw = [check_rw(p) for p in spec.rw]
    a = [BWRAP, "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc"]
    for h in HIDDEN:
        a += ["--tmpfs", str(h)]
    a += ["--tmpfs", str(STUDY), "--tmpfs", str(POOL)]
    for p in rw:
        a += ["--bind", str(p), str(p)]
    for p in spec.code:
        a += ["--ro-bind", str(p), str(p)]
    for src, dst in spec.inputs:
        a += ["--ro-bind-try", str(src), str(check_dst(dst))]
    if spec.clone:
        name, src = spec.clone
        if "/" in name or name in ("", ".", ".."):
            raise SandboxError(f"bad repo name {name!r}")
        a += ["--ro-bind-try", str(src), str(POOL / name)]
    for src, dst in spec.unsafe_rw_for_tests:
        a += ["--bind", str(src), str(dst)]
    for h in HIDDEN + (STUDY, POOL, Path("/dev")):
        a += ["--remount-ro", str(h)]
    a += ["--unshare-net", "--unshare-ipc", "--unshare-pid", "--unshare-uts", "--die-with-parent",
          "--new-session", "--clearenv"]
    for k, v in env.items():
        a += ["--setenv", k, v]
    a += ["--chdir", str(spec.cwd or rw[0])]
    return a


def run(argv: list[str], spec: Spec, home: Path, tmp: Path, timeout: float | None = None,
        guard: bool = True, stdout=None) -> subprocess.CompletedProcess:
    """Run argv inside the read-only sandbox. home and tmp must lie inside one of spec.rw. With guard (the
    default) argv is started through this module's own guard (`exec`), which must therefore be reachable inside:
    this file is in the code tree the launcher copies and binds (spec.code)."""
    env = environment(spec, home, tmp)
    inner = argv
    if guard:
        me = next((c / "tools" / "harness" / "sandbox_ro.py" for c in spec.code
                   if (c / "tools" / "harness" / "sandbox_ro.py").is_file()), None)
        if me is None:
            raise SandboxError("sandbox_ro.py is not in any bound code tree")
        inner = ["/usr/bin/python3", "-I", "-B", str(me), "exec", "--", *argv]
    kw = {"stdout": stdout, "stderr": subprocess.STDOUT} if stdout is not None else {"capture_output": True}
    return subprocess.run(bwrap_argv(spec, env) + inner, text=True, errors="replace", timeout=timeout, **kw)


# ------------------------------------------------------------------------------------------------ the guard
def mounts() -> list[tuple[str, str, str]]:
    """(mount point, filesystem type, per-mount options), in the kernel's order; no path is touched."""
    out = []
    with open("/proc/self/mountinfo") as fh:
        for line in fh:
            left, _, right = line.partition(" - ")
            f = left.split()
            mp = f[4].replace("\\040", " ").replace("\\011", "\t").replace("\\012", "\n").replace("\\134", "\\")
            out.append((mp, right.split()[0] if right else "", f[5]))
    return out


def inside_ro(rw: list[str] | None = None, clone: str | None = None) -> tuple[bool, str]:
    """(True, '') only inside phase B's read-only sandbox. Reads the mount table and the interface list only."""
    rw = [x for x in (os.environ.get("PHASEB_RW", "").split(":") if rw is None else rw) if x]
    clone = os.environ.get("PHASEB_CLONE", "") if clone is None else clone
    top: dict[str, tuple[str, str]] = {}
    for mp, fs, opts in mounts():                    # a later entry at the same point covers the earlier one
        top[mp] = (fs, opts)

    def ro(mp: str) -> bool:
        return "ro" in top[mp][1].split(",")

    if "/" not in top or not ro("/"):
        return False, "the root is not mounted read-only"
    for h in HIDDEN + (STUDY, POOL):
        if str(h) not in top or top[str(h)][0] != "tmpfs" or not ro(str(h)):
            return False, f"{h} is not a read-only tmpfs mount: not inside the read-only sandbox"
    for x in rw:
        p = Path(x)
        if not p.is_absolute() or any(_under(p, b) for b in FORBIDDEN):
            return False, f"declared read-write directory {x} is in a data root"
    roots = [str(h) for h in HIDDEN]
    for mp, (fs, opts) in top.items():
        if any(mp == r or mp.startswith(r.rstrip("/") + "/") for r in roots) and not ro(mp) and mp not in rw:
            return False, f"{mp} is mounted read-write and is not a declared read-write directory"
    if clone:
        if clone not in top:
            return False, f"the declared clone {clone} is not mounted"
        if not ro(clone):
            return False, f"the clone {clone} is not mounted read-only"
    with open("/proc/net/dev") as fh:
        ifaces = [ln.split(":")[0].strip() for ln in fh.readlines()[2:]]
    if any(i != "lo" for i in ifaces):
        return False, f"network interfaces {ifaces}: the network is not unshared"
    return True, ""


def assert_inside_ro() -> None:
    ok, why = inside_ro()
    if not ok:
        raise SandboxError(f"refused: phase B may touch the study path only inside its read-only sandbox ({why})")


def main() -> int:
    argv = sys.argv[1:]
    if len(argv) < 3 or argv[0] != "exec" or argv[1] != "--":
        print("usage: sandbox_ro.py exec -- CMD...", file=sys.stderr)
        return 2
    try:
        assert_inside_ro()
    except SandboxError as e:
        print(str(e), file=sys.stderr)
        return 3
    os.execvp(argv[2], argv[2:])


if __name__ == "__main__":
    raise SystemExit(main())
