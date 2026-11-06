#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""SFS-H1..H4 (docs/sfs_hypotheses.md): structural-fingerprint stability, name-free survival, turnover vs fix classes.
Uses gitgalaxy-population-analyses' structural-fingerprint-scanner through its Python API (as its CLI does).

    SFS_SRC=<popan>/structural-fingerprint-scanner/src python tools/sfs_eval.py --scratch <dir>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, os.environ["SFS_SRC"])
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from structural_fingerprint.compare import compare_cohort  # noqa: E402
from structural_fingerprint.fingerprint import build  # noqa: E402
from structural_fingerprint.reference import load_reference  # noqa: E402
from structural_fingerprint.scan_io import load_scan  # noqa: E402
from structural_fingerprint.timeline import _kept  # noqa: E402
from structural_fingerprint.twins import TwinParams, find_twins  # noqa: E402

from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402

WT = pathlib.Path(os.environ.get("TC_WORKTREES", "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees"))
DBS = {"curl": WT / "forward-asof/dbs/curl_out/curl_galaxy_master.db",
       "ndpi": WT / "forward-asof/dbs/ndpi_out/ndpi_galaxy_master.db",
       "openssl": WT / "frec/dbs/openssl_out/openssl_galaxy_master.db",
       "harfbuzz": WT / "sc-class/dbs/harfbuzz_out/harfbuzz_galaxy_master.db",
       "libarchive": WT / "sc-class/dbs/libarchive_out/libarchive_galaxy_master.db"}
BUG_REPOS = ("curl", "ndpi", "openssl", "harfbuzz")
YEAR, SEED, PERMS = 365.25 * 86400, 2982, 10000


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def yearly(r):
    repo = POOL_DIR / r
    con = sqlite3.connect(f"file:{DBS[r]}?mode=ro", uri=True)
    have = {x[0] for x in con.execute("SELECT DISTINCT commit_hash FROM repo_data")}
    con.close()
    out, years = [], set()
    revs = json.loads((REPO_ROOT / "walks" / f"{r}_quarterly.json").read_text())["revisions"]
    snaps = []
    for s in revs:
        if s.get("status", "ok") == "ok" and s["sha"] in have:
            snaps.append((int(_git(repo, "show", "-s", "--format=%ct", s["sha"]).strip()), s["sha"]))
    for ct, sha in sorted(snaps):
        y = dt.datetime.fromtimestamp(ct, dt.timezone.utc).year
        if y not in years:
            years.add(y)
            out.append({"year": y, "ct": ct, "sha": sha})
    return out


def export(r, sha, dest: pathlib.Path):
    """Single-commit copy of the scan tables sfs reads."""
    db = dest / f"{r}_galaxy_master.db"
    if db.exists():
        return db
    dest.mkdir(parents=True, exist_ok=True)
    tmp = db.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    src = sqlite3.connect(f"file:{DBS[r]}?mode=ro", uri=True)
    ddl = {n: s for n, s in src.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")}
    src.close()
    con = sqlite3.connect(tmp)
    for t in ("file_data", "function_data", "repo_data", "fcall_data"):
        if t in ddl:
            con.execute(ddl[t])
    con.execute("ATTACH DATABASE ? AS src", (f"file:{DBS[r]}?mode=ro",))
    con.execute("INSERT INTO file_data SELECT * FROM src.file_data WHERE commit_hash = ?", (sha,))
    con.execute("INSERT INTO function_data SELECT f.* FROM src.function_data f WHERE f.file_id IN (SELECT id FROM file_data)")
    con.execute("INSERT INTO repo_data SELECT * FROM src.repo_data WHERE commit_hash = ?", (sha,))
    con.commit()
    con.execute("DETACH DATABASE src")
    con.close()
    tmp.rename(db)
    return db


def name_survival(db_a, db_b, min_loc=6):
    def funcs(db):
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        rows = con.execute("SELECT fd.file_path, f.func_name, f.loc FROM function_data f JOIN file_data fd ON f.file_id = fd.id "
                           "WHERE fd.language IN ('c','cpp') AND f.func_name IS NOT NULL AND f.func_name != ''").fetchall()
        con.close()
        d = {}
        for p, n, loc in rows:
            d.setdefault((p, n), loc or 0)
        return d
    a, b = funcs(db_a), funcs(db_b)
    van = [k for k in a if k not in b]
    new = [k for k in b if k not in a]
    vn, nn = defaultdict(list), defaultdict(list)
    for k in van:
        vn[k[1]].append(k)
    for k in new:
        nn[k[1]].append(k)
    moved = {vn[n][0] for n in vn if len(vn[n]) == 1 and len(nn.get(n, [])) == 1}
    elig = [k for k, loc in a.items() if loc >= min_loc]
    return float(np.mean([(k in b) or (k in moved) for k in elig])) if elig else float("nan")


def fix_shares(r, t0, t1):
    xc = json.loads((REPO_ROOT / "events" / f"{r}_xc.json").read_text())["events"]
    if r == "harfbuzz":
        lat = {e["sha"] for e in json.loads((REPO_ROOT / "events" / "harfbuzz.json").read_text())["events"] if e["class"] == "security-fix"}
        ev = [{**e, "class": "latent"} if e["sha"] in lat else e for e in xc]
        # OSV latent fixes absent from the XC file still count as latent
        known = {e["sha"] for e in xc}
        repo = POOL_DIR / r
        for s in lat - known:
            ct = _git(repo, "show", "-s", "--format=%ct", s).strip()
            if ct:
                ev.append({"sha": s, "ct": int(ct), "class": "latent"})
    else:
        ev = xc
    win = [e for e in ev if t0 < e["ct"] <= t1]
    n = len(win)
    c = defaultdict(int)
    for e in win:
        c[e["class"]] += 1
    return n, {k: c[k] / n if n else float("nan") for k in ("regression", "latent", "extrinsic", "other-fix")}


def within_perm(groups, f, rng):
    """Mean over repos of f(x, y); permutation p by shuffling y within each repo."""
    obs = float(np.mean([f(x, y) for x, y in groups]))
    cnt = 0
    for _ in range(PERMS):
        v = float(np.mean([f(x, rng.permutation(y)) for x, y in groups]))
        cnt += v >= obs
    return obs, (cnt + 1) / (PERMS + 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=pathlib.Path, required=True)
    a = ap.parse_args()
    t0 = time.time()
    ref = load_reference("structure")
    params = TwinParams()
    fps, rows = [], []
    for r in DBS:
        ys = yearly(r)
        prev_fp = prev_db = None
        for k, s in enumerate(ys):
            db = export(r, s["sha"], a.scratch / r / f"{s['year']}_{s['sha'][:12]}")
            fp = build(load_scan(db, ref.signal_columns, name=f"{r}@{s['year']}"), ref, min_loc=3)
            fps.append((r, s, fp))
            if prev_fp is not None:
                pt, st = prev_fp.functions, fp.functions
                ret = _kept(pt, find_twins(pt, st, params), find_twins(st, pt, params), params.min_loc)
                ns = name_survival(prev_db, db)
                n, sh = fix_shares(r, ys[k - 1]["ct"], s["ct"])
                rows.append({"repo": r, "year": ys[k - 1]["year"], "retention": ret, "name_survival": ns, "n_fix": n, **sh})
            prev_fp, prev_db = fp, db
        print(f"{r}: {len(ys)} yearly snapshots ({time.time() - t0:.0f}s)", flush=True)

    # H1: nearest neighbour by profile distance, other eras only
    coh = compare_cohort([fp for _, _, fp in fps])
    D = coh.composite
    correct = 0
    for i, (ri, si, _) in enumerate(fps):
        best = None
        for j, (rj, sj, _) in enumerate(fps):
            if i == j or (rj == ri and abs(sj["ct"] - si["ct"]) < 5 * YEAR):
                continue
            if best is None or D[i, j] < D[i, best]:
                best = j
        correct += fps[best][0] == ri
    acc = correct / len(fps)
    # H2
    ok = [x for x in rows if not np.isnan(x["retention"]) and not np.isnan(x["name_survival"])]
    rho2 = spearmanr([x["retention"] for x in ok], [x["name_survival"] for x in ok]).statistic
    # H3/H4
    rng = np.random.default_rng(SEED)
    groups3, groups4 = [], []
    for r in BUG_REPOS:
        xs = [x for x in rows if x["repo"] == r and x["n_fix"] >= 5 and not np.isnan(x["retention"])]
        if len(xs) < 4:
            continue
        turn = np.array([1 - x["retention"] for x in xs])
        groups3.append((turn, np.array([x["regression"] for x in xs])))
        groups4.append((turn, np.array([[x["regression"], x["latent"]] for x in xs])))
    f3 = lambda x, y: spearmanr(x, y).statistic  # noqa: E731
    obs3, p3 = within_perm(groups3, f3, rng)
    def f4(x, y):
        return spearmanr(x, y[:, 0]).statistic - spearmanr(x, y[:, 1]).statistic
    obs4, p4 = within_perm(groups4, f4, rng)

    L = ["# SFS-H1..H4 — structural-fingerprint stability, name-free survival, turnover vs fix classes (SCORED)", "",
         f"- sfs: structure lens, min-loc 3, twins min-loc {params.min_loc}, ratio {params.ratio}, FDR {params.fdr}; "
         f"{len(fps)} yearly snapshots over {len(DBS)} repos; call edges absent in these scans (call-graph component zero for all)", "",
         "| claim | result | verdict |", "|---|---|---|",
         f"| **SFS-H1** fingerprints are stable identities (nearest neighbour, other eras ≥ 5 y) | accuracy **{acc:.1%}** over {len(fps)} snapshots | **{'SUPPORTED' if acc >= 0.90 else 'not supported'}** |",
         f"| **SFS-H2** name-free retention agrees with name-based survival | Spearman **{rho2:+.2f}** over {len(ok)} repo-years | **{'SUPPORTED' if rho2 >= 0.5 else 'not supported'}** |",
         f"| **SFS-H3** turnover goes with regression share | mean within-repo ρ **{obs3:+.2f}**, permutation p {p3:.4f} ({len(groups3)} repos) | **{'SUPPORTED' if obs3 > 0 and p3 < 0.01 else 'not supported'}** |",
         f"| **SFS-H4** …more than with CVE share | mean within-repo Δρ **{obs4:+.2f}**, p {p4:.4f} | **{'SUPPORTED' if obs4 > 0 and p4 < 0.01 else 'not supported'}** |",
         "", "## Per repo (descriptive)", "",
         "| repo | years | median retention | median name-based survival | lowest-retention years | ρ(turnover, regression share) | ρ(turnover, latent share) | ρ(turnover, extrinsic share) |",
         "|---|---:|---:|---:|---|---:|---:|---:|"]
    for r in DBS:
        xs = [x for x in rows if x["repo"] == r]
        low = sorted(xs, key=lambda x: x["retention"])[:3]
        good = [x for x in xs if x["n_fix"] >= 5]
        def rho(key):
            v = [(1 - x["retention"], x[key]) for x in good if not np.isnan(x[key])]
            return spearmanr(*zip(*v)).statistic if len(v) >= 4 else float("nan")
        L.append(f"| {r} | {len(xs)} | {np.median([x['retention'] for x in xs]):.2f} | {np.median([x['name_survival'] for x in xs]):.2f} | "
                 + ", ".join(f"{x['year']} ({x['retention']:.2f})" for x in low) + f" | {rho('regression'):+.2f} | {rho('latent'):+.2f} | {rho('extrinsic'):+.2f} |")
    L += ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED}, {PERMS} permutations."]
    (DOCS_DIR / "sfs.md").write_text("\n".join(L) + "\n")
    (a.scratch / "sfs_rows.json").write_text(json.dumps(rows, indent=1))
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
