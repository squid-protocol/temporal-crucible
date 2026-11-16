#!/usr/bin/env python3
"""Reach head-to-head across languages: GitGalaxy's call graph vs a tree-sitter name-matching baseline, scored on the engine gate's own
compiler-grade references (pyan3 for Python, the TypeScript checker for TS and JS, golang.org/x/tools VTA for Go, ...).

    h2h_multi.py LANG REPO_DIR [REPO_DIR ...]          (run in the venv with tree-sitter-language-pack, pyan3, numpy, scipy)

Environment: IMPORT_GRAPH_CORPUS_PATH (where the pinned repos were fetched), ENGINE (a gitgalaxy checkout), PATH with the reference tools,
NODE_PATH for typescript. Same unit and scoring as h2h_reach.py (file A calls a function defined in file B; precision, recall, and the reach
number's Spearman against the reference). The tree-sitter baseline matches a call's simple name to every file defining that name (ts-all) or to
the one file defining it (ts-unique); an `obj.method()` call matches on `method`, which is what a name-matching tool can do without types."""
import collections
import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ENGINE = pathlib.Path(os.environ["ENGINE"])
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "tests" / "tools"))
import h2h_reach as H  # noqa: E402
from tree_sitter_language_pack import get_parser  # noqa: E402

import callgraph_refs as CR  # noqa: E402

EXT = {"python": (".py",), "typescript": (".ts", ".tsx", ".mts", ".cts"), "javascript": (".js", ".mjs", ".cjs", ".jsx"), "go": (".go",),
       "java": (".java",), "rust": (".rs",)}
PARSER = {"python": "python", "typescript": "typescript", "javascript": "javascript", "go": "go", "java": "java", "rust": "rust"}


def txt(data, n):
    return data[n.start_byte:n.end_byte].decode("utf8", "replace") if n is not None else None


def tail_name(data, n):
    """The simple name a call writes: `f`, `obj.f`, `pkg.F`, `a::b::f` all give the last identifier."""
    if n is None:
        return None
    if n.type in ("identifier", "field_identifier", "property_identifier", "type_identifier"):
        return txt(data, n)
    for field in ("attribute", "property", "field", "name"):
        c = n.child_by_field_name(field)
        if c is not None:
            return tail_name(data, c)
    return None


def walk_file(lang, parser, data):
    defs, calls = set(), set()
    stack = [parser.parse(data).root_node]
    while stack:
        n = stack.pop()
        stack.extend(n.children)
        t = n.type
        if lang == "python":
            if t == "function_definition":
                defs.add(txt(data, n.child_by_field_name("name")))
            elif t == "call":
                calls.add(tail_name(data, n.child_by_field_name("function")))
        elif lang in ("typescript", "javascript"):
            if t in ("function_declaration", "method_definition", "generator_function_declaration", "method_signature"):
                defs.add(txt(data, n.child_by_field_name("name")))
            elif t == "variable_declarator":
                v = n.child_by_field_name("value")
                if v is not None and v.type in ("arrow_function", "function_expression", "function"):
                    defs.add(txt(data, n.child_by_field_name("name")))
            elif t == "call_expression":
                calls.add(tail_name(data, n.child_by_field_name("function")))
        elif lang == "go":
            if t in ("function_declaration", "method_declaration"):
                defs.add(txt(data, n.child_by_field_name("name")))
            elif t == "call_expression":
                calls.add(tail_name(data, n.child_by_field_name("function")))
        elif lang == "java":
            if t in ("method_declaration", "constructor_declaration"):
                defs.add(txt(data, n.child_by_field_name("name")))
            elif t == "method_invocation":
                calls.add(txt(data, n.child_by_field_name("name")))
        elif lang == "rust":
            if t == "function_item":
                defs.add(txt(data, n.child_by_field_name("name")))
            elif t == "call_expression":
                calls.add(tail_name(data, n.child_by_field_name("function")))
    defs.discard(None)
    calls.discard(None)
    return defs, calls


def ts_baseline(lang, root, files):
    parsers = {}
    defs, calls = collections.defaultdict(set), collections.defaultdict(set)
    for rel in files:
        try:
            data = (root / rel).read_bytes()
        except OSError:
            continue
        name = "tsx" if (lang == "typescript" and rel.endswith(".tsx")) else PARSER[lang]
        if name not in parsers:
            parsers[name] = get_parser(name)
        d, c = walk_file(lang, parsers[name], data)
        for x in d:
            defs[x].add(rel)
        calls[rel] = c
    return defs, calls


def contract_pairs(contract):
    return {(e[0][0], e[1][0]) for e in contract["edges"] if e[0][0] != e[1][0]}


def engine_scan(root, outdir):
    db = outdir / f"{root.name}_galaxy_master.db"
    if not db.exists():
        env = {**os.environ, "PYTHONPATH": str(ENGINE), "GITGALAXY_LICENSE_KEY": "COMMUNITY_FREE_TIER", "GITGALAXY_DISABLE_GIT_HISTORY": "1"}
        subprocess.run([sys.executable, "-m", "gitgalaxy.galaxyscope", str(root)], cwd=outdir, env=env, capture_output=True, check=False)
    return db


def main():
    lang = sys.argv[1]
    outdir = pathlib.Path(os.environ.get("H2H_OUT", "/tmp/gitgalaxy-scratch/claude/h2h/scans"))
    outdir.mkdir(parents=True, exist_ok=True)
    for repo in map(pathlib.Path, sys.argv[2:]):
        contract, cached = CR.reference_contract(lang, repo)
        db = engine_scan(repo, outdir)
        if not db.exists():
            print(f"{repo.name}: engine scan produced no database")
            continue
        import sqlite3
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        scanned = {r[0] for r in con.execute("SELECT file_path FROM file_data")}
        con.close()
        files = sorted(p for p in scanned if p.endswith(EXT[lang]))
        scope = set(files)
        truth = {(a, b) for a, b in contract_pairs(contract) if a in scope and b in scope}
        tr = H.reach(truth)
        defs, calls = ts_baseline(lang, repo, files)
        print(f"{repo.name} [{lang}]: {len(scope)} files, {len(truth)} reference cross-file edges, {sum(1 for v in tr.values() if v)} files with a caller")
        print(H.score("engine", H.pairs_engine(db), truth, scope, tr))
        print(H.score("eng-loose", H.pairs_engine_loose(db), truth, scope, tr))
        print(H.score("ts-unique", H.pairs_ts(defs, calls, True), truth, scope, tr))
        print(H.score("ts-all", H.pairs_ts(defs, calls, False), truth, scope, tr), flush=True)


if __name__ == "__main__":
    main()
