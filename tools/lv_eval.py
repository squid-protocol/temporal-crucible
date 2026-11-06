#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LV-H1..H3: are latent defects found at the search frontier? (docs/lv_hypotheses.md, registered 2026-11-06)

Monthly snapshots; candidates = C files at t instrumented in the OSS-Fuzz report nearest t (<= 7 d before);
size = report lines.count; outcome = XC class touches in (t, t+90 d].
  frontier  = max(0, covered_t - covered_{t-90d}) / count_t
  reached   = covered_t / count_t ; unreached = 1 - reached

    python tools/lv_eval.py --repo ndpi --project ndpi --prefix /src/ndpi/ --branch dev
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from ea_eval import recall_at  # noqa: E402

SEED, ITERS, DAY, WINDOW, LOOKBACK, SLACK = 2982, 5000, 86400, 90, 90, 7
ALPHA, MIN_UNITS, EQUIV, BLOCK = 0.01 / 4, 20, 0.02, 3
COVDIR = POOL_DIR / "ossfuzz-coverage"


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def report_dates(project):
    out = []
    for p in (COVDIR / project).glob("2*.json"):
        out.append(dt.date(int(p.stem[:4]), int(p.stem[4:6]), int(p.stem[6:8])))
    return sorted(out)


def nearest_before(dates, day):
    best = None
    for d in dates:
        if d <= day and (day - d).days <= SLACK:
            best = d
    return best


def load(project, d, prefix):
    j = json.loads((COVDIR / project / f"{d:%Y%m%d}.json").read_text())
    out = {}
    for f in j["data"][0]["files"]:
        name = f["filename"]
        if name.startswith(prefix):
            ln = f["summary"]["lines"]
            out[name[len(prefix):]] = (ln["count"], ln["covered"])
    return out


def block_boot(x, rng, iters=ITERS):
    n = len(x)
    nb = int(np.ceil(n / BLOCK))
    starts = np.arange(0, max(n - BLOCK + 1, 1))
    b = np.empty(iters)
    for i in range(iters):
        idx = np.concatenate([np.arange(s, min(s + BLOCK, n)) for s in rng.choice(starts, nb)])[:n]
        b[i] = x[idx].mean()
    return float(np.quantile(b, ALPHA)), (float(np.quantile(b, 0.05)), float(np.quantile(b, 0.95)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--project", required=True)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--start", default="2020-03")
    a = ap.parse_args()
    t0 = time.time()
    repo = POOL_DIR / a.repo
    xc = json.loads((REPO_ROOT / "events" / f"{a.repo}_xc.json").read_text())
    events, head = xc["events"], xc["head"]
    head_ct = int(_git(repo, "show", "-s", "--format=%ct", head).strip())
    fp = [(h, int(c)) for h, c in (l.split() for l in _git(repo, "log", "--first-parent", "--format=%H %ct", head).splitlines())][::-1]
    dates = report_dates(a.project)
    y0, m0 = map(int, a.start.split("-"))
    classes = ("latent", "extrinsic", "regression", "other-fix")
    per, dropped = [], 0
    y, m = y0, m0
    while True:
        bound = dt.datetime(y, m, 1, tzinfo=dt.timezone.utc)
        if bound.timestamp() + WINDOW * DAY >= head_ct:
            break
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        b = int(bound.timestamp())
        sha = None
        for h, c in fp:
            if c < b:
                sha = h
            else:
                break
        d_t = nearest_before(dates, bound.date())
        d_p = nearest_before(dates, bound.date() - dt.timedelta(days=LOOKBACK))
        if sha is None or d_t is None or d_p is None:
            dropped += 1
            continue
        present = {p for p in _git(repo, "ls-tree", "-r", "--name-only", sha).splitlines() if p.endswith((".c", ".h"))}
        cov_t, cov_p = load(a.project, d_t, a.prefix), load(a.project, d_p, a.prefix)
        paths = sorted(p for p, (cnt, _) in cov_t.items() if cnt > 0 and p in present)
        if not paths:
            dropped += 1
            continue
        size = np.array([float(cov_t[p][0]) for p in paths])
        covd = np.array([float(cov_t[p][1]) for p in paths])
        prev = np.array([float(cov_p.get(p, (0, 0))[1]) for p in paths])
        sc = {"frontier": np.maximum(covd - prev, 0) / size, "reached": covd / size}
        sc["unreached"] = 1 - sc["reached"]
        pos = {k: set() for k in classes}
        for e in events:
            if e["class"] in pos and b < e["ct"] <= b + WINDOW * DAY:
                pos[e["class"]].update(e["c_files"])
        rec = {}
        for k in classes:
            yv = np.array([1.0 if p in pos[k] else 0.0 for p in paths])
            if yv.sum() == 0:
                continue
            base = max(recall_at(size, size, paths, yv, 0.2), recall_at(-size, size, paths, yv, 0.2))
            rec[k] = {n: recall_at(v, size, paths, yv, 0.2) - base for n, v in sc.items()}
        per.append({"month": f"{bound:%Y-%m}", "n": len(paths), "frontier_share": float(np.mean(sc["frontier"] > 0)),
                    "reached_mean": float(sc["reached"].mean()), "lift": rec})

    def vec(f, *ks):
        return np.array([f(p) for p in per if all(k in p["lift"] for k in ks)])

    claims = {"LV-H1": ("frontier finds latent fixes beyond size", vec(lambda p: p["lift"]["latent"]["frontier"], "latent")),
              "LV-H2": ("…more than other fixes", vec(lambda p: p["lift"]["latent"]["frontier"] - p["lift"]["other-fix"]["frontier"], "latent", "other-fix")),
              "LV-H3": ("reached beats unreached for latent", vec(lambda p: p["lift"]["latent"]["reached"] - p["lift"]["latent"]["unreached"], "latent"))}
    spawn = iter(np.random.SeedSequence(SEED).spawn(4))
    L = [f"# LV-H1..H3 — the search frontier: {a.repo} (SCORED)", "",
         f"- OSS-Fuzz `{a.project}` daily summaries: {len(dates)} reports; monthly snapshots scored: {len(per)} "
         f"(dropped, no report within {SLACK} d: {dropped})",
         f"- candidates per snapshot: median {np.median([p['n'] for p in per]):.0f} instrumented C files; files with any "
         f"new coverage in 90 d: median {np.median([p['frontier_share'] for p in per]):.1%}; mean line coverage "
         f"{np.median([p['reached_mean'] for p in per]):.1%}",
         f"- labels `events/{a.repo}_xc.json`; window (t, t+{WINDOW} d]; block bootstrap (blocks of {BLOCK})", "",
         "| claim | what | n | mean | lo (α=0.0025) | 90% CI | verdict |", "|---|---|---:|---:|---:|---|---|"]
    for c, (w, x) in claims.items():
        n = len(x)
        rng = np.random.default_rng(next(spawn))
        if n < MIN_UNITS:
            L.append(f"| **{c}** | {w} | {n} | {x.mean() if n else float('nan'):+.3f} | — | — | **not evaluable** |")
            continue
        lo, ci = block_boot(x, rng)
        v = ("SUPPORTED" if x.mean() > 0 and lo > 0 else
             "replicated null (equivalence)" if -EQUIV < ci[0] and ci[1] < EQUIV else "not supported (inconclusive)")
        L.append(f"| **{c}** | {w} | {n} | {x.mean():+.3f} | {lo:+.3f} | [{ci[0]:+.3f}, {ci[1]:+.3f}] | **{v}** |")
    L += ["", "## Descriptive: mean lift over the stronger size order", "", "| score | " + " | ".join(classes) + " |",
          "|---|" + "---:|" * len(classes)]
    for s_ in ("frontier", "reached", "unreached"):
        L.append(f"| {s_} | " + " | ".join(
            f"{np.mean([p['lift'][k][s_] for p in per if k in p['lift']]):+.3f} ({sum(k in p['lift'] for p in per)})"
            for k in classes) + " |")
    L += ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED}."]
    (DOCS_DIR / f"lv_{a.repo}.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
