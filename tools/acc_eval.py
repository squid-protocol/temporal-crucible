#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""ACC-H1..H3 (docs/acc_hypotheses.md): GitGalaxy's compile-free call graph against compiler-grade oracles.

    python tools/acc_eval.py --study ACC_STUDY_DIR > acc_result.json

ACC_STUDY_DIR (outside the repo) holds repos/<repo> (pinned snapshots), engine/<repo>/*_galaxy_master.db (gitgalaxy
8f96d76ba, history off) and the oracle tools from setup.sh (venv, go, gopath, tools/java-callgraph).
Oracles as installed: libclang 18.1.1; PyCG 0.0.8 (module alias pycg, setuptools<81); go1.27.3 + x/tools callgraph
v0.52.0; java-callgraph da81eeb on commons-lang compiled by javac --release 8 from the pinned sources (its Maven
build needs Maven >= 3.9; the box has 3.8.7).

Pre-run clarification (written before any oracle ran): **precision** = engine edges confirmed by any oracle edge
(direct or dynamic) / engine edges; **recall** = oracle *direct* edges the engine has / oracle direct edges. Both
over edges between functions matched on both sides. Engine network = the CGT network (loc >= 3, same-file then
unique-name resolution). Functions match by (file, name, start line +-3); for Java and Python, where oracles name
methods without lines, by (file, name) when that pair is unique on the engine side.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import cgt_eval as G  # noqa: E402

REPOS = {"libgit2": "c", "redis": "c", "commons-lang": "java", "prometheus": "go", "sphinx": "python"}
EXT = {"c": (".c", ".h"), "java": (".java",), "go": (".go",), "python": (".py",)}


# ------------------------------------------------------------------------------------------------- engine
def engine(study, repo, lang):
    db = sorted((study / "engine" / repo).glob("*_galaxy_master.db"))[0]
    root = str(study / "repos" / repo)
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    funcs, meta = [], {}
    for path, name, start, loc, calls in con.execute(
            "SELECT fd.file_path, f.func_name, f.start_line, f.loc, f.calls_out_to FROM function_data f "
            "JOIN file_data fd ON f.file_id = fd.id"):
        p = str(path)
        if p.startswith(root):
            p = p[len(root):].lstrip("/")
        if not name or (loc or 0) < 3 or not p.endswith(EXT[lang]):
            continue
        n = str(name).split("::")[-1].split(".")[-1]
        funcs.append((p, n, G.parse_calls(calls)))
        meta.setdefault((p, n), int(start or 0))
    con.close()
    nodes, edges = G.network(funcs)
    return nodes, edges, meta


# ------------------------------------------------------------------------------------------------- oracles
def oracle_c(study, repo):
    """libclang: direct call edges (caller def -> callee def by USR) and the indirect call-site count."""
    sys.path.insert(0, str(next((study / "venv" / "lib").glob("python3*/site-packages"))))
    import clang.cindex as ci
    root = study / "repos" / repo
    incs = sorted({str(p.parent) for p in root.rglob("*.h")})[:300]
    args = ["-x", "c", "-std=gnu11", f"-I{root}", *[f"-I{d}" for d in incs]]
    idx = ci.Index.create()
    defs, calls, indirect, direct_sites = {}, [], 0, 0
    for f in sorted(root.rglob("*.c")):
        try:
            tu = idx.parse(str(f), args=args, options=ci.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES * 0)
        except ci.TranslationUnitLoadError:
            continue
        def walk(cur, fn):
            nonlocal indirect, direct_sites
            for c in cur.get_children():
                if c.location.file and Path(str(c.location.file.name)).resolve() != f.resolve() and c.kind != ci.CursorKind.CALL_EXPR:
                    continue
                if c.kind == ci.CursorKind.FUNCTION_DECL and c.is_definition():
                    rel = str(Path(str(c.location.file.name)).resolve().relative_to(root.resolve()))
                    defs[c.get_usr()] = (rel, c.spelling, c.extent.start.line)
                    walk(c, c.get_usr())
                    continue
                if c.kind == ci.CursorKind.CALL_EXPR and fn:
                    ref = c.referenced
                    if ref is not None and ref.kind == ci.CursorKind.FUNCTION_DECL:
                        calls.append((fn, ref.get_usr()))
                        direct_sites += 1
                    else:
                        indirect += 1
                walk(c, fn)
        walk(tu.cursor, None)
    edges = {(defs[a], defs[b]) for a, b in calls if a in defs and b in defs and a != b}
    return {"direct": edges, "dynamic": set(), "indirect_sites": indirect, "direct_sites": direct_sites}


def oracle_go(study, repo):
    env = {**os.environ, "GOPATH": str(study / "gopath"), "GOMODCACHE": str(study / "gopath/pkg/mod"),
           "GOTOOLCHAIN": "auto", "GOFLAGS": "-mod=mod", "PATH": f"{study}/go/bin:{study}/gopath/bin:{os.environ['PATH']}"}
    root = (study / "repos" / repo).resolve()
    fmt = "{{.Caller.Pos}}\t{{.Callee.Pos}}\t{{.Caller.Name}}\t{{.Callee.Name}}"
    out = {}
    for algo in ("static", "cha"):
        p = subprocess.run(["callgraph", f"-algo={algo}", f"-format={fmt}", "./..."], cwd=root, env=env,
                           capture_output=True, text=True)
        es = set()
        for line in p.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) != 4:
                continue
            def pos(s):
                m = re.match(r"(.*):(\d+):\d+$", s)
                if not m:
                    return None
                f = Path(m.group(1))
                try:
                    return str(f.resolve().relative_to(root)), int(m.group(2))
                except ValueError:
                    return None
            a, b = pos(parts[0]), pos(parts[1])
            if a and b:
                es.add(((a[0], parts[2].split(".")[-1], a[1]), (b[0], parts[3].split(".")[-1], b[1])))
        out[algo] = es
        out[f"{algo}_rc"] = p.returncode
        out[f"{algo}_err"] = p.stderr[-400:]
    return {"direct": out["static"], "dynamic": out["cha"] - out["static"], "rc": [out["static_rc"], out["cha_rc"]],
            "err": out["static_err"] or out["cha_err"]}


def oracle_java(study, repo):
    jar = sorted((study / "tools/java-callgraph/target").glob("javacg-*-static.jar")) or \
        sorted((study / "tools/java-callgraph/target").glob("*.jar"))
    target = [j for j in (study / "repos" / repo / "target").glob("*.jar")
              if not re.search(r"(sources|javadoc|tests)", j.name)]
    p = subprocess.run(["java", "-jar", str(jar[0]), str(target[0])], capture_output=True, text=True)
    def node(s):
        m = re.match(r"(?:\([A-Z]\))?([\w.$]+):([\w<>$]+)\(", s)
        if not m:
            return None
        cls, meth = m.group(1), m.group(2)
        outer = cls.split("$")[0]
        path = "src/main/java/" + outer.replace(".", "/") + ".java"
        name = outer.split(".")[-1] if meth == "<init>" else meth
        return path, name
    direct, dynamic = set(), set()
    for line in p.stdout.splitlines():
        if not line.startswith("M:"):
            continue
        left, _, right = line[2:].partition(" ")
        kind = right[1:2] if right.startswith("(") else "?"
        a, b = node(left), node(right)
        if a and b and a != b:
            (direct if kind in ("S", "O") else dynamic).add((a, b))
    return {"direct": direct, "dynamic": dynamic, "rc": p.returncode, "err": p.stderr[-400:]}


def oracle_python(study, repo):
    root = (study / "repos" / repo).resolve()
    pkg = root / "sphinx"
    files = [str(f) for f in sorted(pkg.rglob("*.py"))]
    out = study / "oracle_pycg.json"
    p = subprocess.run([str(study / "venv/bin/python"), "-m", "pycg", "--package", str(root), *files, "-o", str(out)],
                       capture_output=True, text=True, timeout=7200)
    if p.returncode != 0 or not out.exists():
        return {"direct": set(), "dynamic": set(), "rc": p.returncode, "err": p.stderr[-400:]}
    cg = json.loads(out.read_text())
    def node(q):
        parts = q.split(".")
        for i in range(len(parts) - 1, 0, -1):
            f = root / ("/".join(parts[:i]) + ".py")
            if f.exists():
                return str(f.relative_to(root)), parts[-1]
        return None
    es = set()
    for a, bs in cg.items():
        na = node(a)
        for b in bs:
            nb = node(b)
            if na and nb and na != nb:
                es.add((na, nb))
    return {"direct": es, "dynamic": set(), "rc": 0, "err": ""}


# ------------------------------------------------------------------------------------------------- comparison
def matcher(nodes, meta, use_line):
    by = collections.defaultdict(list)
    for n in nodes:
        by[n].append(n)
    byline = collections.defaultdict(list)
    for (p, n), ln in meta.items():
        if (p, n) in nodes:
            byline[(p, n)].append(ln)

    def m(o):
        if use_line and len(o) == 3:
            p, n, ln = o
            if (p, n) in nodes and any(abs(x - ln) <= 3 for x in byline[(p, n)]):
                return (p, n)
            return None
        key = (o[0], o[1])
        return key if key in nodes else None
    return m


def kappa(a, b):
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return float((po - pe) / (1 - pe)) if pe < 1 else None


def compare(nodes, edges, meta, orc, use_line):
    m = matcher(nodes, meta, use_line)
    od = {(m(a), m(b)) for a, b in orc["direct"]}
    oy = {(m(a), m(b)) for a, b in orc["dynamic"]}
    od = {e for e in od if e[0] and e[1] and e[0] != e[1]}
    oy = {e for e in oy if e[0] and e[1] and e[0] != e[1]} - od
    matched = {x for e in od | oy for x in e}
    ee = {e for e in edges if e[0] in matched and e[1] in matched}
    oall = od | oy
    prec = len(ee & oall) / len(ee) if ee else None
    rec = len(ee & od) / len(od) if od else None
    only = oall - ee
    dyn_share = len(only & oy) / len(only) if only else None
    din_e = collections.Counter(b for _, b in ee)
    din_o = collections.Counter(b for _, b in oall)
    ms = sorted(matched)
    from scipy.stats import spearmanr
    rho = float(spearmanr([din_e.get(x, 0) for x in ms], [din_o.get(x, 0) for x in ms]).statistic) if len(ms) > 10 else None

    def hubs(c):
        vals = sorted((c.get(x, 0) for x in ms), reverse=True)
        k = max(3, int(round(0.01 * len(ms))))
        thr = vals[min(k, len(vals)) - 1] if vals else 0
        return {x for x in ms if c.get(x, 0) >= thr and c.get(x, 0) > 0}
    he, ho = hubs(din_e), hubs(din_o)
    jac = len(he & ho) / len(he | ho) if (he | ho) else None

    def coup(es):
        nb = collections.defaultdict(set)
        for a, b in es:
            if a[0] != b[0]:
                nb[a[0]].add(b[0])
                nb[b[0]].add(a[0])
        return nb
    files = sorted({x[0] for x in ms})
    ce, co = coup(ee), coup(oall)
    ve, vo = [len(ce[f]) for f in files], [len(co[f]) for f in files]
    qe, qo = np.quantile(ve, 0.8) if ve else 0, np.quantile(vo, 0.8) if vo else 0
    kap = kappa([v >= qe and v > 0 for v in ve], [v >= qo and v > 0 for v in vo]) if files else None
    return {"matched_functions": len(ms), "engine_nodes": len(nodes), "oracle_direct_edges": len(od),
            "oracle_dynamic_edges": len(oy), "engine_edges_on_matched": len(ee), "precision": prec,
            "recall_direct": rec, "oracle_only_dynamic_share": dyn_share, "indegree_spearman": rho,
            "hub_jaccard": jac, "coupling_kappa": kap,
            "H1": bool(prec is not None and rec is not None and prec >= 0.8 and rec >= 0.8),
            "H2": None if dyn_share is None else bool(dyn_share >= 0.5),
            "H3": bool(rho is not None and jac is not None and kap is not None and rho >= 0.8 and jac >= 0.5 and kap >= 0.6)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", type=Path, required=True)
    a = ap.parse_args()
    res = {}
    for repo, lang in REPOS.items():
        nodes, edges, meta = engine(a.study, repo, lang)
        try:
            orc = {"c": oracle_c, "go": oracle_go, "java": oracle_java, "python": oracle_python}[lang](a.study, repo)
        except Exception as e:  # registered: a failing oracle makes the language not evaluable, never a substitute
            res[repo] = {"language": lang, "evaluable": False, "error": f"{type(e).__name__}: {e}"[:400]}
            print(f"{repo}: oracle failed: {e}", file=sys.stderr, flush=True)
            continue
        if not orc["direct"] and not orc["dynamic"]:
            res[repo] = {"language": lang, "evaluable": False, "error": str(orc.get("err", ""))[:400]}
            continue
        r = compare(nodes, edges, meta, orc, use_line=lang in ("c", "go"))
        if lang == "c":
            r["indirect_call_share"] = orc["indirect_sites"] / max(1, orc["indirect_sites"] + orc["direct_sites"])
            r["H2"] = None  # libclang cannot resolve function-pointer targets: H2 not evaluable for C (registered kinds)
        res[repo] = {"language": lang, "evaluable": True, **r}
        print(f"{repo}: done", file=sys.stderr, flush=True)
    by = collections.defaultdict(list)
    for r in res.values():
        by[r["language"]].append(r)
    verdict = {}
    for h in ("H1", "H2", "H3"):
        vals = {lang: [r.get(h) for r in rs if r.get("evaluable")] for lang, rs in by.items()}
        ev = {lang: v for lang, v in vals.items() if v and all(x is not None for x in v)}
        verdict[h] = {"per_language": {lang: all(v) for lang, v in ev.items()},
                      "verdict": ("not evaluable" if not ev else "supported" if all(all(v) for v in ev.values()) else "not supported")}
    res["verdicts"] = verdict
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
