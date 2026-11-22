#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Read what the SA3 pipeline produced for one repo, through the tools' OWN functions, into one JSON file for
tools/harness/compare.py. Runs only inside the sandbox (it imports tools that hold the study path).

    python tools/harness/probe.py --repo NAME --out FILE

Nothing here decides a rule. It calls mod1_lift.frame, sa3_outcomes.universe, sa3_score.load, design_for,
silent and Design.effect exactly as sa3_score.stage_score does for one (repo, outcome, predictor), because
stage_score itself is locked (it needs the seal); and it dumps the scan's per-file columns, the history walk,
and each archive path's unit verdict (laws_units.language_of and Excluder.why with the snapshot's attributes).
"""
from __future__ import annotations

import argparse, json, sqlite3, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sandbox as SB  # noqa: E402

SB.assert_inside(Path(__import__("os").environ["HARNESS_WORK"]))
sys.path.insert(0, str(HERE.parent))
import numpy as np  # noqa: E402
import laws_units as U  # noqa: E402
import mod1_lift as L  # noqa: E402
import sa3_outcomes as O  # noqa: E402
import sa3_score as SC  # noqa: E402
from _engine import POOL_DIR  # noqa: E402
from hist_fixlabel import fix_shas  # noqa: E402
from laws_history import is_fix_message  # noqa: E402

SCAN_COLS = ("total_loc", "coding_loc", "language", "struct_branch", "state_pointers", "state_memory_alloc",
             "state_danger", "function_count")


def num(v):
    v = float(v)
    return None if v != v else v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    r = a.repo
    out: dict = {"repo": r}
    f = L.frame(r)
    out["frame"] = {k: v for k, v in f.items() if k != "langs"} | {"langs": list(f["langs"])}
    files, u = O.universe(r, f["langs"])
    out["universe"] = sorted(files)
    out["universe_meta"] = u
    side = json.loads((O.SCANS / f"{r}.json").read_text())
    out["scan_side"] = {k: v for k, v in side.items() if k != "attrs"} | {"attrs": sorted(side["attrs"])}
    root = side["src_root"].rstrip("/") + "/"
    w = L.ro(O.SCANS / f"{r}_master.db")
    rows = {}
    for row in w.execute(f"select file_path, {', '.join(SCAN_COLS)} from file_data"):
        p = row[0][len(root):] if row[0].startswith(root) else row[0].lstrip("/")
        rows[p] = dict(zip(SCAN_COLS, row[1:]))
    w.close()
    out["scan"] = rows
    # every archive path's unit verdict, with the rule universe() applies (no rule of our own)
    ex = U.Excluder(side["attrs"], include_tutorials=True)
    gen = set(side["generated"])
    arch = subprocess.run(["git", "-C", str(POOL_DIR / r), "archive", side["snapshot"]], capture_output=True)
    tree = subprocess.run(["tar", "-t"], input=arch.stdout, capture_output=True).stdout.decode().splitlines()
    out["archive"] = {p: {"language": U.language_of(p), "why": ex.why(p, p in gen), "in_scan": p in rows}
                      for p in tree if not p.endswith("/")}
    # the scorer's own view
    d = SC.load(r, with_predictors=True)
    out["scorer_paths"] = d["paths"]
    out["scorer_x"] = {p: [num(v) for v in d["x"][p]] for p in d["x"]}
    out["scorer_loc"] = [float(v) for v in d["loc"]]
    eff = {}
    for oc in ("HP", "KW"):
        y = d["y"][oc]
        cell = {}
        for p in SC.PREDICTORS:
            x = d["x"][p]
            valid = ~np.isnan(x)
            c = {"silent": bool(SC.silent(x, p)), "dropped": int((~valid).sum())}
            if valid.sum() > 1 and 0 < y[valid].sum() < valid.sum():
                des, band, k, idx = SC.design_for(d, y, valid)
                c.update({"pairs": des.n, "pairs_gt": des.n_gt, "pairs_lt": des.n_lt,
                          "clears_pair_floor": bool(des.clears_pair_floor()), "effect": num(des.effect(x[idx]))})
            cell[p] = c
        eff[oc] = cell
    out["scorer_effects"] = eff
    # the history walk
    h = L.ro(L.STUDY / "history" / f"{r}.db")
    out["history_meta"] = dict(h.execute("select key, value from meta"))
    out["history"] = [dict(zip(("sha", "ct", "author", "bot", "merge", "fix", "keyword", "n_units", "subject"), x))
                      for x in h.execute("select sha, ct, author, bot, merge, fix, keyword, n_units, subject "
                                         "from commit_ order by rowid")]
    h.close()
    # the code's two keyword rules, applied by the code's own functions: the cleaned (v3c) gate that decides KW
    # and keeps a commit out of the control pool, and FIXLIKE (laws_history.is_fix_message), which taints a merge
    # that brings in a fix-worded commit (sa3_outcomes.py:265-271)
    h = L.ro(L.STUDY / "history" / f"{r}.db")
    out["kw_gate"] = sorted(fix_shas(h, "v3c", f["merge_units"]) or ())
    touch: dict = {}
    for sha, path in h.execute("select sha, path from touch"):
        touch.setdefault(sha, []).append(path)
    out["touch"] = touch                      # the history's own record: what each unit touched, by path at the time
    h.close()
    meta_db = O.META / f"{r}.db"
    if meta_db.exists():
        m = sqlite3.connect(f"file:{meta_db}?mode=ro", uri=True)
        out["links"] = [list(x) for x in m.execute("select sha, kind, value from link")]
        out["fix_worded"] = sorted(s for s, subj, body in m.execute("select sha, subject, body from body")
                                   if is_fix_message((subj or "") + "\n" + (body or "")))
        m.close()
    a.out.write_text(json.dumps(out) + "\n")
    print(f"{r}: probe written, {len(files)} universe files, {len(rows)} scanned files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
