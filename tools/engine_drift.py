#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Old-vs-new engine drift over the same commits (descriptive, not a test).

Joins two history DBs on (commit_hash) at repo grain and (commit_hash,
file_path) at file grain, and reports for every shared numeric column how often
and how much the value moved. Columns present in only one DB are listed as
schema drift. Files present in only one scan of a commit are counted as
coverage drift (the engine now sees, or no longer sees, that file).

    python tools/engine_drift.py --old /srv/.../dbs/curl_out/curl_galaxy_master.db \
        --new dbs/curl_out/curl_galaxy_master.db --out docs/engine_drift.md
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import RISK_VECTOR  # noqa: E402

KEYS = {"id", "repo_name", "commit_date", "commit_hash", "file_name", "file_path",
        "parent_entity", "language", "directory_group", "author"}


def cols(con, schema, table):
    return {r[1]: (r[2] or "").upper() for r in con.execute(f"PRAGMA {schema}.table_info({table})")}


def numeric_shared(con, table):
    o, n = cols(con, "o", table), cols(con, "main", table)
    shared = [c for c in n if c in o and c not in KEYS]
    num = []
    for c in shared:
        t = con.execute(f"SELECT typeof({c}) FROM main.{table} WHERE {c} IS NOT NULL LIMIT 1").fetchone()
        if t and t[0] in ("integer", "real"):
            num.append(c)
    return num, sorted(set(o) - set(n)), sorted(set(n) - set(o))


def drift_rows(con, table, join, num):
    out = []
    for c in num:
        r = con.execute(
            f"SELECT COUNT(*), SUM(n.{c} IS NOT x.{c}), AVG(x.{c}), AVG(n.{c}), "
            f"AVG(ABS(COALESCE(n.{c},0)-COALESCE(x.{c},0))) "
            f"FROM main.{table} n JOIN o.{table} x USING({join})").fetchone()
        tot, changed, mo, mn, mad = r
        out.append({"col": c, "pairs": tot, "changed": changed or 0,
                    "pct_changed": 100.0 * (changed or 0) / tot if tot else 0.0,
                    "mean_old": mo, "mean_new": mn, "mean_abs_delta": mad})
    out.sort(key=lambda d: -d["pct_changed"])
    return out


def fmt(v):
    return "—" if v is None else (f"{v:.4g}" if isinstance(v, float) else str(v))


def table_md(rows, highlight=()):
    lines = ["| column | pairs | % changed | mean old | mean new | mean abs Δ |",
             "|---|---:|---:|---:|---:|---:|"]
    for d in rows:
        name = f"**{d['col']}**" if d["col"] in highlight else d["col"]
        lines.append(f"| {name} | {d['pairs']} | {d['pct_changed']:.1f} | {fmt(d['mean_old'])} | "
                     f"{fmt(d['mean_new'])} | {fmt(d['mean_abs_delta'])} |")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", default=None)
    ap.add_argument("--scratch", default="/nvme-data/tc-scratch")
    args = ap.parse_args()

    con = sqlite3.connect(f"file:{args.new}?mode=ro", uri=True)
    con.execute(f"ATTACH 'file:{args.old}?mode=ro' AS o")
    con.execute("CREATE TEMP TABLE c AS SELECT DISTINCT commit_hash FROM main.repo_data "
                "INTERSECT SELECT DISTINCT commit_hash FROM o.repo_data")
    n_commits = con.execute("SELECT COUNT(*) FROM c").fetchone()[0]
    only_old = con.execute("SELECT COUNT(DISTINCT commit_hash) FROM o.repo_data "
                           "WHERE commit_hash NOT IN c").fetchone()[0]

    rnum, r_old_only, r_new_only = numeric_shared(con, "repo_data")
    repo_rows = drift_rows(con, "repo_data", "commit_hash", rnum)
    fnum, f_old_only, f_new_only = numeric_shared(con, "file_data")
    risk_cols = {f"risk_{v}" for v in RISK_VECTOR}

    # Neither DB indexes file_data by commit, and the old one is the study of
    # record (never written), so stage the needed columns into an indexed
    # scratch DB once, then compare in one ordered merge pass.
    scratch = pathlib.Path(args.scratch) / "engine_drift_scratch.db"
    scratch.unlink(missing_ok=True)
    con.execute(f"ATTACH '{scratch}' AS s")
    sel = ", ".join(["commit_hash", "file_path", "language", *fnum])
    for alias, src in (("xo", "o"), ("xn", "main")):
        con.execute(f"CREATE TABLE s.{alias} AS SELECT {sel} FROM {src}.file_data "
                    f"WHERE commit_hash IN (SELECT commit_hash FROM c)")
        con.execute(f"CREATE INDEX s.{alias}_k ON {alias}(commit_hash, file_path)")
    con.commit()

    st = {c: [0, 0, 0.0, 0.0, 0.0] for c in fnum}  # pairs, changed, sum_old, sum_new, sum_abs
    n_old = n_new = n_both = 0
    gone, added = {}, {}
    co = con.execute(f"SELECT {sel} FROM s.xo ORDER BY commit_hash, file_path")
    cn = con.cursor().execute(f"SELECT {sel} FROM s.xn ORDER BY commit_hash, file_path")
    ro, rn = co.fetchone(), cn.fetchone()
    while ro is not None or rn is not None:
        ko = (ro[0], ro[1]) if ro is not None else None
        kn = (rn[0], rn[1]) if rn is not None else None
        if kn is None or (ko is not None and ko < kn):
            n_old += 1; gone[ro[2]] = gone.get(ro[2], 0) + 1; ro = co.fetchone(); continue
        if ko is None or kn < ko:
            n_new += 1; added[rn[2]] = added.get(rn[2], 0) + 1; rn = cn.fetchone(); continue
        n_old += 1; n_new += 1; n_both += 1
        for i, c in enumerate(fnum, 3):
            a, b = ro[i], rn[i]
            d = st[c]
            d[0] += 1
            if a != b:
                d[1] += 1
            a = a if isinstance(a, (int, float)) else 0
            b = b if isinstance(b, (int, float)) else 0
            d[2] += a; d[3] += b; d[4] += abs(b - a)
        ro, rn = co.fetchone(), cn.fetchone()
    con.execute("DETACH s")
    scratch.unlink(missing_ok=True)
    file_rows = sorted(({"col": c, "pairs": d[0], "changed": d[1],
                         "pct_changed": 100.0 * d[1] / d[0] if d[0] else 0.0,
                         "mean_old": d[2] / d[0] if d[0] else None,
                         "mean_new": d[3] / d[0] if d[0] else None,
                         "mean_abs_delta": d[4] / d[0] if d[0] else None}
                        for c, d in st.items()), key=lambda d: -d["pct_changed"])
    lang_new = sorted(added.items(), key=lambda t: -t[1])[:10]
    lang_gone = sorted(gone.items(), key=lambda t: -t[1])[:10]

    meta_p = pathlib.Path(args.new).parent / "rescan_meta.json"
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    md = [
        "# Engine drift: study-of-record scans vs rescan",
        "",
        "**Descriptive, not a test.** Same commits, two engine builds. Nothing here is a",
        "hypothesis result; it says how far the instrument moved under the study's data.",
        "",
        f"- old DB: `{args.old}` (scanned 2026-09-13)",
        f"- new DB: `{args.new}` — engine `{meta.get('engine_sha', 'unknown')}`",
        f"- commits compared: **{n_commits}** (old-only, not rescanned: {only_old})",
        "",
        "## Coverage",
        "",
        f"- file rows: old {n_old}, new {n_new}, matched on (commit, path) {n_both}",
        f"- files only in the new scan: {n_new - n_both}; only in the old scan: {n_old - n_both}",
        "",
        "New-only files by language: " + (", ".join(f"{l} {k}" for l, k in lang_new) or "none"),
        "",
        "Old-only files by language: " + (", ".join(f"{l} {k}" for l, k in lang_gone) or "none"),
        "",
        "## Schema drift",
        "",
        f"- file_data columns dropped: {', '.join(f_old_only) or 'none'}",
        f"- file_data columns added ({len(f_new_only)}): {', '.join(f_new_only) or 'none'}",
        f"- repo_data columns dropped: {', '.join(r_old_only) or 'none'}; added: {', '.join(r_new_only) or 'none'}",
        "",
        "## Risk vector (file grain, matched files)",
        "",
        table_md([d for d in file_rows if d["col"] in risk_cols]),
        "",
        "## All shared numeric file columns, most-changed first",
        "",
        table_md(file_rows, highlight=risk_cols),
        "",
        "## Repo grain",
        "",
        table_md(repo_rows),
        "",
    ]
    pathlib.Path(args.out).write_text("\n".join(md))
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(
            {"commits": n_commits, "coverage": {"old": n_old, "new": n_new, "both": n_both},
             "file": file_rows, "repo": repo_rows}, indent=1, default=str))
    print(f"wrote {args.out}: {n_commits} commits, {n_both}/{n_old} old files matched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
