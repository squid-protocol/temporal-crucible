#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Private helpers of tools/compare/: loading modules by file under unique names (tools/owner/DECISIONS.md 29),
the shared floating-point encoding, and the guard on the statistics module the comparison scorer loads.

No module of tools/compare/ is ever imported by its bare name, and none puts tools/compare/ on sys.path: the
bare names `tables`, `compare` and `seal` are taken elsewhere (tools/tables/, tools/harness/compare.py,
tools/blind/seal.py and tools/owner/seal.py).
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
WORKTREE = TOOLS.parent


def load_path(path: Path, name: str):
    """the module at `path` under sys.modules[name]; loaded once per name"""
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


def sibling(name: str):
    """tools/compare/<name>.py as tools_compare_<name>"""
    return load_path(HERE / f"{name}.py", f"tools_compare_{name}")


def canon():
    """tools/tables/canon.py (it imports `schema` by its bare name, a name only tools/tables/ uses)"""
    p = str(TOOLS / "tables")
    if p not in sys.path:
        sys.path.append(p)
    return load_path(TOOLS / "tables" / "canon.py", "tools_compare_tables_canon")


def sandbox_ro():
    """tools/harness/sandbox_ro.py: the module phase B uses (its own `import sandbox` is a harness-only name)"""
    p = str(TOOLS / "harness")
    if p not in sys.path:
        sys.path.append(p)
    if "sandbox_ro" in sys.modules and Path(sys.modules["sandbox_ro"].__file__).resolve() == \
            (TOOLS / "harness" / "sandbox_ro.py").resolve():
        return sys.modules["sandbox_ro"]
    return load_path(TOOLS / "harness" / "sandbox_ro.py", "sandbox_ro")


def harness_sandbox():
    p = str(TOOLS / "harness")
    if p not in sys.path:
        sys.path.append(p)
    if "sandbox" in sys.modules and Path(sys.modules["sandbox"].__file__).resolve() == \
            (TOOLS / "harness" / "sandbox.py").resolve():
        return sys.modules["sandbox"]
    return load_path(TOOLS / "harness" / "sandbox.py", "sandbox")


def phase_b():
    sandbox_ro()
    return load_path(TOOLS / "tables" / "phase_b.py", "tools_compare_tables_phase_b")


def owner_report():
    """tools/owner/report.py under the name tools/owner's own loader gives it (DECISIONS 29 there)"""
    return load_path(TOOLS / "owner" / "report.py", "tools_owner_report")


# ------------------------------------------------------------------------------------------ number encoding
def enc(v: float):
    """a float64 as JSON-safe text that round-trips every bit: float.hex, with NaN and the infinities by name"""
    v = float(v)
    if math.isnan(v):
        return "nan"
    if math.isinf(v):
        return "inf" if v > 0 else "-inf"
    return v.hex()


def dec(s) -> float:
    if s == "nan":
        return float("nan")
    if s == "inf":
        return float("inf")
    if s == "-inf":
        return float("-inf")
    return float.fromhex(s)


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# --------------------------------------------------------------------------- the sealed statistics module
STATS_IMPORTS = {"__future__", "sys", "numpy", "scipy.stats"}


def stats_imports(path: Path) -> set[str]:
    """every module the file imports, read from its source by ast (never executed)"""
    tree = ast.parse(Path(path).read_text())
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            out.add(node.module or "")
    return out


def load_sealed_stats(sealed: Path):
    """the statistics module of the sealed copies (sealed/tools/sa3_stats.py), loaded by file under a name that
    carries its hash, after its source was checked to import nothing but sys, numpy and scipy.stats: a module
    that is pure arithmetic may run in this process; anything else is refused"""
    p = Path(sealed) / "tools" / "sa3_stats.py"
    got = stats_imports(p)
    if not got <= STATS_IMPORTS:
        raise RuntimeError(f"{p}: imports {sorted(got - STATS_IMPORTS)}; only {sorted(STATS_IMPORTS)} are allowed "
                           "in-process")
    return load_path(p, "tools_compare_sealed_stats_" + sha256(p)[:16])


def literal(path: Path, name: str):
    """a module-level constant of a source file, by ast.literal_eval of its assignment (never imported);
    `A = B = 200` chains included"""
    tree = ast.parse(Path(path).read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)
