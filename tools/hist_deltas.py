#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The line-delta harvest: what the history databases are missing (docs/hist_replication.md, HR-2 and HR-3).

    python tools/hist_deltas.py --pool <crucible-pool> --out <laws-study/pilot>/deltas [--repos a,b]
    python tools/hist_deltas.py --out ... --report          # what is harvested, no git

The history DBs record WHICH files a commit touched, never HOW MANY LINES. That gap blocks two registered
questions: HR-2 (change entropy `HCM1_LD_30`, defined over line deltas) and HR-3 (function-grain recidivism,
which needs changed line RANGES to map onto the function spans the quarterly walks carry).

Two passes, because they cost very differently:

1. **numstat, every non-merge commit.** `added`/`deleted` per file per commit. Cheap, and it is all HR-2 needs.
2. **hunk ranges, FIX commits only.** `-U0` hunk headers give the changed line range in the new file, which is
   what maps a change onto a function span. Restricted to fix commits because that is the only place HR-3
   reads: the predictor counts prior fixes per function and the outcome counts later ones. Harvesting patch
   text for every commit of postgres would cost hours for data no registered question asks for.

Resumable per repo: a repo with its `done` row is skipped, so a killed run keeps its work. The harvest is
pinned to the clone's current HEAD and records it, so a later mismatch with the history DB's `head` is visible
rather than silent.
"""
from __future__ import annotations

import argparse, re, sqlite3, subprocess, sys, time
from pathlib import Path

REPOS = ("commons-lang", "libgit2", "libxml2", "postgres", "prometheus", "redis", "ripgrep", "sphinx")
SEP = "\x01"
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def schema(con: sqlite3.Connection) -> None:
    con.executescript("""
    CREATE TABLE IF NOT EXISTS delta (sha TEXT, path TEXT, added INTEGER, deleted INTEGER, binary INTEGER);
    CREATE TABLE IF NOT EXISTS hunk  (sha TEXT, path TEXT, new_start INTEGER, new_lines INTEGER);
    CREATE TABLE IF NOT EXISTS meta  (key TEXT PRIMARY KEY, value TEXT);
    CREATE INDEX IF NOT EXISTS delta_sha ON delta(sha);
    CREATE INDEX IF NOT EXISTS delta_path ON delta(path);
    CREATE INDEX IF NOT EXISTS hunk_sha ON hunk(sha);
    """)


def git(repo: Path, *args: str) -> subprocess.Popen:
    return subprocess.Popen(["git", "-C", str(repo), *args], stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, errors="replace", bufsize=1 << 20)


def numstat(repo: Path, con: sqlite3.Connection) -> int:
    """Pass 1: added/deleted per file per non-merge commit."""
    p = git(repo, "log", "--no-merges", "--numstat", f"--format={SEP}%H")
    sha, rows, n = None, [], 0
    for line in p.stdout:
        line = line.rstrip("\n")
        if line.startswith(SEP):
            sha = line[1:].strip()
            continue
        if not line or sha is None:
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        a, d, path = parts
        binary = 1 if (a == "-" or d == "-") else 0
        rows.append((sha, path, 0 if binary else int(a), 0 if binary else int(d), binary))
        if len(rows) >= 20000:
            con.executemany("INSERT INTO delta VALUES (?,?,?,?,?)", rows); con.commit()
            n += len(rows); rows = []
    p.wait()
    if rows:
        con.executemany("INSERT INTO delta VALUES (?,?,?,?,?)", rows); con.commit(); n += len(rows)
    return n


def hunks(repo: Path, con: sqlite3.Connection, shas: list[str]) -> int:
    """Pass 2: changed line ranges in the NEW file, for the given commits only."""
    n, rows = 0, []
    for i in range(0, len(shas), 200):          # batched: one git process per 200 commits
        batch = shas[i:i + 200]
        p = git(repo, "show", "-U0", "--no-merges", f"--format={SEP}%H", "--diff-filter=AM", *batch)
        sha = path = None
        for line in p.stdout:
            if line.startswith(SEP):
                sha = line[1:].strip(); path = None
            elif line.startswith("+++ b/"):
                path = line[6:].rstrip("\n")
            elif line.startswith("@@") and sha and path:
                m = HUNK.match(line)
                if m:
                    start = int(m.group(1))
                    count = int(m.group(2)) if m.group(2) is not None else 1
                    if count:
                        rows.append((sha, path, start, count))
        p.wait()
        if len(rows) >= 20000:
            con.executemany("INSERT INTO hunk VALUES (?,?,?,?)", rows); con.commit()
            n += len(rows); rows = []
    if rows:
        con.executemany("INSERT INTO hunk VALUES (?,?,?,?)", rows); con.commit(); n += len(rows)
    return n


def fix_shas(study: Path, repo: str) -> list[str]:
    """The fix commits the history DB already labelled -- the harvest never re-decides what a fix is."""
    h = study / "history" / f"{repo}.db"
    if not h.exists():
        return []
    con = sqlite3.connect(f"file:{h}?mode=ro", uri=True)
    out = [r[0] for r in con.execute("select sha from commit_ where fix=1 and merge=0 and bot=0")]
    con.close()
    return out


def one(pool: Path, study: Path, out: Path, repo: str) -> dict:
    db = out / f"{repo}.db"
    out.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    schema(con)
    if con.execute("select value from meta where key='done'").fetchone():
        con.close()
        return {"repo": repo, "skipped": "already harvested"}
    src = pool / repo
    if not src.is_dir():
        con.close()
        return {"repo": repo, "error": f"no clone at {src}"}
    head = subprocess.run(["git", "-C", str(src), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    t0 = time.time()
    nd = numstat(src, con)
    shas = fix_shas(study, repo)
    nh = hunks(src, con, shas) if shas else 0
    con.executemany("INSERT OR REPLACE INTO meta VALUES (?,?)",
                    [("head", head), ("deltas", str(nd)), ("hunks", str(nh)),
                     ("fix_commits", str(len(shas))), ("seconds", str(round(time.time() - t0, 1))),
                     ("done", "1")])
    con.commit(); con.close()
    return {"repo": repo, "deltas": nd, "hunks": nh, "fix_commits": len(shas),
            "head": head[:9], "seconds": round(time.time() - t0, 1)}


def report(out: Path) -> int:
    print(f"{'repo':14}{'deltas':>10}{'hunks':>9}{'fix commits':>13}  head")
    for r in REPOS:
        db = out / f"{r}.db"
        if not db.exists():
            print(f"{r:14}{'—':>10}{'—':>9}{'—':>13}  not harvested"); continue
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        m = dict(con.execute("select key,value from meta"))
        con.close()
        print(f"{r:14}{m.get('deltas','?'):>10}{m.get('hunks','?'):>9}{m.get('fix_commits','?'):>13}  "
              f"{(m.get('head') or '')[:9]}{'' if m.get('done') else '  (INCOMPLETE)'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", type=Path, default=Path("/srv/storage_16tb/projects/temporal-crucible-pool"))
    ap.add_argument("--study", type=Path, default=Path("/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--repos", help="comma-separated; default all eight")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        return report(a.out)
    for r in (a.repos.split(",") if a.repos else REPOS):
        rec = one(a.pool, a.study, a.out, r)
        print("  " + ", ".join(f"{k}={v}" for k, v in rec.items()), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
