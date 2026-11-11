#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The LAWS sampling frame and the seeded draw (methods review M9; Amendment 3 for the counts).

    python tools/laws_frame.py slices   --language go                       # the created: windows, no API calls
    python tools/laws_frame.py search   --language go --out DIR --confirm   # SPENDS SEARCH QUOTA
    python tools/laws_frame.py draw     --out DIR --language go --n 16      # after the fingerprint is pushed

**Nothing here runs against GitHub without `--confirm`.** The frame fixes the sample of a pre-registered study:
once the candidate file's SHA-256 is pushed and the draw is taken, the sample cannot be quietly rebuilt -- a
mistake needs a dated amendment admitting it. So the search step is gated, and `draw` refuses to run unless the
fingerprint it is drawing from matches one recorded on disk.

M9's rules, implemented:

**Frame.** GitHub search sliced by `created:` month windows with
`stars:>=500 fork:false archived:false language:<L>`; any slice returning the 1,000-result cap is split in half
and re-queried until no slice is truncated. The frame is complete only when no slice is truncated, and the frame
size per language is reported.

**Share.** A candidate needs >= SHARE of its bytes in the language, from the languages API, not the `language:`
filter (which is primary-language only). **JS/TS is JavaScript + TypeScript bytes combined.** C++ counts
linguist "C++" only.

**History** (clone-time checks, `eligible_history`): at least MIN_COMMITS commits on
`git rev-list --first-parent --count` of the default branch; the quarterly rule giving at least MIN_SNAPSHOTS
quarters with at least MIN_FILES source files; and at least one commit in at least QUARTER_COVERAGE of the
quarters from the first eligible quarter to the panel end. "First commit" is the first quarter with MIN_FILES
source files of the language, not the root commit date.

**Draw.** Candidates sorted by `full_name` lower-cased in byte order, then
`random.Random(2982).sample(list, len(list))` -- a full permutation -- and taken in that order until `n` pass the
clone-time checks. A failure after the first law statistic is computed never causes replacement.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path

SEED = 2982
CAP = 1000  # GitHub search returns at most this many results per query
SHARE = 0.60
MIN_COMMITS = 2000
MIN_SNAPSHOTS = 20
MIN_FILES = 50
QUARTER_COVERAGE = 0.75
PANEL_END = "2026-10-01"
FRAME_START = "2008-01"  # GitHub's own beginning; no repo was created before it
JSTS = ("JavaScript", "TypeScript")


def month_slices(start: str = FRAME_START, end: str | None = None) -> list[tuple[str, str]]:
    """The `created:` windows, one per month, as (inclusive from, inclusive to) ISO dates."""
    y, m = (int(x) for x in start.split("-"))
    last = dt.date.fromisoformat(end or PANEL_END)
    out = []
    while True:
        first = dt.date(y, m, 1)
        if first > last:
            break
        nxt = dt.date(y + (m == 12), (m % 12) + 1, 1)
        out.append((first.isoformat(), (nxt - dt.timedelta(days=1)).isoformat()))
        y, m = nxt.year, nxt.month
    return out


def split_window(lo: str, hi: str) -> list[tuple[str, str]] | None:
    """A truncated window halved by date. None when it cannot be split further (a single day)."""
    a, b = dt.date.fromisoformat(lo), dt.date.fromisoformat(hi)
    if a >= b:
        return None
    mid = a + (b - a) // 2
    return [(a.isoformat(), mid.isoformat()), ((mid + dt.timedelta(days=1)).isoformat(), b.isoformat())]


def query(language: str, lo: str, hi: str) -> str:
    return f"stars:>=500 fork:false archived:false language:{language} created:{lo}..{hi}"


def frame(language: str, run_search, start: str = FRAME_START, end: str | None = None) -> dict:
    """Every candidate for one language. `run_search(q) -> (total_count, [full_name, ...])` is injected so the
    slicing logic is testable without the API. A window at the cap is split and re-queried; the frame is
    complete only when no window is truncated."""
    todo = list(month_slices(start, end))
    names: set[str] = set()
    windows, truncated, calls = [], [], 0
    while todo:
        lo, hi = todo.pop(0)
        total, got = run_search(query(language, lo, hi))
        calls += 1
        if total > CAP:
            parts = split_window(lo, hi)
            if parts is None:
                truncated.append({"from": lo, "to": hi, "total": total})  # a single day over the cap
                names.update(got)
                windows.append({"from": lo, "to": hi, "total": total, "returned": len(got), "truncated": True})
                continue
            todo = parts + todo
            continue
        names.update(got)
        windows.append({"from": lo, "to": hi, "total": total, "returned": len(got), "truncated": False})
    return {"language": language, "candidates": sorted(names), "frame_size": len(names),
            "windows": len(windows), "search_calls": calls, "truncated_windows": truncated,
            "complete": not truncated}


def language_share(bytes_by_language: dict[str, int], language: str) -> float:
    """The share of a repo's bytes in the panel language. JS/TS is JavaScript + TypeScript combined (M9)."""
    total = sum(bytes_by_language.values())
    if not total:
        return 0.0
    keys = JSTS if language == "jsts" else (LINGUIST.get(language, language),)
    return sum(bytes_by_language.get(k, 0) for k in keys) / total


LINGUIST = {"c": "C", "cpp": "C++", "csharp": "C#", "go": "Go", "java": "Java", "kotlin": "Kotlin",
            "php": "PHP", "python": "Python", "rust": "Rust"}


def sorted_candidates(names) -> list[str]:
    """M9's order: `full_name` lower-cased, byte order. The draw is defined on this order, so it is the one
    thing in the frame that must never change."""
    return sorted({n.lower() for n in names})


def permutation(names, seed: int = SEED) -> list[str]:
    """M9's draw order: a full permutation of the sorted candidates by `random.Random(seed).sample`."""
    ordered = sorted_candidates(names)
    return random.Random(seed).sample(ordered, len(ordered))


def fingerprint(path: Path) -> str:
    """The SHA-256 of the candidate file, which M9 requires be committed and pushed BEFORE the draw."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def eligible_history(repo: Path, language: str, snapshots_fn=None) -> dict:
    """The clone-time history checks. `snapshots_fn(repo, language) -> (quarters_with_files, quarters_total,
    quarters_with_commit)` is injected so the rules are testable without a clone."""
    out: dict = {"eligible": False}
    p = subprocess.run(["git", "-C", str(repo), "rev-list", "--first-parent", "--count", "HEAD"],
                       capture_output=True, text=True)
    commits = int(p.stdout.strip() or 0)
    out["first_parent_commits"] = commits
    if commits < MIN_COMMITS:
        return {**out, "why": f"fewer than {MIN_COMMITS} first-parent commits ({commits})"}
    if snapshots_fn is None:
        return {**out, "why": "the quarterly rule needs a scan; run it at clone time"}
    with_files, total, with_commit = snapshots_fn(repo, language)
    out.update(snapshots_with_files=with_files, quarters=total, quarters_with_commit=with_commit)
    if with_files < MIN_SNAPSHOTS:
        return {**out, "why": f"fewer than {MIN_SNAPSHOTS} quarters with {MIN_FILES} source files ({with_files})"}
    cover = with_commit / total if total else 0.0
    out["quarter_coverage"] = round(cover, 4)
    if cover < QUARTER_COVERAGE:
        return {**out, "why": f"a commit in only {cover:.0%} of quarters, under {QUARTER_COVERAGE:.0%}"}
    return {**out, "eligible": True}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("slices", "search", "draw"))
    ap.add_argument("--language")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--confirm", action="store_true", help="required for `search`: it spends GitHub search quota")
    a = ap.parse_args()
    if a.step == "slices":
        w = month_slices()
        print(f"{len(w)} monthly windows, {w[0][0]} to {w[-1][1]}; the query per window is:")
        print(f"  {query(a.language or '<L>', w[0][0], w[0][1])}")
        print("no API call was made")
        return 0
    if a.step == "search":
        if not a.confirm:
            print("refusing to search without --confirm: this fixes the sample of a pre-registered study,\n"
                  "spends search quota, and a mistake afterwards needs a dated amendment. Re-run with --confirm.")
            return 1
        print("not implemented in this change: the search runner is wired in the step that builds the real "
              "frame, under the owner's eye. `frame()` takes the runner as an argument and is tested.")
        return 1
    f = (a.out / "frame" / f"{a.language}.json")
    if not f.exists():
        print(f"{f} does not exist: build the frame first")
        return 1
    rec = json.loads(f.read_text())
    recorded = (a.out / "frame" / f"{a.language}.sha256")
    if not recorded.exists():
        print(f"refusing to draw: {recorded} is missing. M9 requires the candidate file's SHA-256 to be "
              "committed and pushed BEFORE the draw.")
        return 1
    if fingerprint(f) != recorded.read_text().split()[0]:
        print("refusing to draw: the candidate file does not match its recorded SHA-256.")
        return 1
    order = permutation(rec["candidates"])
    print(f"{a.language}: {len(order)} candidates, fingerprint {fingerprint(f)[:12]}; first {a.n} in draw order:")
    for i, name in enumerate(order[:a.n], 1):
        print(f"  {i:3d} {name}")
    print("these are the repos to run the clone-time checks against, in this order")
    return 0


if __name__ == "__main__":
    sys.exit(main())
