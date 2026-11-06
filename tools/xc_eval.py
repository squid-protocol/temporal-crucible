#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""XC-H1..H6: do extrinsic / latent / regression fixes answer to different predictors?
(docs/xc_hypotheses.md, registered 2026-11-06; labels from tools/xc_harvest.py, rules v2)

Per quarterly snapshot t, C files; positive for class K = touched by a class-K commit in (t, t+180 d].
lift(P, K) = recall@20(P, K) - max(recall@20(LOC-desc, K), recall@20(LOC-asc, K)).

    python tools/xc_eval.py --repo curl
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from ea_eval import recall_at  # noqa: E402

SEED, ITERS, DAY, WINDOW = 2982, 5000, 86400, 180
ALPHA = 0.01 / 6
MIN_UNITS, EQUIV = 20, 0.02
CLASSES = ("extrinsic", "latent", "regression", "other-fix")
WT = pathlib.Path(os.environ.get("TC_WORKTREES", "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees"))
DBS = {"curl": WT / "forward-asof/dbs/curl_out/curl_galaxy_master.db",
       "ndpi": WT / "forward-asof/dbs/ndpi_out/ndpi_galaxy_master.db",
       "openssl": WT / "frec/dbs/openssl_out/openssl_galaxy_master.db"}
PREDICTORS = ("LOC-desc", "LOC-asc", "change_entropy", "raw_churn_freq", "prior same-class", "prior other-class",
              "external includes", "flux density")


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def suffixes(paths):
    out = set()
    for p in paths:
        parts = p.split("/")
        for i in range(len(parts)):
            out.add("/".join(parts[i:]))
    return out


def test(x, rng, iters=ITERS):
    """(mean, one-sided lo at ALPHA, 90% CI, verdict) for a vector of per-snapshot differences."""
    n = len(x)
    if n < MIN_UNITS:
        return {"n": n, "mean": float(x.mean()) if n else float("nan"), "verdict": "not evaluable"}
    b = np.array([x[rng.integers(0, n, n)].mean() for _ in range(iters)])
    lo, ci = float(np.quantile(b, ALPHA)), (float(np.quantile(b, 0.05)), float(np.quantile(b, 0.95)))
    v = ("SUPPORTED" if x.mean() > 0 and lo > 0 else
         "replicated null (equivalence)" if -EQUIV < ci[0] and ci[1] < EQUIV else "not supported (inconclusive)")
    return {"n": n, "mean": float(x.mean()), "lo": lo, "ci90": ci, "verdict": v}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    a = ap.parse_args()
    t0 = time.time()
    repo = POOL_DIR / a.repo
    snaps = [s for s in json.loads((REPO_ROOT / "walks" / f"{a.repo}_quarterly.json").read_text())["revisions"]
             if s.get("status", "ok") == "ok"]
    for s in snaps:
        s["ct"] = int(_git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())
    snaps.sort(key=lambda s: s["ct"])
    xc = json.loads((REPO_ROOT / "events" / f"{a.repo}_xc.json").read_text())
    events = xc["events"]

    con = sqlite3.connect(f"file:{DBS[a.repo]}?mode=ro", uri=True)
    per = []
    for s in snaps:
        rows = con.execute("SELECT file_path, total_loc, change_entropy, raw_churn_freq, raw_imports, mitigation_telemetry "
                           "FROM file_data WHERE commit_hash=? AND language='c'", (s["sha"],)).fetchall()
        if not rows:
            continue
        allpaths = [r[0] for r in con.execute("SELECT file_path FROM file_data WHERE commit_hash=?", (s["sha"],))]
        suf = suffixes(allpaths)
        paths = [r[0] for r in rows]
        loc = np.array([float(r[1] or 0) for r in rows])
        if loc.sum() == 0:
            continue
        ext = np.array([float(len({i for i in json.loads(r[4] or "[]") if i not in suf})) for r in rows])
        flux = np.array([float((json.loads(r[5]) if r[5] else {}).get("amplified_cascading_flux", 0) or 0) for r in rows])
        prior = {k: defaultdict(int) for k in CLASSES}
        pos = {k: set() for k in CLASSES}
        for e in events:
            if e["ct"] <= s["ct"]:
                for f in e["c_files"]:
                    prior[e["class"]][f] += 1
            elif e["ct"] <= s["ct"] + WINDOW * DAY:
                pos[e["class"]].update(e["c_files"])
        base_sc = {"LOC-desc": loc, "LOC-asc": -loc,
                   "change_entropy": np.array([float(r[2] or 0) for r in rows]),
                   "raw_churn_freq": np.array([float(r[3] or 0) for r in rows]),
                   "external includes": ext, "flux density": flux / np.maximum(loc, 1.0)}
        rec = {}
        for k in CLASSES:
            y = np.array([1.0 if p in pos[k] else 0.0 for p in paths])
            if y.sum() == 0:
                continue
            sc = dict(base_sc)
            sc["prior same-class"] = np.array([float(prior[k][p]) for p in paths])
            sc["prior other-class"] = np.array([float(sum(prior[j][p] for j in CLASSES if j != k)) for p in paths])
            rec[k] = {n: recall_at(v, loc, paths, y, 0.20) for n, v in sc.items()}
            rec[k]["_pos"] = int(y.sum())
        per.append({"ref": s["ref"], "rec": rec})
    con.close()

    def lift(p, pred, k):
        r = p["rec"][k]
        return r[pred] - max(r["LOC-desc"], r["LOC-asc"])

    def scored(*ks):
        return [p for p in per if all(k in p["rec"] for k in ks)]

    spawn = iter(np.random.SeedSequence(SEED).spawn(8))
    claims = {
        "XC-H1": ("change entropy beats size on regressions",
                  np.array([lift(p, "change_entropy", "regression") for p in scored("regression")])),
        "XC-H2": ("…more than on latent (CVE) fixes",
                  np.array([lift(p, "change_entropy", "regression") - lift(p, "change_entropy", "latent")
                            for p in scored("regression", "latent")])),
        "XC-H3": ("external includes beat size on extrinsic fixes",
                  np.array([lift(p, "external includes", "extrinsic") for p in scored("extrinsic")])),
        "XC-H4": ("…more than on regressions",
                  np.array([lift(p, "external includes", "extrinsic") - lift(p, "external includes", "regression")
                            for p in scored("extrinsic", "regression")])),
        "XC-H5": ("prior regressions beat prior other fixes on regressions",
                  np.array([p["rec"]["regression"]["prior same-class"] - p["rec"]["regression"]["prior other-class"]
                            for p in scored("regression")])),
        "XC-H6": ("prior extrinsic beat prior other fixes on extrinsic",
                  np.array([p["rec"]["extrinsic"]["prior same-class"] - p["rec"]["extrinsic"]["prior other-class"]
                            for p in scored("extrinsic")])),
    }
    res = {c: {"what": w, **test(x, np.random.default_rng(next(spawn)))} for c, (w, x) in claims.items()}

    L = [f"# XC-H1..H6 — fix classes vs predictors: {a.repo} (SCORED)", "",
         f"- labels `events/{a.repo}_xc.json` (rules v2): " + ", ".join(f"{k} {xc['counts'].get(k, 0)}" for k in CLASSES) +
         f"; excluded sweeps {xc['counts'].get('sweep (> 50 C files)', 0)}",
         f"- {len(per)} quarterly snapshots; scored per class: " +
         ", ".join(f"{k} {len(scored(k))}" for k in CLASSES) + f"; window (t, t+{WINDOW} d]", "",
         f"## Verdicts (α = 0.01/6 = {ALPHA:.5f} one-sided; lift over the snapshot's stronger LOC baseline)", "",
         "| claim | what | n | mean | lo | 90% CI | verdict |", "|---|---|---:|---:|---:|---|---|"]
    for c, r in res.items():
        ci = f"[{r['ci90'][0]:+.3f}, {r['ci90'][1]:+.3f}]" if "ci90" in r else "—"
        L.append(f"| **{c}** | {r['what']} | {r['n']} | {r['mean']:+.3f} | {r.get('lo', float('nan')):+.3f} | {ci} | **{r['verdict']}** |")
    L += ["", "## Descriptive: mean recall@20 by predictor × class", "",
          "| predictor | " + " | ".join(CLASSES) + " |", "|---|" + "---:|" * len(CLASSES)]
    for pr in PREDICTORS:
        cells = []
        for k in CLASSES:
            s_ = scored(k)
            cells.append(f"{np.mean([p['rec'][k][pr] for p in s_]):.3f}" if s_ else "—")
        L.append(f"| {pr} | " + " | ".join(cells) + " |")
    L += ["", "Lift over the stronger LOC baseline (same table minus max(LOC-desc, LOC-asc) per snapshot):", "",
          "| predictor | " + " | ".join(CLASSES) + " |", "|---|" + "---:|" * len(CLASSES)]
    for pr in PREDICTORS[2:]:
        cells = []
        for k in CLASSES:
            s_ = scored(k)
            cells.append(f"{np.mean([lift(p, pr, k) for p in s_]):+.3f}" if s_ else "—")
        L.append(f"| {pr} | " + " | ".join(cells) + " |")
    lags = [int(e["why"].split("(")[1].split(" d")[0]) for e in events if e["class"] == "regression" and "references" in e["why"]]
    if lags:
        L += ["", f"Regression lag (SHA-referenced regressions, n={len(lags)}): median {np.median(lags):.0f} d, "
              f"p75 {np.quantile(lags, 0.75):.0f} d, share same-day {np.mean(np.array(lags) == 0):.0%}."]
    L += ["", f"Runtime {time.time() - t0:.0f}s · bootstrap {ITERS} rounds over snapshots, seed {SEED}."]
    out = a.out or DOCS_DIR / f"xc_{a.repo}.md"
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
