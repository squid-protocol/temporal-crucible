#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""CGR data (docs/cgr_hypotheses.md): quarterly walks for the new repos, one-engine snapshot scans into compact
per-repo databases, and xc fix labels.

    python tools/cgr_build.py --gg GG_AT_8f96d76ba --py ENGINE_PY --out DIR [--repos a,b] [--jobs 2]

Writes walks/<repo>_quarterly.json (new repos only), DIR/dbs/<repo>.db, events/<repo>_xc.json. Resumable.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _engine import POOL_DIR, REPO_ROOT  # noqa: E402

LANG = {"libgit2": ".c,.h", "postgres": ".c,.h", "libxml2": ".c,.h", "redis": ".c,.h", "prometheus": ".go",
        "commons-lang": ".java", "sphinx": ".py", "ripgrep": ".rs"}
EXISTING_WALKS = {"libgit2", "postgres"}
LAST_BOUNDARY = dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc)
LATTICE = ["arch_api", "arch_concurrency", "arch_globals", "arch_io", "arch_regex", "arch_ui_framework", "bitwise_ops",
           "def_encapsulation", "def_freeze_hits", "def_safety", "def_test", "state_bailout_hits", "state_cast_hits",
           "state_flux", "state_heat_triggers", "state_memory_alloc", "state_pointers", "state_safety_neg",
           "struct_args", "struct_branch", "struct_class_start", "struct_closures", "struct_decorators",
           "struct_func_start", "struct_generics", "struct_linear"]
COLS = ["func_name", "loc", "calls_out_to", "transfers_to", "complexity", "is_public", "func_archetype", "def_sync_locks",
        *LATTICE]


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def make_walk(r):
    path = REPO_ROOT / "walks" / f"{r}_quarterly.json"
    if r in EXISTING_WALKS or path.exists():
        return
    repo = POOL_DIR / r
    exts = tuple(LANG[r].split(","))
    head = git(repo, "rev-parse", "HEAD").strip()
    first = dt.datetime.fromtimestamp(int(git(repo, "log", "--reverse", "--format=%ct").split()[0]), dt.timezone.utc)
    y, m = first.year, ((first.month - 1) // 3 + 1) * 3 + 1
    if m > 12:
        y, m = y + 1, 1
    revs, started = [], False
    while True:
        b = dt.datetime(y, m, 1, tzinfo=dt.timezone.utc)
        if b > LAST_BOUNDARY:
            break
        sha = git(repo, "rev-list", "--first-parent", "-1", f"--before={b.isoformat()}", head).strip()
        if sha:
            if not started:
                n = sum(1 for f in git(repo, "ls-tree", "-r", "--name-only", sha).splitlines() if f.endswith(exts))
                started = n >= 50
            if started:
                date = git(repo, "show", "-s", "--format=%cI", sha).strip()
                revs.append({"ref": f"pre-{b.date()}", "sha": sha, "date": date, "boundary": b.isoformat(), "status": "ok"})
        m += 3
        if m > 12:
            y, m = y + 1, 1
    path.write_text(json.dumps({"repo": r, "mode": "quarterly", "branch": "first-parent", "events_head": head,
                                "outcome_days": 180, "min_c_files": 50, "exts": LANG[r], "revisions": revs}, indent=1) + "\n")


def init_db(db):
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE IF NOT EXISTS file_data (id INTEGER PRIMARY KEY, file_path TEXT, commit_hash TEXT, language TEXT)")
    con.execute(f"CREATE TABLE IF NOT EXISTS function_data (id INTEGER PRIMARY KEY, file_id INTEGER, "
                f"{', '.join(c + (' TEXT' if c in ('func_name', 'calls_out_to', 'transfers_to', 'func_archetype') else ' REAL') for c in COLS)})")
    con.execute("CREATE TABLE IF NOT EXISTS repo_data (commit_hash TEXT PRIMARY KEY, scanned_at TEXT, rc INTEGER)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_function_file_id ON function_data(file_id)")
    con.commit()
    return con


def scan_repo(r, gg, py, out):
    repo = POOL_DIR / r
    db = out / "dbs" / f"{r}.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    con = init_db(db)
    done = {x[0] for x in con.execute("SELECT commit_hash FROM repo_data")}
    walk = json.loads((REPO_ROOT / "walks" / f"{r}_quarterly.json").read_text())
    env = {**os.environ, "PYTHONPATH": str(gg), "GITGALAXY_LICENSE_KEY": "COMMUNITY_FREE_TIER",
           "GITGALAXY_DISABLE_GIT_HISTORY": "1"}
    fails = 0
    for rev in walk["revisions"]:
        sha = rev["sha"]
        if sha in done or rev.get("status", "ok") != "ok":
            continue
        with tempfile.TemporaryDirectory(dir=out) as tmp:
            src, res = Path(tmp) / "src", Path(tmp) / "out"
            src.mkdir()
            res.mkdir()
            arch = subprocess.run(["git", "-C", str(repo), "archive", sha], capture_output=True)
            subprocess.run(["tar", "-x", "-C", str(src)], input=arch.stdout, capture_output=True)
            p = subprocess.run([py, "-m", "gitgalaxy.galaxyscope", str(src), "--output", str(res) + "/"], env=env,
                               capture_output=True, text=True, errors="replace")
            dbs = sorted(res.glob("*_galaxy_master.db"))
            if p.returncode != 0 or not dbs:
                fails += 1
                con.execute("INSERT OR REPLACE INTO repo_data VALUES (?, ?, ?)", (sha + "-failed", dt.datetime.now().isoformat(), p.returncode))
                con.commit()
                continue
            s = sqlite3.connect(f"file:{dbs[0]}?mode=ro", uri=True)
            have = {c[1] for c in s.execute("PRAGMA table_info(function_data)")}
            sel = ", ".join(f"f.{c}" if c in have else "NULL" for c in COLS)
            fmap = {}
            for fid, path, lang in s.execute("SELECT id, file_path, language FROM file_data"):
                rel = str(path)
                if rel.startswith(str(src)):
                    rel = rel[len(str(src)):].lstrip("/")
                cur = con.execute("INSERT INTO file_data (file_path, commit_hash, language) VALUES (?, ?, ?)", (rel, sha, lang))
                fmap[fid] = cur.lastrowid
            rows = [(fmap[row[0]], *row[1:]) for row in s.execute(f"SELECT f.file_id, {sel} FROM function_data f") if row[0] in fmap]
            con.executemany(f"INSERT INTO function_data (file_id, {', '.join(COLS)}) VALUES ({', '.join('?' * (len(COLS) + 1))})", rows)
            s.close()
            con.execute("INSERT OR REPLACE INTO repo_data VALUES (?, ?, ?)", (sha, dt.datetime.now().isoformat(), 0))
            con.commit()
    con.close()
    return r, len(walk["revisions"]), fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gg", type=Path, required=True)
    ap.add_argument("--py", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--repos", default=",".join(LANG))
    ap.add_argument("--jobs", type=int, default=2)
    a = ap.parse_args()
    repos = a.repos.split(",")
    for r in repos:
        make_walk(r)
        print(f"walk {r}: {len(json.loads((REPO_ROOT / 'walks' / f'{r}_quarterly.json').read_text())['revisions'])}", flush=True)
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for r, n, fails in ex.map(lambda r: scan_repo(r, a.gg, a.py, a.out), repos):
            print(f"scanned {r}: {n} snapshots, {fails} failed", flush=True)
    for r in repos:
        if not (REPO_ROOT / "events" / f"{r}_xc.json").exists():
            p = subprocess.run([sys.executable, str(Path(__file__).parent / "xc_harvest.py"), "--repo", r, "--exts", LANG[r]],
                               capture_output=True, text=True)
            print(f"xc {r}: rc {p.returncode} {p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-200:]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
