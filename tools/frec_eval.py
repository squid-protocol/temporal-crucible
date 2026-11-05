#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""FREC-H1 / FREC-H2: function-grain recidivism (tc#28).

Implements the registration in docs/HYPOTHESES.md (2026-11-05) verbatim:

  * events: the repo's fix-class events, processed in committer-time order;
  * candidates: functions (start_line, loc) in each touched C file at the
    event's parent, files with >= 2 functions; positive = span overlaps the
    parent-side changed lines (signal_anatomy's pass-2 mapping);
  * prior(f, e): earlier events (strictly earlier committer time) whose
    positives included the same (parent-side path, function name);
  * scored: events dated after the median fix-class event date, qualifying
    with >= 1 positive and >= 1 negative;
  * lift = mean over scored events of AUC_e(score) - AUC_e(loc);
    FREC-H1 score = prior, FREC-H2 score = (prior, loc) lexicographic;
    event bootstrap 5,000 rounds, seed 2982, one-sided lower bound at 0.005.

    python tools/frec_eval.py --repo curl --events events/curl.json events/curl_bugs.json
    python tools/frec_eval.py --repo ndpi --events events/ndpi.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from itertools import groupby

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR  # noqa: E402
from exposure_delta import diff_statuses  # noqa: E402
from scan_pair import history_db, out_dir_for, resolve_repo  # noqa: E402
from signal_anatomy import hunk_lines_parent_side, parent_child  # noqa: E402

SEED = 2982
ITERS = 5000
ALPHA = 0.01 / 2
MIN_EVENTS = 20
EQUIV = 0.02
FIX_CLASSES = {"security-fix", "bugfix-fixes", "bugfix-bug", "regression"}


def auc(scores: np.ndarray, labels: np.ndarray) -> float:
    pos, neg = scores[labels == 1], scores[labels == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    gt = (pos[:, None] > neg[None, :]).sum()
    eq = (pos[:, None] == neg[None, :]).sum()
    return float((gt + 0.5 * eq) / (len(pos) * len(neg)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--events", nargs="+", required=True, type=pathlib.Path)
    ap.add_argument("--iters", type=int, default=ITERS)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    args = ap.parse_args()
    t0 = time.time()

    repo = resolve_repo(args.repo)
    out_dir = out_dir_for(repo)
    db = history_db(out_dir)
    meta_p = out_dir / "rescan_meta.json"
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)

    raw = {}
    for f in args.events:
        for e in json.loads(f.read_text())["events"]:
            if e["class"] in FIX_CLASSES and e["sha"] not in raw:
                raw[e["sha"]] = e
    events = []
    for sha, e in raw.items():
        r = subprocess.run(["git", "-C", str(repo), "show", "-s", "--format=%ct", sha],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            events.append({**e, "ct": int(r.stdout.strip())})
    events.sort(key=lambda e: (e["ct"], e["sha"]))
    median_ct = statistics.median(e["ct"] for e in events)

    # ---- per-event candidates (chronological)
    skipped = defaultdict(int)
    for e in events:
        parent, child = parent_child(repo, e["sha"])
        e["cands"] = []
        if parent is None:
            skipped["no parent"] += 1
            continue
        if not con.execute("SELECT 1 FROM repo_data WHERE commit_hash=?", (parent,)).fetchone():
            skipped["parent not scanned"] += 1
            continue
        try:
            statuses = diff_statuses(repo, parent, child)
        except subprocess.CalledProcessError:
            skipped["diff failed"] += 1
            continue
        for path, st in statuses.items():
            if st["status"] != "touched" or not st["old_path"]:
                continue
            old = st["old_path"]
            rows = con.execute(
                "SELECT f.func_name, f.start_line, f.loc FROM function_data f JOIN file_data fd ON f.file_id = fd.id "
                "WHERE fd.commit_hash = ? AND fd.file_path = ? AND fd.language = 'c'", (parent, old)).fetchall()
            rows = [r for r in rows if r[1] is not None and r[2] is not None and r[0]]
            if len(rows) < 2:
                continue
            changed = hunk_lines_parent_side(repo, parent, child, old)
            for name, start, loc in rows:
                hit = any(ln in changed for ln in range(start, start + max(loc, 1)))
                e["cands"].append({"key": (old, name), "loc": loc, "pos": hit})

    # ---- prior counts: strictly earlier events only (same-timestamp events never see each other)
    history: dict[tuple, int] = defaultdict(int)
    for _, group in groupby(events, key=lambda e: e["ct"]):
        group = list(group)
        for e in group:
            for c in e["cands"]:
                c["prior"] = history[c["key"]]
        for e in group:
            for key in {c["key"] for c in e["cands"] if c["pos"]}:
                history[key] += 1

    scored = []
    for e in events:
        if e["ct"] <= median_ct or not e["cands"]:
            continue
        lab = np.array([1 if c["pos"] else 0 for c in e["cands"]])
        if lab.sum() == 0 or lab.sum() == len(lab):
            continue
        prior = np.array([c["prior"] for c in e["cands"]], dtype=float)
        loc = np.array([c["loc"] for c in e["cands"]], dtype=float)
        lexi = prior * 1e7 + loc  # loc < 1e7: lexicographic (prior, loc)
        a_loc = auc(loc, lab)
        top = lexi == lexi.max()
        scored.append({"sha": e["sha"], "class": e["class"], "n": len(lab), "pos": int(lab.sum()),
                       "lift_h1": auc(prior, lab) - a_loc, "lift_h2": auc(lexi, lab) - a_loc,
                       "auc_prior": auc(prior, lab), "auc_lexi": auc(lexi, lab), "auc_loc": a_loc,
                       "all_zero": bool(prior.max() == 0),
                       "recall1_lexi": float(lab[top].mean()),
                       "recall1_loc": float(lab[loc == loc.max()].mean())})

    # ---- verdicts
    rng = np.random.default_rng(SEED)
    res = {}
    n = len(scored)
    for claim, key in (("FREC-H1", "lift_h1"), ("FREC-H2", "lift_h2")):
        x = np.array([s[key] for s in scored])
        if n < MIN_EVENTS:
            res[claim] = {"mean": float(x.mean()) if n else float("nan"), "verdict": "not evaluable"}
            continue
        boots = np.array([x[rng.integers(0, n, n)].mean() for _ in range(args.iters)])
        lo = float(np.quantile(boots, ALPHA))
        ci = (float(np.quantile(boots, 0.05)), float(np.quantile(boots, 0.95)))
        sup = x.mean() > 0 and lo > 0
        verdict = "SUPPORTED" if sup else ("replicated null (equivalence)" if -EQUIV < ci[0] and ci[1] < EQUIV
                                           else "not supported (inconclusive)")
        res[claim] = {"mean": float(x.mean()), "lo": lo, "ci90": ci, "verdict": verdict}

    def mean_of(k, rows):
        return float(np.mean([r[k] for r in rows])) if rows else float("nan")

    lines = [f"# FREC-H1 / FREC-H2 — {repo.name}", "",
             f"- engine `{meta.get('engine_sha', '?')}` · history `{meta.get('history', '?')}` · DB `{db.name}`",
             f"- fix-class events with a date: {len(events)}; skipped: {dict(skipped) or 'none'}; "
             f"median date {time.strftime('%Y-%m-%d', time.gmtime(median_ct))}",
             f"- scored (later half, >= 1 positive and >= 1 negative function): **{n}** events, "
             f"{sum(s['n'] for s in scored)} candidate functions, {sum(s['pos'] for s in scored)} positives", "",
             "| claim | mean lift vs function loc | one-sided lo (α=0.005) | 90% CI | verdict |",
             "|---|---:|---:|---|---|"]
    for claim in ("FREC-H1", "FREC-H2"):
        r = res[claim]
        if "lo" in r:
            lines.append(f"| **{claim}** | {r['mean']:+.4f} | {r['lo']:+.4f} | [{r['ci90'][0]:+.4f}, {r['ci90'][1]:+.4f}] | **{r['verdict']}** |")
        else:
            lines.append(f"| **{claim}** | {r['mean']:+.4f} | — | — | **{r['verdict']}** |")
    lines += ["", f"Mean within-event AUC: prior {mean_of('auc_prior', scored):.4f} · (prior, loc) {mean_of('auc_lexi', scored):.4f} · "
              f"loc {mean_of('auc_loc', scored):.4f}.", "",
              "## Exploratory (no verdicts)", "",
              f"- events where every candidate has prior = 0: {sum(s['all_zero'] for s in scored)} of {n}",
              f"- recall@1 (share of the top-ranked function(s) that are fixed): (prior, loc) {mean_of('recall1_lexi', scored):.3f} vs loc {mean_of('recall1_loc', scored):.3f}",
              "", "| class | events | mean lift H1 | mean lift H2 |", "|---|---:|---:|---:|"]
    for cls in sorted({s["class"] for s in scored}):
        rows = [s for s in scored if s["class"] == cls]
        lines.append(f"| {cls} | {len(rows)} | {mean_of('lift_h1', rows):+.4f} | {mean_of('lift_h2', rows):+.4f} |")
    lines += ["", f"Runtime {time.time() - t0:.0f}s · bootstrap {args.iters} rounds over events, seed {SEED}."]
    out = args.out or DOCS_DIR / f"frec_{repo.name}.md"
    out.write_text("\n".join(lines) + "\n")
    (out_dir / f"frec_{repo.name}.json").write_text(json.dumps({"results": res, "scored": scored}, indent=1))
    print("\n".join(lines[:12]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
