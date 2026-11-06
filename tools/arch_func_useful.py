#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""ARCH-U4: does the function archetype add to function size inside a fixed file?
(docs/archetype_hypotheses.md, registered 2026-11-06)

Candidate construction is FREC's (tools/frec_eval.py) verbatim: fix-class events in committer-time
order; candidates = functions of touched C files at the parent (files with >= 2 functions);
positive = span overlaps parent-side changed lines; scored = events after the median date with
>= 1 positive and >= 1 negative. Only the score differs:

  d_f(a) = (H_a + D * 5000) / (L_a + 5000) over strictly earlier events' candidates
  score  = loc * d_f(func_archetype);  lift = AUC_e(score) - AUC_e(loc)

    python tools/arch_func_useful.py --repo curl --db <db> --events events/curl.json events/curl_bugs.json
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
from collections import Counter, defaultdict
from itertools import groupby

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402
from exposure_delta import diff_statuses  # noqa: E402
from frec_eval import FIX_CLASSES, auc  # noqa: E402
from signal_anatomy import hunk_lines_parent_side, parent_child  # noqa: E402

SEED = 2982
ITERS = 5000
ALPHA = 0.01 / 4
MIN_EVENTS = 20
EQUIV = 0.02
PSEUDO_LOC = 5_000.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--db", required=True, type=pathlib.Path)
    ap.add_argument("--events", nargs="+", required=True, type=pathlib.Path)
    ap.add_argument("--iters", type=int, default=ITERS)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    a = ap.parse_args()
    t0 = time.time()
    repo = POOL_DIR / a.repo
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)

    raw = {}
    for f in a.events:
        for e in json.loads(f.read_text())["events"]:
            if e["class"] in FIX_CLASSES and e["sha"] not in raw:
                raw[e["sha"]] = e
    events = []
    for sha, e in raw.items():
        r = subprocess.run(["git", "-C", str(repo), "show", "-s", "--format=%ct", sha], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            events.append({**e, "ct": int(r.stdout.strip())})
    events.sort(key=lambda e: (e["ct"], e["sha"]))
    median_ct = statistics.median(e["ct"] for e in events)

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
                "SELECT f.func_name, f.start_line, f.loc, f.func_archetype FROM function_data f "
                "JOIN file_data fd ON f.file_id = fd.id "
                "WHERE fd.commit_hash = ? AND fd.file_path = ? AND fd.language = 'c'", (parent, old)).fetchall()
            rows = [r for r in rows if r[1] is not None and r[2] is not None and r[0]]
            if len(rows) < 2:
                continue
            changed = hunk_lines_parent_side(repo, parent, child, old)
            for name, start, loc, arch in rows:
                hit = any(ln in changed for ln in range(start, start + max(loc, 1)))
                e["cands"].append({"loc": loc, "arch": arch, "pos": hit})

    # strictly-earlier training tallies (same-timestamp events never see each other)
    H, L = Counter(), Counter()
    for _, group in groupby(events, key=lambda e: e["ct"]):
        group = list(group)
        th, tl = sum(H.values()), sum(L.values())
        D = th / tl if tl else 0.0
        for e in group:
            e["trained"] = th > 0
            for c in e["cands"]:
                c["d"] = (H[c["arch"]] + D * PSEUDO_LOC) / (L[c["arch"]] + PSEUDO_LOC)
        for e in group:
            for c in e["cands"]:
                H[c["arch"]] += c["pos"]
                L[c["arch"]] += c["loc"]

    scored = []
    for e in events:
        if e["ct"] <= median_ct or not e["cands"] or not e["trained"]:
            continue
        lab = np.array([1 if c["pos"] else 0 for c in e["cands"]])
        if lab.sum() == 0 or lab.sum() == len(lab):
            continue
        loc = np.array([c["loc"] for c in e["cands"]], dtype=float)
        d = np.array([c["d"] for c in e["cands"]])
        a_loc, a_s = auc(loc, lab), auc(loc * d, lab)
        scored.append({"sha": e["sha"], "class": e["class"], "n": len(lab), "pos": int(lab.sum()),
                       "lift": a_s - a_loc, "auc_loc": a_loc, "auc_arch": a_s, "auc_d": auc(d, lab)})

    n = len(scored)
    x = np.array([s["lift"] for s in scored])
    rng = np.random.default_rng(SEED)
    if n >= MIN_EVENTS:
        boots = np.array([x[rng.integers(0, n, n)].mean() for _ in range(a.iters)])
        lo = float(np.quantile(boots, ALPHA))
        ci = (float(np.quantile(boots, 0.05)), float(np.quantile(boots, 0.95)))
        verdict = ("SUPPORTED" if x.mean() > 0 and lo > 0 else
                   "replicated null (equivalence)" if -EQUIV < ci[0] and ci[1] < EQUIV else "not supported (inconclusive)")
    else:
        lo, ci, verdict = float("nan"), (float("nan"),) * 2, "not evaluable"

    tot_h, tot_l = sum(H.values()), sum(L.values())
    Dg = tot_h / tot_l if tot_l else 0.0

    def m(k, rows):
        return float(np.mean([r[k] for r in rows])) if rows else float("nan")

    out_l = [f"# ARCH-U4 — function archetype vs function size: {a.repo} (SCORED)", "",
             f"- DB `{a.db}` · fix-class events with a date: {len(events)}; skipped: {dict(skipped) or 'none'}; "
             f"median date {time.strftime('%Y-%m-%d', time.gmtime(median_ct))}",
             f"- scored (later half, trained, >= 1 positive and >= 1 negative): **{n}** events, "
             f"{sum(s['n'] for s in scored)} candidate functions, {sum(s['pos'] for s in scored)} positives", "",
             "| claim | mean AUC lift over loc | one-sided lo (α=0.0025) | 90% CI | verdict |", "|---|---:|---:|---|---|",
             f"| **ARCH-U4** | {x.mean():+.4f} | {lo:+.4f} | [{ci[0]:+.4f}, {ci[1]:+.4f}] | **{verdict}** |", "",
             f"Mean within-event AUC: loc {m('auc_loc', scored):.4f} · loc × d_f(archetype) {m('auc_arch', scored):.4f} · "
             f"d_f(archetype) alone {m('auc_d', scored):.4f}", "",
             "## Descriptive: per-line hit density by function archetype (all events' candidates)", "",
             "| archetype | candidate kLOC | hit functions | hits per kLOC | ratio to global |", "|---|---:|---:|---:|---:|"]
    for k in sorted(L, key=lambda k: -(H[k] / L[k] if L[k] else 0)):
        out_l.append(f"| {k} | {L[k] / 1000:,.1f} | {H[k]} | {1000 * H[k] / L[k] if L[k] else 0:.2f} | "
                     f"{(H[k] / L[k]) / Dg if L[k] and Dg else float('nan'):.2f} |")
    out_l += ["", "| class | events | mean lift |", "|---|---:|---:|"]
    for cls in sorted({s["class"] for s in scored}):
        rows = [s for s in scored if s["class"] == cls]
        out_l.append(f"| {cls} | {len(rows)} | {m('lift', rows):+.4f} |")
    out_l += ["", f"Runtime {time.time() - t0:.0f}s · bootstrap {a.iters} rounds over events, seed {SEED}."]
    out = a.out or DOCS_DIR / f"arch_func_useful_{a.repo}.md"
    out.write_text("\n".join(out_l) + "\n")
    print("\n".join(out_l))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
