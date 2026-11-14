#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The bwrap sandbox every SA3 tool, the engine and every git call of the pipeline runs in (harness_spec.md).

    python tools/harness/sandbox.py shell --work WORK -- CMD...    # run CMD inside the sandbox
    python tools/harness/sandbox.py exec  --work WORK -- CMD...    # the in-sandbox guard: refuses outside it

Inside the sandbox the whole filesystem is read-only; the study directory's path is WORK/study; the rest of
/srv/storage_16tb/projects (the rest of laws-study, the clone pool, every other checkout) is an empty read-only
tmpfs except the frozen engine export, bound read-only; /nvme-data, the home directory (~/.blind, ~/.ssh,
~/.claude, ~/.cache) and /tmp are empty read-only tmpfs; the network is unshared; only WORK is writable.

Nothing here opens, lists or stats the study directory, /nvme-data, the pool or ~/.blind from outside the
sandbox: the guard decides "inside or not" from /proc/self/mountinfo (the kernel's mount table) before it
touches any path, and the mount list below names those paths only as bwrap arguments.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

BWRAP = "/usr/bin/bwrap"
PROJECTS = Path("/srv/storage_16tb/projects")
LAWS = PROJECTS / "gitgalaxy" / "laws-study"
PILOT = LAWS / "pilot"                      # the study directory (STUDY in mod1_lift.py and copies)
ENGINE = LAWS / "engine-f71181aae7"         # sa3_scan.ENGINE: code, bound read-only
POOL_REAL = PROJECTS / "temporal-crucible-pool"
HOME = Path("/home/joe")
USER_SITE = HOME / ".local" / "lib" / "python3.12" / "site-packages"   # tree_sitter_language_pack 1.20.0 lives here
# a setuptools editable-install hook in the user site would add a finder pointing into /nvme-data; it is
# blanked inside the sandbox (bound over by /dev/null) so no import can even try that path
EDITABLE_PTH = USER_SITE / "__editable__.gitgalaxy-2.9.2.dev492+gfaea7488f.pth"
HIDDEN = (Path("/nvme-data"), PROJECTS, HOME, Path("/tmp"))   # empty, read-only tmpfs inside
LINGUIST_SUB = Path(".cache/temporal-crucible/linguist-e0c78d62c42a")
# tree_sitter_language_pack 1.20.0 loads its grammars from a download cache under $HOME and would fetch them
# from GitHub if absent; the host's cache of exactly that version is bound read-only at the same place under
# WORK/home (no network inside)
TSLP_SUB = Path(".cache/tree-sitter-language-pack/v1.20.0")
FORBIDDEN_ROOTS = (PILOT, LAWS, Path("/nvme-data"), POOL_REAL, HOME / ".blind")
WORKTREE = Path(__file__).resolve().parent.parent.parent


class SandboxError(RuntimeError):
    pass


def check_work(work: Path) -> Path:
    """WORK must be absolute, outside every hidden data root, outside this repository."""
    work = Path(os.path.abspath(work))
    for bad in FORBIDDEN_ROOTS + (PROJECTS, WORKTREE):
        if work == bad or bad in work.parents:
            raise SandboxError(f"WORK {work} is inside {bad}; refused")
    allowed = (HOME / ".claude" / "jobs", Path("/tmp"))
    if not any(a in work.parents for a in allowed):
        raise SandboxError(f"WORK {work} must be under {' or '.join(map(str, allowed))}")
    return work


def prepare(work: Path) -> Path:
    """Create WORK's fixed layout (study, pool, home, tmp) and the private git config. Idempotent."""
    work = check_work(work)
    for d in ("study", "pool", "home", "tmp", "tree", "shm", f"home/{TSLP_SUB}"):
        (work / d).mkdir(parents=True, exist_ok=True)       # the last is the parser cache's mount point
    gc = work / "home" / ".gitconfig"
    if not gc.exists():
        gc.write_text("[gc]\n\tauto = 0\n[maintenance]\n\tauto = false\n[user]\n\tname = harness\n"
                      "\temail = harness@invalid\n[safe]\n\tdirectory = *\n")
    return work


def copy_linguist_cache(work: Path) -> bool:
    """Copy linguist's two lists (sha256-checked by laws_units on every read) into WORK/home. False if absent."""
    src = Path.home() / LINGUIST_SUB
    dst = work / "home" / LINGUIST_SUB
    if (dst / "vendor.yml").is_file() and (dst / "documentation.yml").is_file():
        return True
    if not ((src / "vendor.yml").is_file() and (src / "documentation.yml").is_file()):
        return False
    dst.mkdir(parents=True, exist_ok=True)
    for n in ("vendor.yml", "documentation.yml"):
        shutil.copyfile(src / n, dst / n)
    return True


def sandbox_env(work: Path, extra: dict | None = None) -> dict:
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(work / "home"),
        "TMPDIR": str(work / "tmp"),
        "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TZ": "UTC",
        "PYTHONDONTWRITEBYTECODE": "1",
        # HOME is WORK/home, so name the user site explicitly: tree_sitter_language_pack 1.20.0 is there
        "PYTHONUSERBASE": str(HOME / ".local"),
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(work / "home" / ".gitconfig"),
        "GIT_CONFIG_COUNT": "2", "GIT_CONFIG_KEY_0": "gc.auto", "GIT_CONFIG_VALUE_0": "0",
        "GIT_CONFIG_KEY_1": "maintenance.auto", "GIT_CONFIG_VALUE_1": "false",
        "GIT_CEILING_DIRECTORIES": str(work.parent),
        "GIT_TERMINAL_PROMPT": "0",
        "EXPOSURE_POOL": str(work / "pool"),
        "GITGALAXY_PATH": str(ENGINE),
        "HARNESS_WORK": str(work),
    }
    env.update(extra or {})
    return env


def bwrap_argv(work: Path, env: dict, cwd: Path) -> list[str]:
    """The mount order matters: bind the read-only root, hide by tmpfs, re-expose what is needed (sources are
    resolved on the host, so the engine can be bound back into the hidden tree), then make the hiding tmpfs
    read-only. bwrap applies the arguments in order."""
    a = [BWRAP, "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc"]
    for h in HIDDEN:
        a += ["--tmpfs", str(h)]
    a += ["--ro-bind", str(ENGINE), str(ENGINE),
          "--ro-bind", str(USER_SITE), str(USER_SITE),
          "--ro-bind", "/dev/null", str(EDITABLE_PTH),
          "--bind", str(work / "study"), str(PILOT),
          "--bind", str(work), str(work),
          "--bind", str(work / "shm"), "/dev/shm"]          # POSIX semaphores for multiprocessing, inside WORK
    if (HOME / TSLP_SUB / "libs").is_dir():
        a += ["--ro-bind", str(HOME / TSLP_SUB), str(work / "home" / TSLP_SUB)]
    for h in HIDDEN + (Path("/dev"),):
        a += ["--remount-ro", str(h)]
    a += ["--unshare-net", "--unshare-ipc", "--unshare-pid", "--unshare-uts", "--die-with-parent",
          "--new-session", "--clearenv"]
    for k, v in env.items():
        a += ["--setenv", k, v]
    a += ["--chdir", str(cwd)]
    return a


def run(argv: list[str], work: Path, cwd: Path | None = None, env_extra: dict | None = None,
        timeout: float | None = None, guard: bool = True) -> subprocess.CompletedProcess:
    """Run argv inside the sandbox. With guard (the default) the command is started through this module's
    in-sandbox guard (`exec`), which refuses unless it really is inside."""
    work = prepare(work)
    env = sandbox_env(work, env_extra)
    inner = argv
    if guard:
        me = work / "tree" / "tools" / "harness" / "sandbox.py"
        if not me.is_file():
            raise SandboxError(f"{me} missing: copy the tools tree into WORK/tree first")
        inner = ["/usr/bin/python3", "-I", "-B", str(me), "exec", "--work", str(work), "--", *argv]
    return subprocess.run(bwrap_argv(work, env, cwd or work) + inner, capture_output=True, text=True,
                          errors="replace", timeout=timeout)


# ------------------------------------------------------------------------------------------------ the guard
def _mounts() -> dict[str, tuple[str, str]]:
    """mount point -> (filesystem type, mount options), from the kernel's table; no path is touched."""
    out = {}
    with open("/proc/self/mountinfo") as fh:
        for line in fh:
            left, _, right = line.partition(" - ")
            f = left.split()
            mp = f[4].replace("\\040", " ")
            out[mp] = (right.split()[0] if right else "", f[5])
    return out


def inside(work: Path) -> tuple[bool, str]:
    """(True, '') only inside the harness sandbox for this WORK. Outside it returns before touching any path."""
    m = _mounts()
    if str(PILOT) not in m:
        return False, f"no mount at {PILOT}: not inside the sandbox"
    if "ro" not in m.get("/", ("", ""))[1].split(","):
        return False, "the root is not mounted read-only"
    for h in HIDDEN:
        fs, opts = m.get(str(h), ("", ""))
        if fs != "tmpfs" or "ro" not in opts.split(","):
            return False, f"{h} is not a read-only tmpfs"
    # only now, with the bind proven, may the study path be looked at: it must be WORK/study itself
    a, b = os.stat(PILOT), os.stat(Path(work) / "study")
    if (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino):
        return False, f"{PILOT} is not WORK/study"
    with open("/proc/net/dev") as fh:
        ifaces = [ln.split(":")[0].strip() for ln in fh.readlines()[2:]]
    if any(i != "lo" for i in ifaces):
        return False, f"network interfaces {ifaces}: the network is not unshared"
    return True, ""


def assert_inside(work: Path) -> None:
    ok, why = inside(work)
    if not ok:
        raise SandboxError(f"refused: a pipeline stage may run only inside the sandbox ({why})")


def main() -> int:
    argv = sys.argv[1:]
    cut = argv.index("--") if "--" in argv else len(argv)
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("exec", "shell"))
    ap.add_argument("--work", type=Path, required=True)
    a = ap.parse_args(argv[:cut])
    cmd = argv[cut + 1:]
    if not cmd:
        ap.error("no command")
    if a.mode == "exec":
        try:
            assert_inside(a.work)
        except SandboxError as e:
            print(str(e), file=sys.stderr)
            return 3
        os.execvp(cmd[0], cmd)
    p = run(cmd, a.work, guard=False)
    sys.stdout.write(p.stdout)
    sys.stderr.write(p.stderr)
    return p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
