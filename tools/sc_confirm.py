#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""SC stage 2: confirm the frozen (candidate, class) pairs on the unseen holdout (docs/sc_protocol.md).

    python tools/sc_confirm.py
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).parent / "exploratory"))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from sc_discover import recall20  # noqa: E402
from xc_envcond import PATTERNS  # noqa: E402

HOLD = {"harfbuzz": {"langs": ("c", "cpp"), "exts": (".c", ".h", ".cc", ".hh", ".cpp", ".hpp"), "classes": ("latent", "extrinsic", "regression", "other-fix")},
        "libarchive": {"langs": ("c",), "exts": (".c", ".h"), "classes": ("latent", "extrinsic", "other-fix")}}
SEED, ITERS, DAY, WINDOW, MIN_UNITS, EQUIV = 2982, 5000, 86400, 180, 20, 0.02


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def main() -> int:
    t0 = time.time()
    frozen = json.loads((REPO_ROOT / "events" / "sc_frozen_candidates.json").read_text())
    pairs = [(k, c["candidate"], 1.0 if c["direction"].startswith("higher") else -1.0) for k, cs in frozen.items() for c in cs]
    alpha = 0.01 / len(pairs)
    lift = {(r, k, c): [] for r in HOLD for k, c, _ in pairs}
    counts = {}
    for r, cfg in HOLD.items():
        repo = POOL_DIR / r
        walk = json.loads((REPO_ROOT / "walks" / f"{r}_quarterly.json").read_text())
        head = walk["events_head"]
        xc = json.loads((REPO_ROOT / "events" / f"{r}_xc.json").read_text())["events"]
        lat = []
        for e in json.loads((REPO_ROOT / "events" / f"{r}.json").read_text())["events"]:
            if e["class"] != "security-fix":
                continue
            if subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", e["sha"], head]).returncode != 0:
                continue
            ct = int(_git(repo, "show", "-s", "--format=%ct", e["sha"]).strip())
            files = [f for f in _git(repo, "-c", "core.quotepath=off", "diff-tree", "--no-commit-id", "--name-only", "-r",
                                     e["sha"]).splitlines() if f.endswith(cfg["exts"])]
            lat.append({"sha": e["sha"], "ct": ct, "class": "latent", "c_files": files})
        latset = {e["sha"] for e in lat}
        ev = lat + [e for e in xc if e["sha"] not in latset and e["class"] in cfg["classes"]]
        counts[r] = {k: sum(e["class"] == k for e in ev) for k in cfg["classes"]}
        con = sqlite3.connect(f"file:{REPO_ROOT / 'dbs' / f'{r}_out' / f'{r}_galaxy_master.db'}?mode=ro", uri=True)
        cols = sorted({c for _, c, _ in pairs if not c.startswith("platform_cond")} | {"raw_churn_freq", "risk_churn", "pct_vec_churn"})
        cols = [c.replace(" /line", "") for c in cols]
        for s in walk["revisions"]:
            ct = int(_git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())
            q = (f"SELECT file_path, total_loc, {', '.join(sorted(set(cols)))} FROM file_data WHERE commit_hash=? AND language IN "
                 f"({','.join('?' * len(cfg['langs']))})")
            g = pd.read_sql_query(q, con, params=(s["sha"], *cfg["langs"]))
            if g.empty:
                continue
            pc = {}
            for line in _git(repo, "-c", "core.quotepath=off", "grep", "-c", "-P", PATTERNS["P"], s["sha"], "--",
                             *[f"*{e}" for e in cfg["exts"]]).splitlines():
                _, _, rest = line.partition(":")
                p, _, n = rest.rpartition(":")
                if n.isdigit():
                    pc[p] = int(n)
            g["platform_cond"] = [pc.get(p, 0) for p in g["file_path"]]
            loc = g["total_loc"].astype(float).to_numpy()
            pr = np.argsort(np.argsort(g["file_path"].to_numpy()))
            denom = np.maximum(loc, 1.0)
            for k, c, sign in pairs:
                if k not in cfg["classes"]:
                    continue
                files = set()
                for e in ev:
                    if e["class"] == k and ct < e["ct"] <= ct + WINDOW * DAY:
                        files.update(e["c_files"])
                y = g["file_path"].isin(files).to_numpy().astype(float)
                if y.sum() == 0:
                    continue
                base = c.replace(" /line", "")
                v = pd.to_numeric(g[base], errors="coerce").fillna(0).to_numpy(dtype=float)
                v = v / denom if c.endswith(" /line") else v
                b = max(recall20(loc, loc, pr, y), recall20(-loc, loc, pr, y))
                lift[(r, k, c)].append(recall20(sign * v, loc, pr, y) - b)
        con.close()
        print(f"{r}: scored ({time.time() - t0:.0f}s)", flush=True)

    spawn = iter(np.random.SeedSequence(SEED).spawn(len(lift) + 1))
    L = ["# SC stage 2 — confirmation on the unseen holdout (SCORED)", "",
         f"- frozen pairs {len(pairs)} → α = 0.01/{len(pairs)} = {alpha:.4f} one-sided; holdout harfbuzz (c+cpp) and libarchive (c)",
         "- label counts: " + "; ".join(f"{r} " + ", ".join(f"{k} {n}" for k, n in c.items()) for r, c in counts.items()), "",
         "| class | candidate | repo | scored snapshots | mean R | lo | 90% CI | verdict |", "|---|---|---|---:|---:|---:|---|---|"]
    final = {}
    for k, c, _ in pairs:
        verdicts = []
        for r in HOLD:
            x = np.array(lift[(r, k, c)])
            rng = np.random.default_rng(next(spawn))
            if k not in HOLD[r]["classes"]:
                L.append(f"| {k} | `{c}` | {r} | — | — | — | — | not evaluable (class withheld) |")
                continue
            if len(x) < MIN_UNITS:
                L.append(f"| {k} | `{c}` | {r} | {len(x)} | {x.mean() if len(x) else float('nan'):+.3f} | — | — | **not evaluable** |")
                continue
            b = np.array([x[rng.integers(0, len(x), len(x))].mean() for _ in range(ITERS)])
            lo, ci = float(np.quantile(b, alpha)), (float(np.quantile(b, 0.05)), float(np.quantile(b, 0.95)))
            v = ("SUPPORTED" if x.mean() > 0 and lo > 0 else
                 "replicated null (equivalence)" if -EQUIV < ci[0] and ci[1] < EQUIV else "not supported (inconclusive)")
            verdicts.append(v)
            L.append(f"| {k} | `{c}` | {r} | {len(x)} | {x.mean():+.3f} | {lo:+.3f} | [{ci[0]:+.3f}, {ci[1]:+.3f}] | **{v}** |")
        final[(k, c)] = "CONFIRMED" if verdicts and all(v == "SUPPORTED" for v in verdicts) else "not confirmed"
    L += ["", "| class | candidate | stage-2 verdict |", "|---|---|---|"] + [f"| {k} | `{c}` | **{v}** |" for (k, c), v in final.items()]
    L += ["", f"Runtime {time.time() - t0:.0f}s · bootstrap {ITERS} rounds over snapshots, seed {SEED}."]
    (DOCS_DIR / "sc_confirmation.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
