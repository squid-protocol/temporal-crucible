#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""BURST-H1..H3: do extrinsic fixes surge after compiler releases? (docs/burst_hypotheses.md, registered 2026-11-06)

    python tools/burst_eval.py
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402

REPOS = ("curl", "ndpi", "openssl", "harfbuzz", "libarchive")
SEED, ITERS, DAY = 2982, 5000, 86400
ALPHA, MIN_SHOCKS = 0.01 / 3, 20
EQUIV = {"BURST-H1": 0.01, "BURST-H2": 0.01, "BURST-H3": 0.2}
NAMES = {"gcc": re.compile(r"\bg(cc|nu c)\b|\bgcc-?\d", re.I), "clang": re.compile(r"\bclang\b|\bllvm\b|\bclang-?\d", re.I)}
OTHER = {"gcc": "clang", "clang": "gcc"}


def ts(d):
    return int(dt.datetime.fromisoformat(d).replace(tzinfo=dt.timezone.utc).timestamp())


def shocks():
    out = []
    for s in json.loads((REPO_ROOT / "events" / "shocks_compilers.json").read_text())["shocks"]:
        v = tuple(int(x) for x in s["version"].split("."))
        if s["compiler"] == "clang" and v < (2, 6, 0):
            continue  # registered: Clang from LLVM 2.6
        out.append({**s, "t": ts(s["date"])})
    return out


def units(window, shift=0):
    res = []
    for r in REPOS:
        xc = json.loads((REPO_ROOT / "events" / f"{r}_xc.json").read_text())
        head_ct = int(subprocess.run(["git", "-C", str(POOL_DIR / r), "show", "-s", "--format=%ct", xc["head"]],
                                     capture_output=True, text=True).stdout.strip())
        ev = xc["events"]
        for s in shocks():
            t = s["t"] + shift * DAY
            if xc["since"] > t - window * DAY or head_ct < t + window * DAY:
                continue
            bef = [e for e in ev if t - window * DAY < e["ct"] <= t]
            aft = [e for e in ev if t < e["ct"] <= t + window * DAY]
            if not bef or not aft:
                continue

            def share(es):
                return sum(e["class"] == "extrinsic" for e in es) / len(es)

            def named(es, c):
                return sum(e["class"] == "extrinsic" and bool(NAMES[c].search(e["subject"])) for e in es)

            c = s["compiler"]
            res.append({"repo": r, "shock": f"{c}-{s['version']}", "compiler": c,
                        "d_share": share(aft) - share(bef),
                        "d_spec": (named(aft, c) - named(bef, c)) - (named(aft, OTHER[c]) - named(bef, OTHER[c])),
                        "n_bef": len(bef), "n_aft": len(aft)})
    return res


def cluster_test(us, key, claim, rng):
    by = defaultdict(list)
    for u in us:
        by[u["shock"]].append(u[key])
    keys = sorted(by)
    if len(keys) < MIN_SHOCKS:
        return {"n_shocks": len(keys), "n_units": len(us), "verdict": "not evaluable",
                "mean": float(np.mean([u[key] for u in us])) if us else float("nan")}
    mean = float(np.mean([v for k in keys for v in by[k]]))
    boots = np.empty(ITERS)
    for i in range(ITERS):
        pick = rng.choice(len(keys), len(keys))
        vals = [v for j in pick for v in by[keys[j]]]
        boots[i] = np.mean(vals)
    lo, ci = float(np.quantile(boots, ALPHA)), (float(np.quantile(boots, 0.05)), float(np.quantile(boots, 0.95)))
    e = EQUIV[claim]
    v = ("SUPPORTED" if mean > 0 and lo > 0 else
         "replicated null (equivalence)" if -e < ci[0] and ci[1] < e else "not supported (inconclusive)")
    return {"n_shocks": len(keys), "n_units": len(us), "mean": mean, "lo": lo, "ci90": ci, "verdict": v}


def main() -> int:
    t0 = time.time()
    us = units(90)
    spawn = iter(np.random.SeedSequence(SEED).spawn(8))
    res = {"BURST-H1": cluster_test([u for u in us if u["compiler"] == "gcc"], "d_share", "BURST-H1", np.random.default_rng(next(spawn))),
           "BURST-H2": cluster_test([u for u in us if u["compiler"] == "clang"], "d_share", "BURST-H2", np.random.default_rng(next(spawn))),
           "BURST-H3": cluster_test(us, "d_spec", "BURST-H3", np.random.default_rng(next(spawn)))}
    what = {"BURST-H1": "extrinsic share after − before, GCC releases",
            "BURST-H2": "extrinsic share after − before, Clang releases",
            "BURST-H3": "own-compiler-named − other-compiler-named extrinsic Δcount"}
    L = ["# BURST-H1..H3 — extrinsic fixes vs compiler releases (SCORED)", "",
         f"- repos: {', '.join(REPOS)}; shocks `events/shocks_compilers.json` (Clang from LLVM 2.6); window 90 d", "",
         "| claim | what | shocks | units | mean | lo (α=0.0033) | 90% CI | verdict |", "|---|---|---:|---:|---:|---:|---|---|"]
    for c, r in res.items():
        ci = f"[{r['ci90'][0]:+.4f}, {r['ci90'][1]:+.4f}]" if "ci90" in r else "—"
        L.append(f"| **{c}** | {what[c]} | {r['n_shocks']} | {r['n_units']} | {r['mean']:+.4f} | "
                 f"{r.get('lo', float('nan')):+.4f} | {ci} | **{r['verdict']}** |")
    L += ["", "## Descriptive (no verdicts)", "", "Per repo, mean Δ extrinsic share (90 d):", "",
          "| repo | GCC shocks | Δ share | Clang shocks | Δ share | mean extrinsic share |", "|---|---:|---:|---:|---:|---:|"]
    for rp in REPOS:
        g = [u["d_share"] for u in us if u["repo"] == rp and u["compiler"] == "gcc"]
        k = [u["d_share"] for u in us if u["repo"] == rp and u["compiler"] == "clang"]
        xc = json.loads((REPO_ROOT / "events" / f"{rp}_xc.json").read_text())["events"]
        base = np.mean([e["class"] == "extrinsic" for e in xc])
        L.append(f"| {rp} | {len(g)} | {np.mean(g) if g else float('nan'):+.4f} | {len(k)} | "
                 f"{np.mean(k) if k else float('nan'):+.4f} | {base:.3f} |")
    L += ["", "Robustness and placebo (pooled means):", "", "| variant | GCC Δ share | Clang Δ share | H3 Δ named |",
          "|---|---:|---:|---:|"]
    for lab, w, sh in (("window 30 d", 30, 0), ("window 90 d (registered)", 90, 0), ("window 180 d", 180, 0),
                       ("placebo: shocks +182 d", 90, 182)):
        v = us if (w, sh) == (90, 0) else units(w, sh)
        g = [u["d_share"] for u in v if u["compiler"] == "gcc"]
        k = [u["d_share"] for u in v if u["compiler"] == "clang"]
        L.append(f"| {lab} | {np.mean(g):+.4f} ({len(g)}) | {np.mean(k):+.4f} ({len(k)}) | "
                 f"{np.mean([u['d_spec'] for u in v]):+.3f} ({len(v)}) |")
    L += ["", f"Runtime {time.time() - t0:.0f}s · cluster bootstrap over shocks, {ITERS} rounds, seed {SEED}."]
    (DOCS_DIR / "burst.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
