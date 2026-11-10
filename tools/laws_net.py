#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAWS call networks (docs/laws_hypotheses.md): one network per snapshot, from a tools/laws_build.py database.

  Nodes   functions with loc >= 3 in a source file of the repo's language that M3 does not exclude
          (tools/laws_units.py). Identity is (path, enclosing class or "", name) (Amendment 0 item 6). In the
          languages that overload (OVERLOAD: the engine's own list) the name carries the signature, `name(types)`,
          so overloads are separate nodes; elsewhere it does not, so a function that gains a parameter stays itself.
          Functions that still share an identity are one node, and the share merged is reported (methods review M4).
  Edges   the engine's resolved `call` links whose resolution step is CONFIDENT (Amendment 1 item 1), between two
          nodes, without self-loops. Links of other steps and unresolved links are counted, never used.

    python tools/laws_net.py --db DIR/dbs/<repo>.db --language rust      # the per-snapshot profile, as JSON

No law statistic is computed here.
"""
from __future__ import annotations

import argparse
import collections
import json
import sqlite3
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).parent))
import laws_units as U  # noqa: E402

# gitgalaxy core/call_resolver.py at the panel engine: the steps whose resolution is "scoped" or "unique"
CONFIDENT_STEPS = frozenset({"class", "qualified", "typed", "file", "import", "unique", "proximate"})
MIN_LOC = 3
OVERLOAD = frozenset({"java", "cpp", "csharp", "kotlin"})  # gitgalaxy core/call_resolver.py OVERLOAD_LANGS at the panel engine

Node = tuple[str, str, str]


class Net:
    """One snapshot's network. nodes: {identity: {"loc", "n", "file"}}; edges: set of (src identity, dst identity)."""

    def __init__(self, sha: str, date: str):
        self.sha, self.date = sha, date
        self.nodes: dict[Node, dict] = {}
        self.edges: set[tuple[Node, Node]] = set()
        self.profile: dict = {}

    def in_degree(self) -> collections.Counter:
        return collections.Counter(d for _, d in self.edges)

    def files(self) -> set[str]:
        return {n[0] for n in self.nodes}


def snapshots(con: sqlite3.Connection) -> list[tuple[str, str, str]]:
    """(commit, date, boundary) per quarter boundary whose commit was scanned, oldest first. Two boundaries share a
    commit when a quarter had no commit, so the walk, not the scan table, lists the snapshots."""
    return list(con.execute("SELECT w.commit_hash, w.date, w.boundary FROM walk w JOIN snap s ON s.commit_hash = w.commit_hash "
                            "WHERE s.rc = 0 ORDER BY w.boundary"))


def yearly(snaps: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    """One snapshot per year: the one at the 1 October boundary, the month of the panel's last snapshot."""
    return [s for s in snaps if str(s[2])[5:7] == "10"]


def network(con: sqlite3.Connection, sha: str, date: str, language: str, tests_as_callers: bool = False) -> Net:
    """The network of one snapshot. tests_as_callers: the M3 sensitivity analysis, where test functions are edge
    sources but never nodes of the unit set (they are kept in `nodes` flagged "test": True)."""
    net = Net(sha, date)
    ex = U.Excluder(dict(con.execute("SELECT path, text FROM attrs WHERE commit_hash = ?", (sha,))))
    files = list(con.execute("SELECT id, path, generated FROM file WHERE commit_hash = ?", (sha,)))
    by_dir: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for _, path, _ in files:  # a `.h` belongs to C++ where C++ files are the majority of its directory
        ext = PurePosixPath(path).suffix.lower()
        if ext in U.EXTS["cpp"] and ext != ".h":
            by_dir[str(PurePosixPath(path).parent)]["cpp"] += 1
        elif ext == ".c":
            by_dir[str(PurePosixPath(path).parent)]["c"] += 1
    majority = {d: c.most_common(1)[0][0] for d, c in by_dir.items()}
    keep, why = {}, collections.Counter()
    for fid, path, gen in files:
        if U.language_of(path, majority) != language:
            continue
        reason = ex.why(path, bool(gen))
        why[reason or "unit"] += 1
        if reason is None or (tests_as_callers and reason == "test"):
            keep[fid] = (path, reason == "test")
    ident, raw = {}, 0
    sig = "signature" if "signature" in {c[1] for c in con.execute("PRAGMA table_info(func)")} else "NULL"
    for gid, fid, name, loc, cls, signature in con.execute(
            f"SELECT id, file_id, name, loc, class_name, {sig} FROM func WHERE commit_hash = ?", (sha,)):
        if fid not in keep or not name or (loc or 0) < MIN_LOC:
            continue
        path, test = keep[fid]
        node = (path, cls or "", f"{name}({signature})" if language in OVERLOAD and signature is not None else str(name))
        raw += 1
        ident[gid] = node
        cur = net.nodes.setdefault(node, {"loc": 0, "n": 0, "file": path, "test": test})
        cur["loc"] += int(loc or 0)
        cur["n"] += 1
    steps = collections.Counter()
    for a, b, step in con.execute("SELECT src, dst, step FROM edge WHERE commit_hash = ? AND kind = 'call'", (sha,)):
        if a in ident and b in ident and ident[a] != ident[b] and not net.nodes[ident[b]]["test"]:
            steps[step] += 1
            if step in CONFIDENT_STEPS:
                net.edges.add((ident[a], ident[b]))
    unresolved = dict(con.execute("SELECT step, SUM(n) FROM unresolved WHERE commit_hash = ? AND kind = 'call' GROUP BY step", (sha,)))
    conf = sum(n for s, n in steps.items() if s in CONFIDENT_STEPS)
    amb = sum(n for s, n in steps.items() if s not in CONFIDENT_STEPS)
    net.profile = {"files": dict(why), "functions": raw, "nodes": len(net.nodes),
                   "merged_share": round(1 - len(net.nodes) / raw, 4) if raw else None,
                   "edges": len(net.edges), "links_confident": conf, "links_ambiguous_not_used": amb,
                   "links_unresolved": int(sum(unresolved.values())), "by_step": dict(steps.most_common()),
                   "share_confident_of_repo_links": round(conf / (conf + amb + sum(unresolved.values())), 4)
                   if conf + amb + sum(unresolved.values()) else None}
    return net


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--language", required=True, choices=sorted(U.EXTS))
    ap.add_argument("--yearly", action="store_true")
    a = ap.parse_args()
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    snaps = snapshots(con)
    out = []
    for sha, date, boundary in (yearly(snaps) if a.yearly else snaps):
        out.append({"commit": sha[:12], "date": str(date)[:10], "boundary": str(boundary)[:10],
                    **network(con, sha, date, a.language).profile})
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
