#!/usr/bin/env python3
"""EXPLORATORY (not registered; every XC label used here is already seen). Git only.

(1) Recidivism by class: per quarterly snapshot and outcome class K, recall@20 lift over the stronger LOC order for
    file history of each kind: same-class (all time / last 365 d), pooled (all fix classes), each other class.
(2) Extrinsic dynamics: monthly rate, burstiness (dispersion of the extrinsic share of fixes vs binomial), the
    persistence of the extrinsic "membrane" year over year, and the burstiest months with sample subjects.

    python tools/exploratory/xc_history_dynamics.py --repo curl --exts .c,.h
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, "tools")
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from ea_eval import recall_at  # noqa: E402
from env_eval import _git, grep_counts  # noqa: E402

DAY, WINDOW = 86400, 180


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--exts", default=".c,.h")
    a = ap.parse_args()
    repo = POOL_DIR / a.repo
    exts = tuple(a.exts.split(","))
    snaps = json.loads((REPO_ROOT / "walks" / f"{a.repo}_quarterly.json").read_text())["revisions"]
    snaps = [s for s in snaps if s.get("status", "ok") == "ok"]
    for s in snaps:
        s["ct"] = int(_git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())
    xc = json.loads((REPO_ROOT / "events" / f"{a.repo}_xc.json").read_text())
    ev = sorted(xc["events"], key=lambda e: e["ct"])
    classes = [k for k in ("latent", "extrinsic", "regression", "other-fix") if any(e["class"] == k for e in ev)]

    # ---------------- (1) recidivism matrix
    preds = [f"prior {k}" for k in classes] + ["prior pooled", "recent same (365 d)", "all-time same"]
    lift = defaultdict(lambda: defaultdict(list))
    for s in snaps:
        lines = grep_counts(repo, s["sha"], "", exts)
        if not lines:
            continue
        paths = sorted(lines)
        loc = np.array([float(lines[p]) for p in paths])
        prior = {k: Counter() for k in classes}
        recent = {k: Counter() for k in classes}
        pos = {k: set() for k in classes}
        for e in ev:
            if e["ct"] <= s["ct"]:
                prior[e["class"]].update(e["c_files"])
                if e["ct"] > s["ct"] - 365 * DAY:
                    recent[e["class"]].update(e["c_files"])
            elif e["ct"] <= s["ct"] + WINDOW * DAY:
                pos[e["class"]].update(e["c_files"])
        for k in classes:
            y = np.array([1.0 if p in pos[k] else 0.0 for p in paths])
            if y.sum() == 0:
                continue
            base = max(recall_at(loc, loc, paths, y, 0.2), recall_at(-loc, loc, paths, y, 0.2))
            sc = {f"prior {j}": np.array([float(prior[j][p]) for p in paths]) for j in classes}
            sc["prior pooled"] = sum(sc[f"prior {j}"] for j in classes)
            sc["all-time same"] = sc[f"prior {k}"]
            sc["recent same (365 d)"] = np.array([float(recent[k][p]) for p in paths])
            for n in preds:
                lift[k][n].append(recall_at(sc[n], loc, paths, y, 0.2) - base)

    L = [f"# EXPLORATORY — history dynamics by fix class: {a.repo}", "",
         "Not registered; labels are seen. Lift = recall@20 − the snapshot's stronger size order; quarterly snapshots, "
         f"window {WINDOW} d.", "", "## (1) Which history predicts which class?", "",
         "| history ↓ / outcome → | " + " | ".join(f"{k} (n)" for k in classes) + " |", "|---|" + "---:|" * len(classes)]
    for n in preds:
        L.append(f"| {n} | " + " | ".join(
            f"{np.mean(lift[k][n]):+.3f} ({len(lift[k][n])})" if lift[k][n] else "—" for k in classes) + " |")

    # ---------------- (2) extrinsic dynamics
    month = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m")  # noqa: E731
    allm = Counter(month(e["ct"]) for e in ev)
    extm = Counter(month(e["ct"]) for e in ev if e["class"] == "extrinsic")
    months = sorted(allm)
    n_t = np.array([allm[m] for m in months], dtype=float)
    x_t = np.array([extm.get(m, 0) for m in months], dtype=float)
    p = x_t.sum() / n_t.sum()
    exp_var = (n_t * p * (1 - p)).sum()
    obs_var = ((x_t - n_t * p) ** 2).sum()
    disp = obs_var / exp_var if exp_var else float("nan")
    years = sorted({m[:4] for m in months})
    L += ["", "## (2) The extrinsic change rate", "",
          f"- extrinsic commits {int(x_t.sum())} of {int(n_t.sum())} fix commits ({p:.1%}) over {len(months)} months",
          f"- **dispersion of the monthly extrinsic share vs binomial: {disp:.2f}** (1 = steady background; > 1 = bursty)", "",
          "| year | fix commits | extrinsic | share | extrinsic files touched | of which already membrane (extrinsic before) |",
          "|---|---:|---:|---:|---:|---:|"]
    seen = set()
    for y in years:
        ye = [e for e in ev if month(e["ct"]).startswith(y)]
        xe = [e for e in ye if e["class"] == "extrinsic"]
        files = {f for e in xe for f in e["c_files"]}
        old = len(files & seen)
        L.append(f"| {y} | {len(ye)} | {len(xe)} | {len(xe) / max(len(ye), 1):.1%} | {len(files)} | "
                 f"{old} ({old / max(len(files), 1):.0%}) |")
        seen |= files
    top = sorted(months, key=lambda m: -(extm.get(m, 0) - allm[m] * p))[:5]
    L += ["", "Burstiest months (extrinsic above expectation from overall fix activity), with sample subjects:", ""]
    for m in top:
        subj = [e["subject"][:70] for e in ev if e["class"] == "extrinsic" and month(e["ct"]) == m][:4]
        L.append(f"- **{m}**: {extm.get(m, 0)} extrinsic vs {allm[m] * p:.1f} expected: " + " · ".join(subj))
    out = DOCS_DIR / f"xc_history_dynamics_{a.repo}_exploratory.md"
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
