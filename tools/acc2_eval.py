#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""ACC-2 (docs/acc2_hypotheses.md): the engine's resolved call graph (fcall_data) vs compiler-grade oracles.

    python tools/acc2_eval.py --study ACC_STUDY_DIR > acc2_result.json

Reuses tools/acc_eval.py's oracles with the registered changes: Go in the module's own mode (no -mod flag), PyCG per
top-level sphinx subpackage when the whole-package run fails, Java matched by (file, class, method, argument count),
commons-io added. Aggregates only.
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

sys.path.insert(0, str(Path(__file__).parent))
import acc_eval as A  # noqa: E402

REPOS = {"libgit2": "c", "redis": "c", "commons-lang": "java", "commons-io": "java", "prometheus": "go", "sphinx": "python"}


def resolved(study, repo, lang):
    db = sorted((study / "engine" / repo).glob("*_galaxy_master.db"))[0]
    root = str(study / "repos" / repo)
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    cls = {cid: n for cid, n in con.execute("SELECT id, class_name FROM class_data")}
    rows = {}
    for fid, path, name, start, loc, args, pc in con.execute(
            "SELECT f.id, fd.file_path, f.func_name, f.start_line, f.loc, f.args, f.parent_class_id FROM function_data f "
            "JOIN file_data fd ON f.file_id = fd.id"):
        p = str(path)
        if p.startswith(root):
            p = p[len(root):].lstrip("/")
        if not name or (loc or 0) < 3 or not p.endswith(A.EXT[lang]):
            continue
        try:
            argc = int(args) if args is not None and str(args).strip().lstrip("-").isdigit() else None
        except ValueError:
            argc = None
        rows[fid] = {"file": p, "name": str(name).split("::")[-1].split(".")[-1], "start": int(start or 0),
                     "cls": cls.get(pc), "argc": argc}
    edges, kinds = set(), {}
    for s, d, step in con.execute("SELECT src_func_id, dst_func_id, step FROM fcall_data WHERE kind = 'call' AND dst_func_id IS NOT NULL"):
        if s in rows and d in rows and s != d:
            e = ((rows[s]["file"], s), (rows[d]["file"], d))
            edges.add(e)
            kinds.setdefault(e, step)
    con.close()
    return rows, edges, kinds


def matcher(rows, lang):
    by_file = collections.defaultdict(list)
    for fid, r in rows.items():
        by_file[r["file"]].append((fid, r))

    def m(o):
        if o is None:
            return None
        if lang in ("c", "go"):
            p, n, ln = o
            c = [(fid, r) for fid, r in by_file.get(p, []) if abs(r["start"] - ln) <= 3]
            if len(c) > 1:
                c = [x for x in c if x[1]["name"] == n] or c
            return (p, c[0][0]) if len(c) == 1 else None
        if lang == "java":
            p, cname, n, argc = o
            c = [(fid, r) for fid, r in by_file.get(p, []) if r["name"] == n and (r["cls"] in (cname, None))]
            if len(c) > 1 and argc is not None:
                c = [x for x in c if x[1]["argc"] == argc] or c
            return (p, c[0][0]) if len(c) == 1 else None
        p, cname, n = o
        c = [(fid, r) for fid, r in by_file.get(p, []) if r["name"] == n and (cname is None or r["cls"] in (cname, None))]
        return (p, c[0][0]) if len(c) == 1 else None
    return m


def _go(study, repo, env):
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
                mm = re.match(r"(.*):(\d+):\d+$", s)
                if not mm:
                    return None
                try:
                    return str(Path(mm.group(1)).resolve().relative_to(root)), int(mm.group(2))
                except ValueError:
                    return None
            a, b = pos(parts[0]), pos(parts[1])
            if a and b:
                es.add(((a[0], parts[2].split(".")[-1], a[1]), (b[0], parts[3].split(".")[-1], b[1])))
        out[algo], out[algo + "_rc"], out[algo + "_err"] = es, p.returncode, p.stderr[-400:]
    return {"direct": out["static"], "dynamic": out["cha"] - out["static"], "rc": [out["static_rc"], out["cha_rc"]],
            "err": out["static_err"] or out["cha_err"]}


def oracle_java(study, repo):
    jar = sorted((study / "tools/java-callgraph/target").glob("javacg-*-static.jar"))
    target = [j for j in (study / "repos" / repo / "target").glob("*.jar") if not re.search(r"(sources|javadoc|tests)", j.name)]
    p = subprocess.run(["java", "-jar", str(jar[0]), str(target[0])], capture_output=True, text=True)

    def node(s):
        mm = re.match(r"(?:\([A-Z]\))?([\w.$]+):([\w<>$]+)\(([^)]*)\)", s)
        if not mm:
            return None
        cls, meth, args = mm.group(1), mm.group(2), mm.group(3)
        outer = cls.split("$")[0]
        simple = cls.split(".")[-1].split("$")[-1]
        name = simple if meth == "<init>" else meth
        argc = len([x for x in args.split(",") if x.strip()])
        return ("src/main/java/" + outer.replace(".", "/") + ".java", simple, name, argc)
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

    def run(files, tag):
        out = study / f"oracle_pycg_{tag}.json"
        p = subprocess.run([str(study / "venv/bin/python"), "-m", "pycg", "--package", str(root), *files, "-o", str(out)],
                           capture_output=True, text=True, timeout=7200)
        return json.loads(out.read_text()) if p.returncode == 0 and out.exists() else None, p.stderr[-300:]

    def node(q):
        parts = q.split(".")
        for i in range(len(parts) - 1, 0, -1):
            f = root / ("/".join(parts[:i]) + ".py")
            if f.exists():
                rest = parts[i:]
                return (str(f.relative_to(root)), rest[-2] if len(rest) >= 2 else None, rest[-1])
        return None
    pkg = root / "sphinx"
    cg, err = run([str(f) for f in sorted(pkg.rglob("*.py"))], "all")
    groups, failed = {}, []
    if cg is None:
        subs = [d for d in sorted(pkg.iterdir()) if d.is_dir() and (d / "__init__.py").exists()]
        groups = {d.name: [str(f) for f in sorted(d.rglob("*.py"))] for d in subs}
        groups["_top"] = [str(f) for f in sorted(pkg.glob("*.py"))]
        merged = {}
        for tag, files in groups.items():
            g, e = run(files, tag)
            if g is None:
                failed.append(tag)
                continue
            for k, v in g.items():
                merged.setdefault(k, set()).update(v)
        cg = {k: sorted(v) for k, v in merged.items()} if merged else None
    if cg is None:
        return {"direct": set(), "dynamic": set(), "rc": 1, "err": err, "failed_groups": failed}
    es = set()
    for a, bs in cg.items():
        na = node(a)
        for b in bs:
            nb = node(b)
            if na and nb and na != nb:
                es.add((na, nb))
    return {"direct": es, "dynamic": set(), "rc": 0, "err": "", "mode": "per-subpackage" if groups else "whole",
            "failed_groups": failed, "groups": len(groups)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", type=Path, required=True)
    a = ap.parse_args()
    res = {}
    for repo, lang in REPOS.items():
        rows, edges, kinds = resolved(a.study, repo, lang)
        try:
            orc = {"c": A.oracle_c, "go": lambda s, r: _go(s, r, {**{k: v for k, v in os.environ.items() if k != "GOFLAGS"},
                   "GOPATH": str(s / "gopath"), "GOMODCACHE": str(s / "gopath/pkg/mod"), "GOTOOLCHAIN": "auto",
                   "PATH": f"{s}/go/bin:{s}/gopath/bin:{os.environ['PATH']}"}),
                   "java": oracle_java, "python": oracle_python}[lang](a.study, repo)
        except Exception as e:
            res[repo] = {"language": lang, "evaluable": False, "error": f"{type(e).__name__}: {e}"[:400]}
            print(f"{repo}: oracle failed: {e}", file=sys.stderr, flush=True)
            continue
        if not orc["direct"] and not orc["dynamic"]:
            res[repo] = {"language": lang, "evaluable": False, "error": str(orc.get("err", ""))[:400]}
            continue
        m = matcher(rows, lang)
        mapped = {"direct": {(m(x), m(y)) for x, y in orc["direct"]}, "dynamic": {(m(x), m(y)) for x, y in orc["dynamic"]}}
        nodes = {(r["file"], fid) for fid, r in rows.items()}
        meta = {}
        cmp_ = A.compare(nodes, edges, meta, {"direct": {(x, y) for x, y in mapped["direct"] if x and y},
                                              "dynamic": {(x, y) for x, y in mapped["dynamic"] if x and y}}, use_line=False)
        agree_kinds = collections.Counter(kinds.get(e) for e in edges if e in {(x, y) for x, y in mapped["direct"] | mapped["dynamic"]})
        res[repo] = {"language": lang, "evaluable": True, **cmp_,
                     "oracle_functions_unmatched": sum(1 for x, y in orc["direct"] | orc["dynamic"] for z in (x, y) if m(z) is None),
                     "agreeing_edges_by_resolution": dict(agree_kinds.most_common(8)),
                     **({"python_mode": orc.get("mode"), "python_failed_groups": orc.get("failed_groups")} if lang == "python" else {})}
        if lang == "c":
            res[repo]["H2"] = None
        print(f"{repo}: done", file=sys.stderr, flush=True)
    # descriptive: name-based graph on commons-io (unseen in ACC)
    try:
        n, e, meta = A.engine(a.study, "commons-io", "java")
        res["descriptive_name_based_commons_io"] = A.compare(n, e, meta, A.oracle_java(a.study, "commons-io"), use_line=False)
    except Exception as ex:
        res["descriptive_name_based_commons_io"] = {"error": str(ex)[:300]}
    by = collections.defaultdict(list)
    for k, r in res.items():
        if k in REPOS:
            by[r["language"]].append(r)
    ver = {}
    for h in ("H1", "H3"):
        per = {lang: all(r.get(h) for r in rs if r.get("evaluable")) for lang, rs in by.items() if any(r.get("evaluable") for r in rs)}
        ver[f"ACC2-{h}"] = {"per_language": per, "not_evaluable": sorted(l for l, rs in by.items() if not any(r.get("evaluable") for r in rs))}
    ver["ACC2-G"] = {"gate_passes": sorted(l for l, ok in ver["ACC2-H3"]["per_language"].items() if ok)}
    res["verdicts"] = ver
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
