#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Comment-extraction Wave A (EXPLORATORY): instrument checks before any comment hypothesis.

Two subcommands, both read-only over their inputs:

  hunks   COM-E1. Score every curl event's patch (events/curl.json + curl_wave1.json +
          curl_bugs.json) three ways with hunk_grammar.py's own diff parsing, path filter
          and the engine's C rules: `raw` (the diff text as it is, the pre-#109 tool),
          `code` (hunk_grammar's current Prism strip) and `comments` (only the comment
          text the strip removes). Prints per-class fix-shaped rates and added branch /
          pointer hits per mode.

  scan    COM-E2 / COM-E3 aggregates over one galaxyscope master DB of a C repo (tests/
          and docs/ excluded): per-function `is_documented`, `has_header_comment`, a
          non-empty `docstring`, and the share of each comment signal's file-level hits
          that the engine attributes to function bodies. With --src, it also lists every
          `dead_code` match in the positional comment stream (the COM-H3 precision audit).

Usage (engine checkout on PYTHONPATH, as hunk_grammar.py documents):
    GITGALAXY_PATH=<engine> EXPOSURE_POOL=<pool> python tools/comment_wave_a.py hunks --out <scratch>
    GITGALAXY_PATH=<engine> python tools/comment_wave_a.py scan --db <master.db> [--src <checkout>]
"""

from __future__ import annotations

import argparse
import bisect
import json
import pathlib
import re
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

COMMENT_COLS = ("state_graveyard", "state_planned_debt", "state_fragile_debt", "def_doc", "def_ownership")
C_SCOPE = "f.language = 'c' AND f.file_path NOT LIKE 'tests/%' AND f.file_path NOT LIKE 'docs/%'"
REAL_UNITS = "u.func_name NOT LIKE '!_!_%' ESCAPE '!'"


def _hunks(out: pathlib.Path, workers: int) -> dict:
    import hunk_grammar as h  # noqa: PLC0415 -- needs GITGALAXY_PATH set first

    code_strip = h._strip_c_comments

    def comments_only(text: str) -> str:
        if not text:
            return ""
        streams = h._C_PRISM.split_streams(text, "c")
        orphans = "\n".join(m.group(0) for m in h._ORPHAN_COMMENT_LINE.finditer(streams["code_stream"]))
        return streams["comment_stream"] + "\n" + orphans

    modes = {"raw": lambda t: t or "", "code": code_strip, "comments": comments_only}
    events = h.load_all_events()
    repo = h.POOL_DIR / "curl"
    out.mkdir(parents=True, exist_ok=True)
    summary: dict = {}
    for mode, strip in modes.items():
        h._strip_c_comments = strip  # fork-pool workers inherit the patched module
        cache_path = out / f"comment_wave_a_{mode}.json"
        cache = h.load_cache(cache_path)
        h.compute_all(events, repo, cache, cache_path, workers=workers)
        cache = h.load_cache(cache_path)
        per: dict = {}
        for ev in events:
            st = cache.get(ev["sha"])
            if not st or st.get("bystander_only"):
                continue
            c = per.setdefault(ev["class"], {"n": 0, "fix": 0, "branch_add": 0, "ptr_add": 0})
            c["n"] += 1
            c["fix"] += int(h.fixshaped_h(st))
            c["branch_add"] += st["added"]["branch"]
            c["ptr_add"] += st["added"]["pointers"]
        summary[mode] = per
    h._strip_c_comments = code_strip
    print(f"{'class':13s} {'n':>4s}  fix-shaped% raw/code/comments   branch added raw/code/comments")
    for cls in h.CLASS_ORDER:
        rows = [summary[m].get(cls) for m in modes]
        if not rows[0]:
            continue
        pct = [100 * r["fix"] / r["n"] for r in rows]
        br = [r["branch_add"] for r in rows]
        print(f"{cls:13s} {rows[0]['n']:4d}  {pct[0]:5.0f} {pct[1]:5.0f} {pct[2]:5.0f}      {br[0]:7d} {br[1]:7d} {br[2]:7d}")
    raw_b = sum(v["branch_add"] for v in summary["raw"].values())
    code_b = sum(v["branch_add"] for v in summary["code"].values())
    print(f"comment prose share of raw added branch hits: {100 * (raw_b - code_b) / raw_b:.1f}% ({raw_b - code_b}/{raw_b})")
    return summary


def _scan(db: pathlib.Path, src: pathlib.Path | None) -> None:
    con = sqlite3.connect(db)
    units = f"FROM function_data u JOIN file_data f ON u.file_id = f.id WHERE {C_SCOPE} AND {REAL_UNITS}"

    def one(sql: str) -> int:
        return con.execute(sql).fetchone()[0] or 0

    n = one(f"SELECT COUNT(*) {units}")
    print(f"C files {one(f'SELECT COUNT(*) FROM file_data f WHERE {C_SCOPE}')}, functions {n}")
    for col in ("is_documented", "has_header_comment"):
        k = one(f"SELECT SUM(u.{col}) {units}")
        print(f"  {col:20s} {k:6d}  ({100 * k / n:.1f}%)")
    k = one(f"SELECT SUM(u.docstring <> '') {units}")
    print(f"  {'docstring non-empty':20s} {k:6d}  ({100 * k / n:.1f}%)")
    print("comment hits: file total vs attributed to function bodies")
    for col in COMMENT_COLS:
        ft = one(f"SELECT SUM(f.{col}) FROM file_data f WHERE {C_SCOPE}")
        ut = one(f"SELECT SUM(u.{col}) {units}")
        share = f"{100 * ut / ft:.1f}%" if ft else "n/a"
        print(f"  {col:20s} file {ft:5d}  in functions {ut:5d}  ({share})")
    if src is None:
        return

    from gitgalaxy.core.prism import Prism  # noqa: PLC0415
    from gitgalaxy.standards.gitgalaxy_config import LEXICAL_FAMILY_HEURISTICS  # noqa: PLC0415
    from gitgalaxy.standards.language_standards import LANGUAGE_DEFINITIONS  # noqa: PLC0415

    prism = Prism(LEXICAL_FAMILY_HEURISTICS, LANGUAGE_DEFINITIONS)
    dead = LANGUAGE_DEFINITIONS["c"]["rules"]["dead_code"]
    print("dead_code matches (judge each: commented-out code, prototype note, or prose):")
    for (path,) in con.execute(f"SELECT f.file_path FROM file_data f WHERE {C_SCOPE} AND f.state_graveyard > 0"):
        text = (src / path).read_text(encoding="utf-8", errors="replace")
        pos = prism.split_positional_comment_stream(text, "c")
        newlines = [m.start() for m in re.finditer("\n", pos)]
        for m in dead.finditer(pos):
            line = bisect.bisect_left(newlines, m.start()) + 1
            print(f"  {path}:{line}: {pos[m.start() : m.start() + 80].splitlines()[0]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    hp = sub.add_parser("hunks")
    hp.add_argument("--out", required=True, help="scratch dir for the three per-mode caches")
    hp.add_argument("--workers", type=int, default=10)
    sp = sub.add_parser("scan")
    sp.add_argument("--db", required=True)
    sp.add_argument("--src", help="the scanned checkout, for the dead_code match listing")
    args = ap.parse_args()
    if args.cmd == "hunks":
        summary = _hunks(pathlib.Path(args.out), args.workers)
        (pathlib.Path(args.out) / "comment_wave_a_summary.json").write_text(json.dumps(summary, indent=1))
    else:
        _scan(pathlib.Path(args.db), pathlib.Path(args.src) if args.src else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
