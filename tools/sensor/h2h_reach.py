#!/usr/bin/env python3
"""Reach head-to-head: GitGalaxy's call graph vs a tree-sitter name-matching baseline, scored against libclang's resolved calls.

    h2h_reach.py REPO_TREE ENGINE_DB CLANG_CONTRACT_JSON

Ground truth = libclang (tests/tools/clang_callgraph.py contract). Unit = the cross-file edge "file A calls a function defined in file B" (the
unit reach counts). Sources scored against it:
  engine        fcall_data call edges that resolve to one definition (candidates <= 1), as `gitgalaxy reach` counts them
  ts-unique     tree-sitter: a call to a name that exactly one file defines is an edge to that file
  ts-all        tree-sitter: a call to a name is an edge to EVERY file defining it (the usual name-matching tool)
Reports edge precision and recall, and the reach number itself (distinct caller files per file): Spearman against libclang, mean absolute error,
and how many of libclang's top-10 most-reached files each source finds. Needs the venv with libclang, tree-sitter, tree-sitter-c, scipy."""
import collections
import json
import pathlib
import sqlite3
import sys

import numpy as np
import tree_sitter_c
from scipy.stats import spearmanr
from tree_sitter import Language, Parser

LANG = Language(tree_sitter_c.language())
EXTS = (".c", ".h")


def ts_parse(root: pathlib.Path, files: list[str]):
    parser = Parser(LANG)
    defs, calls = collections.defaultdict(set), collections.defaultdict(set)  # name -> files defining it ; file -> names it calls
    for rel in files:
        try:
            data = (root / rel).read_bytes()
        except OSError:
            continue
        tree = parser.parse(data)
        stack = [tree.root_node]
        while stack:
            n = stack.pop()
            stack.extend(n.children)
            if n.type == "function_definition":
                d = n.child_by_field_name("declarator")
                while d is not None and d.type != "identifier":  # pointer_declarator / function_declarator / parenthesized
                    nxt = d.child_by_field_name("declarator")
                    d = nxt if nxt is not None else next((c for c in d.children if c.type in ("identifier", "function_declarator", "pointer_declarator")), None)
                if d is not None and d.type == "identifier":
                    defs[data[d.start_byte:d.end_byte].decode("utf8", "replace")].add(rel)
            elif n.type == "call_expression":
                f = n.child_by_field_name("function")
                if f is not None and f.type == "identifier":  # a call by plain name; a call through a field or a pointer names no function
                    calls[rel].add(data[f.start_byte:f.end_byte].decode("utf8", "replace"))
    return defs, calls


def pairs_ts(defs, calls, unique_only):
    out = set()
    for src, names in calls.items():
        for name in names:
            where = defs.get(name, ())
            if not where or (unique_only and len(where) != 1):
                continue
            if src in where:
                continue  # defined in the caller's own file: not a cross-file edge
            out.update((src, dst) for dst in where)
    return out


def pairs_engine(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        path = dict(con.execute("SELECT id, file_path FROM file_data"))
        rows = con.execute("SELECT src_file_id, dst_file_id FROM fcall_data WHERE kind='call' AND dst_func_id IS NOT NULL AND COALESCE(candidates,1) <= 1 AND src_file_id <> dst_file_id").fetchall()
    finally:
        con.close()
    return {(path[a], path[b]) for a, b in rows if a in path and b in path}


def pairs_engine_loose(db):
    """Every resolved call edge, ambiguous ones included, plus the tied-call candidates: what the engine knows without the sensor's strict filter."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        path = dict(con.execute("SELECT id, file_path FROM file_data"))
        rows = con.execute("SELECT src_file_id, dst_file_id FROM fcall_data WHERE kind='call' AND dst_file_id IS NOT NULL AND src_file_id <> dst_file_id").fetchall()
        if con.execute("SELECT 1 FROM sqlite_master WHERE name='fcall_candidates'").fetchone():
            rows += con.execute("SELECT src_file_id, dst_file_id FROM fcall_candidates WHERE dst_file_id IS NOT NULL AND src_file_id <> dst_file_id").fetchall()
    finally:
        con.close()
    return {(path[a], path[b]) for a, b in rows if a in path and b in path}


def pairs_clang(contract):
    return {(e[0][0], e[1][0]) for e in contract["edges"] if e[0][0] != e[1][0]}


def reach(pairs):
    r = collections.defaultdict(set)
    for a, b in pairs:
        r[b].add(a)
    return {k: len(v) for k, v in r.items()}


def score(name, got, truth, files, truth_reach):
    got = {(a, b) for a, b in got if a in files and b in files}
    tp = len(got & truth)
    gr = reach(got)
    keys = sorted(files)
    x = np.array([truth_reach.get(k, 0) for k in keys], float)
    y = np.array([gr.get(k, 0) for k in keys], float)
    rho = spearmanr(x, y)[0] if x.std() and y.std() else float("nan")
    top = sorted(truth_reach, key=lambda k: -truth_reach[k])[:10]
    top_got = sorted(gr, key=lambda k: -gr[k])[:10]
    return (f"  {name:10s} edges {len(got):6d}  precision {tp / max(len(got), 1):5.1%}  recall {tp / max(len(truth), 1):5.1%}  "
            f"| reach: Spearman {rho:+.3f}  mean abs error {np.abs(x - y).mean():5.2f}  top-10 found {len(set(top) & set(top_got))}/10")


def main():
    root, db, contract = pathlib.Path(sys.argv[1]), sys.argv[2], json.load(open(sys.argv[3]))
    files = [str(p.relative_to(root)) for p in root.rglob("*") if p.suffix in EXTS and p.is_file()]
    fatal = set(contract.get("fatal", []))
    truth = pairs_clang(contract)
    scope = {f for f in files if f not in fatal}  # files libclang could parse
    truth = {(a, b) for a, b in truth if a in scope and b in scope}
    tr = reach(truth)
    defs, calls = ts_parse(root, files)
    print(f"{root.name}: {len(scope)} files libclang parsed ({len(fatal)} it could not), {len(truth)} libclang cross-file edges, "
          f"{sum(1 for v in tr.values() if v)} files with a caller")
    print(score("engine", pairs_engine(db), truth, scope, tr))
    print(score("eng-loose", pairs_engine_loose(db), truth, scope, tr))
    print(score("ts-unique", pairs_ts(defs, calls, True), truth, scope, tr))
    print(score("ts-all", pairs_ts(defs, calls, False), truth, scope, tr))


if __name__ == "__main__":
    main()
