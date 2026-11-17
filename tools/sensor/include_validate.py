#!/usr/bin/env python3
"""Header include counts: stored-imports reader vs source-text reader vs libclang's own inclusion record (exact, from the preprocessor).

    ENGINE=/path/to/gitgalaxy/checkout include_validate.py REPO_TREE ENGINE_DB     (venv with libclang, numpy, scipy)

Edges are (includer, header) pairs among the repository's own files. libclang parses every .c file as a translation unit with every header-holding directory on the include path
and records each inclusion directive it meets (direct ones, at any nesting depth). Scored per header: the number of distinct includers."""
import collections
import json
import os
import pathlib
import sqlite3
import sys

import numpy as np
from clang import cindex
from scipy.stats import spearmanr

sys.path.insert(0, os.environ["ENGINE"])
from gitgalaxy.tools.sensors import reach  # noqa: E402

root = pathlib.Path(sys.argv[1]).resolve()
db = sys.argv[2]
HDR = (".h", ".hpp", ".hh", ".hxx")
files = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and p.suffix in (".c", ".h"))
header_dirs = sorted({str(pathlib.Path(f).parent) for f in files if f.endswith(HDR)})
args = [f"-I{root / d}" for d in header_dirs] + ["-I" + str(root), "-ferror-limit=0", "-Wno-everything", "-w"]
idx = cindex.Index.create()
clang_edges = set()
parsed = 0
for f in files:
    if not f.endswith(".c"):
        continue
    try:
        tu = idx.parse(str(root / f), args=args, options=cindex.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)
    except cindex.TranslationUnitLoadError:
        continue
    parsed += 1
    for inc in tu.get_includes():
        if inc.source is None or inc.include is None:
            continue
        a, b = pathlib.Path(inc.source.name), pathlib.Path(inc.include.name)
        try:
            a, b = str(a.resolve().relative_to(root)), str(b.resolve().relative_to(root))
        except ValueError:
            continue
        if b.endswith(HDR):
            clang_edges.add((a, b))

con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
imports = {r[0]: reach._tokens(r[1]) for r in con.execute("SELECT file_path, raw_imports FROM file_data")}
con.close()
paths = list(imports)
stored = reach.include_counts_from_imports(imports)
text = reach.include_counts(root, paths)


def edges(counts):
    return {(a, h) for h, srcs in counts.items() for a in srcs}


def per_header(es):
    d = collections.defaultdict(set)
    for a, h in es:
        d[h].add(a)
    return {h: len(v) for h, v in d.items()}


scope = set(paths)
truth = {(a, h) for a, h in clang_edges if a in scope and h in scope}
tc = per_header(truth)
print(f"{root.name}: libclang parsed {parsed} .c files; {len(truth)} include edges into {len(tc)} headers")
for name, counts in (("stored imports", stored), ("source text", text)):
    e = {x for x in edges(counts) if x[0] in scope and x[1] in scope}
    # score only where libclang could see the includer (a header, or a .c file it parsed): edges from files it never parsed are not judged
    seen = {a for a, _ in truth} | {a for a in scope if a.endswith(".c")}
    judged = {x for x in e if x[0] in seen}
    tp = len(judged & truth)
    hs = sorted(set(tc) | {h for _, h in judged})
    x = np.array([tc.get(h, 0) for h in hs], float)
    y = np.array([per_header(judged).get(h, 0) for h in hs], float)
    rho = spearmanr(x, y)[0] if x.std() and y.std() else float("nan")
    exact = float(np.mean(x == y)) if len(hs) else float("nan")
    print(f"  {name:15s} edges {len(judged):6d}  precision {tp / max(len(judged), 1):5.1%}  recall {tp / max(len(truth), 1):5.1%}  | per header: Spearman {rho:+.3f}, exactly right {exact:5.1%}")
# the engine's own file-graph measures, for reference (what reach had before)
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
cols = {r[1] for r in con.execute("PRAGMA table_info(file_data)")}
hs = sorted(tc)
for col in ("import_count", "pagerank_score", "popularity"):
    if col in cols:
        m = dict(con.execute(f"SELECT file_path, {col} FROM file_data"))
        x = np.array([tc[h] for h in hs], float)
        y = np.array([m.get(h) or 0 for h in hs], float)
        if x.std() and y.std():
            print(f"  engine column {col:16s} Spearman {spearmanr(x, y)[0]:+.3f}")
con.close()
