#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Parallel, resumable sibling of run_batch.py.

run_batch.py scans commit pairs strictly serially into one accumulating DB. The
scans of independent commits are embarrassingly parallel, and ~45% of a small-repo
scan is single-threaded tail (census/guidestar/dependency-graph/sqlite), so running
several scans at once overlaps those tails and is a large real win (the engine's
own intra-scan ProcessPoolExecutor still runs; oversubscription is fine here).

Design (why it is not just `run_batch.py` in a Pool):
  * Every worker gets its OWN detached worktree under an NVMe scratch root, with
    basename == repo.name so the engine's `repo_name` key stays stable, and its
    OWN per-commit output DB -- no shared worktree path, no concurrent writers to
    one SQLite file.
  * `git worktree add/remove` mutate `$GIT_DIR/worktrees`, so they run under a
    cross-process lock; the scan itself runs unlocked and parallel.
  * Per-commit shard DBs are merged into the canonical
    `dbs/<repo>_out/<repo>_galaxy_master.db` with id-FK remapping (class/function/
    edge rows reference file_data.id AUTOINCREMENT), keyed idempotently by
    (repo_name, commit_hash) so a re-run skips finished commits -- same
    resumability contract as scan_pair.

    python tools/run_batch_parallel.py --events events/curl.json \
        --classes security-fix,control --limit 50 --jobs 6
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import GALAXYSCOPE_BIN, SCAN_ENV  # noqa: E402
from scan_pair import already_scanned, out_dir_for, resolve_repo  # noqa: E402

# file_data is the id-FK parent; insert it before the tables that reference it.
CHILD_OF_FILE = ("class_data", "function_data", "edge_data")
NATURAL_KEY_TABLES = ("repo_data", "folder_data", "excluded_artifacts")

_LOCK = None  # set per worker by _init


def _init(lock):
    global _LOCK
    _LOCK = lock


def _git(repo, *args, check=True):
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=check)


def scan_one(repo_path: str, sha: str, scratch_root: str,
             workers_per_scan: int | None = None) -> tuple[str, str | None, str]:
    """Scan one commit into an isolated per-commit dir. Returns (sha, db_path|None, status).

    workers_per_scan caps the engine's intra-scan ProcessPoolExecutor
    (GALAXYSCOPE_MAX_WORKERS, galaxyscope.py). On a box where one scan already
    saturates every core, inter-scan parallelism only recovers the single-threaded
    tail (~1.7x ceiling); capping each scan lean (e.g. 2) and running many at once
    partitions the cores and beats that ceiling.
    """
    repo = pathlib.Path(repo_path)
    env = SCAN_ENV if workers_per_scan is None else {**SCAN_ENV, "GALAXYSCOPE_MAX_WORKERS": str(workers_per_scan)}
    work = pathlib.Path(scratch_root) / sha[:12]
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    wt = work / repo.name  # basename == repo name == engine's repo_name key
    try:
        with _LOCK:
            _git(repo, "worktree", "add", "--detach", str(wt), sha)
    except subprocess.CalledProcessError as e:
        return sha, None, f"WORKTREE FAILED: {e.stderr[-200:]}"
    try:
        res = subprocess.run([GALAXYSCOPE_BIN, str(wt), "--db-only"],
                             cwd=work, env=env, capture_output=True, text=True)
        if res.returncode != 0:
            return sha, None, f"SCAN FAILED: {res.stderr[-300:]}"
    finally:
        with _LOCK:
            _git(repo, "worktree", "remove", "--force", str(wt), check=False)
            _git(repo, "worktree", "prune", check=False)
    dbs = sorted(work.rglob("*.db"))
    return (sha, str(dbs[0]), "scanned") if dbs else (sha, None, "NO DB PRODUCED")


def _cols(con, table, drop=("id",)) -> list[str]:
    return [r[1] for r in con.execute(f"PRAGMA table_info({table})") if r[1] not in drop]


def _init_master(master_path: pathlib.Path, shard_path: str) -> None:
    """Create the master DB by cloning a shard's full schema (tables + indexes)."""
    scon = sqlite3.connect(shard_path)
    ddl = [r[0] for r in scon.execute(
        "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'")]
    scon.close()
    mcon = sqlite3.connect(master_path)
    mcon.execute("PRAGMA foreign_keys=OFF")
    for stmt in ddl:
        mcon.execute(stmt)
    mcon.commit()
    mcon.close()


def merge_shard(mcon: sqlite3.Connection, shard_path: str, repo_name: str) -> str:
    """Merge one per-commit shard into master with id-FK remapping. Idempotent."""
    scon = sqlite3.connect(shard_path)
    scon.row_factory = sqlite3.Row
    row = scon.execute("SELECT DISTINCT commit_hash FROM repo_data WHERE repo_name=?",
                       (repo_name,)).fetchone()
    if not row:
        scon.close()
        return "no repo_data"
    commit = row["commit_hash"]
    if mcon.execute("SELECT 1 FROM repo_data WHERE repo_name=? AND commit_hash=?",
                    (repo_name, commit)).fetchone():
        scon.close()
        return f"skip {commit[:12]} (already merged)"

    def copy(table, remap: dict[str, dict] | None = None, capture: bool = False):
        """Copy table rows shard->master; remap {col: id_map}; return old->new id map if capture."""
        cols = _cols(scon, table)
        if not cols:
            return {}
        placeholders = ",".join("?" * len(cols))
        collist = ",".join(cols)
        idx = {c: cols.index(c) for c in (remap or {}) if c in cols}
        out: dict[int, int] = {}
        sel = f"SELECT id,{collist} FROM {table}" if capture else f"SELECT {collist} FROM {table}"
        cur = mcon.cursor()
        for r in scon.execute(sel):
            old_id = r[0] if capture else None
            vals = list(r[1:]) if capture else list(r)
            for c, i in idx.items():
                if vals[i] is not None:
                    vals[i] = remap[c].get(vals[i])
            cur.execute(f"INSERT INTO {table} ({collist}) VALUES ({placeholders})", vals)
            if capture:
                out[old_id] = cur.lastrowid
        return out

    for t in ("repo_data", "folder_data", "excluded_artifacts"):
        copy(t)
    file_map = copy("file_data", capture=True)
    class_map = copy("class_data", remap={"file_id": file_map}, capture=True)
    copy("function_data", remap={"file_id": file_map, "parent_class_id": class_map})
    copy("edge_data", remap={"src_file_id": file_map, "dst_file_id": file_map})
    scon.close()
    return f"merged {commit[:12]}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--events", required=True)
    ap.add_argument("--classes", default="security-fix,control")
    ap.add_argument("--limit", type=int, default=0, help="events per class (0 = all)")
    ap.add_argument("--jobs", type=int, default=0, help="parallel scans (0 = min(nproc, 6))")
    ap.add_argument("--workers-per-scan", type=int, default=None,
                    help="cap each scan's intra-scan pool (GALAXYSCOPE_MAX_WORKERS). "
                         "Best throughput ~ jobs * workers-per-scan == nproc, e.g. --jobs 6 --workers-per-scan 2")
    ap.add_argument("--scratch", default="/nvme-data/tc-scratch",
                    help="fast scratch root for worktrees + shard DBs")
    ap.add_argument("--keep-scratch", action="store_true")
    args = ap.parse_args()

    import os
    jobs = args.jobs or min(os.cpu_count() or 4, 6)
    data = json.loads(pathlib.Path(args.events).read_text())
    repo = resolve_repo(data["repo"])
    out_dir = out_dir_for(repo)
    master_path = out_dir / f"{repo.name}_galaxy_master.db"
    scratch_root = pathlib.Path(args.scratch) / f"{repo.name}_batch"
    scratch_root.mkdir(parents=True, exist_ok=True)
    wanted = args.classes.split(",")

    # Build the ordered, unique sha list (parent^ + child per event), mirroring run_batch.
    per_class: dict[str, int] = {}
    seen: set[str] = set()
    shas: list[str] = []
    for e in data["events"]:
        if e["class"] not in wanted:
            continue
        if args.limit and per_class.get(e["class"], 0) >= args.limit:
            continue
        per_class[e["class"]] = per_class.get(e["class"], 0) + 1
        child = _git(repo, "rev-parse", e["sha"]).stdout.strip()
        try:
            parent = _git(repo, "rev-parse", f"{child}^").stdout.strip()
        except subprocess.CalledProcessError:
            print(f"skip {e['id']}: {child[:12]} has no parent (root commit)", flush=True)
            continue
        for sha in (parent, child):
            if sha not in seen:
                seen.add(sha)
                shas.append(sha)

    todo = [s for s in shas if not already_scanned(out_dir, s)]
    print(f"{len(shas)} unique commits, {len(shas) - len(todo)} already in DB, "
          f"{len(todo)} to scan on {jobs} workers", flush=True)
    if not todo:
        print("nothing to do")
        return 0

    t0 = time.time()
    done = scanned = failed = 0
    mcon: sqlite3.Connection | None = None
    lock = Manager().Lock()
    with ProcessPoolExecutor(max_workers=jobs, initializer=_init, initargs=(lock,)) as ex:
        futures = {ex.submit(scan_one, str(repo), s, str(scratch_root), args.workers_per_scan): s for s in todo}
        for fut in as_completed(futures):
            sha, db_path, status = fut.result()
            done += 1
            if db_path is None:
                failed += 1
                print(f"[{done}/{len(todo)}] {sha[:12]} {status} ({(time.time()-t0)/60:.1f}m)", flush=True)
                continue
            if mcon is None:
                if not master_path.exists():
                    _init_master(master_path, db_path)
                mcon = sqlite3.connect(master_path)
                mcon.execute("PRAGMA foreign_keys=OFF")
            msg = merge_shard(mcon, db_path, repo.name)
            mcon.commit()
            scanned += 1
            if not args.keep_scratch:
                shutil.rmtree(pathlib.Path(db_path).parent, ignore_errors=True)
            print(f"[{done}/{len(todo)}] {sha[:12]} {msg} ({(time.time()-t0)/60:.1f}m)", flush=True)
    if mcon is not None:
        mcon.close()
    if not args.keep_scratch:
        shutil.rmtree(scratch_root, ignore_errors=True)
    print(f"batch complete in {(time.time()-t0)/60:.1f} min: {scanned} scanned, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
