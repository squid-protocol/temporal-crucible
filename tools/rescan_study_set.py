#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Rescan an existing study DB's exact commit set on a newer engine.

Reads every distinct commit_hash in --from-db (the study-of-record DB) and
full-scans each one under SCAN_ENV into this checkout's dbs/<repo>_out master,
reusing run_batch_parallel's isolated scan + id-FK merge. The old DB is only
read, so old-vs-new engine drift can be compared commit-for-commit afterwards.

Resumable: commits already in the new master are skipped. --sample N scans an
evenly spaced (by commit date) pilot of N commits into --pilot-db instead, for
timing; the pilot never touches the real master.

    # spec_match is opt-in since gitgalaxy#3111; the study's 13-slot vector needs it on.
    GALAXYSCOPE_BIN=/path/to/pinned/galaxyscope TC_ENGINE_ARGS=--spec-alignment \
    python tools/rescan_study_set.py --repo curl \
        --from-db /srv/.../temporal-crucible/dbs/curl_out/curl_galaxy_master.db \
        --jobs 5 --workers-per-scan 2
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
from _engine import GALAXYSCOPE_BIN  # noqa: E402
import run_batch_parallel  # noqa: E402
from run_batch_parallel import _init, _init_master, merge_shard, scan_one  # noqa: E402
from scan_pair import out_dir_for, resolve_repo  # noqa: E402


def engine_sha() -> str:
    """Best-effort git SHA of the engine checkout behind GALAXYSCOPE_BIN."""
    bin_dir = pathlib.Path(GALAXYSCOPE_BIN).resolve().parent
    for cand in (bin_dir.parent.parent, bin_dir.parent):
        r = subprocess.run(["git", "-C", str(cand), "rev-parse", "HEAD"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout.strip()
    return "unknown"


def study_commits(db: pathlib.Path, repo_name: str) -> list[tuple[str, str]]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT commit_hash, MIN(commit_date) FROM repo_data WHERE repo_name=? "
        "GROUP BY commit_hash ORDER BY MIN(commit_date)", (repo_name,)).fetchall()
    con.close()
    return [(r[0], r[1] or "") for r in rows]


def commits_from_file(path: pathlib.Path) -> list[tuple[str, str]]:
    text = path.read_text()
    if path.suffix == ".json":
        return [(r["sha"], r.get("date", "")) for r in json.loads(text)["revisions"]
                if r.get("status", "ok") == "ok"]
    return [(line.split()[0], "") for line in text.splitlines() if line.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--from-db", type=pathlib.Path, help="rescan every commit in this study DB")
    src.add_argument("--commits-file", type=pathlib.Path,
                     help="one sha per line, or a walks/<repo>_walk.json manifest")
    ap.add_argument("--history-asof", action="store_true",
                    help="history ENABLED, measured as of each commit (GITGALAXY_HISTORY_ASOF=1, "
                         "gitgalaxy#7818) -- the forward-prediction mode (tc#29), not the ablated "
                         "SCAN_ENV the delta analyses require")
    ap.add_argument("--jobs", type=int, default=5)
    ap.add_argument("--workers-per-scan", type=int, default=2)
    ap.add_argument("--scratch", default="/nvme-data/tc-scratch")
    ap.add_argument("--sample", type=int, default=0, help="pilot: N evenly spaced commits")
    ap.add_argument("--pilot-db", type=pathlib.Path, default=None)
    args = ap.parse_args()

    repo = resolve_repo(args.repo)
    if args.history_asof:
        # Workers fork after this, so they inherit the swapped env (scan_one reads
        # run_batch_parallel.SCAN_ENV at call time).
        env = {k: v for k, v in run_batch_parallel.SCAN_ENV.items() if k != "GITGALAXY_DISABLE_GIT_HISTORY"}
        env["GITGALAXY_HISTORY_ASOF"] = "1"
        run_batch_parallel.SCAN_ENV = env
    if args.from_db:
        commits = study_commits(args.from_db, repo.name)
    else:
        commits = commits_from_file(args.commits_file)
    total = len(commits)
    if args.sample:
        step = max(1, total // args.sample)
        commits = commits[::step][: args.sample]
        master_path = args.pilot_db or pathlib.Path(args.scratch) / f"{repo.name}_pilot.db"
        master_path.unlink(missing_ok=True)
    else:
        master_path = out_dir_for(repo) / f"{repo.name}_galaxy_master.db"

    if master_path.exists():
        con = sqlite3.connect(master_path)
        done = {r[0] for r in con.execute("SELECT commit_hash FROM repo_data")}
        con.close()
    else:
        done = set()
    # A walk can list one commit for several quarters (no new mainline commit). Scanning the duplicates
    # concurrently made them share and delete one scratch dir (scratch/<sha[:12]>), corrupting the scan.
    todo = list(dict.fromkeys(c for c, _ in commits if c not in done))

    eng = engine_sha()
    meta = {"engine_bin": GALAXYSCOPE_BIN, "engine_sha": eng,
            "engine_args": os.environ.get("TC_ENGINE_ARGS", ""),
            "history": "asof" if args.history_asof else "ablated", "from_db": str(args.from_db or args.commits_file),
            "study_commits": total, "selected": len(commits), "todo": len(todo),
            "jobs": args.jobs, "workers_per_scan": args.workers_per_scan,
            "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    print(json.dumps(meta), flush=True)
    if not args.sample:
        (master_path.parent / "rescan_meta.json").write_text(json.dumps(meta, indent=2))

    scratch_root = pathlib.Path(args.scratch) / f"{repo.name}_rescan"
    scratch_root.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    ok = fail = 0
    mcon = None
    with Manager() as mgr:
        lock = mgr.Lock()
        with ProcessPoolExecutor(max_workers=args.jobs, initializer=_init, initargs=(lock,)) as ex:
            futs = [ex.submit(scan_one, str(repo), sha, str(scratch_root), args.workers_per_scan)
                    for sha in todo]
            for i, f in enumerate(as_completed(futs), 1):
                sha, shard, status = f.result()
                if shard:
                    if mcon is None:
                        if not master_path.exists():
                            _init_master(master_path, shard)
                        mcon = sqlite3.connect(master_path)
                        mcon.execute("PRAGMA journal_mode=WAL")
                    msg = merge_shard(mcon, shard, repo.name)
                    mcon.commit()
                    ok += 1
                else:
                    msg = status
                    fail += 1
                shutil.rmtree(scratch_root / sha[:12], ignore_errors=True)
                el = time.time() - t0
                eta = el / i * (len(todo) - i)
                print(f"[{i}/{len(todo)}] {sha[:12]} {msg} | {el/60:.1f}m elapsed, "
                      f"{el/i:.2f}s/commit, eta {eta/60:.1f}m", flush=True)
    if mcon:
        mcon.close()
    el = time.time() - t0
    print(json.dumps({"done": ok, "failed": fail, "wall_s": round(el, 1),
                      "s_per_commit": round(el / max(1, len(todo)), 2)}), flush=True)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
