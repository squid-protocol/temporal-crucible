#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""KF gate G2 (docs/kfr_hypotheses.md): KF's regex construct counts vs tree-sitter-c node counts, per C file at a
repo's head snapshot. Run with the engine venv (tree-sitter-language-pack):

    <engine venv>/bin/python tools/kf_construct_validate.py --repos ndpi openssl curl libxml2 libtiff libpng libexif file
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

import tree_sitter_language_pack as tslp

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402

GOTO = re.compile(r"\bgoto\b")
MACRO = re.compile(r"^\s*#\s*define\s+[A-Za-z_]\w*\(", re.M)


def _git(repo, *a, binary=False):
    r = subprocess.run(["git", "-C", str(repo), *a], capture_output=True)
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def ts_counts(parser, src: bytes):
    g = m = 0
    stack = [parser.parse(src).root_node]
    while stack:
        n = stack.pop()
        if n.type == "goto_statement":
            g += 1
        elif n.type == "preproc_function_def":
            m += 1
        stack.extend(n.children)
    return g, m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", nargs="+", required=True)
    a = ap.parse_args()
    parser = tslp.get_parser("c")
    L = ["# KF gate G2 — regex construct counts vs tree-sitter-c (head snapshots)", "",
         "Per C file (`.c`/`.h`): exposure = count > 0. Agreement = share of files where regex and tree-sitter agree on exposure. "
         "Line-level counts are compared too (regex counts matching *lines*; tree-sitter counts *nodes*).", "",
         "| repo | files | goto exposure agree | goto: regex-only / ts-only files | macro exposure agree | macro: regex-only / ts-only files |",
         "|---|---:|---:|---|---:|---|"]
    tot = {"n": 0, "g": 0, "m": 0}
    samples = []
    for r in a.repos:
        repo = POOL_DIR / r
        head = _git(repo, "rev-parse", "HEAD").strip()
        files = [p for p in _git(repo, "-c", "core.quotepath=off", "ls-tree", "-r", "--name-only", head).splitlines() if p.endswith((".c", ".h"))]
        n = ag_g = ag_m = 0
        g_ro = g_to = m_ro = m_to = 0
        for p in files:
            src = _git(repo, "show", f"{head}:{p}", binary=True)
            text = src.decode("utf-8", "replace")
            # regex per line, as kf_eval counts lines with git grep
            rg = sum(1 for ln in text.splitlines() if GOTO.search(ln))
            rm = len(MACRO.findall(text))
            tg, tm = ts_counts(parser, src)
            n += 1
            ag_g += (rg > 0) == (tg > 0)
            ag_m += (rm > 0) == (tm > 0)
            if rg > 0 and tg == 0:
                g_ro += 1
                if len(samples) < 12:
                    samples.append((r, p, "goto regex-only", next(ln.strip()[:90] for ln in text.splitlines() if GOTO.search(ln))))
            if tg > 0 and rg == 0:
                g_to += 1
            if rm > 0 and tm == 0:
                m_ro += 1
                if len(samples) < 24:
                    samples.append((r, p, "macro regex-only", MACRO.search(text).group(0)[:90]))
            if tm > 0 and rm == 0:
                m_to += 1
        tot["n"] += n
        tot["g"] += ag_g
        tot["m"] += ag_m
        L.append(f"| {r} | {n} | {ag_g / n:.2%} | {g_ro} / {g_to} | {ag_m / n:.2%} | {m_ro} / {m_to} |")
        print(r, n, flush=True)
    pg, pm = tot["g"] / tot["n"], tot["m"] / tot["n"]
    L += ["", f"**Pooled: goto {pg:.2%}, macro {pm:.2%} → G2 {'PASS' if pg >= 0.98 and pm >= 0.98 else 'FAIL (fallback: tree-sitter counts)'}** (gate ≥ 98% each)", "",
          "Disagreement samples (read in source):", ""] + [f"- {r} `{p}` {k}: `{s}`" for r, p, k, s in samples]
    (DOCS_DIR / "kf_construct_validation.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
