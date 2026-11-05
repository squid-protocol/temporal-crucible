#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Validate the engine's C function extraction and call graph on a study repo.

The studies here read `function_data` (spans for FREC, counts for everything)
and the call graph (`fcall` / centrality). gitgalaxy measures both against
independent tools, but only on its own pinned corpora. This runs the SAME
measurement code on a snapshot of a study repo, with the engine build the
study used:

  1. functions vs tree-sitter -- gitgalaxy tests/tools/tree_sitter_accuracy_audit.py
     `measure("c")`, its corpus lookup pointed at the snapshot;
  2. call links vs libclang -- tests/tools/call_graph_resolution.py `_score`
     with callgraph_refs' libclang reference built for the snapshot;
  3. functions vs Universal Ctags -- (path, name) of every C function definition
     (`--kinds-C=f`), against the engine's function_data names.

A reference is not ground truth (gitgalaxy CLAUDE.md): disagreements are
listed as samples to read in source, not counted as engine bugs.

    GITGALAXY_PATH=/path/to/engine/worktree <that worktree's venv>/bin/python \
        tools/engine_validate.py --repo curl --ref curl-8_17_0
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

TC_ROOT = pathlib.Path(__file__).resolve().parent.parent
POOL = pathlib.Path(os.environ.get("EXPOSURE_POOL", "/srv/storage_16tb/projects/temporal-crucible-pool"))
ENGINE = pathlib.Path(os.environ["GITGALAXY_PATH"]).resolve()
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "tests" / "tools"))
os.environ["PATH"] = f"{pathlib.Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}"


def _pct(a, b):
    return round(100.0 * a / b, 2) if b else None


def functions_vs_tree_sitter(snap: pathlib.Path) -> dict:
    import tree_sitter_accuracy_audit as tsa

    tsa.ensure_corpus = lambda lang: snap
    tsa.CRUCIBLE_PATH = snap.parent / "language-crucible"  # it reports the corpus path relative to this root's parent
    m = tsa.measure("c", verbose=True)
    found, real, extra = m["found_functions"], m["real_functions"], m["extra_functions"]
    return {"files": m["files_scanned"], "tree_sitter_functions": real, "engine_matched": found,
            "engine_extra": extra, "recall_pct": _pct(found, real), "precision_pct": _pct(found, found + extra),
            "missing_samples": m.get("_missing_examples", [])[:15], "extra_samples": m.get("_extra_examples", [])[:15]}


def calls_vs_libclang(snap: pathlib.Path, name: str) -> tuple[dict, pathlib.Path]:
    import call_graph_resolution as cgr
    from callgraph_refs import REFERENCES, reference_graph

    graph, version = reference_graph("c", snap, use_cache=False)
    db = cgr._scan(snap)
    res = cgr._score(REFERENCES["c"].tool, [(name, graph, db)], samples=8)
    res["reference_version"] = version
    return res, db


def functions_vs_ctags(snap: pathlib.Path, db: pathlib.Path) -> dict:
    # .h files are C here (ctags maps them to C++ by default).
    out = subprocess.run(["ctags", "-R", "--languages=C", "--langmap=C:+.h", "--kinds-C=f", "--output-format=json",
                          "--fields=+n", "-f", "-", "."], cwd=snap, capture_output=True, text=True).stdout
    ct = set()
    for line in out.splitlines():
        try:
            t = json.loads(line)
        except json.JSONDecodeError:
            continue
        if t.get("_type") == "tag" and t.get("kind") == "function":
            ct.add((t["path"], t["name"]))
    con = sqlite3.connect(db)
    gg = {(p, n) for p, n in con.execute(
        "SELECT fd.file_path, fn.func_name FROM function_data fn JOIN file_data fd ON fd.id = fn.file_id "
        "WHERE fd.language = 'c'")}
    c_files = {r[0] for r in con.execute("SELECT file_path FROM file_data WHERE language = 'c'")}
    con.close()
    both = ct & gg
    # Extraction proper: only files the engine scanned as C (separates file classification
    # -- e.g. docs/examples/ read as documentation -- from function extraction).
    ct_in = {t for t in ct if t[0] in c_files}
    both_in = ct_in & gg
    not_c = sorted({t[0] for t in ct - ct_in})
    return {"ctags_functions": len(ct), "engine_functions": len(gg), "agree": len(both),
            "engine_recall_vs_ctags_pct": _pct(len(both), len(ct)),
            "engine_precision_vs_ctags_pct": _pct(len(both), len(gg)),
            "in_engine_c_files": {"ctags_functions": len(ct_in), "agree": len(both_in),
                                  "recall_pct": _pct(len(both_in), len(ct_in)),
                                  "precision_pct": _pct(len(both_in), len(gg))},
            "ctags_files_not_scanned_as_c": len(not_c), "not_c_dir_samples": sorted({f.split("/")[0] + "/" + (f.split("/")[1] if "/" in f else "") for f in not_c})[:15],
            "ctags_only_samples": sorted(ct_in - gg)[:15], "engine_only_samples": sorted(gg - ct)[:15]}


def spans_vs_tree_sitter(snap: pathlib.Path, db: pathlib.Path) -> dict:
    """FREC maps a fix to a function by its span [start_line, start_line + loc). For every
    engine C function, take the tree-sitter function_definition containing its start line
    and compare the two spans end to end."""
    import tree_sitter_language_pack as tslp

    parser = tslp.get_parser("c")
    con = sqlite3.connect(db)
    rows = con.execute(
        "SELECT fd.file_path, fn.func_name, fn.start_line, fn.loc FROM function_data fn "
        "JOIN file_data fd ON fd.id = fn.file_id WHERE fd.language = 'c' AND fn.start_line IS NOT NULL").fetchall()
    con.close()
    by_file: dict[str, list] = {}
    for r in rows:
        by_file.setdefault(r[0], []).append(r)
    n = exact_start = exact_end = end_pm1 = 0
    jacc = []
    no_ts = 0
    bad = []
    for path, funcs in by_file.items():
        try:
            src = (snap / path).read_bytes()
        except OSError:
            continue
        spans = []
        stack = [parser.parse(src).root_node]
        while stack:
            node = stack.pop()
            if node.type == "function_definition":
                spans.append((node.start_point[0] + 1, node.end_point[0] + 1))
            stack.extend(node.children)
        for _, name, start, loc in funcs:
            n += 1
            end = start + max(loc or 1, 1) - 1
            cands = [sp for sp in spans if sp[0] <= start <= sp[1]] or [sp for sp in spans if start <= sp[0] <= end]
            if not cands:
                no_ts += 1
                continue
            ts = min(cands, key=lambda sp: sp[1] - sp[0])
            exact_start += ts[0] == start
            exact_end += ts[1] == end
            end_pm1 += abs(ts[1] - end) <= 1
            inter = max(0, min(ts[1], end) - max(ts[0], start) + 1)
            union = max(ts[1], end) - min(ts[0], start) + 1
            jacc.append(inter / union)
            if abs(ts[1] - end) > 1 and len(bad) < 12:
                bad.append({"path": path, "func": name, "engine": [start, end], "tree_sitter": list(ts)})
    m = n - no_ts
    jacc.sort()
    return {"engine_functions": n, "matched_to_ts": m, "no_ts_definition": no_ts,
            "start_exact_pct": _pct(exact_start, m), "end_exact_pct": _pct(exact_end, m),
            "end_within_1_pct": _pct(end_pm1, m),
            "overlap_jaccard_median": round(jacc[len(jacc) // 2], 4) if jacc else None,
            "overlap_jaccard_p05": round(jacc[len(jacc) // 20], 4) if jacc else None,
            "end_mismatch_samples": bad}


def imports_vs_includes(snap: pathlib.Path) -> dict:
    import import_graph_accuracy as iga

    with tempfile.TemporaryDirectory(dir=snap.parent) as tmp:
        file_langs, edges, raw = iga.scan_group(snap, pathlib.Path(tmp) / snap.name)
        r = iga.score_group(snap, file_langs, edges, ("c",), raw).get("c", {})
    keep = {k: r[k] for k in ("files", "imports", "found", "edges", "correct") if k in r}
    keep["recall_pct"] = _pct(r.get("found", 0), r.get("imports", 0))
    keep["precision_pct"] = _pct(r.get("correct", 0), r.get("edges", 0))
    keep["fn_samples"] = list(r.get("fn", []))[:12]
    keep["fp_samples"] = list(r.get("fp", []))[:12]
    return keep


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    a = ap.parse_args()
    t0 = time.time()
    repo = POOL / a.repo
    sha = subprocess.run(["git", "-C", str(repo), "rev-parse", f"{a.ref}^{{commit}}"],
                         capture_output=True, text=True, check=True).stdout.strip()
    engine_sha = subprocess.run(["git", "-C", str(ENGINE), "rev-parse", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
    scratch = pathlib.Path(os.environ.get("TC_SCRATCH", "/nvme-data/tc-scratch"))
    scratch.mkdir(parents=True, exist_ok=True)
    work = pathlib.Path(tempfile.mkdtemp(prefix="engval_", dir=scratch))
    snap = work / a.repo  # basename == the repo name the engine keys on
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", "--detach", str(snap), sha], check=True)
    try:
        result = {"repo": a.repo, "ref": a.ref, "sha": sha, "engine_sha": engine_sha}
        result["functions_vs_tree_sitter"] = functions_vs_tree_sitter(snap)
        calls, db = calls_vs_libclang(snap, a.repo)
        result["calls_vs_libclang"] = calls
        result["functions_vs_ctags"] = functions_vs_ctags(snap, db)
        result["spans_vs_tree_sitter"] = spans_vs_tree_sitter(snap, db)
        result["imports_vs_includes"] = imports_vs_includes(snap)
    finally:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(snap)])
        shutil.rmtree(work, ignore_errors=True)
    result["runtime_s"] = round(time.time() - t0, 1)
    out = a.out or TC_ROOT / "dbs" / f"engine_validate_{a.repo}_{a.ref.replace('/', '_')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, default=str))
    f, c, k = result["functions_vs_tree_sitter"], result["calls_vs_libclang"], result["functions_vs_ctags"]
    print(json.dumps({"repo": a.repo, "ref": a.ref, "functions_vs_tree_sitter": {x: f[x] for x in (
        "tree_sitter_functions", "recall_pct", "precision_pct")},
        "functions_vs_ctags": {x: k[x] for x in ("ctags_functions", "engine_recall_vs_ctags_pct",
                                                 "engine_precision_vs_ctags_pct", "in_engine_c_files",
                                                 "ctags_files_not_scanned_as_c")},
        "spans_vs_tree_sitter": {x: v for x, v in result["spans_vs_tree_sitter"].items() if x != "end_mismatch_samples"},
        "imports_vs_includes": {x: v for x, v in result["imports_vs_includes"].items() if not x.endswith("samples")},
        "calls_confident": {x: c["confident"].get(x) for x in ("agree", "wrong", "external", "precision_pct",
                                                              "strict_precision_pct")},
        "calls_vs_libclang": {x: c.get(x) for x in c if not isinstance(c.get(x), (list, dict))},
        "out": str(out), "runtime_s": result["runtime_s"]}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
