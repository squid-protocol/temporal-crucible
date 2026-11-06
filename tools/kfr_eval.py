#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""KF-R (file-level replication on unseen repos) and KF-L (function-level localization). docs/kfr_hypotheses.md.

    python tools/kfr_eval.py
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import time
from collections import Counter

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from exposure_delta import diff_statuses  # noqa: E402
from kf_eval import ITERS, SEED, boot_ratio, boot_rr, collect, fault_type, rr  # noqa: E402
from signal_anatomy import hunk_lines_parent_side, parent_child  # noqa: E402

ALPHA = 0.01 / 4
WT = pathlib.Path(os.environ.get("TC_WORKTREES", "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees"))
NEW = ("libxml2", "libtiff", "libpng", "libexif", "file")
NEW_DBS = {r: REPO_ROOT / "dbs" / f"{r}_out" / f"{r}_galaxy_master.db" for r in NEW}
KFL_DBS = {"ndpi": WT / "frec/dbs/ndpi_out/ndpi_galaxy_master.db", "openssl": WT / "dyncen/dbs/openssl_out/openssl_galaxy_master.db",
           **{r: NEW_DBS[r] for r in ("libxml2", "libtiff", "libpng", "libexif")}}  # file fails G1 -> not in KF-L
GOTO = re.compile(r"\bgoto\b")


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def kfl_collect(repo_name, db):
    """FREC's candidates (touched C files at T0, >= 2 functions; positive = span overlaps parent-side changed lines),
    exposure = span contains a goto line; MH strata = function-LOC quintile within the event."""
    repo = POOL_DIR / repo_name
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    out = []
    for e in json.loads((REPO_ROOT / "events" / f"{repo_name}.json").read_text())["events"]:
        if e["class"] != "security-fix" or str(e.get("on_master", True)) == "False":
            continue
        parent, child = parent_child(repo, e["sha"])
        if parent is None or not con.execute("SELECT 1 FROM repo_data WHERE commit_hash=?", (parent,)).fetchone():
            continue
        try:
            st = diff_statuses(repo, parent, child)
        except subprocess.CalledProcessError:
            continue
        loc, exp, y = [], [], []
        for _p, s in st.items():
            if s["status"] != "touched" or not s["old_path"] or not s["old_path"].endswith((".c", ".h")):
                continue
            old = s["old_path"]
            rows = con.execute("SELECT f.func_name, f.start_line, f.loc FROM function_data f JOIN file_data fd ON f.file_id = fd.id "
                               "WHERE fd.commit_hash = ? AND fd.file_path = ? AND fd.language = 'c'", (parent, old)).fetchall()
            rows = [r for r in rows if r[1] is not None and r[2] is not None and r[0]]
            if len(rows) < 2:
                continue
            src = _git(repo, "show", f"{parent}:{old}").splitlines()
            goto_lines = {i + 1 for i, ln in enumerate(src) if GOTO.search(ln)}
            changed = hunk_lines_parent_side(repo, parent, child, old)
            for _n, start, n in rows:
                span = range(start, start + max(n, 1))
                loc.append(float(n))
                exp.append(any(ln in goto_lines for ln in span))
                y.append(any(ln in changed for ln in span))
        if not loc or not any(y):
            continue
        loc, exp, y = np.array(loc), np.array(exp), np.array(y)
        q = np.minimum((np.argsort(np.argsort(loc, kind="stable")) * 5) // len(loc), 4)
        num = den = 0.0
        for k in range(5):
            m = q == k
            n1, n0 = exp[m].sum(), (~exp[m]).sum()
            if n1 and n0:
                N = n1 + n0
                num += (y[m] & exp[m]).sum() * n0 / N
                den += (y[m] & ~exp[m]).sum() * n1 / N
        out.append({"repo": repo_name, "type": fault_type(e), "goto": (num, den), "n_func": len(loc),
                    "share_goto": float(exp.mean())})
    con.close()
    return out


def verdict_ratio(est, lo, ci):
    return "SUPPORTED" if lo > 1 else "replicated null (equivalence)" if 0.8 < ci[0] and ci[1] < 1.25 else "not supported (inconclusive)"


def main() -> int:
    t0 = time.time()
    spawn = iter(np.random.SeedSequence(SEED).spawn(8))
    # ---- KF-R
    evs = []
    for r, db in NEW_DBS.items():
        if db.exists():
            evs += collect(r, db)
    types = Counter((e["repo"], e["type"]) for e in evs)
    life = [e for e in evs if e["type"] == "lifetime"]
    bounds = [e for e in evs if e["type"] == "bounds"]
    L = ["# KF-R and KF-L — replication and localization of goto ↔ lifetime faults (SCORED)", "",
         "## KF-R — file level, five unseen repos", "",
         f"- events with a scanned T0 and ≥ 1 touched C file: {len(evs)}; types: " + ", ".join(f"{r}/{t} {n}" for (r, t), n in sorted(types.items())),
         f"- G3 power: lifetime {len(life)}, bounds {len(bounds)} → {'PASS' if len(life) >= 20 and len(bounds) >= 20 else 'FAIL (not evaluable)'}", "",
         "| claim | estimate | one-sided lo (α=0.0025) | 90% CI | verdict |", "|---|---:|---:|---|---|"]
    b = boot_rr(evs, "goto", np.random.default_rng(next(spawn)))
    est, lo, ci = rr(evs, "goto"), float(np.quantile(b, ALPHA)), (float(np.quantile(b, 0.05)), float(np.quantile(b, 0.95)))
    L.append(f"| **KFR-H1** RR(goto), all security fixes | {est:.3f} | {lo:.3f} | [{ci[0]:.3f}, {ci[1]:.3f}] | **{'SUPPORTED' if lo > 1 else 'not supported'}** |")
    if len(life) >= 20 and len(bounds) >= 20:
        b = boot_ratio(life, bounds, "goto", np.random.default_rng(next(spawn)))
        est = rr(life, "goto") / rr(bounds, "goto")
        lo, ci = float(np.quantile(b, ALPHA)), (float(np.quantile(b, 0.05)), float(np.quantile(b, 0.95)))
        L.append(f"| **KFR-H3** RR(goto \\| lifetime) / RR(goto \\| bounds) | {est:.3f} | {lo:.3f} | [{ci[0]:.3f}, {ci[1]:.3f}] | **{verdict_ratio(est, lo, ci)}** |")
    else:
        L.append("| **KFR-H3** | — | — | — | **not evaluable** |")
    L += ["", f"Descriptive: RR(goto | lifetime) {rr(life, 'goto'):.2f}, RR(goto | bounds) {rr(bounds, 'goto'):.2f}, "
          f"RR(goto, 50 LOC bins) lifetime {rr(life, 'goto50'):.2f} / bounds {rr(bounds, 'goto50'):.2f}; "
          + "; ".join(f"{r}: RR(goto) {rr([e for e in evs if e['repo'] == r], 'goto'):.2f} ({sum(e['repo'] == r for e in evs)} events)" for r in NEW if any(e['repo'] == r for e in evs))]
    # ---- KF-L
    fe = []
    for r, db in KFL_DBS.items():
        if db.exists():
            fe += kfl_collect(r, db)
        print(f"KF-L {r} ({time.time() - t0:.0f}s)", flush=True)
    fl = [e for e in fe if e["type"] == "lifetime"]
    fb = [e for e in fe if e["type"] == "bounds"]
    L += ["", "## KF-L — function level (nDPI, openssl, libxml2, libtiff, libpng, libexif; file excluded by G1)", "",
          f"- events: {len(fe)} (lifetime {len(fl)}, bounds {len(fb)}); median functions per event {np.median([e['n_func'] for e in fe]):.0f}; "
          f"median share of candidate functions containing goto {np.median([e['share_goto'] for e in fe]):.1%}", "",
          "| claim | estimate | one-sided lo (α=0.0025) | 90% CI | verdict |", "|---|---:|---:|---|---|"]
    b = boot_rr(fl, "goto", np.random.default_rng(next(spawn)))
    est, lo, ci = rr(fl, "goto"), float(np.quantile(b, ALPHA)), (float(np.quantile(b, 0.05)), float(np.quantile(b, 0.95)))
    L.append(f"| **KFL-H1** RR(goto-function \\| lifetime) | {est:.3f} | {lo:.3f} | [{ci[0]:.3f}, {ci[1]:.3f}] | **{'SUPPORTED' if lo > 1 else 'not supported'}** |")
    b = boot_ratio(fl, fb, "goto", np.random.default_rng(next(spawn)))
    est = rr(fl, "goto") / rr(fb, "goto")
    lo, ci = float(np.quantile(b, ALPHA)), (float(np.quantile(b, 0.05)), float(np.quantile(b, 0.95)))
    L.append(f"| **KFL-H2** RR(goto-function \\| lifetime) / RR(goto-function \\| bounds) | {est:.3f} | {lo:.3f} | [{ci[0]:.3f}, {ci[1]:.3f}] | **{verdict_ratio(est, lo, ci)}** |")
    L += ["", "Descriptive per repo (function level): " + "; ".join(
        f"{r}: lifetime RR {rr([e for e in fl if e['repo'] == r], 'goto'):.2f} ({sum(e['repo'] == r for e in fl)}), "
        f"bounds RR {rr([e for e in fb if e['repo'] == r], 'goto'):.2f} ({sum(e['repo'] == r for e in fb)})" for r in KFL_DBS),
          "", f"Runtime {time.time() - t0:.0f}s · event bootstrap {ITERS} rounds, seed {SEED}."]
    (DOCS_DIR / "kfr.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
