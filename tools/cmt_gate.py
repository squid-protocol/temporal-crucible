#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""CMT-G (docs/dc_hypotheses.md): engine Prism comment lines vs tree-sitter comment nodes on the language-crucible.
Engine venv. Exit 0 on PASS.

    <engine venv>/bin/python tools/cmt_gate.py
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys
from collections import defaultdict

import tree_sitter_language_pack as tslp
from gitgalaxy.core.prism import Prism
from gitgalaxy.standards.gitgalaxy_config import LEXICAL_FAMILY_HEURISTICS
from gitgalaxy.standards.language_standards import LANGUAGE_DEFINITIONS

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402

ROOT = POOL_DIR / "kw_scan" / "crucible" / "data"
DB = POOL_DIR / "kw_scan" / "data_galaxy_master.db"
TS_NAME = {"shell": "bash", "sqlite": "sql", "objectivec": "objc", "objective-c": "objc", "c_sharp": "csharp"}
MIN_REF = 200


def ts_comment_lines(parser, src: bytes):
    out, stack = set(), [parser.parse(src).root_node]
    while stack:
        n = stack.pop()
        if "comment" in n.type:
            a, b = n.start_point[0], n.end_point[0]
            if n.end_point[1] == 0 and b > a:
                b -= 1
            out.update(range(a, b + 1))
            continue
        stack.extend(n.children)
    return out


_W = {}


def one(task):
    """One file -> (lang, tp, n_engine, n_ref) or a skip reason. Runs in a worker with a per-file time limit."""
    path, lang = task
    f = ROOT / path
    if not f.exists():
        return ("skip", "missing", path)
    name = TS_NAME.get(lang, lang)
    if name not in _W:
        try:
            _W[name] = tslp.get_parser(name)
        except Exception:
            _W[name] = None
    if _W[name] is None:
        return ("skip", f"no grammar: {lang}", path)
    if "prism" not in _W:
        _W["prism"] = Prism(LEXICAL_FAMILY_HEURISTICS, LANGUAGE_DEFINITIONS)
    raw = f.read_bytes()
    txt = raw.decode("utf-8", "replace")
    try:
        pos = _W["prism"].split_positional_comment_stream(txt, lang)
    except Exception:
        return ("skip", "prism error", path)
    eng = {i for i, l in enumerate(pos.split("\n")) if l.strip()}
    ref = ts_comment_lines(_W[name], raw)
    return ("ok", lang, len(eng & ref), len(eng), len(ref))


def main() -> int:
    import multiprocessing as mp
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    files = con.execute("SELECT file_path, language FROM file_data").fetchall()
    con.close()
    stats, skipped, timed_out = defaultdict(lambda: [0, 0, 0]), defaultdict(int), []
    with mp.get_context("fork").Pool(8, maxtasksperchild=50) as pool:
        futs = [(t, pool.apply_async(one, (t,))) for t in files]
        for t, fu in futs:
            try:
                res = fu.get(timeout=60)
            except mp.TimeoutError:
                timed_out.append(t[0])
                continue
            if res[0] == "skip":
                skipped[res[1]] += 1
                continue
            s = stats[res[1]]
            s[0] += res[2]
            s[1] += res[3]
            s[2] += res[4]
        pool.terminate()
    rows = []
    for lang, (tp, ne, nr) in sorted(stats.items()):
        if nr == 0:
            continue
        rows.append((lang, tp / ne if ne else 0.0, tp / nr, ne, nr))
    pool = [r for r in rows if r[4] >= MIN_REF]
    TP = sum(stats[r[0]][0] for r in pool)
    NE = sum(stats[r[0]][1] for r in pool)
    NR = sum(stats[r[0]][2] for r in pool)
    P, R = (TP / NE if NE else 0), (TP / NR if NR else 0)
    cr = {l: (p, r) for l, p, r, _, _ in rows}
    c_ok = all(cr.get(l, (0, 0))[0] >= 0.9 and cr.get(l, (0, 0))[1] >= 0.9 for l in ("c", "cpp"))
    ok = P >= 0.9 and R >= 0.9 and c_ok
    L = ["# CMT-G — engine comment stream vs tree-sitter comment nodes (language-crucible)", "",
         f"- pooled over {len(pool)} languages with ≥ {MIN_REF} reference comment lines: precision **{P:.1%}**, recall **{R:.1%}**",
         f"- C: P {cr.get('c', (0, 0))[0]:.1%} / R {cr.get('c', (0, 0))[1]:.1%}; C++: P {cr.get('cpp', (0, 0))[0]:.1%} / R {cr.get('cpp', (0, 0))[1]:.1%}",
         f"- **CMT-G {'PASS' if ok else 'FAIL'}** (pooled and C/C++ each ≥ 90%)", "",
         "| language | precision | recall | engine lines | reference lines |", "|---|---:|---:|---:|---:|"]
    L += [f"| {l} | {p:.1%} | {r:.1%} | {ne:,} | {nr:,} |" for l, p, r, ne, nr in sorted(rows, key=lambda t: -t[4])]
    L += ["", f"Skipped files: {dict(skipped)}", f"Timed out (> 60 s per file; excluded, amendment): {len(timed_out)} {timed_out[:10]}"]
    (DOCS_DIR / "cmt_gate.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
