#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The fix label HR-* uses: the raw keyword flag, or the FIXLIKE v3c cleaning (docs/hist_replication.md).

The history DBs' `fix` flag is a keyword gate. Measured on this cohort it is contaminated and unevenly so --
cosmetic commits (javadoc, checkstyle, formatting, typo, lint) are 41.7% of commons-lang's fix commits and
4-20% elsewhere. `rules="v3c"` runs each candidate through tools/fixlike_v2.drop_reason with its subject and
its touched paths.

v3c was audited on xc_harvest's `other-fix` class (precision 0.38 -> 0.77 outside C). Applied here it is an
ADAPTATION to a different label family and inherits no audited precision: a sharper label, not a validated one.
"""
from __future__ import annotations

import sqlite3, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fixlike_v2 as F  # noqa: E402


def fix_shas(h: sqlite3.Connection, rules: str = "raw") -> set[str] | None:
    """The shas to treat as fixes. None means 'no filtering' -- the caller keeps its own `fix=1` test."""
    if rules == "raw":
        return None
    raw = {s: (subj or "") for s, subj in
           h.execute("select sha, subject from commit_ where fix=1 and merge=0 and bot=0")}
    touched: dict[str, list[str]] = {}
    for sha, path in h.execute("select sha, path from touch"):
        if sha in raw:
            touched.setdefault(sha, []).append(path)
    keep = set()
    for sha, subj in raw.items():
        ev = {"class": "other-fix", "subject": subj, "c_files": touched.get(sha, [])}
        if F.drop_reason(ev, rules=rules) is None:
            keep.add(sha)
    return keep


def summary(study: Path, repos, rules: str = "v3c") -> list[dict]:
    out = []
    for r in repos:
        h = sqlite3.connect(f"file:{study/'history'/f'{r}.db'}?mode=ro", uri=True)
        raw = h.execute("select count(*) from commit_ where fix=1 and merge=0 and bot=0").fetchone()[0]
        kept = len(fix_shas(h, rules) or ())
        h.close()
        out.append({"repo": r, "raw": raw, "kept": kept,
                    "dropped_share": round(1 - kept / raw, 4) if raw else None})
    return out


if __name__ == "__main__":
    S = Path("/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot")
    REPOS = ("commons-lang", "libgit2", "libxml2", "postgres", "prometheus", "redis", "ripgrep", "sphinx")
    print(f"{'repo':14}{'raw fix':>9}{'v3c kept':>10}{'dropped':>9}")
    for row in summary(S, REPOS):
        print(f"{row['repo']:14}{row['raw']:>9}{row['kept']:>10}{row['dropped_share']:>9.1%}")
