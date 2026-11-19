#!/usr/bin/env python3
"""Function-pointer edges (dispatch through a named struct field) for C. Hypotheses EP1-EP4: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before building.
    python tools/sensor/fnptr_edges.py <repo> <snapshot index or 'last'> [--sample]"""
import collections
import hashlib
import io
import json
import os
import pickle
import random
import subprocess
import sys
import tarfile
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402

OUT = "/tmp/gitgalaxy-scratch/claude/fnptr"
CAP = 400


def fname_of(decl):
    n = decl
    while n is not None and n.type != "identifier":
        nxt = n.child_by_field_name("declarator")
        if nxt is None:
            nxt = next((c for c in n.children if c.type in ("function_declarator", "pointer_declarator", "parenthesized_declarator", "identifier")), None)
        n = nxt
    return n.text.decode() if n is not None else None


def parse_chunk(items):
    from tree_sitter_language_pack import get_parser
    parser = get_parser("c")
    res = []
    for path, data in items:
        regs, calls = [], []
        t = parser.parse(data)
        lines = data.split(b"\n")
        stack = [(t.root_node, None)]
        while stack:
            n, fn = stack.pop()
            ty = n.type
            if ty == "function_definition":
                d = n.child_by_field_name("declarator")
                fn = fname_of(d) if d is not None else None
            elif ty == "initializer_pair":
                des = next((c for c in n.children if c.type == "field_designator"), None)
                val = n.children[-1]
                if val.type == "pointer_expression":
                    val = val.children[-1]
                if des is not None and val.type == "identifier":
                    fi = next((c for c in des.children if c.type == "field_identifier"), None)
                    if fi is not None:
                        regs.append((fi.text.decode(), val.text.decode(), n.start_point[0] + 1, lines[n.start_point[0]][:110].decode(errors="replace").strip()))
            elif ty == "assignment_expression":
                l, r = n.children[0], n.children[-1]
                if r.type == "pointer_expression":
                    r = r.children[-1]
                if l.type == "field_expression" and r.type == "identifier":
                    fi = l.child_by_field_name("field")
                    if fi is not None:
                        regs.append((fi.text.decode(), r.text.decode(), n.start_point[0] + 1, lines[n.start_point[0]][:110].decode(errors="replace").strip()))
            elif ty == "call_expression" and fn:
                f = n.child_by_field_name("function")
                if f is not None and f.type == "field_expression":
                    fi = f.child_by_field_name("field")
                    a = n.child_by_field_name("arguments")
                    if fi is not None and a is not None:
                        calls.append((fi.text.decode(), fn, a.named_child_count, n.start_point[0] + 1, lines[n.start_point[0]][:110].decode(errors="replace").strip()))
            for c in n.children:
                stack.append((c, fn))
        res.append((path, regs, calls))
    return res


def build(repo, idx):
    sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
    snap = sn[idx]
    g = BR.Graph(snap["db"])
    keys = sorted(g.index, key=g.index.get)
    byname = collections.defaultdict(list)
    for k in keys:
        byname[k[1]].append(k)
    tar = subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "archive", "--format=tar", snap["commit"]], capture_output=True).stdout
    files = []
    with tarfile.open(fileobj=io.BytesIO(tar)) as tf:
        for m in tf:
            if m.isfile() and m.name.endswith((".c", ".h")) and m.size < 2_000_000:
                files.append((m.name, tf.extractfile(m).read()))
    chunks = [files[i : i + 150] for i in range(0, len(files), 150)]
    allr = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for r in ex.map(parse_chunk, chunks):
            allr += r
    regs = collections.defaultdict(list)
    for path, rs, _ in allr:
        for field, fname, line, text in rs:
            cands = byname.get(fname, [])
            same = [k for k in cands if k[0] == path]
            tgt = same[0] if same else (cands[0] if len(cands) == 1 else None)
            if tgt is not None:
                regs[field].append((tgt, path, line, text))
    dropped = {f for f, v in regs.items() if len({r[0] for r in v}) > CAP}
    edges = {}
    info = {}
    for path, _, cs in allr:
        for field, fn, nargs, line, text in cs:
            src = (path, fn)
            if src not in g.index or field not in regs or field in dropped:
                continue
            for tgt, rpath, rline, rtext in regs[field]:
                if tgt != src and (src, tgt) not in edges:
                    edges[(src, tgt)] = (field, nargs)
                    info[(src, tgt)] = (field, path, line, text, rpath, rline, rtext)
    os.makedirs(OUT, exist_ok=True)
    pickle.dump({"edges": list(edges), "info": info}, open(f"{OUT}/{hashlib.md5(snap['db'].encode()).hexdigest()}.pkl", "wb"))
    return g, keys, edges, info, regs, dropped, len(files)


def main():
    repo = sys.argv[1]
    sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
    idx = len(sn) - 1 if sys.argv[2] == "last" else int(sys.argv[2])
    g, keys, edges, info, regs, dropped, nfiles = build(repo, idx)
    print(f"{repo} snapshot {idx}: {nfiles} C files; {len(regs)} registered fields ({sum(len(v) for v in regs.values())} registrations), {len(dropped)} fields dropped for more than {CAP} targets; {len(edges)} new edges", flush=True)
    if "--sample" in sys.argv:
        rng = random.Random(1)
        ar = [1 if nargs == int(g.args[g.index[t]]) else 0 for (s, t), (f, nargs) in edges.items()]
        nvals = [n for (_, n) in edges.values()]
        pairs = [1 if rng.choice(nvals) == int(g.args[rng.randrange(g.n)]) else 0 for _ in range(len(ar))]
        print(f"  argument count at the call equals the parameter count of the target: {100 * sum(ar) / max(len(ar), 1):.1f}% of edges; random call site against random function {100 * sum(pairs) / max(len(pairs), 1):.1f}%")
        samp = rng.sample(sorted(info), min(30, len(info)))
        for k in samp:
            f, path, line, text, rpath, rline, rtext = info[k]
            print(f"  [{f}] call {path}:{line} `{text}`  ->  {k[1][1]} registered {rpath}:{rline} `{rtext}`")
        fan = collections.Counter(f for (s, t), (f, n) in edges.items())
        print("  fields with most edges:", fan.most_common(8))


if __name__ == "__main__":
    main()
