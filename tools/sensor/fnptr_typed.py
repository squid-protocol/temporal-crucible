#!/usr/bin/env python3
"""Type-resolved function-pointer edges for C: registrations and indirect calls matched on (struct type, field). Hypotheses TP1-TP4: docs/sensor-overhaul/sensors/ripple_radius.md.
    python tools/sensor/fnptr_typed.py <repo> <snapshot index or 'last'> [--sample]"""
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

OUT = "/tmp/gitgalaxy-scratch/claude/fnptr_typed"


def dname(d):
    n = d
    for _ in range(12):
        if n is None:
            return None
        if n.type in ("identifier", "field_identifier", "type_identifier"):
            return n.text.decode()
        nxt = n.child_by_field_name("declarator")
        if nxt is None and n.type == "parenthesized_declarator":
            nxt = next((c for c in n.children if c.is_named), None)
        n = nxt
    return None


def tname(decl):
    t = decl.child_by_field_name("type")
    if t is None:
        return None
    if t.type in ("struct_specifier", "union_specifier"):
        nm = t.child_by_field_name("name")
        return nm.text.decode() if nm is not None else None
    if t.type == "type_identifier":
        return t.text.decode()
    return None


def p1(items):
    from tree_sitter_language_pack import get_parser
    parser = get_parser("c")
    structs, tds = {}, {}
    for path, data in items:
        t = parser.parse(data)
        stack = [t.root_node]
        while stack:
            n = stack.pop()
            if n.type in ("struct_specifier", "union_specifier") and n.child_by_field_name("body") is not None:
                nm = n.child_by_field_name("name")
                name = nm.text.decode() if nm is not None else None
                if name is None and n.parent is not None and n.parent.type == "type_definition":
                    name = dname(n.parent.child_by_field_name("declarator"))
                if name:
                    fl = structs.setdefault(name, {})
                    for fd in n.child_by_field_name("body").children:
                        if fd.type == "field_declaration":
                            ty = tname(fd)
                            for d in fd.children_by_field_name("declarator"):
                                fn = dname(d)
                                if fn and ty:
                                    fl[fn] = ty
            elif n.type == "type_definition":
                ty = tname(n)
                al = dname(n.child_by_field_name("declarator"))
                if ty and al and ty != al:
                    tds[al] = ty
            stack.extend(n.children)
    return structs, tds


def p2(args):
    items, structs, tds = args
    from tree_sitter_language_pack import get_parser
    parser = get_parser("c")

    def canon(t):
        for _ in range(8):
            if t in tds and tds[t] != t:
                t = tds[t]
            else:
                break
        return t

    def type_of(e, scope, G):
        if e is None:
            return None
        ty = e.type
        if ty == "identifier":
            v = scope.get(e.text.decode(), G.get(e.text.decode()))
            return canon(v) if v else None
        if ty == "field_expression":
            bt = type_of(e.child_by_field_name("argument"), scope, G)
            f = e.child_by_field_name("field")
            if bt and f is not None:
                m = structs.get(bt, {}).get(f.text.decode())
                return canon(m) if m else None
            return None
        if ty in ("subscript_expression", "pointer_expression"):
            return type_of(e.child_by_field_name("argument"), scope, G)
        if ty == "parenthesized_expression":
            inner = next((c for c in e.children if c.is_named), None)
            return type_of(inner, scope, G)
        if ty == "cast_expression":
            td = e.child_by_field_name("type")
            v = tname(td) if td is not None else None
            return canon(v) if v else None
        return None

    def kind_of(lst):
        p = lst.parent
        if p is None:
            return None
        if p.type == "init_declarator":
            decl = p.parent
            v = tname(decl)
            d = p.child_by_field_name("declarator")
            if not v:
                return None
            return ("array" if d is not None and d.type == "array_declarator" else "struct", canon(v))
        if p.type == "initializer_list":
            pk = kind_of(p)
            return ("struct", pk[1]) if pk and pk[0] == "array" else None
        if p.type == "initializer_pair":
            pk = kind_of(p.parent)
            des = [c for c in p.children if c.type in ("field_designator", "subscript_designator")]
            if len(des) != 1 or not pk:
                return None
            if des[0].type == "subscript_designator" and pk[0] == "array":
                return ("struct", pk[1])
            if des[0].type == "field_designator" and pk[0] == "struct":
                fi = next((c for c in des[0].children if c.type == "field_identifier"), None)
                ft = structs.get(pk[1], {}).get(fi.text.decode()) if fi is not None else None
                return ("struct", canon(ft)) if ft else None
        return None

    def fname_of(d):
        return dname(d)

    res = []
    for path, data in items:
        regs, calls = [], []
        t = parser.parse(data)
        lines = data.split(b"\n")
        G = {}
        for c in t.root_node.children:
            if c.type == "declaration":
                ty = tname(c)
                for d in c.children_by_field_name("declarator"):
                    nm = dname(d)
                    if nm and ty:
                        G[nm] = ty
        stack = [(t.root_node, None, {})]
        while stack:
            n, fn, scope = stack.pop()
            ty = n.type
            if ty == "function_definition":
                d = n.child_by_field_name("declarator")
                fn = fname_of(d) if d is not None else None
                scope = {}
                st = [n]
                while st:
                    x = st.pop()
                    if x.type == "parameter_declaration":
                        tt = tname(x)
                        dn = x.child_by_field_name("declarator")
                        nm = dname(dn) if dn is not None else None
                        if nm and tt:
                            scope[nm] = tt
                    elif x.type == "declaration":
                        tt = tname(x)
                        for dd in x.children_by_field_name("declarator"):
                            nm = dname(dd)
                            if nm and tt:
                                scope[nm] = tt
                    st.extend(x.children)
            elif ty == "initializer_pair":
                des = [c for c in n.children if c.type in ("field_designator", "subscript_designator")]
                val = n.children[-1]
                if val.type == "pointer_expression":
                    val = val.children[-1]
                if len(des) == 1 and des[0].type == "field_designator" and val.type == "identifier":
                    fi = next((c for c in des[0].children if c.type == "field_identifier"), None)
                    pk = kind_of(n.parent) if n.parent is not None else None
                    if fi is not None:
                        regs.append((pk[1] if pk and pk[0] == "struct" else None, fi.text.decode(), val.text.decode(), n.start_point[0] + 1, lines[n.start_point[0]][:110].decode(errors="replace").strip()))
            elif ty == "assignment_expression":
                l, r = n.children[0], n.children[-1]
                if r.type == "pointer_expression":
                    r = r.children[-1]
                if l.type == "field_expression" and r.type == "identifier":
                    fi = l.child_by_field_name("field")
                    if fi is not None:
                        regs.append((type_of(l.child_by_field_name("argument"), scope, G), fi.text.decode(), r.text.decode(), n.start_point[0] + 1, lines[n.start_point[0]][:110].decode(errors="replace").strip()))
            elif ty == "call_expression" and fn:
                f = n.child_by_field_name("function")
                if f is not None and f.type == "field_expression":
                    fi = f.child_by_field_name("field")
                    a = n.child_by_field_name("arguments")
                    if fi is not None and a is not None:
                        calls.append((type_of(f.child_by_field_name("argument"), scope, G), fi.text.decode(), fn, a.named_child_count, n.start_point[0] + 1, lines[n.start_point[0]][:110].decode(errors="replace").strip()))
            for c in n.children:
                stack.append((c, fn, scope))
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
    structs, tds = {}, {}
    with ProcessPoolExecutor(max_workers=6) as ex:
        for s, t in ex.map(p1, chunks):
            for k, v in s.items():
                structs.setdefault(k, {}).update(v)
            tds.update(t)
        allr = []
        for r in ex.map(p2, [(c, structs, tds) for c in chunks]):
            allr += r
    regs = collections.defaultdict(list)
    name_regs = set()
    nreg_all = nreg_typed = 0
    for path, rs, _ in allr:
        for T, field, fname, line, text in rs:
            cands = byname.get(fname, [])
            same = [k for k in cands if k[0] == path]
            tgt = same[0] if same else (cands[0] if len(cands) == 1 else None)
            if tgt is None:
                continue
            name_regs.add(field)
            nreg_all += 1
            if T:
                nreg_typed += 1
                regs[(T, field)].append((tgt, path, line, text))
    edges, info = {}, {}
    ncalls = ncalls_named = ncalls_typed = 0
    for path, _, cs in allr:
        for T, field, fn, nargs, line, text in cs:
            ncalls += 1
            if field in name_regs:
                ncalls_named += 1
                if T:
                    ncalls_typed += 1
            src = (path, fn)
            if not T or src not in g.index or (T, field) not in regs:
                continue
            for tgt, rpath, rline, rtext in regs[(T, field)]:
                if tgt != src and (src, tgt) not in edges:
                    edges[(src, tgt)] = (field, nargs)
                    info[(src, tgt)] = (T, field, path, line, text, rpath, rline, rtext)
    os.makedirs(OUT, exist_ok=True)
    pickle.dump({"edges": list(edges), "info": info}, open(f"{OUT}/{hashlib.md5(snap['db'].encode()).hexdigest()}.pkl", "wb"))
    stats = {"files": len(files), "structs": len(structs), "typedefs": len(tds), "reg_all": nreg_all, "reg_typed": nreg_typed, "calls": ncalls, "calls_named": ncalls_named, "calls_typed": ncalls_typed}
    return g, edges, info, stats


def main():
    repo = sys.argv[1]
    sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
    idx = len(sn) - 1 if sys.argv[2] == "last" else int(sys.argv[2])
    g, edges, info, st = build(repo, idx)
    print(f"{repo} snapshot {idx}: {st['files']} C files, {st['structs']} struct types, {st['typedefs']} typedefs; registrations {st['reg_all']} of which typed {st['reg_typed']} ({100 * st['reg_typed'] / max(st['reg_all'], 1):.0f}%); indirect field calls {st['calls']}, with a registered field name {st['calls_named']}, of those typed {st['calls_typed']} ({100 * st['calls_typed'] / max(st['calls_named'], 1):.0f}%); new edges {len(edges)}", flush=True)
    if "--sample" in sys.argv:
        rng = random.Random(1)
        ar = [1 if nargs == int(g.args[g.index[t]]) else 0 for (s, t), (f, nargs) in edges.items()]
        nvals = [n for (_, n) in edges.values()]
        pairs = [1 if rng.choice(nvals) == int(g.args[rng.randrange(g.n)]) else 0 for _ in range(len(ar))]
        print(f"  argument count equals parameter count: {100 * sum(ar) / max(len(ar), 1):.1f}% of edges; random {100 * sum(pairs) / max(len(pairs), 1):.1f}%")
        for k in rng.sample(sorted(info), min(30, len(info))):
            T, f, path, line, text, rpath, rline, rtext = info[k]
            print(f"  [{T}.{f}] call {path}:{line} `{text}`  ->  {k[1][1]} registered {rpath}:{rline} `{rtext}`")
        fan = collections.Counter(i[0] + "." + i[1] for i in info.values())
        print("  type.field with most edges:", fan.most_common(8))


if __name__ == "__main__":
    main()
