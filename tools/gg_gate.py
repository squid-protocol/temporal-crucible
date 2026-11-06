#!/usr/bin/env python3
"""GG gate G-PY (docs/gg_hypotheses.md): engine Python function extraction vs tree-sitter-python on the head snapshot.
Run with the engine venv (tree-sitter-language-pack):

    <engine venv>/bin/python tools/gg_gate.py --db <head week DB> --sha <head sha>
"""
import argparse
import pathlib
import sqlite3
import subprocess
import sys

import tree_sitter_language_pack as tslp

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402

REPO = POOL_DIR / "gitgalaxy"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--sha", required=True)
    a = ap.parse_args()
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    eng = {(p, n, s) for p, n, s in con.execute(
        "SELECT fd.file_path, f.func_name, f.start_line FROM function_data f JOIN file_data fd ON f.file_id = fd.id "
        "WHERE fd.language = 'python' AND f.func_name IS NOT NULL AND f.func_name != ''")}
    con.close()
    parser = tslp.get_parser("python")
    files = [p for p in subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "--name-only", a.sha, "--", "gitgalaxy"],
                                       capture_output=True, text=True).stdout.splitlines() if p.endswith(".py")]
    ts = set()
    for p in files:
        src = subprocess.run(["git", "-C", str(REPO), "show", f"{a.sha}:{p}"], capture_output=True).stdout
        stack = [parser.parse(src).root_node]
        while stack:
            n = stack.pop()
            if n.type == "function_definition":
                nm = n.child_by_field_name("name")
                if nm is not None:
                    ts.add((p, nm.text.decode("utf-8", "replace"), n.start_point[0] + 1))
            stack.extend(n.children)
    # engine paths may carry the scan-root prefix; normalise to the repo path
    eng_n = set()
    for p, n, s in eng:
        q = p[p.find("gitgalaxy/"):] if "gitgalaxy/" in p else p
        eng_n.add((q, n, s))
    by_line = lambda S: {(p, n) for p, n, _ in S}  # noqa: E731
    exact = len(eng_n & ts)
    rec, prec = exact / len(ts), exact / len(eng_n)
    nm_rec, nm_prec = len(by_line(eng_n) & by_line(ts)) / len(by_line(ts)), len(by_line(eng_n) & by_line(ts)) / len(by_line(eng_n))
    ok = rec >= 0.95 and prec >= 0.95
    L = ["# GG gate G-PY — engine Python functions vs tree-sitter-python (head snapshot, `gitgalaxy/` package)", "",
         f"- tree-sitter functions {len(ts):,}; engine functions {len(eng_n):,}",
         f"- (file, name, start line): recall **{rec:.2%}**, precision **{prec:.2%}** → **G-PY {'PASS' if ok else 'FAIL'}** (gate ≥ 95% each)",
         f"- (file, name) only: recall {nm_rec:.2%}, precision {nm_prec:.2%}", "",
         "Samples: tree-sitter-only " + "; ".join(f"`{p}:{s} {n}`" for p, n, s in sorted(ts - eng_n)[:6]) +
         " · engine-only " + "; ".join(f"`{p}:{s} {n}`" for p, n, s in sorted(eng_n - ts)[:6])]
    (DOCS_DIR / "gg_gate.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
