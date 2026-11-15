#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The external seal (docs/process/owner_job_spec.md section 3; Amendment 5 section 2). Hashes only.

    python3 tools/owner/seal.py verify --seal O/seal.json --protected P2 --decoy DIR [--after-lock]
    python3 tools/owner/seal.py verify --seal O/seal.json --protected P2 --real --i-am-the-owner [--after-lock]

`write` is `compose()`, called by tools/owner/prepare.py at the end of a run; tools/owner/report.py writes the file.
`seal.json` holds:

  inputs         per repo on the frozen list, SHA-256 of: the history database and its -wal, the scan database and
                 its -wal, the sidecar, the link harvest and its -wal, the outcome file, the nesting file (null where
                 absent). Never a -shm: it changes on an ordinary read. Taken inside the read-only sandbox.
  lists          GitHub's two lists, as bound
  clones         per repo, the SHA-256 of the clone's HEAD commit id (the id itself is a 40-character hash; no
                 stage-provided value of that shape reaches a public file)
  code           every module the import recorder found around the placebo stage, and hist_meta by name: SHA-256,
                 git blob hash, and whether the blob equals the file at 8fb7fe0 (read-only git on this checkout)
  job_code       SHA-256 of this job's own files and of the two sandbox modules
  documents      the six documents: the registration, the consolidated text, the placebo output, the marginals
                 file, the power statement, the code review (SHA-256 and blob hash)
  lock_expected  the nine blob hashes the reference `lock` is expected to write, computed as the reference `blob()`
                 computes them (`git hash-object`: SHA-1 of "blob <length>\\0<bytes>", no filter applies here)
  runtime        interpreter, packages, git, tar, the linear-algebra libraries, the environment (the `runtime`
                 stage, in the read-only sandbox); placebo_libraries: those mapped at the end of the placebo stage

`verify` recomputes all of it except placebo_libraries (that needs the placebo run) and prints each entry that
differs, by name. `--after-lock` also compares the nine expected hashes with `docs/sa3_lock.json`: each must be
40 hexadecimal characters and equal (the reference `lock` writes empty hashes when git fails, and its own check
then passes). The seal says what the files were when it was taken; it does not prove that a run read those bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
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


RP = owner_module("report")

REF_COMMIT = "8fb7fe0"
NOT_VERIFIED = ("taken", "target", "placebo_libraries")


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ref_blobs(git_dir: Path, paths: list[str]) -> dict[str, str | None] | None:
    """path -> blob id of that path at REF_COMMIT ("" where the commit has no such file), by read-only git; None
    when the check cannot be made at all (git unavailable or failing, or the commit absent)"""
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"}
    base = ["git", "-C", str(git_dir), "-c", "gc.auto=0", "-c", "maintenance.auto=false"]
    try:
        c = subprocess.run(base + ["cat-file", "-e", f"{REF_COMMIT}^{{commit}}"], capture_output=True, env=env,
                           timeout=120)
        if c.returncode != 0:
            return None
        p = subprocess.run(base + ["cat-file", "--batch-check"], input="".join(f"{REF_COMMIT}:{x}\n" for x in paths),
                           capture_output=True, text=True, env=env, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    lines = p.stdout.splitlines()
    if p.returncode != 0 or len(lines) != len(paths):
        return None
    out = {}
    for x, line in zip(paths, lines):
        f = line.split()
        out[x] = f[0] if len(f) == 3 and f[1] == "blob" else ""
    return out


def code_entries(code_root: Path, git_dir: Path, modules: list[str]) -> dict:
    names = sorted(set(modules))
    ref = ref_blobs(git_dir, [f"tools/{m}.py" for m in names])
    out = {}
    for m in names:
        data = (code_root / "tools" / f"{m}.py").read_bytes()
        b = blob(data)
        out[m] = {"sha256": sha256(data), "blob": b,                 # None: could not be checked
                  "unchanged_since_8fb7fe0": None if ref is None else ref[f"tools/{m}.py"] == b}
    return out


def documents(docs: Path) -> dict:
    out = {}
    for n in RP.DOCUMENTS:
        f = docs / n
        data = f.read_bytes() if f.is_file() else None
        out[n] = {"sha256": sha256(data) if data is not None else None,
                  "blob": blob(data) if data is not None else None}
    return out


def lock_expected(code_root: Path, docs: Path, sealed: list[str]) -> dict:
    out = {}
    for f in sealed:
        p = code_root / f if f.startswith("tools/") else docs / f.split("/", 1)[1]
        out[f] = blob(p.read_bytes()) if p.is_file() else None
    return out


def job_code(code_root: Path) -> dict:
    return {f: sha256((code_root / f).read_bytes()) for f in RP.JOB_CODE if (code_root / f).is_file()}


def compose(job, si: dict, runtime: dict, modules: list[str], placebo_libraries: dict) -> dict:
    """the seal from validated stage values (inputs, lists, clones, runtime) and the launcher's own hashes of
    code and documents; validated again before it is returned"""
    P = owner_module("prepare")
    seal = {"taken": int(time.time()), "target": "real" if job.tgt.real else "decoy",
            "inputs": si["inputs"], "lists": si["lists"], "clones": si["clones"],
            "code": code_entries(job.code_root, job.ref_git, list(modules) + list(P.BY_NAME)),
            "job_code": job_code(job.code_root), "documents": documents(job.tgt.docs),
            "lock_expected": lock_expected(job.code_root, job.tgt.docs, job.sealed),
            "runtime": runtime, "placebo_libraries": placebo_libraries}
    RP.check(RP.SEAL, seal, "seal", job.vocab)
    return seal


def diff(old: dict, new: dict, prefix: str = "") -> list[str]:
    """names of the entries that differ; every key printed here has passed the validator in both seals"""
    out = []
    for k in sorted(set(old) | set(new)):
        if not prefix and k in NOT_VERIFIED:
            continue
        name = f"{prefix}{k}"
        a, b = old.get(k, "<absent>"), new.get(k, "<absent>")
        if isinstance(a, dict) and isinstance(b, dict):
            out += diff(a, b, name + ".")
        elif a != b:
            out.append(name)
    return out


def after_lock(seal: dict, lock_file: Path) -> list[str]:
    """the expected lock hashes against the lock file: each must be 40 hex characters and equal"""
    try:
        files = json.loads(lock_file.read_text())["files"]
    except (OSError, ValueError, KeyError, TypeError):
        return ["lock"]
    bad = []
    for f, want in sorted(seal["lock_expected"].items()):
        got = files.get(f) if isinstance(files, dict) else None
        if not (isinstance(got, str) and RP.HEX40.fullmatch(got)) or want is None or got != want:
            bad.append(f"lock.{f}")
    return bad


def verify(argv: list[str], echo=print) -> int:
    P = owner_module("prepare")
    ap = argparse.ArgumentParser(prog="seal.py verify")
    ap.add_argument("--seal", required=True)
    ap.add_argument("--protected", required=True)
    ap.add_argument("--after-lock", action="store_true")
    ap.add_argument("--decoy")
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--i-am-the-owner", action="store_true")
    ap.add_argument("--real-study", default=str(P.SR.STUDY))
    ap.add_argument("--real-pool", default=str(P.SR.POOL))
    ap.add_argument("--real-docs", default=str(P.WORKTREE / P.DOCS))
    ap.add_argument("--linguist", default=str(P.LINGUIST_HOST))
    ap.add_argument("--code-root")
    ap.add_argument("--reference-git")
    a = ap.parse_args(argv)
    try:
        P.test_root_from_env()
        tgt = P.resolve_target(a)
        seal_file = Path(os.path.abspath(a.seal))
        prot, _ = P.check_places(Path(a.protected), seal_file.parent, tgt.real)
        P.new_or_empty(prot, "protected")
    except P.Refused as e:
        print(f"seal: {e}", file=sys.stderr)
        return 2
    code_root = Path(os.path.abspath(a.code_root)) if a.code_root else P.WORKTREE
    prot.mkdir(parents=True, exist_ok=True, mode=0o700)
    job = P.Job(tgt, prot, None, code_root, echo)
    if a.reference_git:
        job.ref_git = Path(os.path.abspath(a.reference_git))
    try:
        job.setup()
        old = json.loads(seal_file.read_text())
        RP.check(RP.SEAL, old, "seal", job.vocab)
        si = job.run("seal_inputs", "*", job.everything(), {"repos": job.repos})
        rt = job.runtime()
        if si["status"] != "ok" or rt["status"] != "ok" or not job.copy_ok:
            echo("seal: a stage failed; NOT VERIFIED")
            return 1
        new = compose(job, si, rt["runtime"], [m for m in old["code"] if m not in P.BY_NAME], {})
    except RP.ReportError as e:
        echo(str(e))
        echo("seal: NOT VERIFIED")
        return 1
    bad = diff(old, new)
    if a.after_lock:
        bad += after_lock(new, tgt.docs / "sa3_lock.json")
    for name in bad:
        echo(f"differs: {name}")
    echo("VERIFIED" if not bad else f"DIFFERS {len(bad)}")
    return 0 if not bad else 1


def main() -> int:
    if sys.argv[1:2] == ["verify"]:
        return verify(sys.argv[2:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
