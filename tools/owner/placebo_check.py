#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The placebo output reproduced (docs/process/owner_job_spec.md section 2; Amendment 5 section 9, layer 2).

Runs INSIDE the read-only sandbox (tools/owner/prepare.py's stage `placebo`). The reference scorer's
`stage_placebo` is called unchanged from a copy of the code under the protected directory, `<ref>/tools`, bound
read-only; its `ROOT` is `<ref>` (its own `Path(__file__).resolve().parent.parent`), so it reads
`<ref>/docs/sa3_outcome_marginals.json` and writes `<ref>/docs/sa3_placebo.json`, a directory bound read-write
that holds a copy of the marginals file and nothing else. The committed file is never bound writable: a copy of
it is bound read-only for the comparison, which also runs here and returns a verdict:

  bytes_equal     the regenerated file has the committed file's bytes
  numbers_equal   bytes differ; same structure, every string and boolean equal, every number within 1e-9
                  (absolute)
  differs         anything else; the largest absolute difference among numbers and how many differ, not which
  failed          the stage did not complete (prepare.py maps the exception's type to a fixed code)

The import recorder: the modules in sys.modules whose file lies in `<ref>/tools` after `stage_placebo` returned,
each with the SHA-256 of the file it was loaded from. `fingerprint()` is the runtime part of the seal: the
interpreter, the distributions of every loaded top-level module, git and tar, the linear-algebra libraries mapped
into the process (/proc/self/maps), and the environment variables that can change a result.
"""
from __future__ import annotations

import hashlib
import importlib.metadata as md
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOL = 1e-9
LIB_RX = re.compile(r"lib(blas|cblas|lapack|openblas|mkl|blis|atlas|gfortran|quadmath|flexiblas)[^/]*\.so[^/]*$")
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


ENV_VARS = owner_module("report").ENV_VARS


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------ the comparison
def compare(new: bytes, old: bytes) -> dict:
    if new == old:
        return {"verdict": "bytes_equal", "largest_difference": 0.0, "numbers_differing": 0,
                "integer_fields_equal": True}
    try:
        a, b = json.loads(new), json.loads(old)
    except ValueError:
        return {"verdict": "differs", "largest_difference": None, "numbers_differing": None,
                "integer_fields_equal": None}
    st = {"largest": 0.0, "differ": 0, "ints_equal": True, "other": 0}

    def num(x):
        return (isinstance(x, (int, float))) and not isinstance(x, bool)

    def walk(x, y):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in set(x) | set(y):
                if k in x and k in y:
                    walk(x[k], y[k])
                else:
                    st["other"] += 1
        elif isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y):
                st["other"] += 1
            for u, v in zip(x, y):
                walk(u, v)
        elif num(x) and num(y):
            if isinstance(x, int) and isinstance(y, int) and x != y:
                st["ints_equal"] = False
            if isinstance(x, float) and isinstance(y, float) and math.isnan(x) and math.isnan(y):
                return
            d = abs(float(x) - float(y))
            if d != d or d == math.inf:
                st["differ"] += 1
                return
            st["largest"] = max(st["largest"], d)
            if d > TOL:
                st["differ"] += 1
        elif x != y or type(x) is not type(y):
            st["other"] += 1
    walk(a, b)
    ok = st["differ"] == 0 and st["other"] == 0
    return {"verdict": "numbers_equal" if ok else "differs", "largest_difference": float(st["largest"]),
            "numbers_differing": st["differ"] + st["other"], "integer_fields_equal": st["ints_equal"]}


# ------------------------------------------------------------------------------------------ the fingerprint
def _version_of(argv: list[str]) -> tuple[str | None, str | None]:
    exe = shutil.which(argv[0])
    if not exe:
        return None, None
    p = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    m = re.search(r"(\d+(?:\.\d+)+)", p.stdout.splitlines()[0] if p.stdout else "")
    return (m.group(1) if m else None), sha256_file(Path(os.path.realpath(exe)))


def libraries() -> dict[str, str]:
    """the linear-algebra (and Fortran runtime) shared objects mapped into this process: file name -> SHA-256"""
    out = {}
    with open("/proc/self/maps") as fh:
        for line in fh:
            parts = line.split(None, 5)
            if len(parts) == 6 and parts[5].strip().startswith("/"):
                path = parts[5].strip()
                if LIB_RX.search(os.path.basename(path)) and os.path.isfile(path):
                    real = os.path.realpath(path)
                    out[os.path.basename(real)] = sha256_file(Path(real))
    return dict(sorted(out.items()))


def fingerprint() -> dict:
    tops = {n.split(".")[0] for n in list(sys.modules)}
    dist_of = md.packages_distributions()
    packages = {}
    for t in sorted(tops):
        names = dist_of.get(t)
        if not names:                                   # a distribution without RECORD (Debian's): by name
            try:
                names = [md.distribution(t).metadata.get("Name")]
            except (md.PackageNotFoundError, ValueError):
                names = []
        for d in names:
            if not d:
                continue
            try:
                packages[d] = md.version(d)
            except md.PackageNotFoundError:
                pass
    git_v, git_h = _version_of(["git", "--version"])
    tar_v, tar_h = _version_of(["tar", "--version"])
    env = {}
    for k in ENV_VARS:
        v = os.environ.get(k)
        env[k] = None if v is None else \
            (int(v) if v.isdigit() and len(v) < 7 else hashlib.sha256(v.encode()).hexdigest())
    return {"python": platform.python_version(), "python_sha256": sha256_file(Path(os.path.realpath(sys.executable))),
            "packages": dict(sorted(packages.items())), "git": git_v, "git_sha256": git_h, "tar": tar_v,
            "tar_sha256": tar_h, "libraries": libraries(), "environment": env}


def exercise(ref_tools: Path) -> None:
    """the runtime stage: import the reference scorer and use its linear algebra on made-up numbers, so that the
    same libraries are mapped as after the placebo stage (no study input is read)"""
    sys.path.insert(0, str(ref_tools))
    import numpy as np
    import sa3_score as SC
    assert Path(SC.__file__).resolve().parent == ref_tools.resolve()
    x = np.arange(1.0, 101.0)
    SC.fit_size_model(x, np.log(x), score=False)
    SC.fit_size_model(x, np.log(x), score=True)
    SC.sps.t.ppf(0.99, 10)


# ------------------------------------------------------------------------------------------------ the stage
def stage(ref_root: Path, committed: Path, rundir: Path) -> dict:
    tools = (ref_root / "tools").resolve()
    sys.path.insert(0, str(tools))
    import sa3_score as SC                                      # the reference file, from the reference copy
    assert Path(SC.__file__).resolve().parent == tools, "the reference scorer was not the copy"
    assert SC.DOCS.resolve() == (ref_root / "docs").resolve(), "the scorer's docs directory is not the copy's"
    out = SC.DOCS / "sa3_placebo.json"
    if out.exists():
        raise FileExistsError("a regenerated placebo file exists before the stage ran")
    SC.stage_placebo()
    modules = {}
    for name, m in sorted(sys.modules.items()):
        f = getattr(m, "__file__", None)
        if f and Path(f).resolve().parent == tools:
            modules[name] = sha256_file(Path(f).resolve())
    res = compare(out.read_bytes(), committed.read_bytes())
    fp = fingerprint()
    (rundir / "placebo_fingerprint.json").write_text(json.dumps(fp, indent=1) + "\n")   # protected directory
    return {**res, "modules": modules, "libraries": fp["libraries"]}
