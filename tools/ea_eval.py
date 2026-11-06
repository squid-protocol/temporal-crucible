#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""EA-H1..EA-H5: effort-aware history ranking (registered 2026-11-05, docs/HYPOTHESES.md).

Per quarterly snapshot t (as-of scan, history enabled):
  * candidates: C files; positive: touched by an on-master security-fix dated in (t, t+180 d];
  * scores: change_entropy (H1), raw_churn_freq (H2), -risk_stability (H3, recency),
    prior on-master security fixes touching the file dated <= t (H4), H4 / total_loc (H5);
  * recall@B: rank by score (ties: smaller total_loc, then path), take whole files while
    cumulative LOC <= B of the snapshot's C LOC; covered positives / positives;
  * a claim must beat BOTH baselines (LOC-desc, LOC-asc): mean per-snapshot recall@20
    difference > 0 with a one-sided snapshot-cluster bootstrap lower bound > 0 at 0.002.
The binding gates (churn reconstruction >= 0.95, HCM parity >= 0.99) and the unusable-history
exclusion are FWD's (tools/fwd_eval.py), applied before any EA statistic.

    python tools/ea_eval.py --repo openssl --events events/openssl.json --mode scored
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, REPO_ROOT  # noqa: E402
from centrality_bands import ABS_CUTS, ABS_LABELS, absolute_bands  # noqa: E402
from fwd_eval import (  # noqa: E402
    GATE_RHO, HCM_GATE_RHO, hcm_gate, ignored_revs, independent_churn_freq, load_rows, weighted_auc,
)
from scan_pair import history_db, out_dir_for, resolve_repo  # noqa: E402
from walk_trajectories import harvest_touched_files  # noqa: E402

from scipy.stats import spearmanr  # noqa: E402

SEED = 2982
ITERS = 5000
ALPHA = 0.01 / 5
OUTCOME_DAYS = 180
DAY = 86400
MIN_SNAPSHOTS = 20
EQUIV = 0.02
CLAIMS = {"EA-H1": "change_entropy", "EA-H2": "raw_churn_freq", "EA-H3": "recency",
          "EA-H4": "prior_fixes", "EA-H5": "prior_fix_density"}
BUDGETS = (0.10, 0.20, 0.30)


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def recall_at(score: np.ndarray, loc: np.ndarray, paths: list[str], pos: np.ndarray, budget: float) -> float:
    order = sorted(range(len(score)), key=lambda i: (-score[i], loc[i], paths[i]))
    cap = budget * loc.sum()
    used = cov = 0.0
    for i in order:
        if used + loc[i] > cap:
            break  # registered: whole files, taken in rank order WHILE the budget holds
        used += loc[i]
        cov += pos[i]
    return cov / pos.sum()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--events", nargs="+", required=True, type=pathlib.Path)
    ap.add_argument("--mode", choices=["scored", "exploratory"], required=True)
    ap.add_argument("--fix-classes", default="security-fix")
    ap.add_argument("--iters", type=int, default=ITERS)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    a = ap.parse_args()
    t0 = time.time()
    repo = resolve_repo(a.repo)
    out_dir = out_dir_for(repo)
    db = history_db(out_dir)
    meta = json.loads((out_dir / "rescan_meta.json").read_text())
    if meta.get("history") != "asof":
        sys.exit("registration requires as-of scans (rescan_meta history=asof)")
    snaps = json.loads((REPO_ROOT / "walks" / f"{repo.name}_quarterly.json").read_text())["revisions"]
    for s in snaps:
        s["ct"] = int(_git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())

    feats = ["raw_churn_freq", "ownership_entropy", "change_entropy", "silo_risk", "risk_stability"]
    rows, feats, missing = load_rows(db, repo.name, snaps, feats)
    if missing:
        sys.exit(f"{len(missing)} snapshots missing from the DB: {missing[:5]}")
    fi = {f: 3 + feats.index(f) for f in feats}
    by_snap = defaultdict(list)
    for r in rows:
        by_snap[r[0]].append(r)

    # unusable history (FWD amendment 1)
    unusable = {k for k in range(len(snaps)) if by_snap[k] and all(
        r[fi["risk_stability"]] == 50.0 and (r[fi["raw_churn_freq"]] or 0) == 0 for r in by_snap[k])}
    keep = [k for k in range(len(snaps)) if k not in unusable and by_snap[k]]
    excluded = [snaps[k]["ref"] for k in sorted(set(range(len(snaps))) - set(keep))]

    # binding gates
    gate = []
    for k in keep:
        s = snaps[k]
        ind = independent_churn_freq(repo, s["sha"], s["ct"], ignored_revs(repo, s["sha"]))
        pairs = [(r[fi["raw_churn_freq"]] or 0.0, ind[r[1]]) for r in by_snap[k] if r[1] in ind and ind[r[1]] > 0]
        rho = spearmanr(*zip(*pairs)).statistic if len(pairs) >= 3 else float("nan")
        gate.append({"ref": s["ref"], "n": len(pairs), "rho": rho})
    ev = [g for g in gate if g["n"] >= 3]
    gate_ok = all(g["rho"] >= GATE_RHO for g in ev)
    kept_snaps = [snaps[k] for k in keep]
    kept_by = defaultdict(list)
    for j, k in enumerate(keep):
        kept_by[j] = by_snap[k]
    hcm = hcm_gate(repo, kept_snaps, kept_by, fi["change_entropy"], out_dir / "hcmwalk_cache")
    hev = [g for g in hcm if g["n"] >= 3]
    hcm_ok = all(g["rho"] >= HCM_GATE_RHO for g in hev)
    print(f"gates: churn {sum(g['rho'] >= GATE_RHO for g in ev)}/{len(ev)} (min {min(g['rho'] for g in ev):.4f}); "
          f"HCM {sum(g['rho'] >= HCM_GATE_RHO for g in hev)}/{len(hev)} (min {min(g['rho'] for g in hev):.4f})", flush=True)

    # events: on-master fixes, dated by committer time
    classes = set(a.fix_classes.split(","))
    events = []
    for f in a.events:
        for e in json.loads(f.read_text())["events"]:
            if e["class"] in classes and e.get("on_master", True):
                ct = _git(repo, "show", "-s", "--format=%ct", e["sha"]).strip()
                if ct:
                    events.append({**e, "ct": int(ct)})
    uniq = {e["sha"]: e for e in events}
    events = list(uniq.values())
    touched = harvest_touched_files(repo, events, 8, out_dir / f"ea_touch_cache_{repo.name}.json")
    efiles = {e["sha"]: set(touched[e["sha"]]["old"]) | set(touched[e["sha"]]["new"])
              for e in events if touched.get(e["sha"])}

    per = []  # one dict per scored snapshot
    pooled = defaultdict(list)
    for j, s in enumerate(kept_snaps):
        rs = kept_by[j]
        paths = [r[1] for r in rs]
        loc = np.array([float(r[2] or 0) for r in rs])
        pos_files = set().union(*[efiles[e["sha"]] for e in events
                                  if s["ct"] < e["ct"] <= s["ct"] + OUTCOME_DAYS * DAY and e["sha"] in efiles] or [set()])
        pos = np.array([1.0 if p in pos_files else 0.0 for p in paths])
        if pos.sum() == 0 or loc.sum() == 0:
            continue
        prior = defaultdict(int)
        for e in events:
            if e["ct"] <= s["ct"] and e["sha"] in efiles:
                for p in efiles[e["sha"]]:
                    prior[p] += 1
        sc = {"change_entropy": np.array([float(r[fi["change_entropy"]] or 0) for r in rs]),
              "raw_churn_freq": np.array([float(r[fi["raw_churn_freq"]] or 0) for r in rs]),
              "recency": -np.array([float(r[fi["risk_stability"]] if r[fi["risk_stability"]] is not None else 50.0) for r in rs]),
              "prior_fixes": np.array([float(prior[p]) for p in paths]),
              "LOC-desc": loc.copy(), "LOC-asc": -loc}
        sc["prior_fix_density"] = sc["prior_fixes"] / np.maximum(loc, 1.0)
        rec = {b: {k: recall_at(v, loc, paths, pos, b) for k, v in sc.items()} for b in BUDGETS}
        per.append({"ref": s["ref"], "n": len(rs), "pos": int(pos.sum()), "recall": rec})
        for k, v in sc.items():
            pooled[k].append(v)
        pooled["_pos"].append(pos)
        pooled["_loc"].append(loc)

    # verdicts
    rng_seq = np.random.SeedSequence(SEED)
    n = len(per)
    res = {}
    for ci, (claim, feat) in enumerate(CLAIMS.items()):
        out = {}
        for bi, base in enumerate(("LOC-desc", "LOC-asc")):
            d = np.array([p["recall"][0.20][feat] - p["recall"][0.20][base] for p in per])
            if n < MIN_SNAPSHOTS:
                out[base] = {"mean": float(d.mean()) if n else float("nan")}
                continue
            rng = np.random.default_rng(rng_seq.spawn(ci * 2 + bi + 1)[-1])
            boots = np.array([d[rng.integers(0, n, n)].mean() for _ in range(a.iters)])
            out[base] = {"mean": float(d.mean()), "lo": float(np.quantile(boots, ALPHA)),
                         "ci90": (float(np.quantile(boots, 0.05)), float(np.quantile(boots, 0.95)))}
        if n < MIN_SNAPSHOTS:
            verdict = "not evaluable"
        elif not (gate_ok and (hcm_ok or feat != "change_entropy")):
            verdict = "withheld (instrument gate failed)"
        elif all(out[b]["mean"] > 0 and out[b]["lo"] > 0 for b in out):
            verdict = "SUPPORTED"
        else:
            stronger = max(out, key=lambda b: np.mean([p["recall"][0.20][b] for p in per]))
            c = out[stronger]["ci90"]
            verdict = "replicated null (equivalence)" if -EQUIV < c[0] and c[1] < EQUIV else "not supported (inconclusive)"
        res[claim] = {"feature": feat, "vs": out, "verdict": verdict}

    def mrec(k, b=0.20):
        return float(np.mean([p["recall"][b][k] for p in per])) if per else float("nan")

    allpos = np.concatenate(pooled["_pos"]) if per else np.array([])
    allloc = np.concatenate(pooled["_loc"]) if per else np.array([])
    ones = np.ones(len(allpos))
    scored = a.mode == "scored"
    L = [f"# EA-H1..EA-H5 — {repo.name} ({'SCORED' if scored else 'EXPLORATORY: no verdicts'})", ""]
    if not scored:
        L += ["**EXPLORATORY.** These features have been seen on this repo; nothing here is a verdict.", ""]
    L += [f"- engine `{meta.get('engine_sha')}` · args `{meta.get('engine_args')}` · history `{meta.get('history')}`",
          f"- snapshots: {len(snaps)} quarterly; excluded (unusable history / empty): {', '.join(excluded) or 'none'}; "
          f"scored (≥ 1 positive): **{n}**",
          f"- events: {len(events)} on-master `{a.fix_classes}` fixes; outcome window (t, t+{OUTCOME_DAYS} d]",
          f"- gates: churn reconstruction **{'PASS' if gate_ok else 'FAIL'}** ({sum(g['rho'] >= GATE_RHO for g in ev)}/{len(ev)}), "
          f"HCM parity **{'PASS' if hcm_ok else 'FAIL'}** ({sum(g['rho'] >= HCM_GATE_RHO for g in hev)}/{len(hev)})", "",
          "## Mean recall at a share of lines reviewed", "",
          "| ranking | @10% | @20% (primary) | @30% |", "|---|---:|---:|---:|"]
    for k in ("LOC-desc", "LOC-asc", *CLAIMS.values()):
        L.append(f"| {k} | {mrec(k, 0.10):.3f} | **{mrec(k):.3f}** | {mrec(k, 0.30):.3f} |")
    L += ["", "## Verdicts (recall@20 lift; must beat both baselines; α = 0.002 one-sided)", "",
          "| claim | feature | vs LOC-desc: mean [lo] | vs LOC-asc: mean [lo], 90% CI | verdict |", "|---|---|---|---|---|"]
    for claim, r in res.items():
        vd, va = r["vs"]["LOC-desc"], r["vs"]["LOC-asc"]
        f1 = f"{vd['mean']:+.3f} [{vd.get('lo', float('nan')):+.3f}]"
        f2 = f"{va['mean']:+.3f} [{va.get('lo', float('nan')):+.3f}], [{va['ci90'][0]:+.3f}, {va['ci90'][1]:+.3f}]" if "ci90" in va else f"{va['mean']:+.3f}"
        L.append(f"| **{claim}** | {r['feature']} | {f1} | {f2} | {'**' + r['verdict'] + '**' if scored else '(exploratory)'} |")
    L += ["", "## Secondary (descriptive): pooled AUC and size bands", "",
          "| ranking | pooled AUC | " + " | ".join(ABS_LABELS) + " |", "|---|---:|" + "---:|" * len(ABS_LABELS)]
    if per:
        band = np.array(absolute_bands(allloc.tolist(), ABS_CUTS))
        for k in ("LOC-desc", *CLAIMS.values()):
            v = np.concatenate(pooled[k])
            cells = []
            for b in range(len(ABS_LABELS)):
                m = band == b
                cells.append(f"{weighted_auc(v[m], allpos[m], ones[m]):.3f} ({int(allpos[m].sum())})" if allpos[m].sum() else "—")
            L.append(f"| {k} | {weighted_auc(v, allpos, ones):.3f} | " + " | ".join(cells) + " |")
    L += ["", f"Runtime {time.time() - t0:.0f}s · bootstrap {a.iters} rounds over snapshots, seed {SEED}."]
    out = a.out or DOCS_DIR / f"ea_{repo.name}.md"
    out.write_text("\n".join(L) + "\n")
    (out_dir / f"ea_{repo.name}.json").write_text(json.dumps(
        {"gate": gate, "hcm_gate": hcm, "per_snapshot": per, "results": res}, indent=1, default=float))
    print("\n".join(L[:40]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
