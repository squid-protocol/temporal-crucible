#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""SC stage 1: discovery screen of every numeric file metric × fix class (docs/sc_protocol.md).

Per (candidate, class, repo), mean over scored quarterly snapshots of
  D = stratified AUC(candidate) - stratified AUC(total_loc), 50 equal-count total_loc bins
  R = recall@20(candidate in its pooled-D direction) - max(recall@20 LOC-desc, LOC-asc)

    python tools/sc_discover.py
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).parent / "exploratory"))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from xc_envcond import PATTERNS  # noqa: E402

WT = pathlib.Path(os.environ.get("TC_WORKTREES", "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees"))
DBS = {"curl": WT / "forward-asof/dbs/curl_out/curl_galaxy_master.db",
       "ndpi": WT / "forward-asof/dbs/ndpi_out/ndpi_galaxy_master.db",
       "openssl": WT / "frec/dbs/openssl_out/openssl_galaxy_master.db"}
CLASSES = ("latent", "extrinsic", "regression", "other-fix")
DAY, WINDOW, BINS, TOPK, RHO_MAX = 86400, 180, 50, 5, 0.8
EXCLUDE = {"id", "total_loc"}


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def recall20(score, loc, path_rank, pos):
    """EA's recall_at(…, 0.20), vectorised: rank by (-score, loc, path); whole files while cum LOC <= 20%."""
    order = np.lexsort((path_rank, loc, -score))
    cum = np.cumsum(loc[order])
    k = int(np.searchsorted(cum, 0.2 * loc.sum(), side="right"))
    return pos[order][:k].sum() / pos.sum()


def strat_auc_all(df, cols, pos, bins):
    """Pair-pooled within-bin AUC for many columns at once (ties 1/2 via average ranks)."""
    r = df[cols].groupby(bins).rank(method="average")
    n1 = pd.Series(pos).groupby(bins).sum()
    n = pd.Series(pos).groupby(bins).size()
    den = float((n1 * (n - n1)).sum())
    if den == 0:
        return None
    s1 = r[pos == 1].groupby(bins[pos == 1]).sum()
    corr = (n1 * (n1 + 1) / 2).reindex(s1.index)
    return ((s1.sub(corr, axis=0)).sum() / den).to_dict()


def main() -> int:
    t0 = time.time()
    cols_by_repo, data = {}, {}
    for r, db in DBS.items():
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        cols_by_repo[r] = [c[1] for c in con.execute("PRAGMA table_info(file_data)")
                           if (c[2] or "").upper() in ("INTEGER", "REAL", "BOOLEAN") and c[1] not in EXCLUDE]
        con.close()
    common = sorted(set.intersection(*map(set, cols_by_repo.values())))
    for r, db in DBS.items():
        repo = POOL_DIR / r
        snaps = [s for s in json.loads((REPO_ROOT / "walks" / f"{r}_quarterly.json").read_text())["revisions"]
                 if s.get("status", "ok") == "ok"]
        ev = json.loads((REPO_ROOT / "events" / f"{r}_xc.json").read_text())["events"]
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        frames = []
        for k, s in enumerate(snaps):
            ct = int(_git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())
            df = pd.read_sql_query(f"SELECT file_path, total_loc, mitigation_telemetry, {', '.join(common)} FROM file_data "
                                   "WHERE commit_hash=? AND language='c'", con, params=(s["sha"],))
            if df.empty:
                continue
            df["flux"] = [float((json.loads(m) if m else {}).get("amplified_cascading_flux", 0) or 0) for m in df.pop("mitigation_telemetry")]
            pc = {}
            for line in _git(repo, "-c", "core.quotepath=off", "grep", "-c", "-P", PATTERNS["P"], s["sha"], "--", "*.c", "*.h").splitlines():
                _, _, rest = line.partition(":")
                p, _, n = rest.rpartition(":")
                if n.isdigit():
                    pc[p] = int(n)
            df["platform_cond"] = [pc.get(p, 0) for p in df["file_path"]]
            for kk in CLASSES:
                files = set()
                for e in ev:
                    if e["class"] == kk and ct < e["ct"] <= ct + WINDOW * DAY:
                        files.update(e["c_files"])
                df[f"_y_{kk}"] = df["file_path"].isin(files).astype(float)
            df["_snap"] = k
            frames.append(df)
        con.close()
        data[r] = pd.concat(frames, ignore_index=True)
        print(f"{r}: {len(frames)} snapshots, {len(data[r])} rows ({time.time() - t0:.0f}s)", flush=True)

    base = common + ["flux", "platform_cond"]
    for r, df in data.items():
        df[base] = df[base].apply(pd.to_numeric, errors="coerce").fillna(0.0).astype(float)
        loc = df["total_loc"].clip(lower=1).astype(float)
        per = (df[base].div(loc, axis=0)).add_suffix(" /line")
        data[r] = pd.concat([df, per], axis=1)
    raw_c = base + [b + " /line" for b in base]
    entry = [c for c in raw_c if all((data[r][c] != 0).mean() >= 0.05 and data[r][c].nunique() >= 3 for r in data)]
    print(f"{len(raw_c)} candidate forms, {len(entry)} pass the entry rule", flush=True)

    D = defaultdict(lambda: defaultdict(list))
    Rraw = {}  # (repo, snap, class) -> needed for R later
    for r, df in data.items():
        for k, g in df.groupby("_snap"):
            loc = g["total_loc"].astype(float).to_numpy()
            bins = pd.Series(np.minimum((pd.Series(loc).rank(method="first").to_numpy() - 1) * BINS // len(loc), BINS - 1).astype(int),
                             index=g.index)
            for kk in CLASSES:
                y = g[f"_y_{kk}"].to_numpy()
                if y.sum() == 0:
                    continue
                a = strat_auc_all(g, entry + ["total_loc"], y, bins)
                if a is None:
                    continue
                for c in entry:
                    D[(kk, c)][r].append(a[c] - a["total_loc"])
                Rraw[(r, k, kk)] = (g, loc, y)
        print(f"{r}: D done ({time.time() - t0:.0f}s)", flush=True)

    rows = []
    for kk in CLASSES:
        for c in entry:
            dm = {r: float(np.mean(D[(kk, c)][r])) if D[(kk, c)][r] else float("nan") for r in data}
            sign = 1.0 if np.nanmean(list(dm.values())) >= 0 else -1.0
            rows.append({"class": kk, "cand": c, "sign": sign, **{f"D_{r}": dm[r] for r in data}})
    tab = pd.DataFrame(rows)
    # R only for candidates whose D has one sign on all three repos (others cannot pass the rule)
    tab["d_consistent"] = tab.apply(lambda x: all(np.sign(x[f"D_{r}"]) == x["sign"] for r in data), axis=1)
    for r in data:
        tab[f"R_{r}"] = np.nan
    for i, x in tab[tab["d_consistent"]].iterrows():
        for r in data:
            vals = []
            for (rr, k, kk), (g, loc, y) in Rraw.items():
                if rr != r or kk != x["class"]:
                    continue
                pr = np.argsort(np.argsort(g["file_path"].to_numpy()))
                base_r = max(recall20(loc, loc, pr, y), recall20(-loc, loc, pr, y))
                vals.append(recall20(x["sign"] * g[x["cand"]].to_numpy(), loc, pr, y) - base_r)
            tab.at[i, f"R_{r}"] = float(np.mean(vals))
    print(f"R done ({time.time() - t0:.0f}s)", flush=True)

    tab["passes"] = tab["d_consistent"] & tab.apply(lambda x: all(x[f"R_{r}"] > 0 for r in data), axis=1)
    tab["minR"] = tab[[f"R_{r}" for r in data]].min(axis=1)
    pooled = pd.concat([data[r][entry] for r in data]).sample(n=min(200000, sum(len(d) for d in data.values())), random_state=2982)
    frozen = {}
    for kk in CLASSES:
        cand = tab[(tab["class"] == kk) & tab["passes"]].sort_values("minR", ascending=False)
        kept = []
        for _, x in cand.iterrows():
            if all(abs(pooled[x["cand"]].corr(pooled[k2], method="spearman")) <= RHO_MAX for k2, _ in kept):
                kept.append((x["cand"], x["sign"]))
            if len(kept) == TOPK:
                break
        frozen[kk] = [{"candidate": c, "direction": "higher = review first" if s > 0 else "lower = review first"} for c, s in kept]

    L = ["# SC stage 1 — discovery screen: file metrics × fix class (EXPLORATORY; selection rule per sc_protocol.md)", "",
         f"- repos curl / nDPI / openssl; {len(raw_c)} candidate forms, **{len(entry)}** pass the entry rule",
         "- D = within-bin AUC(candidate) − within-bin AUC(total_loc), 50 size bins; R = recall@20 lift over the stronger size order",
         "", "## Passing candidates per class (D and R same sign and > 0 on all three repos), ranked by min R", ""]
    for kk in CLASSES:
        c = tab[(tab["class"] == kk) & tab["passes"]].sort_values("minR", ascending=False)
        L += [f"### {kk}: {len(c)} pass", "", "| candidate | dir | D curl / nDPI / openssl | R curl / nDPI / openssl |", "|---|---|---|---|"]
        for _, x in c.head(15).iterrows():
            L.append(f"| `{x['cand']}` | {'+' if x['sign'] > 0 else '−'} | {x['D_curl']:+.3f} / {x['D_ndpi']:+.3f} / {x['D_openssl']:+.3f} | "
                     f"{x['R_curl']:+.3f} / {x['R_ndpi']:+.3f} / {x['R_openssl']:+.3f} |")
        L.append("")
    L += ["## Frozen for stage 2 (top 5 per class after the |ρ| ≤ 0.8 de-duplication)", "", "```json", json.dumps(frozen, indent=1), "```", ""]
    pc = tab[(tab["class"] == "extrinsic") & (tab["cand"] == "platform_cond /line")]
    ok = bool(len(pc) and pc["passes"].iloc[0])
    L += [f"**Instrument check (P per line recovered for extrinsic): {'PASS' if ok else 'FAIL'}**", "",
          f"Runtime {time.time() - t0:.0f}s."]
    (DOCS_DIR / "sc_discovery.md").write_text("\n".join(L) + "\n")
    tab.to_csv(DOCS_DIR / "sc_discovery_table.csv", index=False)
    (REPO_ROOT / "events" / "sc_frozen_candidates.json").write_text(json.dumps(frozen, indent=1))
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
