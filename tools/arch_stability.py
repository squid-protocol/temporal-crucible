#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""ARCH-S1..S5: archetype stability over a repo's scanned history (docs/archetype_hypotheses.md).

Snapshots = every commit in the DB, ordered by committer time. "Unchanged" = identical git blob at
the path (git ls-tree, from the pool clone). Pass 1 extracts one compact pickle per snapshot (in
parallel); pass 2 walks consecutive pairs.

    python tools/arch_stability.py --repo curl --db <curl_galaxy_master.db> --jobs 4
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing
import pathlib
import pickle
import sqlite3
import subprocess
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402

EDIT_BINS = [(0.0, 0.0, "0 (LOC equal)"), (0.0, 0.01, "(0, 1%]"), (0.01, 0.05, "(1, 5%]"),
             (0.05, 0.20, "(5, 20%]"), (0.20, math.inf, "> 20%")]
S1_BAR = 0.999
S2_BAR = 0.90


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def blob_map(repo, sha):
    out = {}
    for line in _git(repo, "-c", "core.quotepath=off", "ls-tree", "-r", sha).splitlines():
        meta, _, path = line.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[1] == "blob":
            out[path] = parts[2]
    return out


def margin(fp):
    try:
        d = sorted(json.loads(fp).values())
    except (TypeError, ValueError):
        return float("nan")
    return d[1] - d[0] if len(d) >= 2 else float("nan")


def extract(task):
    db, repo, repo_name, sha, out = task
    out = pathlib.Path(out)
    if out.exists():
        return sha
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    blobs = blob_map(repo, sha)
    files = {}
    for fid, path, cloc, tloc, fa, ca, fp in con.execute(
            "SELECT id, file_path, coding_loc, total_loc, file_archetype, composition_file_archetype, file_fingerprint "
            "FROM file_data WHERE repo_name=? AND commit_hash=? AND language='c'", (repo_name, sha)):
        files[fid] = [path, blobs.get(path), cloc or 0, tloc or 0, fa, ca, margin(fp), []]
    if files:
        q = ("SELECT f.file_id, f.func_name, f.start_line, f.loc, f.complexity, f.func_archetype FROM function_data f "
             "JOIN file_data fd ON f.file_id = fd.id WHERE fd.repo_name=? AND fd.commit_hash=? AND fd.language='c'")
        for fid, name, start, loc, cx, arch in con.execute(q, (repo_name, sha)):
            if fid in files:
                files[fid][7].append((name, start, loc, cx, arch))
    con.close()
    snap = {r[0]: tuple(r[1:]) for r in files.values()}  # path -> (blob, cloc, tloc, fa, ca, margin, funcs)
    tmp = out.with_suffix(".tmp")
    tmp.write_bytes(pickle.dumps(snap, protocol=5))
    tmp.rename(out)
    return sha


def kappa(pairs):
    """Cohen's kappa for a list of (label_t, label_t1)."""
    n = len(pairs)
    if n == 0:
        return float("nan")
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def jsd(p: Counter, q: Counter):
    keys = set(p) | set(q)
    sp, sq = sum(p.values()), sum(q.values())
    if not sp or not sq:
        return float("nan")
    out = 0.0
    for k in keys:
        a, b = p.get(k, 0) / sp, q.get(k, 0) / sq
        m = (a + b) / 2
        if a:
            out += 0.5 * a * math.log2(a / m)
        if b:
            out += 0.5 * b * math.log2(b / m)
    return out


def edit_bin(c0, c1):
    if c0 == c1:
        return 0
    rel = abs(c1 - c0) / max(c0, 1)
    for i, (lo, hi, _) in enumerate(EDIT_BINS[1:], 1):
        if lo < rel <= hi:
            return i
    return len(EDIT_BINS) - 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--db", required=True, type=pathlib.Path)
    ap.add_argument("--repo-name", default=None, help="repo_data.repo_name (default: --repo)")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--cache", type=pathlib.Path, required=True, help="per-snapshot pickle dir")
    ap.add_argument("--out", type=pathlib.Path, default=None)
    a = ap.parse_args()
    t0 = time.time()
    repo = POOL_DIR / a.repo
    name = a.repo_name or a.repo
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    shas = [r[0] for r in con.execute("SELECT commit_hash FROM repo_data WHERE repo_name=?", (name,))]
    con.close()
    ct = {}
    for i in range(0, len(shas), 500):
        for line in _git(repo, "show", "-s", "--format=%H %ct", *shas[i:i + 500]).splitlines():
            h, _, c = line.partition(" ")
            if c.strip().isdigit():
                ct[h] = int(c)
    snaps = sorted((s for s in shas if s in ct), key=lambda s: (ct[s], s))
    print(f"{name}: {len(snaps)} snapshots ({len(shas) - len(snaps)} without a commit time)", flush=True)
    cache = a.cache / name
    cache.mkdir(parents=True, exist_ok=True)
    tasks = [(str(a.db), str(repo), name, s, str(cache / f"{s}.pkl")) for s in snaps]
    with multiprocessing.get_context("fork").Pool(a.jobs) as pool:
        for i, _ in enumerate(pool.imap_unordered(extract, tasks, chunksize=4), 1):
            if i % 200 == 0:
                print(f"  extracted {i}/{len(tasks)} ({time.time() - t0:.0f}s)", flush=True)

    def load(s):
        return pickle.loads((cache / f"{s}.pkl").read_bytes())

    # ---- pass 2: consecutive pairs
    s1_file = [0, 0]      # [same, total] file_archetype on unchanged blob
    s1_func = [0, 0]      # func_archetype, functions inside unchanged blobs
    s1_examples = []
    s4 = [0, 0]           # composition label on unchanged blob
    s2 = defaultdict(lambda: [0, 0])     # bin -> [same, total] file_archetype
    s2c = defaultdict(lambda: [0, 0])    # bin -> composition
    s2_pairs = defaultdict(list)         # bin -> (a, b) for kappa
    fn_changed = {"same_shape": [0, 0], "new_shape": [0, 0]}  # functions in changed files, matched by name
    s5 = []               # (margin_t, flipped) for changed files
    drift_prev, drift_first = [], []
    per_file_labels = defaultdict(list)  # path -> labels over life
    first_dist = None
    prev = None
    snap_dist = []
    for k, s in enumerate(snaps):
        cur = load(s)
        dist = Counter(v[3] for v in cur.values() if v[3])
        snap_dist.append(dist)
        if first_dist is None and dist:
            first_dist = dist
        for path, v in cur.items():
            per_file_labels[path].append(v[3])
        if prev is not None:
            drift_prev.append(jsd(snap_dist[-2], dist))
            drift_first.append(jsd(first_dist, dist))
            for path, v in cur.items():
                p = prev.get(path)
                if p is None or not p[0] or not v[0]:
                    continue
                if p[0] == v[0]:
                    s1_file[1] += 1
                    s1_file[0] += p[3] == v[3]
                    if p[3] != v[3] and len(s1_examples) < 10:
                        s1_examples.append((snaps[k - 1][:10], s[:10], path, p[3], v[3]))
                    s4[1] += 1
                    s4[0] += p[4] == v[4]
                    fp = {(n, st): ar for n, st, _, _, ar in p[6]}
                    for n, st, _, _, ar in v[6]:
                        if (n, st) in fp:
                            s1_func[1] += 1
                            s1_func[0] += fp[(n, st)] == ar
                else:
                    b = edit_bin(p[1], v[1])
                    s2[b][1] += 1
                    s2[b][0] += p[3] == v[3]
                    s2c[b][1] += 1
                    s2c[b][0] += p[4] == v[4]
                    s2_pairs[b].append((p[3], v[3]))
                    if not math.isnan(p[5]):
                        s5.append((p[5], p[3] != v[3]))
                    fp = {}
                    for n, st, lo, cx, ar in p[6]:
                        fp.setdefault(n, (lo, cx, ar))
                    for n, st, lo, cx, ar in v[6]:
                        if n in fp:
                            key = "same_shape" if fp[n][:2] == (lo, cx) else "new_shape"
                            fn_changed[key][1] += 1
                            fn_changed[key][0] += fp[n][2] == ar
        prev = cur
        if k % 500 == 0:
            print(f"  paired {k}/{len(snaps)} ({time.time() - t0:.0f}s)", flush=True)

    # ---- S3: one-year horizon (file labels only; reload sparse)
    cts = [ct[s] for s in snaps]
    year = 365 * 86400
    j = 0
    s3_pairs, s3_changed, s3_unchanged = [], [0, 0], [0, 0]
    step = max(1, len(snaps) // 150)  # ≤ ~150 origins keeps reloads cheap; origins are evenly spaced
    for i in range(0, len(snaps), step):
        while j < len(snaps) and cts[j] < cts[i] + year:
            j += 1
        if j >= len(snaps):
            break
        A, B = load(snaps[i]), load(snaps[j])
        for path, v in A.items():
            w = B.get(path)
            if w is None or not v[3] or not w[3]:
                continue
            s3_pairs.append((v[3], w[3]))
            bucket = s3_unchanged if v[0] == w[0] else s3_changed
            bucket[1] += 1
            bucket[0] += v[3] == w[3]

    life = [len(set(ls)) for ls in per_file_labels.values() if len(ls) >= 10]
    life_c = Counter(min(x, 6) for x in life)

    # ---- report
    def r(x):
        return x[0] / x[1] if x[1] else float("nan")

    small = [s2[1][0] + s2[2][0], s2[1][1] + s2[2][1]]
    L = [f"# ARCH-S — archetype stability: {name}", "",
         f"- DB `{a.db}` · {len(snaps)} snapshots, {time.strftime('%Y-%m-%d', time.gmtime(cts[0]))} .. "
         f"{time.strftime('%Y-%m-%d', time.gmtime(cts[-1]))} · C files only", "",
         "## S1 — determinism gate (unchanged blob between consecutive snapshots)", "",
         "| label | pairs | same label | bar | gate |", "|---|---:|---:|---:|---|",
         f"| file cluster (`file_archetype`) | {s1_file[1]:,} | {r(s1_file):.5f} | {S1_BAR} | **{'PASS' if r(s1_file) >= S1_BAR else 'FAIL'}** |",
         f"| function (`func_archetype`), matched by (name, start_line) | {s1_func[1]:,} | {r(s1_func):.5f} | {S1_BAR} | **{'PASS' if r(s1_func) >= S1_BAR else 'FAIL'}** |",
         f"| S4: composition (`composition_file_archetype`) — not gated | {s4[1]:,} | {r(s4):.5f} | — | (context-sensitive by design) |"]
    if s1_examples:
        L += ["", "File-cluster changes on unchanged blobs (first 10): " + "; ".join(
            f"`{p}` {a_}→{b_} ({x}→{y})" for x, y, p, a_, b_ in s1_examples)]
    L += ["", "## S2 — retention under edits (changed blob between consecutive snapshots)", "",
          "| relative edit \\|Δcoding_loc\\|/coding_loc | pairs | file cluster kept | κ | composition kept |",
          "|---|---:|---:|---:|---:|"]
    for b, (_, _, lab) in enumerate(EDIT_BINS):
        L.append(f"| {lab} | {s2[b][1]:,} | {r(s2[b]):.3f} | {kappa(s2_pairs[b]):.3f} | {r(s2c[b]):.3f} |")
    L += ["", f"**S2 bar** (file cluster, (0, 5%] bins combined): retention **{r(small):.3f}** on {small[1]:,} pairs → "
          f"**{'trackable' if r(small) >= S2_BAR else 'NOT trackable'}** (bar {S2_BAR}).", "",
          f"Functions in changed files, matched by name: same (loc, complexity) kept label {r(fn_changed['same_shape']):.4f} "
          f"(n={fn_changed['same_shape'][1]:,}); changed shape kept {r(fn_changed['new_shape']):.3f} (n={fn_changed['new_shape'][1]:,}).", "",
          "## S3 — one-year horizon (file cluster)", "",
          f"- origins: every {step} snapshot(s); pairs {len(s3_pairs):,}; agreement {np.mean([x == y for x, y in s3_pairs]):.3f}, "
          f"κ {kappa(s3_pairs):.3f}",
          f"- unchanged over the year: kept {r(s3_unchanged):.4f} (n={s3_unchanged[1]:,}); changed: kept {r(s3_changed):.3f} (n={s3_changed[1]:,})",
          f"- distinct file-cluster labels over a file's life (files seen in ≥ 10 snapshots, n={len(life):,}): " +
          ", ".join(f"{k if k < 6 else '6+'}: {life_c[k] / len(life):.1%}" for k in sorted(life_c)), "",
          "## S5 — does a thin centroid margin predict a flip? (changed files)", "",
          "| margin decile (d₂ − d₁) | range | pairs | flip rate |", "|---|---|---:|---:|"]
    if s5:
        m = np.array([x for x, _ in s5])
        f = np.array([y for _, y in s5], dtype=float)
        qs = np.quantile(m, np.linspace(0, 1, 11))
        idx = np.clip(np.searchsorted(qs, m, side="right") - 1, 0, 9)
        for d in range(10):
            sel = idx == d
            L.append(f"| {d + 1} | {qs[d]:.3f}–{qs[d + 1]:.3f} | {int(sel.sum()):,} | {f[sel].mean():.3f} |")
    L += ["", "## Population drift (file-cluster distribution, JSD bits)", "",
          f"- consecutive snapshots: median {np.nanmedian(drift_prev):.4f}, p99 {np.nanquantile(drift_prev, 0.99):.4f}",
          f"- vs first snapshot, at the end: {drift_first[-1]:.3f}", "",
          f"Runtime {time.time() - t0:.0f}s."]
    out = a.out or DOCS_DIR / f"arch_stability_{name}.md"
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
