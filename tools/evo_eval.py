#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""SIG-H1..H3 (keyword mix over time) and CPL-H1..H3 (coupling surface over time). docs/evo_hypotheses.md.

    python tools/evo_eval.py
"""
from __future__ import annotations

import json
import math
import multiprocessing
import os
import pathlib
import sqlite3
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np
from scipy.stats import binomtest, spearmanr

sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).parent / "exploratory"))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from lib_eval import DEPS, EXTS, grep_counts, work_commits  # noqa: E402
from tgt_eval import SUBJ as PLATFORM_SUBJ  # noqa: E402
from xc_envcond import PATTERNS  # noqa: E402

WT = pathlib.Path(os.environ.get("TC_WORKTREES", "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees"))
DBS = {"curl": WT / "forward-asof/dbs/curl_out/curl_galaxy_master.db",
       "ndpi": WT / "forward-asof/dbs/ndpi_out/ndpi_galaxy_master.db",
       "openssl": WT / "frec/dbs/openssl_out/openssl_galaxy_master.db",
       "harfbuzz": WT / "sc-class/dbs/harfbuzz_out/harfbuzz_galaxy_master.db",
       "libarchive": WT / "sc-class/dbs/libarchive_out/libarchive_galaxy_master.db"}
LIB_UNITS = {"curl": ["openssl", "zlib", "libssh2", "nghttp2", "c-ares", "wolfssl", "mbedtls", "gnutls"],
             "libarchive": ["openssl", "zlib", "bzip2", "xz", "zstd"], "ndpi": ["libpcap"],
             "harfbuzz": ["freetype", "icu", "coretext", "directwrite", "uniscribe", "graphite", "glib"]}
YEAR, DAY, SEED, ITERS = 365.25 * 86400, 86400, 2982, 5000


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def snapshots(r):
    repo = POOL_DIR / r
    con = sqlite3.connect(f"file:{DBS[r]}?mode=ro", uri=True)
    have = {x[0] for x in con.execute("SELECT DISTINCT commit_hash FROM repo_data")}
    con.close()
    seen, out = set(), []
    for s in json.loads((REPO_ROOT / "walks" / f"{r}_quarterly.json").read_text())["revisions"]:
        if s.get("status", "ok") == "ok" and s["sha"] in have and s["sha"] not in seen:
            seen.add(s["sha"])
            out.append({"sha": s["sha"], "ct": int(_git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())})
    return sorted(out, key=lambda s: s["ct"])


def jsd(p, q):
    m = (p + q) / 2
    def kl(a, b):
        nz = a > 0
        return float((a[nz] * np.log2(a[nz] / b[nz])).sum())
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


# ------------------------------------------------------------------------------------------------- SIG
def sig_data(r):
    con = sqlite3.connect(f"file:{DBS[r]}?mode=ro", uri=True)
    fam = sorted(c[1] for c in con.execute("PRAGMA table_info(file_data)") if c[1].startswith("fam_"))
    out = []
    for s in snapshots(r):
        rows = con.execute(f"SELECT file_path, {', '.join(fam)} FROM file_data WHERE commit_hash=? AND language IN ('c','cpp')", (s["sha"],)).fetchall()
        files = {p: np.array([float(x or 0) for x in v]) for p, *v in rows}
        tot = sum(files.values()) if files else np.zeros(len(fam))
        out.append({"ct": s["ct"], "mix": tot / tot.sum() if tot.sum() else tot, "files": files})
    con.close()
    return fam, out


def sig(L):
    data = {}
    for r in DBS:
        fam, data[r] = sig_data(r)
    # H1: nearest-neighbour identification across eras
    correct = total = 0
    allsn = [(r, k, s) for r, ss in data.items() for k, s in enumerate(ss)]
    for r, k, s in allsn:
        best, best_r = None, None
        for r2, k2, s2 in allsn:
            if r2 == r and abs(s2["ct"] - s["ct"]) < 5 * YEAR:
                continue
            d = jsd(s["mix"], s2["mix"])
            if best is None or d < best:
                best, best_r = d, r2
        total += 1
        correct += best_r == r
    acc = correct / total
    # H2: drift concentration
    h2 = {}
    drift_detail = {}
    for r, ss in data.items():
        dr = np.array([jsd(ss[i - 1]["mix"], ss[i]["mix"]) for i in range(1, len(ss))])
        k = max(1, math.ceil(0.1 * len(dr)))
        h2[r] = float(np.sort(dr)[::-1][:k].sum() / dr.sum()) if dr.sum() else float("nan")
        top = np.argsort(dr)[::-1][:3]
        det = []
        for i in top:
            a, b = ss[i], ss[i + 1]
            dm = b["mix"] - a["mix"]
            fams = [(fam[j], dm[j]) for j in np.argsort(-np.abs(dm))[:2]]
            deltas = []
            for p in set(a["files"]) | set(b["files"]):
                va, vb = a["files"].get(p, np.zeros(len(fam))), b["files"].get(p, np.zeros(len(fam)))
                deltas.append((float(np.abs(vb - va).sum()), p, "new" if p not in a["files"] else "gone" if p not in b["files"] else "changed"))
            deltas.sort(reverse=True)
            det.append((time.strftime("%Y-%m", time.gmtime(b["ct"])), float(dr[i]), fams, deltas[:3]))
        drift_detail[r] = det
    # H3: per-file profile persistence
    cos_by_pair = []
    for r, ss in data.items():
        for i, s in enumerate(ss):
            j = next((j for j in range(i + 1, len(ss)) if ss[j]["ct"] >= s["ct"] + YEAR), None)
            if j is None:
                break
            cs = []
            for p, v in s["files"].items():
                w = ss[j]["files"].get(p)
                if w is not None and v.sum() >= 20 and w.sum() >= 20:
                    cs.append(float(v @ w / (np.linalg.norm(v) * np.linalg.norm(w))))
            if cs:
                cos_by_pair.append(np.array(cs))
    med = float(np.median(np.concatenate(cos_by_pair)))
    rng = np.random.default_rng(SEED)
    boots = [float(np.median(np.concatenate([cos_by_pair[i] for i in rng.integers(0, len(cos_by_pair), len(cos_by_pair))]))) for _ in range(1000)]
    lo3 = float(np.quantile(boots, 0.01))
    L += ["## Part 1 — SIG: the keyword mix over time", "",
          "| claim | result | verdict |", "|---|---|---|",
          f"| **SIG-H1** a project has a stable keyword fingerprint (nearest-neighbour, other eras ≥ 5 y away) | accuracy **{acc:.1%}** over {total} snapshots (chance 20%) | **{'SUPPORTED' if acc >= 0.90 else 'not supported'}** |",
          f"| **SIG-H2** the mix changes in spurts (top-10% quarters' share of drift) | " + " / ".join(f"{r} {v:.2f}" for r, v in h2.items()) +
          f" | **{'SUPPORTED' if sum(v >= 0.40 for v in h2.values()) >= 4 else 'not supported'}** |",
          f"| **SIG-H3** files keep their keyword profile (cosine, t vs t + 1 y) | median **{med:.3f}**, lo {lo3:.3f} | **{'SUPPORTED' if med >= 0.90 and lo3 >= 0.90 else 'not supported'}** |",
          "", "Largest-drift quarters (descriptive):", ""]
    for r, det in drift_detail.items():
        for when, d, fams, deltas in det:
            L.append(f"- **{r} {when}** (JSD {d:.4f}): " + ", ".join(f"{f} {x:+.3f}" for f, x in fams) +
                     " · files: " + "; ".join(f"`{p}` ({k}, Δ{v:.0f})" for v, p, k in deltas))
    L.append("")


# ------------------------------------------------------------------------------------------------- CPL
def cpl_snap(task):
    r, sha, units = task
    repo, exts = POOL_DIR / r, EXTS[r]
    files = [p for p in _git(repo, "-c", "core.quotepath=off", "ls-tree", "-r", "--name-only", sha).splitlines() if p.endswith(exts)]
    return sha, len(files), {u: grep_counts(repo, sha, pat, exts) for u, pat in units}


def cpl(L):
    rows = []
    for r, deps in LIB_UNITS.items():
        repo = POOL_DIR / r
        walk = json.loads((REPO_ROOT / "walks" / f"{r}_quarterly.json").read_text())
        snaps = [s for s in walk["revisions"] if s.get("status", "ok") == "ok"]
        for s in snaps:
            s["ct"] = int(_git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())
        pats = {d: pat for d, _, pat in DEPS[r] if d in deps}
        units = [(d, pats[d]) for d in deps] + [("platform", PATTERNS["P"])]
        with multiprocessing.get_context("fork").Pool(6) as p:
            data = {sha: (n, c) for sha, n, c in p.imap_unordered(cpl_snap, [(r, s["sha"], units) for s in snaps])}
        work = work_commits(r)
        xc = json.loads((REPO_ROOT / "events" / f"{r}_xc.json").read_text())["events"]
        work["platform"] = [{"ct": e["ct"], "files": e["c_files"]} for e in xc
                            if e["class"] == "extrinsic" and any(rx.search(e["subject"]) for rx in PLATFORM_SUBJ.values())]
        for u, _ in units:
            ts, spread, conc, cost = [], [], [], []
            for s in snaps:
                n, c = data[s["sha"]]
                cu = c[u]
                if len(cu) < 3 or n == 0:
                    continue
                vals = np.sort(np.array(list(cu.values()), float))[::-1]
                k = max(1, math.ceil(0.1 * len(vals)))
                ts.append(s["ct"])
                spread.append(len(cu) / n)
                conc.append(float(vals[:k].sum() / vals.sum()))
                win = [len(w["files"]) for w in work[u] if s["ct"] < w["ct"] <= s["ct"] + 180 * DAY]
                cost.append(float(np.median(win)) if len(win) >= 3 else np.nan)
            if len(ts) < 5:
                continue
            row = {"repo": r, "unit": u, "n": len(ts),
                   "rho_conc": spearmanr(ts, conc).statistic, "rho_spread": spearmanr(ts, spread).statistic,
                   "conc_first": conc[0], "conc_last": conc[-1], "spread_first": spread[0], "spread_last": spread[-1]}
            cc = [(a, b) for a, b in zip(conc, cost) if not np.isnan(b)]
            row["n_cost"] = len(cc)
            row["rho_cost"] = spearmanr(*zip(*cc)).statistic if len(cc) >= 10 else np.nan
            rows.append(row)
    def sign(vals, direction):
        v = [x for x in vals if not np.isnan(x) and x != 0]
        k = sum((x > 0) if direction > 0 else (x < 0) for x in v)
        return float(np.median(v)) if v else float("nan"), len(v), k, binomtest(k, len(v), 0.5, alternative="greater").pvalue if v else 1.0
    m1, n1, k1, p1 = sign([x["rho_conc"] for x in rows], +1)
    m2, n2, k2, p2 = sign([x["rho_spread"] for x in rows], -1)
    m3, n3, k3, p3 = sign([x["rho_cost"] for x in rows], -1)
    L += ["## Part 2 — CPL: the coupling surface over time", "",
          "| claim | median ρ | units in direction | sign-test p | verdict |", "|---|---:|---:|---:|---|",
          f"| **CPL-H1** coupling centralises with age (ρ time, concentration > 0) | {m1:+.2f} | {k1}/{n1} | {p1:.4f} | **{'SUPPORTED' if m1 > 0 and p1 < 0.01 else 'not supported'}** |",
          f"| **CPL-H2** coupling's footprint shrinks as a share (ρ time, spread < 0) | {m2:+.2f} | {k2}/{n2} | {p2:.4f} | **{'SUPPORTED' if m2 < 0 and p2 < 0.01 else 'not supported'}** |",
          f"| **CPL-H3** concentrated coupling → later work touches fewer files (ρ conc, files < 0) | {m3:+.2f} | {k3}/{n3} | {p3:.4f} | **{'SUPPORTED' if m3 < 0 and p3 < 0.01 else 'not supported'}** |",
          "", "| repo | unit | snapshots | ρ(time, conc) | conc first → last | ρ(time, spread) | spread first → last | ρ(conc, files per later commit) (n) |",
          "|---|---|---:|---:|---|---:|---|---|"]
    for x in rows:
        L.append(f"| {x['repo']} | {x['unit']} | {x['n']} | {x['rho_conc']:+.2f} | {x['conc_first']:.2f} → {x['conc_last']:.2f} | {x['rho_spread']:+.2f} | "
                 f"{x['spread_first']:.1%} → {x['spread_last']:.1%} | {x['rho_cost']:+.2f} ({x['n_cost']}) |")
    L.append("")


def main() -> int:
    t0 = time.time()
    L = ["# SIG + CPL — the keyword mix and the coupling surface over time (SCORED)", ""]
    sig(L)
    print(f"SIG done ({time.time() - t0:.0f}s)", flush=True)
    cpl(L)
    L += [f"Runtime {time.time() - t0:.0f}s · seed {SEED}. Note: SIG-H3's bootstrap uses 1,000 rounds over snapshot pairs."]
    (DOCS_DIR / "evo.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
