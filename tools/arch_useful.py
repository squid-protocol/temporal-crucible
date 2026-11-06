#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""ARCH-U1..U3: are file archetypes useful for finding fixed files? (docs/archetype_hypotheses.md)

Per quarterly snapshot t: candidates = C files; positive = touched by an on-master fix-class event
dated in (t, t+180 d] (EA's outcome). The archetype score d(a) = shrunk positives-per-line of label
a, learned only from earlier snapshots whose outcome window has closed (s + 180 d <= t).

  U1  d(file_archetype)                recall@20 vs LOC-desc AND LOC-asc
  U2  d(composition_file_archetype)    recall@20 vs both
  U3  total_loc * d(file_archetype)    AUC lift over total_loc

    python tools/arch_useful.py --repo curl --db <db> --events events/curl.json --mode scored
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import subprocess
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from ea_eval import recall_at  # noqa: E402
from frec_eval import auc  # noqa: E402
from walk_trajectories import harvest_touched_files  # noqa: E402

SEED = 2982
ITERS = 5000
ALPHA = 0.01 / 4
OUTCOME_DAYS = 180
DAY = 86400
MIN_UNITS = 20
EQUIV = 0.02
PSEUDO_LOC = 50_000.0
BUDGETS = (0.10, 0.20, 0.30)
LABELS = {"fa": "file_archetype", "ca": "composition_file_archetype"}


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def density(P: Counter, L: Counter):
    tp, tl = sum(P.values()), sum(L.values())
    D = tp / tl if tl else 0.0
    return {a: (P[a] + D * PSEUDO_LOC) / (L[a] + PSEUDO_LOC) for a in L}, D


def boot(x, rng, iters):
    n = len(x)
    b = np.array([x[rng.integers(0, n, n)].mean() for _ in range(iters)])
    return float(np.quantile(b, ALPHA)), (float(np.quantile(b, 0.05)), float(np.quantile(b, 0.95)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--db", required=True, type=pathlib.Path)
    ap.add_argument("--events", nargs="+", required=True, type=pathlib.Path)
    ap.add_argument("--fix-classes", default="security-fix")
    ap.add_argument("--mode", choices=["scored", "exploratory"], required=True)
    ap.add_argument("--iters", type=int, default=ITERS)
    ap.add_argument("--cache", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    a = ap.parse_args()
    t0 = time.time()
    repo = POOL_DIR / a.repo
    snaps = json.loads((REPO_ROOT / "walks" / f"{a.repo}_quarterly.json").read_text())["revisions"]
    snaps = [s for s in snaps if s.get("status", "ok") == "ok"]
    for s in snaps:
        s["ct"] = int(_git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())
    snaps.sort(key=lambda s: s["ct"])

    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    rows = {}
    for k, s in enumerate(snaps):
        rows[k] = con.execute("SELECT file_path, total_loc, file_archetype, composition_file_archetype FROM file_data "
                              "WHERE commit_hash=? AND language='c'", (s["sha"],)).fetchall()
    con.close()
    missing = [snaps[k]["ref"] for k in rows if not rows[k]]

    classes = set(a.fix_classes.split(","))
    events = {}
    for f in a.events:
        for e in json.loads(f.read_text())["events"]:
            if e["class"] in classes and e.get("on_master", True) and e["sha"] not in events:
                ct = _git(repo, "show", "-s", "--format=%ct", e["sha"]).strip()
                if ct:
                    events[e["sha"]] = {**e, "ct": int(ct)}
    events = list(events.values())
    a.cache.mkdir(parents=True, exist_ok=True)
    touched = harvest_touched_files(repo, events, 8, a.cache / f"arch_touch_{a.repo}.json")
    efiles = {e["sha"]: set(touched[e["sha"]]["old"]) | set(touched[e["sha"]]["new"])
              for e in events if touched.get(e["sha"])}

    # per-snapshot labels: positives + per-label tallies
    snapdat = []
    for k, s in enumerate(snaps):
        rs = rows[k]
        pos_files = set()
        for e in events:
            if s["ct"] < e["ct"] <= s["ct"] + OUTCOME_DAYS * DAY and e["sha"] in efiles:
                pos_files |= efiles[e["sha"]]
        pos = np.array([1.0 if r[0] in pos_files else 0.0 for r in rs])
        loc = np.array([float(r[1] or 0) for r in rs])
        tal = {}
        for key, col in (("fa", 2), ("ca", 3)):
            P, L = Counter(), Counter()
            for r, p, lo in zip(rs, pos, loc):
                P[r[col]] += p
                L[r[col]] += lo
            tal[key] = (P, L)
        snapdat.append({"pos": pos, "loc": loc, "tal": tal})

    per = []
    last_dens = None
    flip_rows = []  # exploratory: (changed_in_prior_year, flipped, pos, loc)
    for k, s in enumerate(snaps):
        sd = snapdat[k]
        if sd["pos"].sum() == 0 or sd["loc"].sum() == 0:
            continue
        closed = [j for j in range(k) if snaps[j]["ct"] + OUTCOME_DAYS * DAY <= s["ct"]]
        trainP = {key: Counter() for key in LABELS}
        trainL = {key: Counter() for key in LABELS}
        for j in closed:
            for key in LABELS:
                trainP[key].update(snapdat[j]["tal"][key][0])
                trainL[key].update(snapdat[j]["tal"][key][1])
        if sum(trainP["fa"].values()) == 0:
            continue
        rs = rows[k]
        paths = [r[0] for r in rs]
        loc, pos = sd["loc"], sd["pos"]
        sc = {}
        for key, col in (("fa", 2), ("ca", 3)):
            d, D = density(trainP[key], trainL[key])
            sc[key] = np.array([d.get(r[col], D) for r in rs])
            if key == "fa":
                last_dens = (s["ref"], d, D, trainP[key], trainL[key])
        sc["LOC-desc"] = loc.copy()
        sc["LOC-asc"] = -loc
        rec = {b: {n: recall_at(v, loc, paths, pos, b) for n, v in sc.items()} for b in BUDGETS}
        u3 = auc(loc * sc["fa"], pos) - auc(loc, pos)
        per.append({"ref": s["ref"], "n": len(rs), "pos": int(pos.sum()), "recall": rec, "u3": u3,
                    "auc_loc": auc(loc, pos), "auc_u3": auc(loc * sc["fa"], pos)})
        # exploratory: label flip over the prior year among files present then
        prior = [j for j in range(k) if snaps[j]["ct"] <= s["ct"] - 365 * DAY]
        if prior:
            old = {r[0]: r for r in rows[prior[-1]]}
            for r, p, lo in zip(rs, pos, loc):
                o = old.get(r[0])
                if o is not None:
                    flip_rows.append((o[1] != r[1], o[2] != r[2], p, lo))

    rng_seq = np.random.SeedSequence(SEED)
    n = len(per)
    res = {}
    spawn = iter(rng_seq.spawn(16))
    for claim, key in (("ARCH-U1", "fa"), ("ARCH-U2", "ca")):
        out = {}
        for base in ("LOC-desc", "LOC-asc"):
            x = np.array([p["recall"][0.20][key] - p["recall"][0.20][base] for p in per])
            rng = np.random.default_rng(next(spawn))
            if n >= MIN_UNITS:
                lo, ci = boot(x, rng, a.iters)
                out[base] = {"mean": float(x.mean()), "lo": lo, "ci90": ci}
            else:
                out[base] = {"mean": float(x.mean()) if n else float("nan")}
        if n < MIN_UNITS:
            v = "not evaluable"
        elif all(out[b]["mean"] > 0 and out[b]["lo"] > 0 for b in out):
            v = "SUPPORTED"
        else:
            stronger = max(out, key=lambda b: np.mean([p["recall"][0.20][b] for p in per]))
            c = out[stronger]["ci90"]
            v = "replicated null (equivalence)" if -EQUIV < c[0] and c[1] < EQUIV else "not supported (inconclusive)"
        res[claim] = {"vs": out, "verdict": v}
    x = np.array([p["u3"] for p in per if not np.isnan(p["u3"])])
    rng = np.random.default_rng(next(spawn))
    if len(x) >= MIN_UNITS:
        lo, ci = boot(x, rng, a.iters)
        v = ("SUPPORTED" if x.mean() > 0 and lo > 0 else
             "replicated null (equivalence)" if -EQUIV < ci[0] and ci[1] < EQUIV else "not supported (inconclusive)")
        res["ARCH-U3"] = {"mean": float(x.mean()), "lo": lo, "ci90": ci, "verdict": v}
    else:
        res["ARCH-U3"] = {"mean": float(x.mean()) if len(x) else float("nan"), "verdict": "not evaluable"}

    scored = a.mode == "scored"

    def mrec(k_, b=0.20):
        return float(np.mean([p["recall"][b][k_] for p in per])) if per else float("nan")

    L = [f"# ARCH-U1..U3 — {a.repo} ({'SCORED' if scored else 'EXPLORATORY: no verdicts'})", ""]
    if not scored:
        L += ["**EXPLORATORY.** Not a registered configuration; nothing here is a verdict.", ""]
    L += [f"- DB `{a.db}`; {len(snaps)} quarterly snapshots; empty: {', '.join(missing) or 'none'}; scored: **{n}**",
          f"- events: {len(events)} on-master `{a.fix_classes}`; outcome window (t, t+{OUTCOME_DAYS} d]; "
          f"d(a) shrinkage pseudo-LOC {PSEUDO_LOC:,.0f}", "",
          "## Mean recall at a share of lines reviewed", "",
          "| ranking | @10% | @20% (primary) | @30% |", "|---|---:|---:|---:|"]
    for k_, lab in (("LOC-desc", "LOC-desc"), ("LOC-asc", "LOC-asc"), ("fa", "U1 d(file cluster)"), ("ca", "U2 d(composition)")):
        L.append(f"| {lab} | {mrec(k_, 0.10):.3f} | **{mrec(k_):.3f}** | {mrec(k_, 0.30):.3f} |")
    L += ["", f"## Verdicts (α = {ALPHA} one-sided)", "",
          "| claim | vs LOC-desc: mean [lo] | vs LOC-asc: mean [lo], 90% CI | verdict |", "|---|---|---|---|"]
    for claim in ("ARCH-U1", "ARCH-U2"):
        r = res[claim]
        vd, va = r["vs"]["LOC-desc"], r["vs"]["LOC-asc"]
        f1 = f"{vd['mean']:+.3f} [{vd.get('lo', float('nan')):+.3f}]"
        f2 = (f"{va['mean']:+.3f} [{va['lo']:+.3f}], [{va['ci90'][0]:+.3f}, {va['ci90'][1]:+.3f}]"
              if "ci90" in va else f"{va['mean']:+.3f}")
        L.append(f"| **{claim}** | {f1} | {f2} | {'**' + r['verdict'] + '**' if scored else '(exploratory)'} |")
    r3 = res["ARCH-U3"]
    L += ["", "| claim | mean AUC lift over total_loc | lo | 90% CI | verdict |", "|---|---:|---:|---|---|",
          f"| **ARCH-U3** | {r3['mean']:+.4f} | {r3.get('lo', float('nan')):+.4f} | "
          f"{'[%+.4f, %+.4f]' % r3['ci90'] if 'ci90' in r3 else '—'} | {'**' + r3['verdict'] + '**' if scored else '(exploratory)'} |",
          "", f"Mean per-snapshot AUC: total_loc {np.nanmean([p['auc_loc'] for p in per]):.4f} · "
          f"total_loc × d(file cluster) {np.nanmean([p['auc_u3'] for p in per]):.4f}", "",
          "## Secondary (descriptive)", ""]
    if last_dens:
        ref, d, D, P, Lc = last_dens
        L += [f"Learned per-line fix density by file cluster at the last scored snapshot ({ref}); global "
              f"{D * 1000:.3f} positives/kLOC:", "", "| label | training rows' kLOC | positives | d(a) per kLOC | ratio to global |",
              "|---|---:|---:|---:|---:|"]
        for lab in sorted(d, key=lambda x: -d[x]):
            L.append(f"| {lab} | {Lc[lab] / 1000:,.0f} | {int(P[lab])} | {d[lab] * 1000:.3f} | {d[lab] / D if D else float('nan'):.2f} |")
    if flip_rows:
        fr = np.array(flip_rows, dtype=float)
        L += ["", "Label flip over the prior year vs future fix (files present a year earlier):", "",
              "| group | files | positive rate | mean total_loc |", "|---|---:|---:|---:|"]
        for lab, m in (("unchanged LOC (no edit)", fr[:, 0] == 0),
                       ("edited, label kept", (fr[:, 0] == 1) & (fr[:, 1] == 0)),
                       ("edited, label flipped", (fr[:, 0] == 1) & (fr[:, 1] == 1))):
            if m.sum():
                L.append(f"| {lab} | {int(m.sum()):,} | {fr[m, 2].mean():.4f} | {fr[m, 3].mean():,.0f} |")
    L += ["", f"Runtime {time.time() - t0:.0f}s · bootstrap {a.iters} rounds over snapshots, seed {SEED}."]
    out = a.out or DOCS_DIR / f"arch_useful_{a.repo}.md"
    out.write_text("\n".join(L) + "\n")
    (a.cache / f"arch_useful_{a.repo}_{a.fix_classes.replace(',', '+')}.json").write_text(
        json.dumps({"per_snapshot": per, "results": res}, indent=1, default=float))
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
