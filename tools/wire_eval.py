#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""WIRE-H1..H3 (docs/wire_hypotheses.md): COBOL -> det Java call networks along the translator's map. Aggregates only.

    python tools/wire_eval.py --gg GG_CHECKOUT --ports-dispatch DIR --ports-structured DIR --scratch DIR \
        [--py ENGINE_PY] > wire_result.json

GG_CHECKOUT is gitgalaxy at the registered commit (8f96d76ba); its tests/tools give the cases, corpora and programs.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np

SEED, NULL_DRAWS, BOOT, PERM_DRAWS, ALPHA = 2982, 1000, 5000, 10000, 0.01 / 3
MIN_UNITS, MIN_EDGES, MIN_PROGRAMS, SFS_BAR = 3, 2, 30, 3 / 124
HEADER = re.compile(r"/\*\*\s*([A-Z0-9][A-Z0-9-]*)\.\s*\*/\s*\n\s*(?:public|private|protected)?\s*(?:static\s+)?"
                    r"(?:void|int|boolean|long|String)\s+(\w+)\s*\(")
STRUCT_MAIN = re.compile(r"(?:private|public)\s+void\s+main\s*\(\s*\)")
PERFORM = re.compile(r"\bperform\(\s*(\d+)\s*,\s*(\d+)\s*\)")
CASE_RET = re.compile(r"case\s+(\d+)\s*:\s*return\s+(\w+)\s*\(")


def norm(x: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", x).lower()


def scan(src: Path, out: Path, gg: Path, py: str) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    dbs = sorted(out.glob("*_galaxy_master.db"))
    if dbs:
        return dbs[0]
    env = {**os.environ, "PYTHONPATH": str(gg), "GITGALAXY_LICENSE_KEY": "COMMUNITY_FREE_TIER"}
    with open(out / "scan.log", "w") as log:
        subprocess.run([py, "-m", "gitgalaxy.galaxyscope", str(src), "--output", str(out) + "/"], env=env,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    return sorted(out.glob("*_galaxy_master.db"))[0]


def units(db: Path) -> dict[str, dict[str, tuple[int, set[str]]]]:
    """file path -> unit name -> (start line, callee names) from calls_out_to + transfers_to."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    out: dict[str, dict[str, tuple[int, set[str]]]] = collections.defaultdict(dict)
    for p, n, start, c, t in con.execute("SELECT fd.file_path, f.func_name, f.start_line, f.calls_out_to, "
                                          "f.transfers_to FROM function_data f JOIN file_data fd ON f.file_id = fd.id"):
        callees: set[str] = set()
        for raw in (c, t):
            try:
                vals = json.loads(raw) if raw else []
            except ValueError:
                vals = []
            for v in vals:
                for tok in str(v).replace("(", " ").split():
                    callees.add(tok.split(".")[-1].split("::")[-1])
        if n:
            out[Path(p).name][str(n).split(".")[-1].split("::")[-1]] = (start or 0, callees)
    con.close()
    return out


def jacc(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 0.0


def wl_hist(n: int, edges: set[tuple[int, int]], iters: int = 3) -> collections.Counter:
    outn, inn = collections.defaultdict(list), collections.defaultdict(list)
    for a, b in edges:
        outn[a].append(b)
        inn[b].append(a)
    lab = [f"{len(inn[i])},{len(outn[i])}" for i in range(n)]
    h = collections.Counter(f"0:{x}" for x in lab)
    for it in range(1, iters + 1):
        lab = [hashlib.sha1(f"{lab[i]}|{sorted(lab[j] for j in outn[i])}|{sorted(lab[j] for j in inn[i])}".encode())
               .hexdigest()[:12] for i in range(n)]
        h.update(f"{it}:{x}" for x in lab)
    return h


def cos(a: collections.Counter, b: collections.Counter) -> float:
    d = sum(a[k] * b[k] for k in a.keys() & b.keys())
    na, nb = np.sqrt(sum(v * v for v in a.values())), np.sqrt(sum(v * v for v in b.values()))
    return d / (na * nb) if na and nb else 0.0


def java_map(text: str, style: str, program: str) -> dict[str, str]:
    """Java method name -> COBOL unit name, from the translator's headers."""
    m = {meth: para for para, meth in HEADER.findall(text)}
    for meth, para in list(m.items()):
        if para == "MAINLINE":
            m[meth] = program
    if style == "structured" and STRUCT_MAIN.search(text):
        m["main"] = program
    return m


def dispatch_resolved_edges(text: str, jm: dict[str, str]) -> set[tuple[str, str]]:
    """Descriptive only (a parser, not the engine): perform(a, b) inside a headed method -> paragraphs a..b."""
    idx = {int(i): meth for i, meth in CASE_RET.findall(text)}
    edges = set()
    heads = [(mm.start(), mm.group(2)) for mm in HEADER.finditer(text)]
    for k, (pos, meth) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(text)
        for a, b in PERFORM.findall(text[pos:end]):
            for i in range(int(a), int(b) + 1):
                if i in idx and idx[i] in jm and meth in jm:
                    edges.add((jm[meth], jm[idx[i]]))
    return edges


def program_eval(cob: dict[str, tuple[int, set[str]]], jav: dict[str, tuple[int, set[str]]], jm: dict[str, str],
                 rng: np.random.Generator, extra_java_edges: set[tuple[str, str]] | None = None) -> dict | None:
    cob_names = {n.upper(): n for n in cob}
    mapped = sorted({jm[m].upper() for m in jav if m in jm and jm[m].upper() in cob_names})
    if len(mapped) < MIN_UNITS:
        return {"evaluable": False, "why": f"{len(mapped)} mapped units"}
    ix = {u: i for i, u in enumerate(mapped)}
    ec = {(ix[a], ix[b.upper()]) for a in mapped for b in cob[cob_names[a]][1]
          if b.upper() in ix and b.upper() != a}
    if len(ec) < MIN_EDGES:
        return {"evaluable": False, "why": f"{len(ec)} COBOL edges among mapped units"}
    m2u = {m: jm[m].upper() for m in jav if m in jm and jm[m].upper() in ix}
    u2m = collections.defaultdict(set)
    for m, u in m2u.items():
        u2m[u].add(m)
    ej = set()
    for m, u in m2u.items():
        for callee in jav[m][1]:
            for u2, ms in u2m.items():
                if callee in ms and u2 != u:
                    ej.add((ix[u], ix[u2]))
    if extra_java_edges is not None:
        ej = {(ix[a.upper()], ix[b.upper()]) for a, b in extra_java_edges if a.upper() in ix and b.upper() in ix
              and a.upper() != b.upper()}
    j = jacc(ec, ej)
    n = len(mapped)
    nulls = []
    for _ in range(NULL_DRAWS):
        p = rng.permutation(n)
        nulls.append(jacc(ec, {(p[a], p[b]) for a, b in ej}))
    nulls = np.array(nulls)
    return {"evaluable": True, "units": n, "cobol_edges": len(ec), "java_edges": len(ej), "J": j,
            "null_mean": float(nulls.mean()), "null_p95": float(np.percentile(nulls, 95)),
            "gap": j - float(nulls.mean()), "beats_null": bool(j > np.percentile(nulls, 95))}


def summarise(rows: list[dict], rng: np.random.Generator) -> dict:
    ev = [r for r in rows if r.get("evaluable")]
    out = {"programs": len(rows), "evaluable": len(ev)}
    if len(ev) < MIN_PROGRAMS:
        return {**out, "verdict": "not evaluable"}
    g = np.array([r["gap"] for r in ev])
    boots = np.array([rng.choice(g, len(g)).mean() for _ in range(BOOT)])
    lo = float(np.quantile(boots, ALPHA))
    beat = float(np.mean([r["beats_null"] for r in ev]))
    ok = g.mean() > 0 and lo > 0 and beat >= 0.5
    return {**out, "mean_J": float(np.mean([r["J"] for r in ev])), "mean_null": float(np.mean([r["null_mean"] for r in ev])),
            "mean_gap": float(g.mean()), "gap_lo": lo, "share_beating_null": beat,
            "verdict": "supported" if ok else "not supported"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gg", type=Path, required=True)
    ap.add_argument("--ports-dispatch", type=Path, required=True)
    ap.add_argument("--ports-structured", type=Path, required=True)
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--py", default=sys.executable)
    a = ap.parse_args()
    sys.path.insert(0, str(a.gg / "tests" / "tools"))
    sys.path.insert(0, str(a.gg))
    import det_port  # noqa: E402
    import equivalence as eq  # noqa: E402
    import equivalence_common as ec  # noqa: E402
    import mainframe_corpus as mc  # noqa: E402

    rng = np.random.default_rng(SEED)
    corp: dict[str, Path] = {}
    progs: dict[str, dict] = {}  # content hash -> program record
    styles = {"dispatch": a.ports_dispatch, "structured": a.ports_structured}
    cases = sorted({p.parent.parent.name for st in styles.values() for p in st.glob("*/port/service")})
    for c in cases:
        case = eq.load_case(c)
        cname = case["corpus"]
        if cname not in corp:
            try:
                corp[cname] = mc.require_clone(mc.select([cname])[0])
            except SystemExit:
                corp[cname] = None
        if corp[cname] is None:
            continue
        plist = [(case["program"], ec.program_file(case, corp[cname]))]
        plist += [(x["program"], corp[cname] / x["program_source"]) for x in det_port._extra_programs(case)]
        for prog, src in plist:
            if not Path(src).is_file():
                continue
            h = hashlib.sha1(Path(src).read_bytes()).hexdigest()
            if h in progs:
                continue
            progs[h] = {"program": prog.upper(), "case": c, "corpus": cname, "src": Path(src), "hash": h[:12]}
    # one COBOL scan, one Java scan per style
    cdir = a.scratch / "cobol_src"
    shutil.rmtree(cdir, ignore_errors=True)
    cdir.mkdir(parents=True)
    for r in progs.values():
        r["cfile"] = f"{r['hash']}_{r['src'].name}"
        shutil.copy(r["src"], cdir / r["cfile"])
    cobu = units(scan(cdir, a.scratch / "cobol_scan", a.gg, a.py))
    result: dict = {"cases": len(cases), "unique_programs": len(progs), "corpora": sorted(k for k, v in corp.items() if v)}
    java: dict[str, dict] = {}
    for st, root in styles.items():
        jdir = a.scratch / f"java_{st}"
        shutil.rmtree(jdir, ignore_errors=True)
        jdir.mkdir(parents=True)
        for r in progs.values():
            svc = [f for f in (root / r["case"] / "port" / "service").glob("*.java")
                   if norm(f.stem) == norm(r["program"]) + "service"]
            if svc:
                r[f"jfile_{st}"] = f"{r['hash']}_{svc[0].name}"
                shutil.copy(svc[0], jdir / r[f"jfile_{st}"])
        java[st] = units(scan(jdir, a.scratch / f"java_scan_{st}", a.gg, a.py))
    rows: dict[str, list[dict]] = {"dispatch": [], "structured": [], "dispatch_resolved": []}
    for r in progs.values():
        cob = cobu.get(r["cfile"], {})
        for st in ("dispatch", "structured"):
            jf = r.get(f"jfile_{st}")
            base = {"program": r["program"], "corpus": r["corpus"], "case": r["case"]}
            if not jf or jf not in java[st] or not cob:
                rows[st].append({**base, "evaluable": False, "why": "no port or no scan"})
                continue
            text = (a.scratch / f"java_{st}" / jf).read_text(errors="replace")
            jm = java_map(text, st, r["program"])
            rows[st].append({**base, **program_eval(cob, java[st][jf], jm, rng)})
            if st == "dispatch":
                rows["dispatch_resolved"].append({**base, **program_eval(cob, java[st][jf], jm, rng,
                                                                         dispatch_resolved_edges(text, jm))})
    result["WIRE-H1"] = summarise(rows["structured"], rng)
    result["WIRE-H2"] = summarise(rows["dispatch"], rng)
    result["descriptive_dispatch_resolved_by_parser"] = summarise(rows["dispatch_resolved"], rng)
    result["descriptive_dispatch_resolved_by_parser"].pop("verdict", None)
    # H3: name-free identification, structured ports vs every evaluable COBOL program
    graphs = {}
    for r in progs.values():
        cob = cobu.get(r["cfile"], {})
        names = sorted(cob)
        ix = {n.upper(): i for i, n in enumerate(names)}
        e = {(ix[n.upper()], ix[c.upper()]) for n in names for c in cob[n][1] if c.upper() in ix and c.upper() != n.upper()}
        if len(names) >= MIN_UNITS and len(e) >= MIN_EDGES:
            graphs[r["hash"]] = wl_hist(len(names), e)
    queries = []
    for r in progs.values():
        jf = r.get("jfile_structured")
        if not jf or r["hash"] not in graphs or jf not in java["structured"]:
            continue
        jav = java["structured"][jf]
        jm = java_map((a.scratch / "java_structured" / jf).read_text(errors="replace"), "structured", r["program"])
        meths = sorted(m for m in jav if m in jm)
        if len(meths) < MIN_UNITS:
            continue
        ix = {m: i for i, m in enumerate(meths)}
        e = {(ix[m], ix[c]) for m in meths for c in jav[m][1] if c in ix and c != m}
        queries.append((r["hash"], wl_hist(len(meths), e)))
    cands = sorted(graphs)
    S = np.array([[cos(q, graphs[c]) for c in cands] for _, q in queries]) if queries else np.zeros((0, 0))
    own = np.array([cands.index(h) for h, _ in queries])

    def hits(owner: np.ndarray, k: int = 1) -> int:
        tot = 0
        for i, o in enumerate(owner):
            rank = int((S[i] >= S[i, o]).sum())  # pessimistic: ties count against the true source
            tot += rank <= k
        return tot

    h3 = {"queries": len(queries), "candidates": len(cands)}
    if len(queries) >= MIN_PROGRAMS:
        h = hits(own)
        ge = sum(hits(rng.integers(0, len(cands), len(own))) >= h for _ in range(PERM_DRAWS))
        rate, chance = h / len(queries), 1 / len(cands)
        p = (1 + ge) / (1 + PERM_DRAWS)
        h3.update({"top1": h, "top1_rate": rate, "chance": chance, "p": p, "top5_rate": hits(own, 5) / len(queries),
                   "verdict": "supported" if (p < ALPHA and rate > SFS_BAR) else "not supported"})
    else:
        h3["verdict"] = "not evaluable"
    result["WIRE-H3"] = h3
    # descriptive: per estate, drops
    for st in ("structured", "dispatch"):
        by = collections.defaultdict(list)
        for r in rows[st]:
            if r.get("evaluable"):
                by[r["corpus"]].append(r)
        result[f"by_estate_{st}"] = {c: {"n": len(v), "mean_J": float(np.mean([x["J"] for x in v])),
                                          "mean_gap": float(np.mean([x["gap"] for x in v])),
                                          "beat": float(np.mean([x["beats_null"] for x in v]))} for c, v in by.items()}
        result[f"dropped_{st}"] = dict(collections.Counter(re.sub(r"\d+ ", "", r.get("why", "?"))
                                                           for r in rows[st] if not r.get("evaluable")))
    # descriptive: model-refined B2 ports (gitgalaxy docs/benchmarks/det-refine-*)
    b2 = {}
    bdir = a.scratch / "b2_java"
    shutil.rmtree(bdir, ignore_errors=True)
    bdir.mkdir(parents=True)
    for f in sorted((a.gg / "docs" / "benchmarks").glob("det-refine-*/*.java")):
        shutil.copy(f, bdir / f"{f.parent.name}__{f.name}")
    bu = units(scan(bdir, a.scratch / "b2_scan", a.gg, a.py))
    for fname, jav in bu.items():
        prog = fname.split("__")[1].split("Service")[0].upper()
        r = next((x for x in progs.values() if x["program"] == prog), None)
        if r is None:
            continue
        jm = java_map((bdir / fname).read_text(errors="replace"), "structured", prog)
        if not any(m in jm for m in jav):
            jm = java_map((bdir / fname).read_text(errors="replace"), "dispatch", prog)
        b2[fname] = program_eval(cobu.get(r["cfile"], {}), jav, jm, rng)
    result["descriptive_b2_refined"] = b2
    print(json.dumps(result, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
