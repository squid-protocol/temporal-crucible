#!/usr/bin/env python3
"""UT: scan the fork heads with the engine that scanned the OpenSSL snapshots (docs/ut_hypotheses.md)."""
import os, pathlib, shutil, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import POOL_DIR  # noqa: E402
from run_batch_parallel import SCAN_ENV  # noqa: E402
BIN = "/srv/storage_16tb/projects/gitgalaxy-worktrees/tc-asof-da852aa54/.venv-tc/bin/galaxyscope-tc"
FORKS = {"boringssl": ("e375adcf13f841eabd872e2e7c6030aab6be3117", ["crypto", "ssl", "decrepit", "include"]),
         "libressl": ("a22aeee114ad90a9145672868d02197bfd76a96f", ["src/lib/libcrypto", "src/lib/libssl"])}
OUT = POOL_DIR / "ut_forks"
for name, (sha, dirs) in FORKS.items():
    repo = POOL_DIR / ("boringssl" if name == "boringssl" else "openbsd")
    work = OUT / name / "src"
    db = OUT / name / f"{name}_galaxy_master.db"
    if db.exists():
        print(name, "done"); continue
    shutil.rmtree(work.parent, ignore_errors=True); work.mkdir(parents=True)
    tar = subprocess.run(["git", "-C", str(repo), "archive", sha, "--", *dirs], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(work)], input=tar, check=True)
    tgt = work.parent / name
    work.rename(tgt)
    r = subprocess.run([BIN, str(tgt), "--db-only", "--spec-alignment"], cwd=work.parent,
                       env={**SCAN_ENV, "GALAXYSCOPE_MAX_WORKERS": "4"}, capture_output=True, text=True)
    dbs = sorted(work.parent.rglob("*_galaxy_master.db"))
    print(name, r.returncode, dbs, r.stderr[-400:], flush=True)
    if dbs:
        dbs[0].rename(db)
