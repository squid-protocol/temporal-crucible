#!/usr/bin/env python3
"""Function-pointer and callback references in C, found with tree-sitter: the edges the engine's call graph does not have.

A reference is an identifier that names a function defined in the same snapshot and is NOT in call position, a declaration or a definition: `signal(2, cb)`,
`.do_it = cb`, `p = &cb`, `return cb;`. Each is recorded with the function that contains it (None at file level, where function tables live) and the syntactic
context. The engine's `fcall_data` has call edges (and a handful of `reference` edges); this is the rest.

    python tools/sensor/ts_refs.py census REPO SNAPSHOT_INDEX        census: how many functions are reachable only through a pointer
    (library use)   from ts_refs import refs_for_snapshot"""
import collections
import json
import pickle
import sqlite3
import subprocess
import sys
from pathlib import Path

from tree_sitter_language_pack import get_parser

ROOT = "/srv/storage_16tb/projects"
B = f"{ROOT}/curl_call_graph_evolution/turn_v2"
POOL = f"{ROOT}/temporal-crucible-pool"
CACHE = Path("/tmp/gitgalaxy-scratch/claude/refs")
CACHE.mkdir(parents=True, exist_ok=True)
_P = get_parser("c")
# Value contexts where a function name is a function pointer. Left out: member access (`conn->x`: a variable that shares the function's name), declarators (a variable
# declared with the function's name), comparisons and parentheses (cannot tell a pointer from a variable without scoping).
VALUE_PARENTS = {"initializer_list", "initializer_pair", "argument_list", "assignment_expression", "pointer_expression", "cast_expression", "conditional_expression", "return_statement", "comma_expression", "subscript_expression"}
SKIP_PARENTS = {"function_declarator", "preproc_def", "preproc_function_def", "preproc_params", "parameter_declaration", "type_definition", "labeled_statement", "goto_statement"}


def _fn_name(node, src):
    d = node.child_by_field_name("declarator")
    while d is not None and d.type != "identifier":
        nxt = d.child_by_field_name("declarator")
        if nxt is None:
            return None
        d = nxt
    return src[d.start_byte:d.end_byte].decode("utf8", "replace") if d is not None else None


def parse(src, names):
    """References to names in `names` (defined functions) found in one file's bytes: [(enclosing function or None, target, parent node type)]."""
    out = []
    tree = _P.parse(src)
    stack = [(tree.root_node, None, None)]
    while stack:
        n, enc, table = stack.pop()
        if n.type == "function_definition":
            enc = _fn_name(n, src) or enc
        elif n.type == "init_declarator" and enc is None:
            table = _fn_name(n, src) or table  # the variable (a table of function pointers) this initializer fills
        elif n.type == "identifier":
            text = src[n.start_byte:n.end_byte].decode("utf8", "replace")
            if text in names:
                p = n.parent
                if p is None or p.type in SKIP_PARENTS:
                    pass
                elif p.type == "call_expression" and p.child_by_field_name("function") == n:
                    pass  # an ordinary call: the engine has it
                elif p.type == "init_declarator" and p.child_by_field_name("declarator") == n:
                    pass  # the variable being declared
                elif p.type == "function_definition":
                    pass
                elif p.type == "pointer_expression" and p.children[0].type != "&":
                    pass  # a dereference `*x`: x is a pointer variable, not a function being referenced
                elif p.type in VALUE_PARENTS and not (p.type == "assignment_expression" and p.child_by_field_name("left") == n) and not (p.type == "subscript_expression" and p.child_by_field_name("argument") != n):
                    out.append((enc, text, p.type, n.start_point[0] + 1, table))
        for c in n.children:
            stack.append((c, enc, table))
    return out


def snapshot_files(repo, commit, paths):
    """{path: bytes} for `paths` at `commit`, through one `git cat-file --batch`."""
    proc = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    out = {}
    stdin, stdout = proc.stdin, proc.stdout
    for p in paths:
        stdin.write(f"{commit}:{p}\n".encode())
        stdin.flush()
        head = stdout.readline().split()
        if len(head) == 3 and head[1] == b"blob":
            size = int(head[2])
            out[p] = stdout.read(size)
            stdout.read(1)
    stdin.close()
    proc.wait()
    return out


def refs_for_snapshot(name, s):
    f = CACHE / f"{name}_{s:03d}.pkl"
    if f.exists():
        return pickle.load(open(f, "rb"))
    sn = json.load(open(f"{B}/scan_{name}/snapshots.json"))[s]
    con = sqlite3.connect(f"file:{sn['db']}?mode=ro", uri=True)
    files = {r[0]: r[1] for r in con.execute("SELECT id, file_path FROM file_data")}
    defs = collections.defaultdict(set)  # name -> {path}
    callers = collections.Counter()
    fn_key = {}
    for fid, ffile, nm in con.execute("SELECT id, file_id, func_name FROM function_data"):
        if ffile in files and files[ffile].endswith((".c", ".h")):
            defs[nm].add(files[ffile])
            fn_key[fid] = (files[ffile], nm)
    for dst in con.execute("SELECT dst_func_id FROM fcall_data WHERE kind = 'call' AND dst_func_id IS NOT NULL"):
        if dst[0] in fn_key:
            callers[fn_key[dst[0]]] += 1
    con.close()
    names = set(defs)
    paths = sorted({p for ps in defs.values() for p in ps} | {p for p in files.values() if p.endswith((".c", ".h"))})
    blobs = snapshot_files(f"{POOL}/{name}", sn["commit"], paths)
    refs = []
    for p, src in blobs.items():
        for enc, target, ctx, line, table in parse(src, names):
            refs.append((p, enc, target, ctx, line, table))
    res = {"snapshot": s, "commit": sn["commit"], "defs": {k: sorted(v) for k, v in defs.items()}, "callers": dict(callers), "refs": refs, "files": len(blobs)}
    pickle.dump(res, open(f, "wb"))
    return res


def census(name, s):
    r = refs_for_snapshot(name, s)
    defs = r["defs"]
    nodes = [(p, n) for n, ps in defs.items() for p in ps]
    unique = {n for n, ps in defs.items() if len(ps) == 1}
    referenced = collections.Counter()
    for p, enc, target, ctx, _ln, _tb in r["refs"]:
        if target in unique and enc != target:
            referenced[target] += 1
    ctxs = collections.Counter(x[3] for x in r["refs"])
    zero = [(p, n) for p, n in nodes if r["callers"].get((p, n), 0) == 0 and n in unique]
    zero_ref = [k for k in zero if referenced.get(k[1], 0) > 0]
    called = [(p, n) for p, n in nodes if r["callers"].get((p, n), 0) > 0 and n in unique]
    called_ref = [k for k in called if referenced.get(k[1], 0) > 0]
    file_level = sum(1 for x in r["refs"] if x[1] is None and x[2] in unique)
    in_fn = sum(1 for x in r["refs"] if x[1] is not None and x[2] in unique)
    print(f"{name} snapshot {s} ({r['commit'][:10]}): {r['files']} C files parsed, {len(nodes)} function definitions ({len(unique)} with a name unique in the repository)")
    print(f"  references found (function name in a non-call position): {len(r['refs'])}; for unique names: {in_fn} inside a function (callback registration, address taken) and {file_level} at file level (tables of function pointers)")
    print(f"  by syntactic context: " + ", ".join(f"{k} {v}" for k, v in ctxs.most_common(8)))
    print(f"  functions with NO static caller in the engine's graph: {len(zero)}; of those, referenced as a pointer/callback somewhere: {len(zero_ref)} ({100 * len(zero_ref) / max(len(zero), 1):.0f}%)")
    print(f"  functions WITH a static caller: {len(called)}; also referenced as a pointer: {len(called_ref)} ({100 * len(called_ref) / max(len(called), 1):.0f}%)")
    import random

    random.seed(7)
    print("  precision spot check (random references, file:line and the source line):")
    blobs = {}
    for p, enc, t, ctx, ln, _tb in random.sample([x for x in r["refs"] if x[2] in unique], min(14, len(r["refs"]))):
        if p not in blobs:
            blobs[p] = snapshot_files(f"{POOL}/{name}", r["commit"], [p]).get(p, b"").decode("utf8", "replace").splitlines()
        line = blobs[p][ln - 1].strip() if 0 < ln <= len(blobs[p]) else "?"
        print(f"    {p}:{ln} [{ctx}] in {enc or '(file level)'}: {line[:110]}")
    return r


if __name__ == "__main__":
    if sys.argv[1] == "census":
        census(sys.argv[2], int(sys.argv[3]))
