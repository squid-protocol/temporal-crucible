#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Delta + parallel batch scanner (FAST MODE).

For each (parent, child) event pair this scans the parent FULL, then the child
INCREMENTALLY against the parent (gitgalaxy#3220's rehydrator), and merges the
resulting DB -- which already holds both commits -- into the canonical per-repo
master. Pairs run in parallel; each worker owns an isolated NVMe scratch dir and
per-pair DB, merged with id-FK remapping (reused from run_batch_parallel).

WHY / WHEN:
  * Speedup ceiling is structural: only the CHILD is a delta (the parent must be
    scanned to seed it), so per pair it is ~ (full + delta) vs (full + full).
    Measured on curl: full child 6.24s, delta child 3.44s -> ~1.3x per pair from
    delta, then ~Nx more from running pairs in parallel. Use --full to A/B.
  * FAST MODE, not study-of-record: the incremental path is bit-exact on 12/13
    risk vectors + full coverage, but risk_verification still differs on a few
    files per repo (#3220 residual). Do not treat delta output as the pre-registered
    validation corpus without accepting that.
  * Requires an engine with the #3220 rehydrator fix. Point GALAXYSCOPE_BIN at it
    (until #3227 merges, a build of that branch).

    GALAXYSCOPE_BIN=/path/to/fixed/galaxyscope \
    python tools/run_batch_delta.py --events events/curl.json --jobs 8 --workers-per-scan 2
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
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import GALAXYSCOPE_BIN, SCAN_ENV  # noqa: E402
from run_batch_parallel import _init, _init_master, merge_shard  # noqa: E402
from scan_pair import already_scanned, out_dir_for, resolve_repo  # noqa: E402

_LOCK = None


def _init_lock(lock):
    global _LOCK
    _LOCK = lock
    _init(lock)  # run_batch_parallel's worktree lock too (same object)


def _git(repo, *a, check=True):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=check)


def _scan(repo: pathlib.Path, sha: str, work: pathlib.Path, env: dict, extra=()) -> pathlib.Path | None:
    wt = work / repo.name  # basename == repo_name key
    try:
        with _LOCK:
            _git(repo, "worktree", "add", "--detach", str(wt), sha)
    except subprocess.CalledProcessError:
        return None
    try:
        res = subprocess.run([GALAXYSCOPE_BIN, str(wt), "--db-only", *extra],
                             cwd=work, env=env, capture_output=True, text=True)
        if res.returncode != 0:
            return None
    finally:
        with _LOCK:
            _git(repo, "worktree", "remove", "--force", str(wt), check=False)
            _git(repo, "worktree", "prune", check=False)
    dbs = sorted(work.rglob("*.db"))
    return dbs[0] if dbs else None


def scan_pair_delta(repo_path: str, parent: str, child: str, scratch_root: str,
                    wps: int | None, full_mode: bool) -> tuple[str, str | None, str]:
    """Scan parent FULL, then child (delta unless --full), returning the DB that
    holds BOTH commits, ready to merge. Returns (child, db_path|None, status)."""
    repo = pathlib.Path(repo_path)
    env = SCAN_ENV if wps is None else {**SCAN_ENV, "GALAXYSCOPE_MAX_WORKERS": str(wps)}
    base = pathlib.Path(scratch_root) / child[:12]
    shutil.rmtree(base, ignore_errors=True)
    pdir, cdir = base / "p", base / "c"
    pdir.mkdir(parents=True)
    cdir.mkdir(parents=True)

    pdb = _scan(repo, parent, pdir, env)
    if pdb is None:
        return child, None, "PARENT SCAN FAILED"
    if full_mode:
        cdb_seed = None  # independent full child
        extra = ()
    else:
        cdb_seed = cdir / f"{repo.name}_galaxy_master.db"
        shutil.copy(pdb, cdb_seed)  # child delta appends onto the parent's DB
        extra = ("--incremental", str(cdb_seed), "--baseline", parent)

    cdb = _scan(repo, child, cdir, env, extra=extra)
    if cdb is None:
        return child, None, "CHILD SCAN FAILED"
    # In delta mode cdb already carries parent+child. In full mode it carries only
    # the child; the parent rows live in pdb, so hand back BOTH via a merge marker.
    return child, str(cdb), ("scanned-delta" if not full_mode else f"scanned-full+parent:{pdb}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--events", required=True)
    ap.add_argument("--classes", default="security-fix,control")
    ap.add_argument("--limit", type=int, default=0, help="events per class (0 = all)")
    ap.add_argument("--jobs", type=int, default=0, help="parallel pairs (0 = min(nproc,6))")
    ap.add_argument("--workers-per-scan", type=int, default=None)
    ap.add_argument("--scratch", default="/nvme-data/tc-scratch/delta")
    ap.add_argument("--full", action="store_true", help="A/B baseline: full child instead of delta")
    ap.add_argument("--keep-scratch", action="store_true")
    args = ap.parse_args()

    jobs = args.jobs or min(os.cpu_count() or 4, 6)
    data = json.loads(pathlib.Path(args.events).read_text())
    repo = resolve_repo(data["repo"])
    out_dir = out_dir_for(repo)
    master = out_dir / f"{repo.name}_galaxy_master.db"
    scratch = pathlib.Path(args.scratch) / repo.name
    scratch.mkdir(parents=True, exist_ok=True)
    wanted = args.classes.split(",")

    per_class: dict[str, int] = {}
    pairs = []
    for e in data["events"]:
        if e["class"] not in wanted:
            continue
        if args.limit and per_class.get(e["class"], 0) >= args.limit:
            continue
        child = _git(repo, "rev-parse", e["sha"]).stdout.strip()
        try:
            parent = _git(repo, "rev-parse", f"{child}^").stdout.strip()
        except subprocess.CalledProcessError:
            continue
        per_class[e["class"]] = per_class.get(e["class"], 0) + 1
        if not (already_scanned(out_dir, child) and already_scanned(out_dir, parent)):
            pairs.append((parent, child))

    mode = "FULL (A/B baseline)" if args.full else "DELTA"
    print(f"{len(pairs)} pairs to scan [{mode}] on {jobs} workers "
          f"(wps={args.workers_per_scan})", flush=True)
    if not pairs:
        print("nothing to do")
        return 0

    t0 = time.time()
    done = failed = 0
    mcon: sqlite3.Connection | None = None
    lock = Manager().Lock()
    with ProcessPoolExecutor(max_workers=jobs, initializer=_init_lock, initargs=(lock,)) as ex:
        futs = {ex.submit(scan_pair_delta, str(repo), p, c, str(scratch),
                          args.workers_per_scan, args.full): c for p, c in pairs}
        for fut in as_completed(futs):
            child, db, status = fut.result()
            done += 1
            if db is None:
                failed += 1
                print(f"[{done}/{len(pairs)}] {child[:12]} {status}", flush=True)
                continue
            if mcon is None:
                if not master.exists():
                    _init_master(master, db)
                mcon = sqlite3.connect(master)
                mcon.execute("PRAGMA foreign_keys=OFF")
            merge_shard(mcon, db, repo.name)
            # full-mode also needs the parent DB merged (it lives outside `db`)
            if status.startswith("scanned-full+parent:"):
                merge_shard(mcon, status.split(":", 1)[1], repo.name)
            mcon.commit()
            if not args.keep_scratch:
                shutil.rmtree(pathlib.Path(db).parent.parent, ignore_errors=True)
            print(f"[{done}/{len(pairs)}] {child[:12]} {status.split(':')[0]} "
                  f"({(time.time()-t0)/60:.1f}m)", flush=True)
    if mcon is not None:
        mcon.close()
    if not args.keep_scratch:
        shutil.rmtree(scratch, ignore_errors=True)
    dt = time.time() - t0
    print(f"\n{mode}: {len(pairs)-failed} pairs in {dt:.1f}s ({dt/max(len(pairs)-failed,1):.2f}s/pair), {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
