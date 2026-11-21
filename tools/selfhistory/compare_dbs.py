#!/usr/bin/env python3
"""Compare two GitGalaxy snapshot DBs table by table. Ids are mapped to file paths so
row order / autoincrement ids do not matter. Used as the validity control for delta scans.

    compare_dbs.py A.db B.db      -> prints the report as JSON

verdict: "identical"        every compared cell equal (floats within 1e-9)
         "structure_equal"  same files, functions, edges, call sites, and structural columns; only metrics drift
         "STRUCTURE_DIFFERS" the sets of files / functions / edges / call sites differ
"""
import json, sqlite3, sys
from collections import Counter

SKIP = {"id", "commit_hash", "commit_date", "parent_class_id", "scan_timestamp"}
# table -> columns that make a row's identity (id columns are mapped to paths first)
KEYS = {
    "file_data": ["file_path"],
    "function_data": ["file_id", "func_name", "start_line"],
    "edge_data": ["src_file_id", "dst_file_id", "edge_kind"],
    "call_site_data": ["src_file_id", "line_number", "verb", "target"],
    "repo_data": ["repo_name"],
}
# columns whose drift is a structural failure, not just a metric difference
STRUCTURAL = {
    "file_data": {"language", "total_loc", "coding_loc", "doc_loc", "function_count", "class_count",
                  "import_count", "directory_group"},
    "function_data": {"loc", "complexity", "args"},
    "edge_data": {"weight", "import_statements"},
    "call_site_data": {"dst_file_id", "operand", "form"},
    "repo_data": {"total_files", "total_loc", "total_functions", "total_classes"},
}


def _load(path):
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    ids = dict(c.execute("select id, file_path from file_data"))
    out = {}
    for t, key in KEYS.items():
        try:
            rows = {}
            for r in c.execute(f"select * from {t}"):
                d = {}
                for k in r.keys():
                    if k in SKIP:
                        continue
                    v = r[k]
                    if k.endswith("file_id"):
                        v = ids.get(v, v)
                    d[k] = v
                rows[tuple(d.get(k) for k in key)] = d
            out[t] = rows
        except sqlite3.Error:
            out[t] = None
    c.close()
    return out


def _eq(x, y):
    if isinstance(x, float) or isinstance(y, float):
        try:
            return abs(float(x) - float(y)) <= 1e-9
        except (TypeError, ValueError):
            return x == y
    return x == y


def compare(a_path, b_path):
    A, B = _load(a_path), _load(b_path)
    rep, structure_ok, identical = {}, True, True
    for t in KEYS:
        a, b = A[t], B[t]
        if a is None or b is None:
            rep[t] = {"skipped": "table missing"}
            continue
        only_a, only_b = len(set(a) - set(b)), len(set(b) - set(a))
        cols, maxd, rows_diff, struct_cells = Counter(), {}, 0, 0
        for k in set(a) & set(b):
            hit = False
            for col, x in a[k].items():
                y = b[k].get(col)
                if not _eq(x, y):
                    cols[col] += 1
                    hit = True
                    if col in STRUCTURAL.get(t, ()):
                        struct_cells += 1
                    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                        maxd[col] = max(maxd.get(col, 0.0), abs(x - y))
            rows_diff += hit
        rep[t] = {"rows_a": len(a), "rows_b": len(b), "only_a": only_a, "only_b": only_b,
                  "rows_differing": rows_diff, "structural_cell_diffs": struct_cells,
                  "differing_columns": dict(cols.most_common()),
                  "max_abs_diff": {k: round(v, 6) for k, v in maxd.items()}}
        if only_a or only_b or struct_cells:
            structure_ok = False
        if only_a or only_b or rows_diff:
            identical = False
    rep["verdict"] = "identical" if identical else ("structure_equal" if structure_ok else "STRUCTURE_DIFFERS")
    return rep


if __name__ == "__main__":
    print(json.dumps(compare(sys.argv[1], sys.argv[2]), indent=1))
