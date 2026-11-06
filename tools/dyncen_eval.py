#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""DYN-H1/H2 (registered 2026-10-23) and CEN-H1/H2 (registered 2026-11-06), verbatim.

    python tools/dyncen_eval.py dyn --repo ndpi --db <ablated T0 DB>
    python tools/dyncen_eval.py cen --repo openssl --db <quarterly as-of DB> --langs c
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from bh_eval import auc_numpy, bootstrap_chunk_lift, event_offsets  # noqa: E402
from centrality_bands import ABS_CUTS, ABS_LABELS  # noqa: E402
from exposure_delta import diff_statuses  # noqa: E402
from signal_anatomy import parent_child  # noqa: E402

SEED, ITERS, MIN_POS, EQUIV = 2982, 5000, 20, 0.02
EVIDENCE_COLUMNS = ("struct_branch", "state_danger", "state_pointers", "state_memory_alloc", "state_bailout_hits",
                    "state_halt_hits", "state_cast_hits", "state_fragile_debt", "arch_io", "arch_concurrency")
DAY = 86400


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def lift_cell(score, ctrl, pos, cluster, n_clusters, alpha, seed):
    """Pooled AUC(score) - AUC(ctrl) with a cluster bootstrap (bh_eval's engine). Rows must be contiguous per cluster."""
    starts, sizes = event_offsets(cluster, n_clusters)
    obs = auc_numpy(score, pos) - auc_numpy(ctrl, pos)
    boot = bootstrap_chunk_lift(score, ctrl, pos, starts, sizes, n_clusters, ITERS, seed)
    b = np.sort(boot[~np.isnan(boot)])
    q = lambda f: float(np.quantile(b, f)) if b.size else float("nan")  # noqa: E731
    return {"n": int(score.size), "n_pos": int(pos.sum()), "auc": auc_numpy(score, pos), "auc_ctrl": auc_numpy(ctrl, pos),
            "lift": float(obs), "lo": q(alpha), "ci90": (q(0.05), q(0.95)), "alpha": alpha}


def verdict(c):
    if c["n_pos"] < MIN_POS:
        return "not evaluable (< 20 positives)"
    if c["lift"] > 0 and c["lo"] > 0:
        return "SUPPORTED"
    if -EQUIV < c["ci90"][0] and c["ci90"][1] < EQUIV:
        return "replicated null (equivalence)"
    return "not supported (inconclusive)"


def bands(loc):
    return np.searchsorted(np.asarray(ABS_CUTS, dtype=float), loc, side="left")


# ------------------------------------------------------------------------------------------------ DYN
def dyn(a):
    t0 = time.time()
    repo = POOL_DIR / a.repo
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    events = [e for e in json.loads((REPO_ROOT / "events" / f"{a.repo}.json").read_text())["events"]
              if e["class"] == "security-fix" and e.get("on_master", True)]
    cols = ", ".join(EVIDENCE_COLUMNS)
    loc_l, heat_l, ev_l, pos_l, eid_l, stratum_num, stratum_den = [], [], [], [], [], [], []
    skip = {}
    n_ev = 0
    for e in events:
        parent, child = parent_child(repo, e["sha"])
        if parent is None:
            skip["no parent"] = skip.get("no parent", 0) + 1
            continue
        rows = con.execute(f"SELECT file_path, total_loc, state_heat_triggers, {cols} FROM file_data WHERE commit_hash=?",
                           (parent,)).fetchall()
        if not rows:
            skip["parent not scanned"] = skip.get("parent not scanned", 0) + 1
            continue
        snap = {r[0] for r in rows}
        st = diff_statuses(repo, parent, child)
        positives = {s["old_path"] for _p, s in st.items() if s["status"] == "touched" and s["old_path"] in snap}
        if not positives:
            skip["no touched file in parent snapshot"] = skip.get("no touched file in parent snapshot", 0) + 1
            continue
        loc = np.array([float(r[1] or 0) for r in rows])
        heat = np.array([float(r[2] or 0) for r in rows])
        evid = np.array([sum(float(x or 0) for x in r[3:]) for r in rows])
        y = np.array([r[0] in positives for r in rows])
        # DYN-H2 strata: LOC decile x evidence quartile, edges per T0 snapshot (event is the outer stratum)
        ld = np.searchsorted(np.quantile(loc, np.linspace(0, 1, 11)[1:-1]), loc, side="right")
        eq = np.searchsorted(np.quantile(evid, [0.25, 0.5, 0.75]), evid, side="right")
        num = den = 0.0
        exp = heat > 0
        for s in np.unique(ld * 10 + eq):
            m = (ld * 10 + eq) == s
            n1, n0 = exp[m].sum(), (~exp[m]).sum()
            N = n1 + n0
            if n1 == 0 or n0 == 0:
                continue
            a_ = (y[m] & exp[m]).sum()
            c_ = (y[m] & ~exp[m]).sum()
            num += a_ * n0 / N
            den += c_ * n1 / N
        stratum_num.append(num)
        stratum_den.append(den)
        loc_l.append(loc), heat_l.append(heat), ev_l.append(evid), pos_l.append(y), eid_l.append(np.full(len(rows), n_ev))
        n_ev += 1
    con.close()
    loc, heat, pos, eid = map(np.concatenate, (loc_l, heat_l, pos_l, eid_l))
    b = bands(loc)
    powered = [k for k in range(4) if pos[b == k].sum() >= MIN_POS]
    alpha1 = 0.01 / max(len(powered), 1)
    cells = {}
    for k in range(4):
        m = b == k
        cells[k] = lift_cell(heat[m], loc[m], pos[m], eid[m], n_ev, alpha1, SEED + k)
    h1 = "SUPPORTED" if any(verdict(cells[k]) == "SUPPORTED" for k in powered) else (
        "replicated null (equivalence)" if powered and all(verdict(cells[k]) == "replicated null (equivalence)" for k in powered)
        else "not supported (inconclusive)")
    num, den = np.array(stratum_num), np.array(stratum_den)
    rr = num.sum() / den.sum() if den.sum() else float("nan")
    rng = np.random.default_rng(SEED)
    boots = []
    for _ in range(ITERS):
        idx = rng.integers(0, n_ev, n_ev)
        d = den[idx].sum()
        if d > 0:
            boots.append(num[idx].sum() / d)
    boots = np.sort(np.array(boots))
    lo2, ci2 = float(np.quantile(boots, 0.01)), (float(np.quantile(boots, 0.05)), float(np.quantile(boots, 0.95)))
    h2 = ("SUPPORTED" if lo2 > 1.0 else "replicated null (equivalence)" if 0.80 < ci2[0] and ci2[1] < 1.25
          else "not supported (inconclusive)")
    L = [f"# DYN-H1 / DYN-H2 — per-file dynamism (`state_heat_triggers`): {a.repo} (SCORED)", "",
         f"- DB `{a.db.name}`; {n_ev} security-fix events scored; skipped {skip or 'none'}; {int(pos.sum())} positives over {pos.size:,} T0 file rows",
         f"- files with any dynamism: {np.mean(heat > 0):.1%}", "",
         f"## DYN-H1 (bands; powered: {', '.join(ABS_LABELS[k] for k in powered) or 'none'}; α = 0.01/{len(powered)})", "",
         "| band | n | positives | AUC dynamism | AUC LOC | lift | lo | 90% CI | cell |", "|---|---:|---:|---:|---:|---:|---:|---|---|"]
    for k in range(4):
        c = cells[k]
        L.append(f"| {ABS_LABELS[k]} | {c['n']:,} | {c['n_pos']} | {c['auc']:.3f} | {c['auc_ctrl']:.3f} | {c['lift']:+.3f} | "
                 f"{c['lo']:+.3f} | [{c['ci90'][0]:+.3f}, {c['ci90'][1]:+.3f}] | {verdict(c)} |")
    L += ["", f"**DYN-H1: {h1}**", "", "## DYN-H2 (Mantel-Haenszel, exposed = any dynamism; strata event × LOC decile × evidence quartile)", "",
          f"- rate ratio **{rr:.3f}**, one-sided lo (α = 0.01) {lo2:.3f}, 90% CI [{ci2[0]:.3f}, {ci2[1]:.3f}] → **{h2}**", "",
          f"Runtime {time.time() - t0:.0f}s · event bootstrap {ITERS} rounds, seed {SEED}."]
    (DOCS_DIR / f"dyn_{a.repo}.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


# ------------------------------------------------------------------------------------------------ CEN
def cen(a):
    t0 = time.time()
    repo = POOL_DIR / a.repo
    langs = tuple(a.langs.split(","))
    snaps = [s for s in json.loads((REPO_ROOT / "walks" / f"{a.repo}_quarterly.json").read_text())["revisions"]
             if s.get("status", "ok") == "ok"]
    ev = [e for e in json.loads((REPO_ROOT / "events" / f"{a.repo}_xc.json").read_text())["events"]
          if e["class"] in ("latent", "regression", "other-fix")]
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    loc_l, pr_l, pop_l, pos_l, cid_l = [], [], [], [], []
    k = 0
    for s in snaps:
        ct = int(_git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())
        rows = con.execute(f"SELECT file_path, total_loc, pagerank_score, popularity FROM file_data WHERE commit_hash=? AND "
                           f"language IN ({','.join('?' * len(langs))})", (s["sha"], *langs)).fetchall()
        if not rows:
            continue
        files = set()
        for e in ev:
            if ct < e["ct"] <= ct + 180 * DAY:
                files.update(e["c_files"])
        loc_l.append(np.array([float(r[1] or 0) for r in rows]))
        pr_l.append(np.array([float(r[2] or 0) for r in rows]))
        pop_l.append(np.array([float(r[3] or 0) for r in rows]))
        pos_l.append(np.array([r[0] in files for r in rows]))
        cid_l.append(np.full(len(rows), k))
        k += 1
    con.close()
    loc, pr, pop, pos, cid = map(np.concatenate, (loc_l, pr_l, pop_l, pos_l, cid_l))
    b = bands(loc)
    L = [f"# CEN-H1 / CEN-H2 — mid-band centrality: {a.repo} (SCORED)", "",
         f"- {k} quarterly snapshots; files `language IN {langs}`; outcome = latent/regression/other-fix touch in (t, t+180 d]", "",
         "| claim | band | n | positives | AUC score | AUC LOC | lift | lo (α=0.005) | 90% CI | verdict |",
         "|---|---|---:|---:|---:|---:|---:|---:|---|---|"]
    for claim, sc, name in (("CEN-H1", pr, "pagerank_score"), ("CEN-H2", pop, "popularity")):
        for band in range(4):
            m = b == band
            c = lift_cell(sc[m], loc[m], pos[m], cid[m], k, 0.005, SEED + band + (10 if claim == "CEN-H2" else 0))
            tag = f"**{claim}** `{name}`" if band == 2 else f"(descriptive) `{name}`"
            v = verdict(c) if band == 2 else "—"
            L.append(f"| {tag} | {ABS_LABELS[band]} | {c['n']:,} | {c['n_pos']} | {c['auc']:.3f} | {c['auc_ctrl']:.3f} | "
                     f"{c['lift']:+.3f} | {c['lo']:+.3f} | [{c['ci90'][0]:+.3f}, {c['ci90'][1]:+.3f}] | {'**' + v + '**' if band == 2 else v} |")
    L += ["", f"Runtime {time.time() - t0:.0f}s · snapshot-cluster bootstrap {ITERS} rounds, seed {SEED}."]
    (DOCS_DIR / f"cen_{a.repo}.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("which", choices=["dyn", "cen"])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--db", required=True, type=pathlib.Path)
    ap.add_argument("--langs", default="c")
    a = ap.parse_args()
    (dyn if a.which == "dyn" else cen)(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
