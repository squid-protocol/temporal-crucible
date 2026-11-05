#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Quarterly snapshot manifest for the FWD-H forward-prediction design (tc#29).

Snapshot t = the newest first-parent commit on the default branch dated before
each calendar-quarter boundary (Jan/Apr/Jul/Oct 1 UTC), from the first quarter
whose tree holds >= 50 C files (.c/.h) through the last quarter whose outcome
window (t, t+180 d] closes on or before the events harvest's pool_head date.
Writes walks/<repo>_quarterly.json in the walk-manifest shape, so
rescan_study_set.py --commits-file reads it directly. Registered in
docs/HYPOTHESES.md (FWD-H1..H3).

    python tools/fwd_snapshots.py --repo curl --events events/curl.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import REPO_ROOT  # noqa: E402
from scan_pair import resolve_repo  # noqa: E402

OUTCOME_DAYS = 180
MIN_C_FILES = 50
DAY = 86400


def _git(repo, *args) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          text=True, check=True, errors="replace").stdout


def default_branch(repo) -> str:
    for ref in ("refs/remotes/origin/HEAD",):
        r = subprocess.run(["git", "-C", str(repo), "symbolic-ref", "--short", ref],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    return _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()


def quarter_boundaries(start: int, end: int) -> list[int]:
    d = datetime.fromtimestamp(start, timezone.utc)
    y, m = d.year, ((d.month - 1) // 3) * 3 + 1
    out = []
    while True:
        m += 3
        if m > 12:
            y, m = y + 1, m - 12
        ts = int(datetime(y, m, 1, tzinfo=timezone.utc).timestamp())
        if ts > end:
            return out
        out.append(ts)


def c_file_count(repo, sha: str) -> int:
    names = _git(repo, "ls-tree", "-r", "--name-only", sha).splitlines()
    return sum(1 for n in names if n.endswith((".c", ".h")))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--events", required=True, type=pathlib.Path,
                    help="events file whose pool_head bounds the last outcome window")
    ap.add_argument("--branch", default=None)
    args = ap.parse_args()

    repo = resolve_repo(args.repo)
    branch = args.branch or default_branch(repo)
    head = json.loads(args.events.read_text()).get("pool_head") or _git(repo, "rev-parse", branch).strip()
    end = int(_git(repo, "show", "-s", "--format=%ct", head).strip())
    log = [line.split() for line in _git(repo, "log", "--first-parent", "--format=%H %ct", head).splitlines()]
    commits = sorted(((int(ct), sha) for sha, ct in log))  # oldest first
    revisions, j, started = [], 0, False
    for b in quarter_boundaries(commits[0][0], end - OUTCOME_DAYS * DAY):
        while j + 1 < len(commits) and commits[j + 1][0] < b:
            j += 1
        ct, sha = commits[j]
        if ct >= b:
            continue
        if not started:
            if c_file_count(repo, sha) < MIN_C_FILES:
                continue
            started = True
        q = datetime.fromtimestamp(b, timezone.utc)
        revisions.append({"ref": f"pre-{q:%Y-%m-%d}", "sha": sha,
                          "date": datetime.fromtimestamp(ct, timezone.utc).isoformat(),
                          "boundary": q.isoformat(), "status": "ok"})
    # One commit can precede two boundaries in a quiet stretch: keep one snapshot per sha.
    seen, uniq = set(), []
    for r in revisions:
        if r["sha"] not in seen:
            seen.add(r["sha"])
            uniq.append(r)
    out = REPO_ROOT / "walks" / f"{repo.name}_quarterly.json"
    out.write_text(json.dumps({"repo": repo.name, "mode": "quarterly", "branch": branch,
                               "events_head": head, "outcome_days": OUTCOME_DAYS,
                               "min_c_files": MIN_C_FILES, "revisions": uniq}, indent=1) + "\n")
    print(f"{out}: {len(uniq)} snapshots ({uniq[0]['ref']} .. {uniq[-1]['ref']}) on {branch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
