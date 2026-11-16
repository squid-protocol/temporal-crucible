#!/usr/bin/env python3
"""Macros: where does tree-sitter name matching lose, and what does GitGalaxy recover? Scored on libclang's resolved calls (which see the preprocessed code).

    h2h_macro.py REPO_TREE ENGINE_DB CLANG_CONTRACT_JSON [REPO_TREE ENGINE_DB CLANG_CONTRACT_JSON ...]     (venv with tree-sitter-c, numpy, scipy)

Two questions, both on C:
  A. DEFINITIONS: of the functions libclang finds (path, name), how many does each source find? A function a macro generates (`TEST_IMPL(kill) {` defines run_test_kill)
     has no `function_definition` in the pre-preprocessor tree-sitter parse. Reported overall and for the definitions tree-sitter finds NOWHERE in the repository.
  B. CALL EDGES: a cross-file pair is `macro-only` when every libclang edge between the two files sits inside a macro expansion whose invocation text does not name the
     callee (libclang's own edge kind); otherwise `named`. Recall of each source on each class.
Sources: engine (one-definition edges, what `gitgalaxy reach` counts), eng-loose (+ambiguous and tied), ts-unique and ts-all (tree-sitter name matching)."""
import collections
import json
import pathlib
import sqlite3
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import h2h_reach as H  # noqa: E402


def engine_defs(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return set(con.execute("SELECT f.file_path, d.func_name FROM function_data d JOIN file_data f ON f.id = d.file_id"))
    finally:
        con.close()


def analyse(root, db, contract):
    fatal = set(contract.get("fatal", []))
    files = [str(p.relative_to(root)) for p in root.rglob("*") if p.suffix in H.EXTS and p.is_file()]
    scope = {f for f in files if f not in fatal}
    # A. definitions
    truth_defs = {(d[0], d[1]) for d in contract["defs"] if d[0] in scope}
    ts_defs, ts_calls = H.ts_parse(root, files)
    ts_def_pairs = {(f, n) for n, fs in ts_defs.items() for f in fs}
    eng_def_pairs = engine_defs(db)
    nowhere = {(p, n) for p, n in truth_defs if n not in ts_defs}  # tree-sitter sees no function_definition of that name anywhere
    # B. edges by kind
    kind = {(tuple(e[0]), tuple(e[1])): e[2] for e in contract.get("edge_kinds", [])}
    per_pair = collections.defaultdict(list)
    for e in contract["edges"]:
        a, b = e[0][0], e[1][0]
        if a == b or a not in scope or b not in scope:
            continue
        per_pair[(a, b)].append(kind.get((tuple(e[0]), tuple(e[1])), "named"))
    named = {p for p, ks in per_pair.items() if "named" in ks}
    macro_only = {p for p, ks in per_pair.items() if "named" not in ks}
    sources = {
        "engine": H.pairs_engine(db),
        "eng-loose": H.pairs_engine_loose(db),
        "ts-unique": H.pairs_ts(ts_defs, ts_calls, True),
        "ts-all": H.pairs_ts(ts_defs, ts_calls, False),
    }
    return {
        "defs": len(truth_defs), "defs_macro_generated": len(nowhere),
        "def_found": {"engine": len(truth_defs & eng_def_pairs), "tree-sitter": len(truth_defs & ts_def_pairs)},
        "def_found_macro_generated": {"engine": len(nowhere & eng_def_pairs), "tree-sitter": len(nowhere & ts_def_pairs)},
        "named": len(named), "macro_only": len(macro_only),
        "recall_named": {k: len(named & v) for k, v in sources.items()},
        "recall_macro": {k: len(macro_only & v) for k, v in sources.items()},
    }


def main():
    args = sys.argv[1:]
    tot = collections.Counter()
    tot_sub = collections.defaultdict(collections.Counter)
    for i in range(0, len(args), 3):
        root, db, contract = pathlib.Path(args[i]), args[i + 1], json.load(open(args[i + 2]))
        r = analyse(root, db, contract)
        print(f"{root.name}: definitions libclang found {r['defs']} (of which {r['defs_macro_generated']} have no function_definition anywhere in tree-sitter's parse); "
              f"cross-file pairs: {r['named']} named, {r['macro_only']} macro-only")
        print(f"   definitions found: engine {r['def_found']['engine']}/{r['defs']}, tree-sitter {r['def_found']['tree-sitter']}/{r['defs']};  "
              f"of the macro-generated ones: engine {r['def_found_macro_generated']['engine']}/{r['defs_macro_generated']}, tree-sitter {r['def_found_macro_generated']['tree-sitter']}/{r['defs_macro_generated']}")
        for cls, key, n in (("named pairs", "recall_named", r["named"]), ("macro-only pairs", "recall_macro", r["macro_only"])):
            if n:
                print(f"   recall on {cls} ({n}): " + ", ".join(f"{k} {v}/{n}" for k, v in r[key].items()))
        tot.update({"defs": r["defs"], "defs_macro": r["defs_macro_generated"], "named": r["named"], "macro_only": r["macro_only"]})
        for who in ("engine", "tree-sitter"):
            tot_sub["def_found"][who] += r["def_found"][who]
            tot_sub["def_found_macro"][who] += r["def_found_macro_generated"][who]
        for k, v in r["recall_named"].items():
            tot_sub["recall_named"][k] += v
        for k, v in r["recall_macro"].items():
            tot_sub["recall_macro"][k] += v
    print("\nPOOLED over the repositories above")
    print(f"  definitions: {tot['defs']} (macro-generated, absent from tree-sitter's parse: {tot['defs_macro']}); found: engine {tot_sub['def_found']['engine']}, tree-sitter {tot_sub['def_found']['tree-sitter']}; "
          f"macro-generated: engine {tot_sub['def_found_macro']['engine']}/{tot['defs_macro']}, tree-sitter {tot_sub['def_found_macro']['tree-sitter']}/{tot['defs_macro']}")
    for cls, key, n in (("named pairs", "recall_named", tot["named"]), ("macro-only pairs", "recall_macro", tot["macro_only"])):
        print(f"  recall on {cls} ({n}): " + ", ".join(f"{k} {v / max(n, 1):.0%} ({v})" for k, v in tot_sub[key].items()))


if __name__ == "__main__":
    main()
