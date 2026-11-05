#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""FWD-H1..H3: forward prediction from engine-native, as-of history (tc#29).

Implements the registration in docs/HYPOTHESES.md (2026-11-05) verbatim:

  * snapshots: walks/<repo>_quarterly.json (tools/fwd_snapshots.py);
  * candidates: C files in each snapshot, read from an as-of scan
    (rescan_meta.json must say history=asof);
  * positive: a candidate touched by a fix-class event dated in (t, t+180 d]
    (walk_trajectories' rename-aware touched-file harvest: parent or child path);
  * INSTRUMENT GATE first: per snapshot, Spearman(raw_churn_freq, independent
    git-log count over [t-365 d, t], --no-merges, blame-ignore revs excluded)
    >= 0.95 over C files with >= 1 commit. Any failure stops the run;
  * per absolute-NLOC band (<=22, 23-48, 49-108, >108 by total_loc): lift =
    AUC(feature) - AUC(total_loc); one-sided snapshot-cluster bootstrap
    (5,000 rounds, seed 2982) lower bound at alpha 0.01 / #powered bands;
    two-sided 90% CI for the equivalence null [-0.02, +0.02]; < 20 positives
    = not evaluable.

--mode scored writes verdicts (unseen repos only: nDPI, openssl). --mode
exploratory (curl) writes the same tables with no verdicts, labelled as such.

    python tools/fwd_eval.py --repo ndpi --events events/ndpi.json --mode scored
    python tools/fwd_eval.py --repo curl --events events/curl.json events/curl_bugs.json --mode exploratory
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, REPO_ROOT  # noqa: E402
from centrality_bands import ABS_CUTS, ABS_LABELS, absolute_bands  # noqa: E402
from scan_pair import history_db, out_dir_for, resolve_repo  # noqa: E402
from walk_trajectories import harvest_touched_files  # noqa: E402

SEED = 2982
ITERS = 5000
ALPHA = 0.01
OUTCOME_DAYS = 180
WINDOW_DAYS = 365
MIN_POS = 20
EQUIV = 0.02
GATE_RHO = 0.95
HCM_GATE_RHO = 0.99
DAY = 86400
FIX_CLASSES = {"security-fix", "bugfix-fixes", "bugfix-bug", "regression"}
SCORED = {"FWD-H1": "raw_churn_freq", "FWD-H2": "ownership_entropy", "FWD-H3": "change_entropy"}
EXPLORATORY_EXTRA = ["silo_risk", "risk_stability"]


def _git(repo, *args) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          check=True, errors="replace").stdout


# --------------------------------------------------------------------- AUC
def weighted_auc(scores: np.ndarray, labels: np.ndarray, w: np.ndarray) -> float:
    """Mann-Whitney AUC with per-row weights (cluster-bootstrap multiplicities), ties = 1/2."""
    pos_w = w * labels
    neg_w = w * (1 - labels)
    P, N = pos_w.sum(), neg_w.sum()
    if P == 0 or N == 0:
        return float("nan")
    order = np.argsort(scores, kind="mergesort")
    s, pw, nw = scores[order], pos_w[order], neg_w[order]
    uniq, start = np.unique(s, return_index=True)
    pos_g = np.add.reduceat(pw, start)
    neg_g = np.add.reduceat(nw, start)
    neg_below = np.cumsum(neg_g) - neg_g
    return float((pos_g * (neg_below + 0.5 * neg_g)).sum() / (P * N))


# --------------------------------------------------------------------- data
def load_rows(db: pathlib.Path, repo_name: str, snaps: list[dict], feats: list[str]):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    have = {r[1] for r in con.execute("PRAGMA table_info(file_data)")}
    feats = [f for f in feats if f in have]
    sel = ", ".join(["file_path", "total_loc", *feats])
    rows, missing = [], []
    for k, s in enumerate(snaps):
        got = con.execute(f"SELECT {sel} FROM file_data WHERE repo_name=? AND commit_hash=? "
                          "AND language='c'", (repo_name, s["sha"])).fetchall()
        if not got:
            missing.append(s["ref"])
        rows.extend((k, *r) for r in got)
    con.close()
    return rows, feats, missing


def independent_churn_freq(repo, sha: str, ct: int, ignored: set) -> dict[str, float]:
    """FWD amendment 1: an independent reconstruction of the engine's raw_churn_freq,
    commits_in_window / sqrt(max(weeks since last change, 1)), straight from git.
    Window = no-merges commits with committer time in [t - 365 d, t]; blame-ignore revs
    excluded; last change = newest author time of a qualifying commit at or before t."""
    out = _git(repo, "-c", "core.quotepath=off", "log", sha, "--no-merges", "--name-only",
               "--pretty=format:@@%H|%at|%ct")
    counts: dict[str, int] = defaultdict(int)
    last: dict[str, int] = {}
    skip, at, cct = False, 0, 0
    for line in out.splitlines():
        if line.startswith("@@"):
            h, a, c = line[2:].split("|")
            skip, at, cct = h in ignored, int(a), int(c)
            continue
        f = line.strip()
        if not f or skip:
            continue
        if cct >= ct - WINDOW_DAYS * DAY:
            counts[f] += 1
            last[f] = max(last.get(f, 0), at)
        elif f not in last:
            last[f] = at
    return {f: counts.get(f, 0) / (max(max(ct - t, 0) / (7 * DAY), 1.0) ** 0.5) for f, t in last.items()}


def ignored_revs(repo, sha: str) -> set:
    r = subprocess.run(["git", "-C", str(repo), "show", f"{sha}:.git-blame-ignore-revs"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return set()
    return {ln.strip() for ln in r.stdout.splitlines() if ln.strip() and not ln.startswith("#")}


def hcm_gate(repo, snaps, by_snap, ce_idx: int, cache_dir: pathlib.Path) -> list[dict]:
    """FWD-H3's registration condition: per snapshot, Spearman(engine change_entropy,
    tools/hcm_variants.py HCM1_LD_30 from the same commit) >= 0.99 over C files where
    either is non-zero."""
    from hcm_variants import compute_all_variants, raw_commit_walk

    out = []
    for k, s in enumerate(snaps):
        walk = raw_commit_walk(repo, s["sha"], cache_dir=cache_dir)
        ref = compute_all_variants(walk["commits"], walk["parent_epoch"], walk["window_days"])["HCM1_LD_30"]
        pairs = [(r[ce_idx] or 0.0, ref.get(r[1], 0.0)) for r in by_snap[k]]
        pairs = [p for p in pairs if p[0] or p[1]]
        rho = spearmanr([p[0] for p in pairs], [p[1] for p in pairs]).statistic if len(pairs) >= 3 else float("nan")
        out.append({"ref": s["ref"], "n": len(pairs), "rho": rho})
    return out


# --------------------------------------------------------------------- stats
def cluster_bootstrap(snap_idx, scores_f, scores_l, labels, n_snaps, rng, iters):
    lifts = np.empty(iters)
    for i in range(iters):
        draw = rng.integers(0, n_snaps, n_snaps)
        mult = np.bincount(draw, minlength=n_snaps).astype(float)
        w = mult[snap_idx]
        lifts[i] = weighted_auc(scores_f, labels, w) - weighted_auc(scores_l, labels, w)
    return lifts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--events", nargs="+", required=True, type=pathlib.Path)
    ap.add_argument("--mode", choices=["scored", "exploratory"], required=True)
    ap.add_argument("--snapshots", type=pathlib.Path, default=None)
    ap.add_argument("--iters", type=int, default=ITERS)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    args = ap.parse_args()
    t_start = time.time()

    repo = resolve_repo(args.repo)
    out_dir = out_dir_for(repo)
    db = history_db(out_dir)
    meta_p = out_dir / "rescan_meta.json"
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    if meta.get("history") != "asof":
        sys.exit(f"{db}: rescan_meta.json does not say history=asof -- refusing (registration requires as-of scans)")
    snaps = json.loads((args.snapshots or REPO_ROOT / "walks" / f"{repo.name}_quarterly.json").read_text())["revisions"]
    for s in snaps:
        s["ct"] = int(_git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())

    feats = list(SCORED.values()) + EXPLORATORY_EXTRA
    rows, feats, missing = load_rows(db, repo.name, snaps, feats)
    if missing:
        sys.exit(f"{len(missing)} snapshots not in the DB (scan them first): {missing[:5]}")
    print(f"{len(rows)} (snapshot, C file) rows over {len(snaps)} snapshots; features {feats}", flush=True)

    # ---- FWD amendment 1: drop snapshots where the engine reports no usable history
    by_snap = defaultdict(list)
    for r in rows:
        by_snap[r[0]].append(r)
    ci = 3 + feats.index("raw_churn_freq")
    si = 3 + feats.index("risk_stability")
    unusable = {k for k in range(len(snaps))
                if by_snap[k] and all((r[si] == 50.0 and (r[ci] or 0.0) == 0.0) for r in by_snap[k])}
    if unusable:
        print(f"excluded (engine-reported unusable history): {[snaps[k]['ref'] for k in sorted(unusable)]}", flush=True)
        keep = [k for k in range(len(snaps)) if k not in unusable]
        remap = {old: new for new, old in enumerate(keep)}
        excluded_refs = [snaps[k]["ref"] for k in sorted(unusable)]
        snaps = [snaps[k] for k in keep]
        rows = [(remap[r[0]], *r[1:]) for r in rows if r[0] in remap]
        by_snap = defaultdict(list)
        for r in rows:
            by_snap[r[0]].append(r)
    else:
        excluded_refs = []

    # ---- instrument gate (binding)
    gate = []
    for k, s in enumerate(snaps):
        ind = independent_churn_freq(repo, s["sha"], s["ct"], ignored_revs(repo, s["sha"]))
        pairs = [(r[ci] or 0.0, ind[r[1]]) for r in by_snap[k] if r[1] in ind and ind[r[1]] > 0]
        rho = spearmanr([p[0] for p in pairs], [p[1] for p in pairs]).statistic if len(pairs) >= 3 else float("nan")
        gate.append({"ref": s["ref"], "n": len(pairs), "rho": rho})
    evaluable_gate = [g for g in gate if g["n"] >= 3]
    failed = [g for g in evaluable_gate if not (g["rho"] >= GATE_RHO)]
    print(f"instrument gate: {len(evaluable_gate) - len(failed)}/{len(evaluable_gate)} snapshots pass "
          f"(min rho {min(g['rho'] for g in evaluable_gate):.4f})", flush=True)

    # ---- FWD-H3 condition: the engine's change entropy is the registered HCM1_LD_30
    hcm_ok, hcm_rows = False, []
    if "change_entropy" in feats:
        hcm_rows = hcm_gate(repo, snaps, by_snap, 3 + feats.index("change_entropy"), out_dir / "hcmwalk_cache")
        ev = [g for g in hcm_rows if g["n"] >= 3]
        hcm_ok = bool(ev) and all(g["rho"] >= HCM_GATE_RHO for g in ev)
        print(f"HCM parity: {sum(g['rho'] >= HCM_GATE_RHO for g in ev)}/{len(ev)} snapshots >= {HCM_GATE_RHO} "
              f"(min {min(g['rho'] for g in ev):.4f})", flush=True)

    # ---- outcome labels
    events = []
    for f in args.events:
        for e in json.loads(f.read_text())["events"]:
            if e["class"] in FIX_CLASSES:
                events.append(e)
    uniq = {e["sha"]: e for e in events}
    events = list(uniq.values())
    ets = {}
    for e in events:
        r = subprocess.run(["git", "-C", str(repo), "show", "-s", "--format=%ct", e["sha"]],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            ets[e["sha"]] = int(r.stdout.strip())
    cache = out_dir / f"fwd_touch_cache_{repo.name}.json"
    touched = harvest_touched_files(repo, [e for e in events if e["sha"] in ets], args.workers, cache)
    labels = np.zeros(len(rows))
    snap_pos_files: dict[int, set] = defaultdict(set)
    for k, s in enumerate(snaps):
        lo, hi = s["ct"], s["ct"] + OUTCOME_DAYS * DAY
        for sha, t in ets.items():
            if lo < t <= hi and touched.get(sha):
                snap_pos_files[k] |= set(touched[sha]["old"]) | set(touched[sha]["new"])
    for i, r in enumerate(rows):
        labels[i] = 1.0 if r[1] in snap_pos_files[r[0]] else 0.0

    snap_idx = np.array([r[0] for r in rows])
    loc = np.array([float(r[2] or 0) for r in rows])
    band = np.array(absolute_bands(loc.tolist(), ABS_CUTS))
    F = {f: np.array([float(r[3 + j] or 0) for r in rows]) for j, f in enumerate(feats)}

    band_stats = []
    for b in range(len(ABS_LABELS)):
        m = band == b
        band_stats.append({"band": ABS_LABELS[b], "n": int(m.sum()), "pos": int(labels[m].sum()),
                           "powered": int(labels[m].sum()) >= MIN_POS})
    n_powered = sum(bs["powered"] for bs in band_stats)
    alpha_b = ALPHA / max(n_powered, 1)

    results = {}
    rng_base = np.random.SeedSequence(SEED)
    for fi, feat in enumerate(feats):
        per_band = []
        for b, bs in enumerate(band_stats):
            m = band == b
            row = {**bs, "auc_f": float("nan"), "auc_loc": float("nan"), "lift": float("nan")}
            if bs["pos"] > 0 and bs["pos"] < bs["n"]:
                ones = np.ones(int(m.sum()))
                row["auc_f"] = weighted_auc(F[feat][m], labels[m], ones)
                row["auc_loc"] = weighted_auc(loc[m], labels[m], ones)
                row["lift"] = row["auc_f"] - row["auc_loc"]
                if bs["powered"]:
                    # Snapshot ids re-indexed within the band, so empty snapshots are not drawn.
                    sids, inv = np.unique(snap_idx[m], return_inverse=True)
                    rng = np.random.default_rng(rng_base.spawn(fi * 10 + b + 1)[-1])
                    lifts = cluster_bootstrap(inv, F[feat][m], loc[m], labels[m], len(sids), rng, args.iters)
                    lifts = lifts[~np.isnan(lifts)]
                    row["lo_one_sided"] = float(np.quantile(lifts, alpha_b))
                    row["ci90"] = (float(np.quantile(lifts, 0.05)), float(np.quantile(lifts, 0.95)))
                    row["supported"] = row["lift"] > 0 and row["lo_one_sided"] > 0
                    row["equiv_null"] = -EQUIV < row["ci90"][0] and row["ci90"][1] < EQUIV
            per_band.append(row)
        pooled = weighted_auc(F[feat], labels, np.ones(len(rows)))
        results[feat] = {"bands": per_band, "pooled_auc": pooled}
        print(f"{feat}: pooled AUC {pooled:.4f}", flush=True)
    pooled_loc = weighted_auc(loc, labels, np.ones(len(rows)))

    # ---- report
    scored = args.mode == "scored"
    lines = [f"# FWD-H1..H3 — {repo.name} ({'SCORED' if scored else 'EXPLORATORY: no verdicts'})", ""]
    if not scored:
        lines += ["**EXPLORATORY.** This repository supplied the evidence the FWD claims rest on, so per the",
                  "registration (docs/HYPOTHESES.md, 2026-11-05) nothing here is a verdict. It is the instrument",
                  "check plus labelled context.", ""]
    lines += [f"- engine `{meta.get('engine_sha', '?')}` · args `{meta.get('engine_args', '')}` · history `{meta.get('history')}`",
              f"- {len(snaps)} quarterly snapshots ({snaps[0]['ref']} .. {snaps[-1]['ref']}); {len(rows)} (snapshot, C file) rows;"
              f" {int(labels.sum())} positives (fix-class touch in (t, t+{OUTCOME_DAYS} d])",
              f"- excluded for engine-reported unusable history (amendment 1): {', '.join(excluded_refs) or 'none'}",
              f"- fix events with a resolvable date: {len(ets)} of {len(events)} (classes {sorted(FIX_CLASSES)})",
              f"- pooled AUC total_loc: {pooled_loc:.4f}", "",
              "## Instrument gate", "",
              f"Spearman(raw_churn_freq, independent reconstruction from git; amendment 1) >= {GATE_RHO} on every snapshot with >= 3 active C files: "
              f"**{'PASS' if not failed else 'FAIL'}** ({len(evaluable_gate) - len(failed)}/{len(evaluable_gate)}; "
              f"min rho {min(g['rho'] for g in evaluable_gate):.4f}, median {float(np.median([g['rho'] for g in evaluable_gate])):.4f}).", ""]
    if failed:
        lines += ["Failing snapshots: " + ", ".join(f"{g['ref']} ({g['rho']:.3f}, n={g['n']})" for g in failed[:20]), ""]
    if hcm_rows:
        ev = [g for g in hcm_rows if g["n"] >= 3]
        bad = [g for g in ev if not g["rho"] >= HCM_GATE_RHO]
        lines += ["## FWD-H3 condition: engine change entropy = HCM1_LD_30", "",
                  f"Spearman(change_entropy, tools/hcm_variants.py HCM1_LD_30) >= {HCM_GATE_RHO} on every snapshot: "
                  f"**{'PASS' if hcm_ok else 'FAIL'}** ({len(ev) - len(bad)}/{len(ev)}; min {min(g['rho'] for g in ev):.4f}, "
                  f"median {float(np.median([g['rho'] for g in ev])):.4f}).", ""]
        if bad:
            lines += ["Below threshold: " + ", ".join(f"{g['ref']} ({g['rho']:.3f}, n={g['n']})" for g in bad[:20]), ""]
    lines += ["## Bands", "", "| band | n | positives | powered |", "|---|---:|---:|---|"]
    lines += [f"| {bs['band']} | {bs['n']} | {bs['pos']} | {'yes' if bs['powered'] else 'no (<20)'} |" for bs in band_stats]
    lines += ["", f"Bonferroni alpha per band = 0.01 / {n_powered} = {alpha_b:.4f}", ""]
    claim_of = {v: k for k, v in SCORED.items()}
    verdicts = {}
    for feat in feats:
        tag = claim_of.get(feat, "exploratory")
        lines += [f"## `{feat}` ({tag})", "", f"Pooled AUC {results[feat]['pooled_auc']:.4f} (total_loc {pooled_loc:.4f}).", "",
                  "| band | AUC feature | AUC total_loc | lift | one-sided lo | 90% CI | " + ("verdict |" if scored and tag != "exploratory" else "|"),
                  "|---|---:|---:|---:|---:|---|" + ("---|" if scored and tag != "exploratory" else "")]
        any_sup, all_equiv, any_powered = False, True, False
        for r in results[feat]["bands"]:
            if r["powered"]:
                any_powered = True
                v = "SUPPORTED" if r.get("supported") else ("equivalence-null" if r.get("equiv_null") else "inconclusive")
                any_sup |= bool(r.get("supported"))
                all_equiv &= bool(r.get("equiv_null"))
                ci = f"[{r['ci90'][0]:+.4f}, {r['ci90'][1]:+.4f}]"
                lo = f"{r['lo_one_sided']:+.4f}"
            else:
                v, ci, lo = "not evaluable", "—", "—"
            cells = f"| {r['band']} | {r['auc_f']:.4f} | {r['auc_loc']:.4f} | {r['lift']:+.4f} | {lo} | {ci} |"
            lines.append(cells + (f" {v} |" if scored and tag != "exploratory" else ""))
        if scored and tag == "FWD-H3" and not hcm_ok:
            verdicts[tag] = "not evaluable (HCM parity condition failed; registration must be amended)"
            lines += ["", f"**{tag}: {verdicts[tag]}.**"]
        elif scored and tag != "exploratory":
            if not any_powered:
                verdicts[tag] = "not evaluable"
            else:
                verdicts[tag] = "SUPPORTED" if any_sup else ("replicated null (equivalence)" if all_equiv else "not supported (inconclusive)")
            lines += ["", f"**{tag}: {verdicts[tag]}.**"]
        lines.append("")
    if scored and "FWD-H3" not in verdicts:
        lines += ["**FWD-H3: not evaluable** — no engine change-entropy column in this scan (registration condition).", ""]
    if failed:
        lines = lines[:2] + ["**INSTRUMENT GATE FAILED — per the registration nothing below is scored.**", ""] + lines[2:]
        verdicts = {k: "withheld (instrument gate failed)" for k in verdicts}
    lines += [f"Runtime {time.time() - t_start:.0f}s · bootstrap {args.iters} rounds, seed {SEED}, snapshot clusters."]
    out = args.out or DOCS_DIR / f"fwd_{repo.name}.md"
    out.write_text("\n".join(lines) + "\n")
    (out_dir / f"fwd_{repo.name}.json").write_text(json.dumps(
        {"gate": gate, "hcm_gate": hcm_rows, "bands": band_stats, "results": results, "verdicts": verdicts,
         "pooled_auc_total_loc": pooled_loc}, indent=1, default=float))
    print(f"wrote {out}; verdicts {verdicts or '(exploratory)'}", flush=True)
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
