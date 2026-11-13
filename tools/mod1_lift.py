#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""MOD-1's per-repo measurement, as fixed by Amendment 3 of docs/moderator_registration.md.

    python tools/mod1_lift.py --repo NAME [--out docs/mod1/lift_NAME.json]

lift = AUC(in_degree) - AUC(loc) over the files that CAN be positive, cascade label, one snapshot at the cut.

What Amendment 3 changed from struct_null.py, each because an independent review showed the old rule moved the
sign by itself:

  universe   only the repo's unit files (its language, not test / vendored / doc / example / generated) -- the
             same rule the history uses to record a touch. Docs, tests and other languages can never be fixed
             here, mostly have no callers, and so handed in-degree credit for telling source from non-source.
  merges     kept where the history made the merge the labelled unit (first-parent walk); dropping them threw
             away most of a merge-workflow repo's commits, and those repos are mostly young.
  label      the full cascade, with reverts / fix references / CVEs read from a body harvest that exists for
             every repo and saw the merges (pilot/meta_mod1), not only for the earlier eleven.
  checks     scan completeness and call coverage are read from structure BEFORE any outcome is looked at, and
             each failure has its own stated reason.
"""
from __future__ import annotations

import argparse, datetime as dt, json, sqlite3, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import laws_units as U  # noqa: E402
from _engine import POOL_DIR  # noqa: E402
from hist_replicate import auc, boot_ci, CUT_Q, WINDOW_DAYS, MIN_POSITIVES  # noqa: E402
from label_cascade import tiers_for  # noqa: E402

STUDY = Path("/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot")
META = STUDY / "meta_mod1"
FIX_TIERS = ("T1_revert", "T2_fixref", "T3_cve", "T4_keyword")
MIN_COMPLETE = 0.90   # unit files in the scan / unit files in the git tree at the snapshot
C_FAMILY = ("c", "cpp", "zig", "fortran")


def ro(p: Path):
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True)


def frame(repo: str) -> dict:
    """everything the history alone decides: language, unit, cut, window, age"""
    h = ro(STUDY / "history" / f"{repo}.db")
    meta = dict(h.execute("select key, value from meta"))
    merge_units = meta.get("unit", "").startswith("first-parent")
    where = "bot=0" + ("" if merge_units else " and merge=0")
    cts = [r[0] for r in h.execute(f"select ct from commit_ where {where} order by ct")]
    every = [r[0] for r in h.execute("select ct from commit_ order by ct")]
    h.close()
    cut = cts[int(len(cts) * CUT_Q)]
    end = cut + WINDOW_DAYS * 86400
    p1 = every[int(len(every) * 0.01)]  # the 1st-percentile commit: immune to one imported or joke commit
    lang = meta["language"]
    return {"language": lang, "langs": ("c", "cpp") if meta.get("units") == "c+cpp" else (lang,),
            "family": "C" if lang in C_FAMILY else "managed", "merge_units": merge_units, "where": where,
            "usable_commits": len(cts), "cut": cut, "end": end,
            "window_days": round((min(end, every[-1]) - cut) / 86400, 1),
            "start_year": dt.datetime.fromtimestamp(p1, dt.timezone.utc).year,
            "age_at_cut": round((cut - p1) / 31557600, 2)}


def measure(repo: str) -> dict:
    out = {"repo": repo, "status": "ok"}
    if not (STUDY / "history" / f"{repo}.db").exists():
        return {**out, "status": "unprepared", "why": "no history"}
    f = frame(repo)
    out.update({k: v for k, v in f.items() if k not in ("where", "langs")})
    ex = U.Excluder()

    def unit(path: str) -> bool:
        return U.language_of(path) in f["langs"] and ex.why(path) is None

    db = STUDY / "dbs" / f"{repo}.db"
    if not db.exists():
        return {**out, "status": "unprepared", "why": "no scan"}
    w = ro(db)
    best, sha = None, None
    for c, d in w.execute("select commit_hash, date from snap where rc=0"):
        try:
            e = dt.datetime.fromisoformat(d.replace("Z", "+00:00")).timestamp()
        except Exception:
            continue
        if best is None or abs(e - f["cut"]) < best:
            best, sha = abs(e - f["cut"]), c
    if not sha:
        w.close()
        return {**out, "status": "unprepared", "why": "no scanned snapshot"}
    out["snapshot"], out["snapshot_offset_days"] = sha, round(best / 86400, 1)
    loc, fid2path, scanned_units = {}, {}, 0
    for fid, path, l, gen in w.execute("select id, path, total_loc, generated from file where commit_hash=?", (sha,)):
        if not unit(path):
            continue
        scanned_units += 1
        if l and not gen:
            loc[path] = float(l)
            fid2path[fid] = path
    func2path = {}
    for uid, fid in w.execute("select id, file_id from func where commit_hash=?", (sha,)):
        if fid in fid2path:
            func2path[uid] = fid2path[fid]
    indeg, edges = {}, 0
    for (dst,) in w.execute("select dst from edge where commit_hash=?", (sha,)):
        p = func2path.get(dst)
        if p:
            indeg[p] = indeg.get(p, 0) + 1
            edges += 1
    w.close()
    # --- structural checks, decided before any outcome is read
    tree = subprocess.run(["git", "-C", str(POOL_DIR / repo), "ls-tree", "-r", "--name-only", sha],
                          capture_output=True, text=True, timeout=600).stdout.splitlines()
    tree_units = sum(1 for p in tree if unit(p))
    out.update({"unit_files": len(loc), "tree_unit_files": tree_units, "inbound_edges": edges,
                "complete": round(scanned_units / tree_units, 3) if tree_units else 0.0,
                "call_coverage": round(sum(1 for p in loc if indeg.get(p)) / len(loc), 3) if loc else 0.0})
    if not tree_units or out["complete"] < MIN_COMPLETE:
        return {**out, "status": "scan_incomplete",
                "why": f"scan holds {scanned_units} of {tree_units} unit files in the tree"}
    if not loc or edges * 10 < len(loc):
        return {**out, "status": "no_calls", "why": f"{edges} inbound edges over {len(loc)} unit files"}
    if not (META / f"{repo}.db").exists():
        return {**out, "status": "no_meta", "why": "no commit-body harvest, so the cascade would be keyword-only"}
    # --- outcome
    tier, _ = tiers_for(repo, f["merge_units"], META)
    keep = {s for s, t in tier.items() if t in FIX_TIERS}
    h = ro(STUDY / "history" / f"{repo}.db")
    post = {p for p, s in h.execute(
        f"select t.path, t.sha from touch t join commit_ c on c.sha=t.sha where c.{f['where'].replace(' and ', ' and c.')} "
        "and c.ct>? and c.ct<=?", (f["cut"], f["end"])) if s in keep}
    h.close()
    paths = sorted(loc)
    y = [1 if p in post else 0 for p in paths]
    out["positives"] = sum(y)
    if out["positives"] < MIN_POSITIVES:
        return {**out, "status": "under_floor", "why": f"{out['positives']} positives, floor {MIN_POSITIVES}"}
    L = [loc[p] for p in paths]
    D = [float(indeg.get(p, 0)) for p in paths]
    a_loc, a_deg = auc(L, y), auc(D, y)
    lo, hi = boot_ci(lambda ix: (auc([D[i] for i in ix], [y[i] for i in ix]) or 0)
                     - (auc([L[i] for i in ix], [y[i] for i in ix]) or 0), len(paths), reps=600)
    out.update({"auc_loc": a_loc, "auc_in_degree": a_deg, "lift": a_deg - a_loc, "ci95": [lo, hi]})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    r = measure(a.repo)
    print(json.dumps(r, indent=1))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(r, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
