#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The tracker-key count of docs/process/owner_job_spec.md section 1 (Amendment 5 section 7, item 5, last part).

Every function here runs INSIDE the read-only sandbox (tools/owner/prepare.py's stages `copy`, `build_A`,
`build_Aprime` and `count`); none restates a rule of SA3.

  strip_harvest   the A' harvest: a copy of the (already copied and converted) link harvest from which every row
                  with kind 'issue_fix', a hyphen in value and value != value.upper() is deleted. The `meta` rows
                  are kept, so the reference builder does not try to re-harvest it.
  build_stage     `sa3_outcomes.build(repo)` called unchanged. Which harvest it reads is decided by what the
                  sandbox binds at the path the module has compiled in, `sa3_outcomes.META / '<repo>.db'`
                  (= <study>/meta_sa3/<repo>.db): the copy for A, the stripped copy for A'. The primary outcome's
                  commits go to a file in the protected directory; the stage result carries only the build status.
  count_stage     the count = |A - A'|, "A equals the stored outcome file's primary commits, as a set", and the
                  number of disagreements between the hyphen rule and the reference module's own compiled pattern
                  (`hist_meta.RX['issue_fix_sa3']`, imported, never copied) re-applied to the stored messages.
                  Only integers and yes/no leave the stage; A itself and A - A' stay in the protected directory.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True

BUILD_STATUSES = ("ok", "unprepared", "scan_incomplete", "no_meta")


def is_lower_key(value: str | None) -> bool:
    """the hyphen rule: a stored fix-reference value with a hyphen is a tracker key (the only alternative of the
    pattern that keeps one); it is lower-case when it is not its own upper-case form"""
    return value is not None and "-" in value and value != value.upper()


def strip_harvest(src: Path, dst: Path) -> dict:
    """dst = src without its lower-case tracker-key rows; src is a rollback-mode copy in the protected directory"""
    shutil.copyfile(src, dst)
    con = sqlite3.connect(str(dst))
    try:
        rows = con.execute("select rowid, value from link where kind = 'issue_fix'").fetchall()
        gone = [rid for rid, v in rows if is_lower_key(v)]
        con.executemany("delete from link where rowid = ?", [(r,) for r in gone])
        con.commit()
        meta = dict(con.execute("select key, value from meta"))
        left = sum(1 for (v,) in con.execute("select value from link where kind = 'issue_fix'") if is_lower_key(v))
        mode = con.execute("pragma journal_mode").fetchone()[0]
    finally:
        con.close()
    kept = meta.get("done") == "1" and meta.get("with_merges") == "1" and meta.get("sa3_links") == "1"
    return {"deleted_rows": len(gone), "left_rows": left, "meta_kept": kept, "journal_mode": mode}


def build_stage(repo: str, ref_tools: Path, out_file: Path) -> dict:
    """A (or A'): the reference builder, unchanged, on whatever is bound at the study path"""
    sys.path.insert(0, str(ref_tools))
    import sa3_outcomes as SO                                   # the reference file, from the reference copy
    assert Path(SO.__file__).resolve().parent == ref_tools.resolve(), "the reference builder was not the copy"
    r = SO.build(repo)
    status = r.get("status")
    hp = sorted(r["outcomes"]["HP"]["commits"]) if status == "ok" else []
    out_file.write_text(json.dumps({"status": status, "hp": hp}) + "\n")        # protected directory only
    return {"build_status": status if status in BUILD_STATUSES else "build_status_other"}


def ro(p: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True)


def disagreements(harvest: Path, ref_tools: Path) -> int:
    """How often the hyphen rule and the reference pattern disagree on the stored messages. For every match of
    `hist_meta.RX['issue_fix_sa3']` on subject + newline + body (as `extract_links` reads them): the pattern says
    "tracker key" when its second alternative matched (`m.lastindex == 2`), the hyphen rule when the stored
    value (the first non-empty group, as `extract_links` keeps it) has a hyphen; each match where they differ is
    one. And per commit, the tracker keys the pattern finds against the hyphenated `issue_fix` values stored for
    it: each value in one set and not the other is one."""
    if str(ref_tools) not in sys.path:
        sys.path.insert(0, str(ref_tools))
    import hist_meta as HM                                      # the reference module's own compiled pattern
    rx = HM.RX["issue_fix_sa3"]
    con = ro(harvest)
    try:
        stored: dict[str, set[str]] = defaultdict(set)
        for sha, v in con.execute("select sha, value from link where kind = 'issue_fix'"):
            if v and "-" in v:
                stored[sha].add(v)
        n, seen = 0, set()
        for sha, subject, body in con.execute("select sha, subject, body from body"):
            keys = set()
            for m in rx.finditer((subject or "") + "\n" + (body or "")):
                val = next((g for g in m.groups() if g is not None), None)
                if not val:
                    continue
                if ("-" in val) != (m.lastindex == 2):
                    n += 1
                if m.lastindex == 2:
                    keys.add(val)
            n += len(keys ^ stored.get(sha, set()))
            seen.add(sha)
        n += sum(len(v) for s, v in stored.items() if s not in seen)
    finally:
        con.close()
    return n


def count_stage(repo: str, a_file: Path, ap_file: Path, stored_file: Path, harvest: Path, ref_tools: Path,
                detail_file: Path) -> dict:
    a, ap = json.loads(a_file.read_text()), json.loads(ap_file.read_text())
    none = {"count": None, "a_equals_stored": None, "disagreements": None}
    if a["status"] != "ok":
        st = a["status"] if a["status"] in BUILD_STATUSES else "build_status_other"
        return {"determined": False, "reason": st, **none}
    if ap["status"] != a["status"]:
        return {"determined": False, "reason": "aprime_status_differs", **none}
    stored = json.loads(stored_file.read_text())
    if stored.get("status") != "ok":
        return {"determined": False, "reason": "stored_not_ok", **none}
    A, Ap = set(a["hp"]), set(ap["hp"])
    same = A == set(stored["outcomes"]["HP"]["commits"])
    dis = disagreements(harvest, ref_tools)
    detail_file.write_text(json.dumps({"a_minus_aprime": sorted(A - Ap), "aprime_minus_a": sorted(Ap - A),
                                       "a_equals_stored": same}, indent=1) + "\n")     # protected directory only
    return {"determined": True, "reason": "none", "count": len(A - Ap) if same else None, "a_equals_stored": same,
            "disagreements": dis}
