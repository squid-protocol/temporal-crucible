#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""KF-H1..H4: construct split of dynamism + keyword -> fault-type specificity (docs/kf_hypotheses.md).

    python tools/kf_eval.py
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
from dyncen_eval import EVIDENCE_COLUMNS  # noqa: E402
from exposure_delta import diff_statuses  # noqa: E402
from signal_anatomy import parent_child  # noqa: E402

WT = pathlib.Path(os.environ.get("TC_WORKTREES", "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees"))
DBS = {"ndpi": WT / "frec/dbs/ndpi_out/ndpi_galaxy_master.db", "openssl": WT / "dyncen/dbs/openssl_out/openssl_galaxy_master.db"}
CONTEXT = {"curl": WT / "rescan-engine-32619e4a5/dbs/curl_out/curl_galaxy_master.db"}
GOTO, MACRO = r"\bgoto\b", r"^\s*#\s*define\s+[A-Za-z_]\w*\("
BOUNDS_CWE = {119, 120, 121, 122, 123, 124, 125, 126, 127, 129, 130, 131, 170, 193, 786, 787, 788, 805, 806, 823, 1284}
LIFE_CWE = {401, 404, 415, 416, 457, 459, 672, 763, 772, 824, 825, 908, 909, 911}
BOUNDS_FUZZ = {"heap-buffer-overflow", "stack-buffer-overflow", "global-buffer-overflow", "dynamic-stack-buffer-overflow",
               "index-out-of-bounds", "negative-size-param", "container-overflow"}
LIFE_FUZZ = {"memory leak", "heap-use-after-free", "use-after-free", "double-free", "use-of-uninitialized-value",
             "use-after-poison", "stack-use-after-return", "stack-use-after-scope", "bad-free", "invalid-free"}
SEED, ITERS, ALPHA = 2982, 5000, 0.01 / 4


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def fault_type(e):
    cwe = {int(x) for x in re.findall(r"CWE-(\d+)", str(e.get("cwe", "")))}
    if cwe:
        b, l = bool(cwe & BOUNDS_CWE), bool(cwe & LIFE_CWE)
        return "both" if b and l else "bounds" if b else "lifetime" if l else "other"
    kind = str(e.get("summary", "")).split(" in ")[0].strip().lower()
    return "bounds" if kind in BOUNDS_FUZZ else "lifetime" if kind in LIFE_FUZZ else "other"


def grep_counts(repo, sha, pat):
    out = {}
    for line in _git(repo, "-c", "core.quotepath=off", "grep", "-c", "-P", pat, sha, "--", "*.c", "*.h").splitlines():
        _, _, rest = line.partition(":")
        p, _, n = rest.rpartition(":")
        if n.isdigit():
            out[p] = int(n)
    return out


def mh_parts(loc, evid, exp, y, nloc=10, nev=4):
    lb = (np.searchsorted(np.quantile(loc, np.linspace(0, 1, 11)[1:-1]), loc, side="right") if nloc == 10
          else np.minimum((np.argsort(np.argsort(loc, kind="stable")) * nloc) // len(loc), nloc - 1))
    eb = np.searchsorted(np.quantile(evid, np.linspace(0, 1, nev + 1)[1:-1]), evid, side="right")
    s = lb * 100 + eb
    num = den = 0.0
    for k in np.unique(s):
        m = s == k
        n1, n0 = exp[m].sum(), (~exp[m]).sum()
        if n1 and n0:
            N = n1 + n0
            num += (y[m] & exp[m]).sum() * n0 / N
            den += (y[m] & ~exp[m]).sum() * n1 / N
    return num, den


def collect(repo_name, db):
    repo = POOL_DIR / repo_name
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    out = []
    for e in json.loads((REPO_ROOT / "events" / f"{repo_name}.json").read_text())["events"]:
        if e["class"] != "security-fix" or str(e.get("on_master", True)) == "False":
            continue
        parent, child = parent_child(repo, e["sha"])
        if parent is None:
            continue
        rows = con.execute(f"SELECT file_path, total_loc, {', '.join(EVIDENCE_COLUMNS)} FROM file_data WHERE commit_hash=?",
                           (parent,)).fetchall()
        rows = [r for r in rows if r[0].endswith((".c", ".h"))]
        if not rows:
            continue
        snap = {r[0] for r in rows}
        pos = {s["old_path"] for _, s in diff_statuses(repo, parent, child).items() if s["status"] == "touched" and s["old_path"] in snap}
        if not pos:
            continue
        g, m = grep_counts(repo, parent, GOTO), grep_counts(repo, parent, MACRO)
        loc = np.array([float(r[1] or 0) for r in rows])
        evid = np.array([sum(float(x or 0) for x in r[2:]) for r in rows])
        y = np.array([r[0] in pos for r in rows])
        eg = np.array([g.get(r[0], 0) > 0 for r in rows])
        em = np.array([m.get(r[0], 0) > 0 for r in rows])
        out.append({"repo": repo_name, "type": fault_type(e),
                    "goto": mh_parts(loc, evid, eg, y), "macro": mh_parts(loc, evid, em, y),
                    "goto50": mh_parts(loc, evid, eg, y, 50), "macro50": mh_parts(loc, evid, em, y, 50),
                    "share_goto": float(eg.mean()), "share_macro": float(em.mean())})
    con.close()
    return out


def rr(evs, key):
    n = sum(e[key][0] for e in evs)
    d = sum(e[key][1] for e in evs)
    return n / d if d else float("nan")


def boot_rr(evs, key, rng):
    arr = np.array([e[key] for e in evs])
    b = []
    for _ in range(ITERS):
        s = arr[rng.integers(0, len(arr), len(arr))].sum(axis=0)
        if s[1] > 0:
            b.append(s[0] / s[1])
    return np.array(b)


def boot_ratio(a_evs, b_evs, key, rng):
    A, B = np.array([e[key] for e in a_evs]), np.array([e[key] for e in b_evs])
    out = []
    for _ in range(ITERS):
        sa, sb = A[rng.integers(0, len(A), len(A))].sum(axis=0), B[rng.integers(0, len(B), len(B))].sum(axis=0)
        if sa[1] > 0 and sb[1] > 0 and sb[0] > 0:
            out.append((sa[0] / sa[1]) / (sb[0] / sb[1]))
    return np.array(out)


def main() -> int:
    t0 = time.time()
    evs = []
    for r, db in DBS.items():
        evs += collect(r, db)
        print(f"{r}: collected ({time.time() - t0:.0f}s)", flush=True)
    ctx = []
    for r, db in CONTEXT.items():
        if db.exists():
            ctx += collect(r, db)
    types = Counter((e["repo"], e["type"]) for e in evs)
    bounds = [e for e in evs if e["type"] == "bounds"]
    life = [e for e in evs if e["type"] == "lifetime"]
    spawn = iter(np.random.SeedSequence(SEED).spawn(8))
    L = ["# KF-H1..H4 — construct split and keyword → fault type (SCORED)", "",
         f"- events: {len(evs)} (nDPI + openssl pooled); fault types: " + ", ".join(f"{r}/{t} {n}" for (r, t), n in sorted(types.items())),
         f"- files exposed (median per T0): goto {np.median([e['share_goto'] for e in evs]):.1%}, function-like macro {np.median([e['share_macro'] for e in evs]):.1%}", "",
         "| claim | what | estimate | one-sided lo (α=0.0025) | 90% CI | verdict |", "|---|---|---:|---:|---|---|"]
    for c, key, what in (("KF-H1", "goto", "RR(goto), all security fixes"), ("KF-H2", "macro", "RR(function-like macro), all security fixes")):
        b = boot_rr(evs, key, np.random.default_rng(next(spawn)))
        est, lo, ci = rr(evs, key), float(np.quantile(b, ALPHA)), (float(np.quantile(b, 0.05)), float(np.quantile(b, 0.95)))
        L.append(f"| **{c}** | {what} | {est:.3f} | {lo:.3f} | [{ci[0]:.3f}, {ci[1]:.3f}] | **{'SUPPORTED' if lo > 1 else 'not supported'}** |")
    for c, key, num, den, what in (("KF-H3", "goto", life, bounds, "RR(goto | lifetime) / RR(goto | bounds)"),
                                   ("KF-H4", "macro", bounds, life, "RR(macro | bounds) / RR(macro | lifetime)")):
        if len(num) < 20 or len(den) < 20:
            L.append(f"| **{c}** | {what} | — | — | — | **not evaluable** (lifetime {len(life)}, bounds {len(bounds)} events) |")
            continue
        b = boot_ratio(num, den, key, np.random.default_rng(next(spawn)))
        est = rr(num, key) / rr(den, key)
        lo, ci = float(np.quantile(b, ALPHA)), (float(np.quantile(b, 0.05)), float(np.quantile(b, 0.95)))
        v = "SUPPORTED" if lo > 1 else "replicated null (equivalence)" if 0.8 < ci[0] and ci[1] < 1.25 else "not supported (inconclusive)"
        L.append(f"| **{c}** | {what} | {est:.3f} | {lo:.3f} | [{ci[0]:.3f}, {ci[1]:.3f}] | **{v}** |")
    L += ["", "## Descriptive (no verdicts)", "", "| subset | events | RR goto | RR macro | RR goto (50 LOC bins) | RR macro (50 LOC bins) |",
          "|---|---:|---:|---:|---:|---:|"]
    subsets = [("all", evs), ("bounds", bounds), ("lifetime", life), ("other", [e for e in evs if e["type"] == "other"])]
    subsets += [(f"{r} all", [e for e in evs if e["repo"] == r]) for r in DBS]
    subsets += [("curl all (context, never scored)", ctx), ("curl bounds (context)", [e for e in ctx if e["type"] == "bounds"]),
                ("curl lifetime (context)", [e for e in ctx if e["type"] == "lifetime"])]
    for lab, s in subsets:
        if s:
            L.append(f"| {lab} | {len(s)} | {rr(s, 'goto'):.2f} | {rr(s, 'macro'):.2f} | {rr(s, 'goto50'):.2f} | {rr(s, 'macro50'):.2f} |")
    L += ["", f"Runtime {time.time() - t0:.0f}s · event bootstrap {ITERS} rounds, seed {SEED}."]
    (DOCS_DIR / "kf.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
