#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""ARCH-Z1..Z4: does archetype atypicality mark fixed files? (docs/archetype_hypotheses.md)

Data/unit/outcome as ARCH-U1..U3. Scores read at t: zc = composition_file_z, dc = nearest
file-cluster centroid distance (min of file_fingerprint). Z1/Z2: recall@20 vs both LOC orders.
Z3/Z4: size-stratified AUC (pairs within the same ABS_CUTS LOC band) - 0.5.

    python tools/arch_z.py --repo curl --db <db> --events events/curl.json --cache <dir>
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import sys
import time

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from arch_useful import ALPHA, DAY, EQUIV, ITERS, MIN_UNITS, OUTCOME_DAYS, SEED, _git, boot  # noqa: E402
from centrality_bands import ABS_CUTS, absolute_bands  # noqa: E402
from ea_eval import recall_at  # noqa: E402
from frec_eval import auc  # noqa: E402
from walk_trajectories import harvest_touched_files  # noqa: E402


def strat_auc(score, pos, band):
    """Pair-count-weighted AUC over pairs within the same band (ties = 1/2)."""
    num = den = 0.0
    for b in np.unique(band):
        m = band == b
        p, n = score[m & (pos == 1)], score[m & (pos == 0)]
        if len(p) and len(n):
            num += (p[:, None] > n[None, :]).sum() + 0.5 * (p[:, None] == n[None, :]).sum()
            den += len(p) * len(n)
    return num / den if den else float("nan")


def nearest(fp):
    try:
        return min(json.loads(fp).values())
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--db", required=True, type=pathlib.Path)
    ap.add_argument("--events", nargs="+", required=True, type=pathlib.Path)
    ap.add_argument("--iters", type=int, default=ITERS)
    ap.add_argument("--cache", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    a = ap.parse_args()
    t0 = time.time()
    repo = POOL_DIR / a.repo
    snaps = [s for s in json.loads((REPO_ROOT / "walks" / f"{a.repo}_quarterly.json").read_text())["revisions"]
             if s.get("status", "ok") == "ok"]
    for s in snaps:
        s["ct"] = int(_git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())
    snaps.sort(key=lambda s: s["ct"])
    events = {}
    for f in a.events:
        for e in json.loads(f.read_text())["events"]:
            if e["class"] == "security-fix" and e.get("on_master", True) and e["sha"] not in events:
                ct = _git(repo, "show", "-s", "--format=%ct", e["sha"]).strip()
                if ct:
                    events[e["sha"]] = {**e, "ct": int(ct)}
    events = list(events.values())
    touched = harvest_touched_files(repo, events, 8, a.cache / f"arch_touch_{a.repo}.json")
    efiles = {e["sha"]: set(touched[e["sha"]]["old"]) | set(touched[e["sha"]]["new"]) for e in events if touched.get(e["sha"])}

    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    per, pooled = [], {"zc": [], "dc": [], "loc": [], "pos": []}
    for s in snaps:
        rs = con.execute("SELECT file_path, total_loc, composition_file_z, file_fingerprint FROM file_data "
                         "WHERE commit_hash=? AND language='c'", (s["sha"],)).fetchall()
        if not rs:
            continue
        pf = set()
        for e in events:
            if s["ct"] < e["ct"] <= s["ct"] + OUTCOME_DAYS * DAY and e["sha"] in efiles:
                pf |= efiles[e["sha"]]
        pos = np.array([1.0 if r[0] in pf else 0.0 for r in rs])
        loc = np.array([float(r[1] or 0) for r in rs])
        if pos.sum() == 0 or loc.sum() == 0:
            continue
        paths = [r[0] for r in rs]
        sc = {"zc": np.array([float(r[2] or 0) for r in rs]), "dc": np.array([nearest(r[3]) for r in rs])}
        band = np.array(absolute_bands(loc.tolist(), ABS_CUTS))
        rec = {k: recall_at(v, loc, paths, pos, 0.20) for k, v in {**sc, "LOC-desc": loc, "LOC-asc": -loc}.items()}
        per.append({"ref": s["ref"], "rec": rec,
                    "sauc": {k: strat_auc(v, pos, band) for k, v in sc.items()},
                    "sauc_neg": {k: strat_auc(-v, pos, band) for k, v in sc.items()},
                    "auc": {k: auc(v, pos) for k, v in sc.items()}})
        for k in ("zc", "dc"):
            pooled[k].append(sc[k])
        pooled["loc"].append(loc)
        pooled["pos"].append(pos)
    con.close()

    n = len(per)
    spawn = iter(np.random.SeedSequence(SEED).spawn(16))
    res = {}
    for claim, k in (("ARCH-Z1", "zc"), ("ARCH-Z2", "dc")):
        out = {}
        for base in ("LOC-desc", "LOC-asc"):
            x = np.array([p["rec"][k] - p["rec"][base] for p in per])
            rng = np.random.default_rng(next(spawn))
            lo, ci = boot(x, rng, a.iters) if n >= MIN_UNITS else (float("nan"), (float("nan"),) * 2)
            out[base] = {"mean": float(x.mean()), "lo": lo, "ci90": ci}
        if n < MIN_UNITS:
            v = "not evaluable"
        elif all(out[b]["mean"] > 0 and out[b]["lo"] > 0 for b in out):
            v = "SUPPORTED"
        else:
            stronger = max(out, key=lambda b: np.mean([p["rec"][b] for p in per]))
            c = out[stronger]["ci90"]
            v = "replicated null (equivalence)" if -EQUIV < c[0] and c[1] < EQUIV else "not supported (inconclusive)"
        res[claim] = {"vs": out, "verdict": v}
    for claim, k in (("ARCH-Z3", "zc"), ("ARCH-Z4", "dc")):
        x = np.array([p["sauc"][k] - 0.5 for p in per if not np.isnan(p["sauc"][k])])
        rng = np.random.default_rng(next(spawn))
        if len(x) >= MIN_UNITS:
            lo, ci = boot(x, rng, a.iters)
            v = ("SUPPORTED" if x.mean() > 0 and lo > 0 else
                 "replicated null (equivalence)" if -EQUIV < ci[0] and ci[1] < EQUIV else "not supported (inconclusive)")
        else:
            lo, ci, v = float("nan"), (float("nan"),) * 2, "not evaluable"
        res[claim] = {"mean": float(x.mean()) if len(x) else float("nan"), "lo": lo, "ci90": ci, "verdict": v}

    allloc = np.concatenate(pooled["loc"])
    allpos = np.concatenate(pooled["pos"])

    def mean(f):
        v = [f(p) for p in per]
        v = [x for x in v if not np.isnan(x)]
        return float(np.mean(v)) if v else float("nan")

    L = [f"# ARCH-Z1..Z4 — archetype atypicality: {a.repo} (SCORED)", "",
         f"- DB `{a.db}` · {len(snaps)} quarterly snapshots · scored: **{n}** · {len(events)} on-master security fixes, "
         f"window (t, t+{OUTCOME_DAYS} d]", "",
         "| ranking | mean recall@20 |", "|---|---:|"]
    for k, lab in (("LOC-desc", "LOC-desc"), ("LOC-asc", "LOC-asc"), ("zc", "composition fit z"), ("dc", "file-cluster distance")):
        L.append(f"| {lab} | {mean(lambda p, k=k: p['rec'][k]):.3f} |")
    L += ["", f"| claim | vs LOC-desc mean [lo] | vs LOC-asc mean [lo] | verdict |", "|---|---|---|---|"]
    for c in ("ARCH-Z1", "ARCH-Z2"):
        d, s_ = res[c]["vs"]["LOC-desc"], res[c]["vs"]["LOC-asc"]
        L.append(f"| **{c}** | {d['mean']:+.3f} [{d['lo']:+.3f}] | {s_['mean']:+.3f} [{s_['lo']:+.3f}] | **{res[c]['verdict']}** |")
    L += ["", "| claim | size-stratified AUC − 0.5 | lo | 90% CI | verdict |", "|---|---:|---:|---|---|"]
    for c in ("ARCH-Z3", "ARCH-Z4"):
        r = res[c]
        L.append(f"| **{c}** | {r['mean']:+.4f} | {r['lo']:+.4f} | [{r['ci90'][0]:+.4f}, {r['ci90'][1]:+.4f}] | **{r['verdict']}** |")
    L += ["", "## Secondary (descriptive / exploratory)", ""]
    for k, lab in (("zc", "composition fit z"), ("dc", "file-cluster distance")):
        allv = np.concatenate(pooled[k])
        rho = spearmanr(allv, allloc).statistic
        L.append(f"- {lab}: Spearman ρ with total_loc **{rho:+.3f}**; mean raw AUC {mean(lambda p, k=k: p['auc'][k]):.3f}; "
                 f"size-stratified AUC {mean(lambda p, k=k: p['sauc'][k]):.3f} (sign flipped, i.e. *typical* first: "
                 f"{mean(lambda p, k=k: p['sauc_neg'][k]):.3f})")
    L += ["", f"Pooled rows {len(allpos):,}, positives {int(allpos.sum()):,}. Runtime {time.time() - t0:.0f}s · "
          f"bootstrap {a.iters} rounds, seed {SEED}, α = {ALPHA}."]
    out = a.out or DOCS_DIR / f"arch_z_{a.repo}.md"
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
