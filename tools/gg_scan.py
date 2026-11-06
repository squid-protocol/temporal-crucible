#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""GG: weekly scans of the GitGalaxy repo's own `gitgalaxy/` package (docs/gg_hypotheses.md).
One single-commit DB per week, engine pinned, history ablated.

    GALAXYSCOPE_BIN=<pinned engine> python tools/gg_scan.py --out <dir> --jobs 4
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import POOL_DIR  # noqa: E402
from run_batch_parallel import SCAN_ENV  # noqa: E402

REPO = POOL_DIR / "gitgalaxy"


def _git(*a):
    return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True, errors="replace").stdout


def weeks(start="2026-03-23", end="2026-11-02"):
    d, e = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    out = []
    while d <= e:
        sha = _git("rev-list", "-1", "--first-parent", f"--before={d.isoformat()} 00:00:00 +0000", "HEAD").strip()
        if sha and (not out or out[-1]["sha"] != sha):
            out.append({"week": d.isoformat(), "sha": sha})
        d += dt.timedelta(days=7)
    return out


def scan(task):
    week, sha, out = task
    dest = pathlib.Path(out) / f"{week}_{sha[:9]}"
    db = dest / "gg_galaxy_master.db"
    if db.exists():
        return week, "cached"
    work = dest / "work"
    shutil.rmtree(work, ignore_errors=True)
    (work / "gg").mkdir(parents=True)
    arch = subprocess.run(["git", "-C", str(REPO), "archive", sha, "gitgalaxy"], capture_output=True)
    subprocess.run(["tar", "-x", "-C", str(work / "gg")], input=arch.stdout, check=True)
    env = {**SCAN_ENV, "GALAXYSCOPE_MAX_WORKERS": "2"}
    r = subprocess.run([os.environ["GALAXYSCOPE_BIN"], str(work / "gg"), "--db-only", "--spec-alignment"],
                       cwd=work, env=env, capture_output=True, text=True)
    dbs = sorted(work.rglob("*_galaxy_master.db"))
    if r.returncode != 0 or not dbs:
        return week, f"FAILED {r.stderr[-200:]}"
    shutil.move(str(dbs[0]), db)
    shutil.rmtree(work, ignore_errors=True)
    return week, "scanned"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    ws = weeks()
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "weeks.json").write_text(json.dumps(ws, indent=1))
    with ProcessPoolExecutor(a.jobs) as ex:
        for week, st in ex.map(scan, [(w["week"], w["sha"], str(a.out)) for w in ws]):
            print(week, st, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
