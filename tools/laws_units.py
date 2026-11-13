#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAWS units (methods review M3): which files are a language's source files, and which are excluded from every
network, unit and fix-size count. No data is read here beyond GitHub linguist's two path lists.

  language_of(path, dir_majority)   the panel language a path belongs to, or None
  Excluder(attrs).why(path, generated)   None for a unit, else the first rule that excludes it:
        "vendored" (i: linguist vendor.yml, or .gitattributes linguist-vendored), "documentation" (i),
        "generated" (ii: .gitattributes linguist-generated, a generated-file name, or the builder's first-5-lines
        flag), "test" (iii), "example" (iv)
  is_test(path)                     rule (iii) alone, for the "tests as callers only" sensitivity analysis

Linguist's lists are GitHub's files, so they are not copied into this repository: they are read from a cache
directory (LAWS_LINGUIST_DIR, default ~/.cache/temporal-crucible/linguist-<sha12>/) and fetched there on first use
from the pinned commit, each checked by sha256.

Two things M3 leaves open, settled here and to be listed at the scorer freeze:
  - M3 names no extensions for Rust, Kotlin and PHP (Amendment 2 admitted the last two): `.rs`; `.kt .kts`; `.php`.
  - of linguist's generated.rb only the file-name rules below are applied; its content heuristics are covered by
    the first-5-lines rule alone.
"""
from __future__ import annotations

import fnmatch
import hashlib
import os
import re
import urllib.request
from pathlib import Path, PurePosixPath

LINGUIST = "e0c78d62c42abae6122235d8e68a7aa43eef89da"  # github-linguist/linguist v9.7.0
LINGUIST_SHA256 = {"vendor.yml": "1ae9980298c7c4b89fa663f1efbab3c977818a0fcb59ddc869f2b8060a7ad345",
                   "documentation.yml": "9bcc2d965be92c009926dd9390b5a454e309d851f7b26a0f51d6570a808a8745"}

EXTS = {"c": (".c", ".h"), "cpp": (".cc", ".cpp", ".cxx", ".hh", ".hpp", ".h"), "java": (".java",), "go": (".go",),
        "python": (".py",), "jsts": (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"), "csharp": (".cs",),
        "rust": (".rs",), "kotlin": (".kt", ".kts"), "php": (".php",),
        # MOD-1 Amendment 2 (docs/moderator_registration.md): the main languages of ten drawn repos. No LAWS panel
        # language is touched -- a repo is harvested in ONE language, so these only widen what can be asked for.
        "ruby": (".rb", ".rake"), "zig": (".zig",), "swift": (".swift",), "perl": (".pl", ".pm", ".cgi"),
        "racket": (".rkt", ".rktl", ".scm", ".ss", ".sls"), "fortran": (".f", ".for", ".f90", ".f95", ".f03", ".f08"),
        "matlab": (".m",)}
TEST_PARTS = {"test", "tests", "testing", "__tests__", "spec", "testdata"}
TEST_NAMES = ("*_test.go", "test_*.py", "*_test.py", "*Test.java", "*Tests.java", "*.test.js", "*.test.ts",
              "*.spec.js", "*.spec.ts", "*_test.rb", "*_spec.rb", "*.t", "*Tests.swift", "*Test.swift")
EXAMPLE_PARTS = {"examples", "example", "samples", "benchmarks", "bench", "docs"}
GENERATED_NAMES = ("*.pb.go", "*.pb.cc", "*.pb.h", "*_pb2.py", "*_pb2_grpc.py", "*.min.js", "*.designer.cs", "*.g.cs",
                   "*.generated.cs", "*.generated.go", "zz_generated.*", "*.pb.swift", "*_generated.go", "*.g.dart")


def linguist_dir() -> Path:
    return Path(os.environ.get("LAWS_LINGUIST_DIR", str(Path.home() / ".cache/temporal-crucible" / f"linguist-{LINGUIST[:12]}")))


def linguist_patterns(name: str) -> list[re.Pattern]:
    """The regexes of linguist's `name` at the pinned commit (fetched once, sha256 checked on every read)."""
    path = linguist_dir() / name
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://raw.githubusercontent.com/github-linguist/linguist/{LINGUIST}/lib/linguist/{name}"
        with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 -- a fixed https URL at a pinned commit
            path.write_bytes(r.read())
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != LINGUIST_SHA256[name]:
        raise RuntimeError(f"{path}: not linguist {LINGUIST[:12]}'s {name} (sha256 differs)")
    return [re.compile(line[2:].strip()) for line in data.decode("utf-8").splitlines() if line.startswith("- ")]


def language_of(path: str, dir_majority: dict[str, str] | None = None) -> str | None:
    """The language whose source file `path` is. A `.h` is C++'s where C++ is the majority language of its directory
    (dir_majority[directory] == "cpp"), else C's."""
    ext = PurePosixPath(path).suffix.lower()
    if ext == ".h":
        return "cpp" if (dir_majority or {}).get(str(PurePosixPath(path).parent)) == "cpp" else "c"
    return next((lang for lang, exts in EXTS.items() if ext in exts and ext != ".h"), None)


def is_test(path: str) -> bool:
    p = PurePosixPath(path)
    parts = [x.lower() for x in p.parts[:-1]]
    if TEST_PARTS & set(parts) or any(a == "src" and b == "test" for a, b in zip(parts, parts[1:])):
        return True
    return any(fnmatch.fnmatchcase(p.name, pat) for pat in TEST_NAMES)


def _attr_rules(attrs: dict[str, str]) -> list[tuple[str, str, str, bool]]:
    """(directory of the .gitattributes, pattern, "vendored" | "generated", set?) in file order, root first."""
    out = []
    for where in sorted(attrs, key=lambda w: (w.count("/"), w)):
        base = str(PurePosixPath(where).parent)
        base = "" if base == "." else base
        for line in attrs[where].splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            pat, *flags = line.split()
            for f in flags:
                m = re.fullmatch(r"(-|!)?linguist-(vendored|generated)(=(true|false))?", f)
                if m:
                    out.append((base, pat, m.group(2), not m.group(1) and m.group(4) != "false"))
    return out


def _attr_match(base: str, pat: str, path: str) -> bool:
    if base and not path.startswith(base + "/"):
        return False
    rel = path[len(base) + 1:] if base else path
    if pat.endswith("/"):
        pat += "**"
    if "/" not in pat.rstrip("*").rstrip("/") and "/" not in pat:
        return fnmatch.fnmatchcase(PurePosixPath(rel).name, pat)  # no slash: the basename at any depth
    pat = pat.lstrip("/")
    rx = re.escape(pat).replace(r"\*\*/", "(?:.*/)?").replace(r"\*\*", ".*").replace(r"\*", "[^/]*").replace(r"\?", "[^/]")
    return re.fullmatch(rx, rel) is not None


class Excluder:
    """The M3 exclusions for one snapshot. `attrs`: {path of a .gitattributes: its text} at that snapshot."""

    def __init__(self, attrs: dict[str, str] | None = None):
        self.vendor = linguist_patterns("vendor.yml")
        self.docs = linguist_patterns("documentation.yml")
        self.rules = _attr_rules(attrs or {})

    def _attr(self, path: str, kind: str) -> bool | None:
        got = None
        for base, pat, k, on in self.rules:  # the last matching rule wins, as in git
            if k == kind and _attr_match(base, pat, path):
                got = on
        return got

    def why(self, path: str, generated: bool = False) -> str | None:
        vend, gen = self._attr(path, "vendored"), self._attr(path, "generated")
        if vend or (vend is None and any(r.search(path) for r in self.vendor)):
            return "vendored"
        if any(r.search(path) for r in self.docs):
            return "documentation"
        name = PurePosixPath(path).name
        if gen or (gen is None and (generated or any(fnmatch.fnmatchcase(name, pat) for pat in GENERATED_NAMES))):
            return "generated"
        if is_test(path):
            return "test"
        if EXAMPLE_PARTS & {x.lower() for x in PurePosixPath(path).parts[:-1]}:
            return "example"
        return None
