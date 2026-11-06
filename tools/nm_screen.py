#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""NM-F / NM-G: screen the engine's untested metrics against future fixes at equal size
(docs/newmetrics_hypotheses.md, registered 2026-11-06).

  file      python tools/nm_screen.py file --cache <dir>
  function  python tools/nm_screen.py function
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sqlite3
import statistics
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np
from scipy.stats import rankdata

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from ea_eval import recall_at  # noqa: E402
from exposure_delta import diff_statuses  # noqa: E402
from frec_eval import FIX_CLASSES  # noqa: E402
from signal_anatomy import hunk_lines_parent_side, parent_child  # noqa: E402
from walk_trajectories import harvest_touched_files  # noqa: E402

SEED, ITERS, DAY, OUTCOME_DAYS = 2982, 5000, 86400, 180
# the scan DBs live in the main checkout's worktrees (override with TC_WORKTREES)
WT = pathlib.Path(os.environ.get("TC_WORKTREES", "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees"))
FILE_DBS = {"curl": WT / "forward-asof/dbs/curl_out/curl_galaxy_master.db",
            "ndpi": WT / "forward-asof/dbs/ndpi_out/ndpi_galaxy_master.db",
            "openssl": WT / "frec/dbs/openssl_out/openssl_galaxy_master.db"}
FUNC_DBS = {"curl": (WT / "rescan-engine-32619e4a5/dbs/curl_out/curl_galaxy_master.db",
                     ["events/curl.json", "events/curl_bugs.json"]),
            "ndpi": (WT / "frec/dbs/ndpi_out/ndpi_galaxy_master.db", ["events/ndpi.json"])}
FAM = [f"fam_{x}" for x in ("memory cleanup guards danger concurrency connectivity io ipc time events tests docs "
                            "debt mutation dead_code credential threat ml_ai").split()]
FILE_COLS = FAM + ["rel_guard_balance", "rel_alloc_cleanup", "doc_umbrella", "wrapped_debug_prints",
                   "wrapped_memory_alloc", "wrapped_panics_and_aborts", "threat_db_sinks", "threat_api_near_db_sink"]
MITIG = ["amplified_cascading_flux", "amplified_exfiltration", "amplified_race_conditions",
         "mitigated_danger", "mitigated_memory_allocs"]
FUNC_COLS = ["func_fan_in", "func_fan_out", "func_pagerank", "is_public", "is_documented"]


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def strat_auc(x, pos, strata):
    """Pair-count-pooled AUC over within-stratum pairs (Mann-Whitney per stratum, ties 1/2)."""
    num = den = 0.0
    for s in np.unique(strata):
        m = strata == s
        y = pos[m]
        n1 = y.sum()
        n0 = len(y) - n1
        if n1 == 0 or n0 == 0:
            continue
        r = rankdata(x[m])
        num += r[y == 1].sum() - n1 * (n1 + 1) / 2
        den += n1 * n0
    return (num / den if den else np.nan), den


def equal_strata(v, k):
    r = rankdata(v, method="ordinal") - 1
    return np.minimum((r * k / len(v)).astype(int), k - 1)


def entry(values: dict[str, np.ndarray]) -> dict[str, bool]:
    return {c: (np.mean(v != 0) >= 0.05 and len(np.unique(v)) >= 3) for c, v in values.items()}


def ci(x, alpha, rng, iters=ITERS):
    n = len(x)
    b = np.array([x[rng.integers(0, n, n)].mean() for _ in range(iters)])
    return float(np.quantile(b, alpha / 2)), float(np.quantile(b, 1 - alpha / 2))


def classify(per_repo):
    signs = []
    for r in per_repo.values():
        lo, hi = r["ci"]
        signs.append(1 if lo > 0 else -1 if hi < 0 else 0)
    if all(s == signs[0] != 0 for s in signs):
        return "SIGNAL", signs[0]
    nz = [s for s in signs if s]
    if len(nz) >= len(signs) - 1 and len(set(nz)) == 1 and len(signs) > 2:
        return "LEAD", nz[0]
    return "no signal", 0


def file_screen(a):
    t0 = time.time()
    data, entered = {}, {}
    for repo_name, db in FILE_DBS.items():
        repo = POOL_DIR / repo_name
        snaps = [s for s in json.loads((REPO_ROOT / "walks" / f"{repo_name}_quarterly.json").read_text())["revisions"]
                 if s.get("status", "ok") == "ok"]
        for s in snaps:
            s["ct"] = int(_git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())
        ev = {}
        for e in json.loads((REPO_ROOT / "events" / f"{repo_name}.json").read_text())["events"]:
            if e["class"] == "security-fix" and e.get("on_master", True):
                ct = _git(repo, "show", "-s", "--format=%ct", e["sha"]).strip()
                if ct:
                    ev[e["sha"]] = {**e, "ct": int(ct)}
        ev = list(ev.values())
        touched = harvest_touched_files(repo, ev, 8, a.cache / f"arch_touch_{repo_name}.json")
        ef = {e["sha"]: set(touched[e["sha"]]["old"]) | set(touched[e["sha"]]["new"]) for e in ev if touched.get(e["sha"])}
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        snapdat = []
        for s in snaps:
            rows = con.execute(f"SELECT file_path, total_loc, mitigation_telemetry, {', '.join(FILE_COLS)} FROM file_data "
                               "WHERE commit_hash=? AND language='c'", (s["sha"],)).fetchall()
            if not rows:
                continue
            pf = set()
            for e in ev:
                if s["ct"] < e["ct"] <= s["ct"] + OUTCOME_DAYS * DAY and e["sha"] in ef:
                    pf |= ef[e["sha"]]
            vals = {c: np.array([float(r[3 + i] or 0) for r in rows]) for i, c in enumerate(FILE_COLS)}
            mt = [json.loads(r[2]) if r[2] else {} for r in rows]
            for k in MITIG:
                vals[k] = np.array([float(m.get(k, 0) or 0) for m in mt])
            snapdat.append({"paths": [r[0] for r in rows], "loc": np.array([float(r[1] or 0) for r in rows]),
                            "pos": np.array([1.0 if r[0] in pf else 0.0 for r in rows]), "vals": vals})
        con.close()
        allv = {c: np.concatenate([sd["vals"][c] for sd in snapdat]) for c in FILE_COLS + MITIG}
        entered[repo_name] = entry(allv)
        data[repo_name] = snapdat
        print(f"{repo_name}: {len(snapdat)} snapshots loaded ({time.time() - t0:.0f}s)", flush=True)
    metrics = [c for c in FILE_COLS + MITIG if all(entered[r][c] for r in FILE_DBS)]
    alpha = 0.01 / len(metrics)
    res = {}
    spawn = iter(np.random.SeedSequence(SEED).spawn(len(metrics) * len(FILE_DBS) + 1))
    for c in metrics:
        res[c] = {}
        for repo_name, snapdat in data.items():
            lifts = []
            for sd in snapdat:
                if sd["pos"].sum() == 0:
                    continue
                v, _ = strat_auc(sd["vals"][c], sd["pos"], equal_strata(sd["loc"], 10))
                if not np.isnan(v):
                    lifts.append(v - 0.5)
            x = np.array(lifts)
            res[c][repo_name] = {"mean": float(x.mean()), "ci": ci(x, alpha, np.random.default_rng(next(spawn))), "n": len(x)}
        res[c]["_verdict"] = classify({r: res[c][r] for r in FILE_DBS})
    # secondary: effort-aware for SIGNALs
    sec = {}
    for c in metrics:
        v, sgn = res[c]["_verdict"]
        if v != "SIGNAL":
            continue
        sec[c] = {}
        for repo_name, snapdat in data.items():
            d = defaultdict(list)
            for sd in snapdat:
                if sd["pos"].sum() == 0:
                    continue
                for k, sc in (("metric", sgn * sd["vals"][c]), ("LOC-desc", sd["loc"]), ("LOC-asc", -sd["loc"])):
                    d[k].append(recall_at(sc, sd["loc"], sd["paths"], sd["pos"], 0.20))
            sec[c][repo_name] = {k: float(np.mean(v_)) for k, v_ in d.items()}
    dropped = [c for c in FILE_COLS + MITIG if c not in metrics]
    L = ["# NM-F — untested file metrics vs future security fixes, at equal size (SCORED)", "",
         f"- quarterly snapshots: " + ", ".join(f"{r} {len(d)}" for r, d in data.items()) +
         "; strata = 10 equal-count `total_loc` bins per snapshot",
         f"- entered the screen: **{len(metrics)}** metrics → two-sided α = 0.01/{len(metrics)} = {alpha:.5f}",
         f"- failed the entry rule (≥ 5% non-zero and ≥ 3 distinct values in every repo): {', '.join(dropped)}", "",
         "Lift = size-stratified AUC − 0.5 (positive = higher value, more fixes at equal size). "
         "Brackets: the Bonferroni CI.", "",
         "| metric | curl | nDPI | openssl | verdict |", "|---|---|---|---|---|"]
    order = sorted(metrics, key=lambda c: (res[c]["_verdict"][0] != "SIGNAL", res[c]["_verdict"][0] != "LEAD",
                                           -abs(np.mean([res[c][r]["mean"] for r in FILE_DBS]))))
    for c in order:
        cells = [f"{res[c][r]['mean']:+.3f} [{res[c][r]['ci'][0]:+.3f}, {res[c][r]['ci'][1]:+.3f}]" for r in FILE_DBS]
        v, sgn = res[c]["_verdict"]
        lab = f"**{v}** ({'higher = riskier' if sgn > 0 else 'lower = riskier'})" if sgn else v
        L.append(f"| `{c}` | " + " | ".join(cells) + f" | {lab} |")
    if sec:
        L += ["", "## Secondary: effort-aware recall@20 for SIGNALs (descriptive)", "",
              "| metric | repo | metric (signal direction) | LOC-desc | LOC-asc |", "|---|---|---:|---:|---:|"]
        for c, rr in sec.items():
            for r, d in rr.items():
                L.append(f"| `{c}` | {r} | {d['metric']:.3f} | {d['LOC-desc']:.3f} | {d['LOC-asc']:.3f} |")
    L += ["", f"Runtime {time.time() - t0:.0f}s · bootstrap {ITERS} rounds over snapshots, seed {SEED}."]
    (a.out or DOCS_DIR / "nm_file_screen.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def function_screen(a):
    t0 = time.time()
    data = {}
    for repo_name, (db, evf) in FUNC_DBS.items():
        repo = POOL_DIR / repo_name
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        raw = {}
        for f in evf:
            for e in json.loads((REPO_ROOT / f).read_text())["events"]:
                if e["class"] in FIX_CLASSES and e["sha"] not in raw:
                    raw[e["sha"]] = e
        events = []
        for sha, e in raw.items():
            ct = _git(repo, "show", "-s", "--format=%ct", sha).strip()
            if ct:
                events.append({**e, "ct": int(ct)})
        events.sort(key=lambda e: (e["ct"], e["sha"]))
        med = statistics.median(e["ct"] for e in events)
        scored = []
        for e in events:
            if e["ct"] <= med:
                continue
            parent, child = parent_child(repo, e["sha"])
            if parent is None or not con.execute("SELECT 1 FROM repo_data WHERE commit_hash=?", (parent,)).fetchone():
                continue
            try:
                statuses = diff_statuses(repo, parent, child)
            except subprocess.CalledProcessError:
                continue
            cands = []
            for path, st in statuses.items():
                if st["status"] != "touched" or not st["old_path"]:
                    continue
                old = st["old_path"]
                rows = con.execute(
                    f"SELECT f.func_name, f.start_line, f.loc, {', '.join('f.' + c for c in FUNC_COLS)} FROM function_data f "
                    "JOIN file_data fd ON f.file_id = fd.id WHERE fd.commit_hash = ? AND fd.file_path = ? "
                    "AND fd.language = 'c'", (parent, old)).fetchall()
                rows = [r for r in rows if r[1] is not None and r[2] is not None and r[0]]
                if len(rows) < 2:
                    continue
                changed = hunk_lines_parent_side(repo, parent, child, old)
                for r in rows:
                    hit = any(ln in changed for ln in range(r[1], r[1] + max(r[2], 1)))
                    cands.append((r[2], hit, *[float(x or 0) for x in r[3:]]))
            if cands:
                arr = np.array(cands, dtype=float)
                if 0 < arr[:, 1].sum() < len(arr):
                    scored.append(arr)
        con.close()
        data[repo_name] = scored
        print(f"{repo_name}: {len(scored)} events ({time.time() - t0:.0f}s)", flush=True)
    entered = {r: entry({c: np.concatenate([ev[:, 2 + i] for ev in data[r]]) for i, c in enumerate(FUNC_COLS)})
               for r in data}
    metrics = [c for c in FUNC_COLS if all(entered[r][c] for r in data)]
    alpha = 0.01 / len(metrics)
    spawn = iter(np.random.SeedSequence(SEED).spawn(len(metrics) * len(data) + 1))
    res = {}
    for c in metrics:
        i = 2 + FUNC_COLS.index(c)
        res[c] = {}
        for r, evs in data.items():
            lifts = []
            for ev in evs:
                v, den = strat_auc(ev[:, i], ev[:, 1], equal_strata(ev[:, 0], 3))
                if den > 0:
                    lifts.append(v - 0.5)
            x = np.array(lifts)
            res[c][r] = {"mean": float(x.mean()), "ci": ci(x, alpha, np.random.default_rng(next(spawn))), "n": len(x)}
        res[c]["_verdict"] = classify({r: res[c][r] for r in data})
    L = ["# NM-G — untested function metrics vs which function a fix touches, at equal size (SCORED)", "",
         "- FREC's events and candidates; scored = later-half events; strata = `loc` tertiles within each event",
         "- events: " + ", ".join(f"{r} {len(d)}" for r, d in data.items()) +
         f"; entered: **{len(metrics)}** → two-sided α = 0.01/{len(metrics)} = {alpha:.4f}; "
         f"failed entry: {', '.join(c for c in FUNC_COLS if c not in metrics) or 'none'}", "",
         "| metric | curl lift [CI] (n events) | nDPI lift [CI] (n) | verdict |", "|---|---|---|---|"]
    for c in metrics:
        cells = [f"{res[c][r]['mean']:+.3f} [{res[c][r]['ci'][0]:+.3f}, {res[c][r]['ci'][1]:+.3f}] ({res[c][r]['n']})" for r in data]
        v, sgn = res[c]["_verdict"]
        lab = f"**{v}** ({'higher = more often fixed' if sgn > 0 else 'lower = more often fixed'})" if sgn else v
        L.append(f"| `{c}` | " + " | ".join(cells) + f" | {lab} |")
    L += ["", f"Runtime {time.time() - t0:.0f}s · bootstrap {ITERS} rounds over events, seed {SEED}."]
    (a.out or DOCS_DIR / "nm_function_screen.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("which", choices=["file", "function"])
    ap.add_argument("--cache", type=pathlib.Path, default=pathlib.Path("."))
    ap.add_argument("--out", type=pathlib.Path, default=None)
    a = ap.parse_args()
    (file_screen if a.which == "file" else function_screen)(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
