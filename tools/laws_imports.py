#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The file-level IMPORT graph of each snapshot, as a second instrument beside the call graph.

    python tools/laws_imports.py --repo NAME --language c --out DIR    -> DIR/imports/NAME.json

Why. Every law so far is computed from one edge kind: the engine's confident `call` links, which cover about 99%
of call sites in C and 56 to 60% in Java, Go and Python (`docs/laws_coverage.md`). That gap is a between-language
difference in measurement quality running straight through a test that compares languages. An import edge is
**declared, not inferred** -- it is read off an `#include` or `import` line -- so its completeness is a parsing
question rather than an inference one, and it does not vary with how hard a language's dispatch is. Laws that can
be computed on both graphs can therefore be compared across languages on an instrument whose quality does not
move with the language.

What this is NOT. A different network, not a repair of the call graph: "the law holds on the declared-dependency
graph too" is a companion result. It is coarser (files, not functions), so LAW-2 has no function-level choice to
model on it. Java's import graph misses intra-package edges, which need no import at all, and C's include graph
is dense through header fan-in; both are reported, not corrected.

Independent of the pinned engine. The engine already builds a per-file import map and uses it as its `import`
resolution step, but persists only call edges, so reading it back would mean changing the scanner and rescanning
every snapshot -- an engine change under Amendment 1. This extractor reads the import lines from git instead, so
the pin is untouched and the instrument is genuinely separate. It does take the snapshot list, the unit file set
and each file's LOC from the existing scan databases, so the node set is exactly the call graph's file
projection and the two graphs are directly comparable.

Resolution, per language. An edge exists only where the target resolves to an in-repo unit file:
  c/cpp    `#include "x.h"` and `#include <x.h>` alike: relative to the including file's directory, then by
           suffix match on the repo's paths. A system header simply fails to resolve, which is the right answer.
  python   `import a.b`, `from a.b import c`, and relative `from .x import y`, against a module index built from
           the repo's own paths (`a/b.py`, `a/b/__init__.py`).
  go       every quoted path under the module path in go.mod, in both the single and the grouped import form;
           the target is a directory, so the edge goes to every unit file in it.
  java     `import a.b.C;` resolved by suffix match on `a/b/C.java`; a static import drops its trailing member.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).parent))
import laws_net as N  # noqa: E402
import laws_units as U  # noqa: E402
from laws_osv import _git  # noqa: E402

GREP = {
    "c": r"^[[:space:]]*#[[:space:]]*include",
    "cpp": r"^[[:space:]]*#[[:space:]]*include",
    "python": r"^[[:space:]]*(import|from)[[:space:]]",
    "java": r"^[[:space:]]*import[[:space:]]",
    # a Go import is either `import "x"` or a bare quoted path inside an import block
    "go": r"^[[:space:]]*(import[[:space:]]|[_[:alnum:].]*[[:space:]]*\"[^\"]+\"[[:space:]]*$)",
}
INCLUDE = re.compile(r'#\s*include\s*[<"]([^>"]+)[>"]')
PY_IMPORT = re.compile(r"^\s*import\s+([\w.]+)")
PY_FROM = re.compile(r"^\s*from\s+(\.*)([\w.]*)\s+import\s+(.+)")
JAVA_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)\s*;")
GO_QUOTED = re.compile(r'"([^"]+)"')


def snapshots(db: Path) -> list[tuple[str, str, str]]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    out = N.snapshots(con)
    con.close()
    return out


def unit_files(db: Path, sha: str, language: str) -> dict[str, int]:
    """{unit source path: coding LOC} for one snapshot, by the same rules laws_net.network applies."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    ex = U.Excluder(dict(con.execute("SELECT path, text FROM attrs WHERE commit_hash = ?", (sha,))))
    rows = list(con.execute("SELECT path, generated, coding_loc FROM file WHERE commit_hash = ?", (sha,)))
    con.close()
    by_dir: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for path, _, _ in rows:  # the .h majority rule, as in laws_net
        ext = PurePosixPath(path).suffix.lower()
        if ext in U.EXTS["cpp"] and ext != ".h":
            by_dir[str(PurePosixPath(path).parent)]["cpp"] += 1
        elif ext == ".c":
            by_dir[str(PurePosixPath(path).parent)]["c"] += 1
    majority = {d: c.most_common(1)[0][0] for d, c in by_dir.items()}
    keep = {}
    for path, gen, loc in rows:
        if U.language_of(path, majority) == language and ex.why(path, bool(gen)) is None:
            keep[path] = int(loc or 0)
    return keep


def go_module(repo: Path, sha: str) -> str | None:
    text = _git(repo, "show", f"{sha}:go.mod")
    for line in text.splitlines():
        if line.startswith("module "):
            return line.split(None, 1)[1].strip()
    return None


def _suffix_index(paths) -> dict[str, list[str]]:
    """Every path indexed by each of its trailing path segments, for suffix matching."""
    idx: dict[str, list[str]] = collections.defaultdict(list)
    for p in paths:
        parts = p.split("/")
        for i in range(len(parts)):
            idx["/".join(parts[i:])].append(p)
    return idx


def _module_index(paths) -> dict[str, str]:
    """Python dotted module name -> path, for the repo's own files."""
    out = {}
    for p in paths:
        if not p.endswith(".py"):
            continue
        stem = p[:-3]
        if stem.endswith("/__init__"):
            stem = stem[: -len("/__init__")]
        out.setdefault(stem.replace("/", "."), p)
    return out


def targets(line: str, path: str, language: str, suffix: dict, module: dict, go_prefix: str | None,
            by_dir: dict | None = None) -> list[str]:
    """The in-repo unit files one import line points at (possibly none)."""
    hits: list[str] = []
    if language in ("c", "cpp"):
        for m in INCLUDE.finditer(line):
            raw = m.group(1).strip()
            rel = str(PurePosixPath(path).parent / raw).replace("./", "")
            if rel in suffix:  # an exact path relative to the including file
                hits.extend(suffix[rel][:1])
            elif raw in suffix:
                hits.extend(suffix[raw][:1])
            elif (base := raw.split("/")[-1]) in suffix and len(suffix[base]) == 1:
                hits.extend(suffix[base])  # a unique basename; ambiguous ones are dropped
    elif language == "python":
        if m := PY_IMPORT.match(line):
            if (t := module.get(m.group(1))) is not None:
                hits.append(t)
        elif m := PY_FROM.match(line):
            dots, mod, names = m.group(1), m.group(2), m.group(3)
            if dots:  # a relative import: climb from the importing file's package
                pkg = PurePosixPath(path).parent
                for _ in range(len(dots) - 1):
                    pkg = pkg.parent
                base = str(pkg).replace("/", ".")
                mod = f"{base}.{mod}" if mod else base
            if (t := module.get(mod)) is not None:
                hits.append(t)
            for nm in re.findall(r"[\w*]+", names):  # `from a import b` where b is itself a module
                if (t := module.get(f"{mod}.{nm}")) is not None:
                    hits.append(t)
    elif language == "java":
        if m := JAVA_IMPORT.match(line):
            dotted = m.group(1)
            for cand in (dotted, dotted.rsplit(".", 1)[0]):  # a static import names a member
                key = cand.replace(".", "/") + ".java"
                if key in suffix and len(suffix[key]) == 1:
                    hits.append(suffix[key][0])
                    break
    elif language == "go" and go_prefix:
        for m in GO_QUOTED.finditer(line):
            raw = m.group(1)
            if raw == go_prefix or raw.startswith(go_prefix + "/"):
                d = raw[len(go_prefix):].lstrip("/") or "."
                hits.extend((by_dir or {}).get(d, ()))  # a Go import names a directory, so every file in it
    return hits


HEADER_EXTS = (".h", ".hpp", ".hh", ".hxx")


def collapse_headers(edges: set, paths) -> set:
    """Map every header onto the implementation file(s) sharing its basename stem (`a.h` -> `a.c`).

    Without this the C and C++ import graph cannot be compared with the call graph at all: if `a.c` calls into
    `b.c` it must include `b.h`, so include edges point at HEADERS while call edges point at IMPLEMENTATIONS, and
    the two live in disjoint halves of the file set. On the pilot's last snapshot the raw overlap was 18 of 847
    edges on libxml2 and **zero** of 2,358 on libgit2; collapsed it is 59.1% and 46.1% of the call graph's file
    edges. Languages with no header/implementation split are unaffected and skip this.

    This is the one inference step in an otherwise declarative graph, and it is a shallow one -- a basename stem
    match, not type inference -- but it is an inference, and a header whose implementation has a different stem
    is missed.
    """
    impl: dict[str, list[str]] = collections.defaultdict(list)
    for pth in paths:
        if not pth.endswith(HEADER_EXTS):
            impl[PurePosixPath(pth).stem].append(pth)
    out = set()
    for a, b in edges:
        srcs = impl.get(PurePosixPath(a).stem, []) if a.endswith(HEADER_EXTS) else [a]
        tgts = impl.get(PurePosixPath(b).stem, []) if b.endswith(HEADER_EXTS) else [b]
        for src in srcs:
            for tgt in tgts:
                if src != tgt:
                    out.add((src, tgt))
    return out


def graph(repo: Path, db: Path, sha: str, language: str) -> tuple[set, dict, dict]:
    """(edges, {path: loc}, stats) for one snapshot: the file-level import graph over unit source files."""
    keep = unit_files(db, sha, language)
    if not keep:
        return set(), {}, {"files": 0, "lines": 0, "resolved": 0, "unresolved": 0}
    suffix = _suffix_index(keep)
    by_dir: dict[str, list[str]] = collections.defaultdict(list)
    for pth in sorted(keep):
        by_dir[str(PurePosixPath(pth).parent)].append(pth)
    module = _module_index(keep) if language == "python" else {}
    go_prefix = go_module(repo, sha) if language == "go" else None
    globs = {"c": ["*.c", "*.h"], "cpp": ["*.cpp", "*.cc", "*.hpp", "*.h"], "python": ["*.py"],
             "java": ["*.java"], "go": ["*.go"]}[language]
    raw = _git(repo, "grep", "-n", "-E", GREP[language], sha, "--", *globs)
    edges, lines, resolved = set(), 0, 0
    for row in raw.splitlines():
        parts = row.split(":", 3)
        if len(parts) < 4:
            continue
        _, path, _, text = parts
        if path not in keep:
            continue
        lines += 1
        hit = [t for t in targets(text, path, language, suffix, module, go_prefix, by_dir)
               if t in keep and t != path]
        resolved += bool(hit)
        for t in hit:
            edges.add((path, t))
    raw_edges = len(edges)
    if language in ("c", "cpp"):
        edges = collapse_headers(edges, keep)
    return edges, keep, {"files": len(keep), "lines": lines, "resolved": resolved,
                         "edges_before_collapse": raw_edges,
                         "external": lines - resolved,
                         # the share of import lines pointing at an in-repo unit file. This is a property of the
                         # CODE -- how self-referential the repo is -- NOT of the instrument. An import of the
                         # JDK or the Go standard library correctly fails to resolve, because the target is not
                         # part of the intra-repo network the laws are about. Do not read it as coverage: that
                         # was the mistake `share_confident_of_repo_links` makes (docs/laws_coverage.md).
                         "share_in_repo": round(resolved / lines, 4) if lines else None}


def nets(repo: Path, db: Path, language: str, snaps=None) -> tuple[list, list[dict]]:
    """laws_net.Net objects at FILE granularity, oldest first, so the existing estimators can read them.
    A node is (path, "", "") and its `loc` is the file's coding LOC from the scan."""
    out, stats = [], []
    for sha, date, _ in (snaps if snaps is not None else snapshots(db)):
        edges, keep, st = graph(repo, db, sha, language)
        net = N.Net(sha, date)
        net.nodes = {(p, "", ""): {"loc": loc, "n": 1, "file": p, "test": False} for p, loc in keep.items()}
        net.edges = {((a, "", ""), (b, "", "")) for a, b in edges}
        net.profile = st
        out.append(net)
        stats.append({"sha": sha, "date": date, **st, "edges": len(net.edges)})
    return out, stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--language", required=True, choices=sorted(GREP))
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    from laws_osv import POOL_DIR
    repo = Path(a.repo) if Path(a.repo).is_dir() else POOL_DIR / a.repo
    db = a.out / "dbs" / f"{repo.name}.db"
    _, stats = nets(repo, db, a.language)
    rec = {"repo": repo.name, "language": a.language, "snapshots": len(stats), "by_snapshot": stats}
    if stats:
        last = stats[-1]
        rec["last"] = last
        rec["share_in_repo_median"] = sorted(s["share_in_repo"] for s in stats if s["share_in_repo"])[len(stats) // 2]
    f = a.out / "imports" / f"{repo.name}.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(rec, indent=1) + "\n")
    print(f"{repo.name} ({a.language}): {len(stats)} snapshots; last {rec.get('last', {}).get('files')} files, "
          f"{rec.get('last', {}).get('edges')} import edges, "
          f"{rec.get('last', {}).get('share_in_repo')} of import lines pointing in-repo "
          f"(median {rec.get('share_in_repo_median')}) -> {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
