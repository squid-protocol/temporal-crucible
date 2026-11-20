#!/usr/bin/env python3
"""How often does a function's keyword shape (which keyword signals it carries) move between scans, and how? Uses the frozen shape lattice of the fingerprint study
(docs/fingerprint_trees_exploratory.json, sha-checked) to name family and rung; moves are measured between consecutive scans for functions present in both.
Three kinds of move, as in tools/lat_eval.py: one-signal step (a keyword added or removed), rung change (climb or descent in the number of signals), family change.
    python tools/report/shape_moves.py NAME SNAPSHOTS.json [AREAS]    AREAS: openfold | colabfold (core vs rest)"""
import collections
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

DOCS = Path(__file__).resolve().parents[2] / "docs"
TREES = DOCS / "fingerprint_trees_exploratory.json"
SHA = "a27d2c93f817"
sys.path.insert(0, str(Path(__file__).parent))
from core_area import AREAS, area_of  # noqa: E402


def lattice():
    raw = TREES.read_bytes()
    assert hashlib.sha256(raw).hexdigest().startswith(SHA), "frozen tree data changed"
    D = json.loads(raw)
    sets = [frozenset(s["signals"]) for s in D["shapes"]]
    n = len(sets)
    J = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            u = len(sets[i] | sets[j])
            J[i, j] = J[j, i] = 1 - (len(sets[i] & sets[j]) / u if u else 1)
    fam = fcluster(linkage(squareform(J, checks=False), method="average"), 14, criterion="maxclust")
    cnt = np.array([s["n"] for s in D["shapes"]], float)
    return sets, fam, cnt, sorted(set().union(*sets))


def family(P, cols, sets, fam, cnt):
    avail = list(cols)
    S = np.array([[c in s for c in avail] for s in sets], np.int32)
    keys, inv = np.unique(P, axis=0, return_inverse=True)
    inter = keys @ S.T
    union = keys.sum(1)[:, None] + S.sum(1)[None, :] - inter
    jac = np.where(union > 0, inter / np.maximum(union, 1), 1.0)
    order = np.argsort(-cnt, kind="stable")
    pick = order[np.argmax(jac[:, order], axis=1)]
    return np.where(jac.max(1) > 0, fam[pick], 0)[inv.ravel()]


def main():
    name, snap = sys.argv[1], sys.argv[2]
    rules = AREAS.get(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] in AREAS else None
    repo = sys.argv[4] if len(sys.argv) > 4 else None
    sets, fam, cnt, U = lattice()
    sn = json.load(open(snap))
    per = []
    cols_used = None
    for s in sn:
        con = sqlite3.connect(f"file:{s['db']}?mode=ro", uri=True)
        have = {c[1] for c in con.execute("PRAGMA table_info(function_data)")}
        cols = [c for c in U if c in have]
        cols_used = cols if cols_used is None else [c for c in cols_used if c in cols]
        rows = con.execute("SELECT f.file_path, x.func_name, x.start_line, " + ", ".join("x." + c for c in cols) + " FROM function_data x JOIN file_data f ON f.id = x.file_id WHERE x.func_name IS NOT NULL AND x.func_name != ''").fetchall()
        con.close()
        d = {}
        for r in sorted(rows, key=lambda r: (r[0], r[1], r[2] or 0)):
            d.setdefault((r[0], r[1]), (cols, tuple(1 if (v or 0) > 0 else 0 for v in r[3:])))
        per.append(d)
    cols = cols_used
    # re-project every snapshot onto the common signal set
    P = []
    for d in per:
        P.append({k: tuple(v[1][v[0].index(c)] for c in cols) for k, v in d.items()})
    allk = sorted({k for d in P for k in d})
    kidx = {k: i for i, k in enumerate(allk)}
    # family per (function, scan)
    fams = []
    for d in P:
        ks = list(d)
        X = np.array([d[k] for k in ks], np.int32) if ks else np.zeros((0, len(cols)), np.int32)
        f = family(X, cols, sets, fam, cnt) if ks else np.array([])
        fams.append(dict(zip(ks, f)))
    edited = None
    if repo:  # functions edited between two scans (commit time window), from the evolution report's one-pass diff cache
        import evolution_report as ER
        lang = "python" if sys.argv[3:4] and sys.argv[3] in ("openfold", "colabfold", "python") else "c"
        commits = ER.load_commits(repo)
        diff = ER.diff_pass(repo, lang, Path("/tmp/gitgalaxy-scratch/claude/report/out") / name / "cache", name)
        cts = [commits[s_["commit"]]["ct"] if s_["commit"] in commits else None for s_ in sn]
        by_time = sorted((c["ct"], sha) for sha, c in commits.items() if diff.get(sha, {}).get("funcs"))
        import bisect
        edited = [set() for _ in sn]
        times = [t for t, _ in by_time]
        for i in range(1, len(sn)):
            if cts[i] is None or cts[i - 1] is None:
                continue
            for _, sha in by_time[bisect.bisect_right(times, cts[i - 1]):bisect.bisect_right(times, cts[i])]:
                for path, fn in diff[sha]["funcs"]:
                    edited[i].add((path, fn))
    stats = collections.defaultdict(lambda: collections.Counter())
    ed = collections.Counter()
    life = collections.defaultdict(lambda: [0, 0])  # key -> [intervals, moved intervals]
    for i in range(1, len(P)):
        for k, v in P[i].items():
            if k not in P[i - 1]:
                continue
            u = v
            w = P[i - 1][k]
            a_ = area_of(k[0], rules) if rules else "all"
            for tag in {a_, "all"}:
                st = stats[tag]
                st["pairs"] += 1
                diff = sum(x != y for x, y in zip(u, w))
                rung = sum(u) - sum(w)
                st["moved"] += diff > 0
                st["step1"] += diff == 1
                st["jump2"] += diff >= 2
                st["climb"] += rung > 0
                st["descent"] += rung < 0
                st["family"] += fams[i][k] != fams[i - 1][k]
            if edited is not None and k in edited[i]:
                ed["edited"] += 1
                ed["edited_moved"] += sum(x != y for x, y in zip(u, w)) > 0
                ed["edited_family"] += fams[i][k] != fams[i - 1][k]
            life[k][0] += 1
            life[k][1] += any(x != y for x, y in zip(u, w))
    print(f"== {name}: {len(P)} scans, {len(cols)} lattice signals present in the scan schema (of {len(U)} in the frozen lattice)")
    print(f"{'area':8s} {'pairs':>8s} {'moved':>7s} {'one-signal':>11s} {'2+ signals':>11s} {'climb':>7s} {'descent':>8s} {'family chg':>11s} {'never moved (functions)':>24s}")
    for tag in sorted(stats, key=lambda t: (t != "all", t)):
        st = stats[tag]
        keys_t = [k for k in life if life[k][0] and (tag == "all" or area_of(k[0], rules) == tag)]
        never = np.mean([life[k][1] == 0 for k in keys_t]) if keys_t else float("nan")
        n = st["pairs"]
        print(f"{tag:8s} {n:8,} {st['moved'] / n * 100:6.1f}% {st['step1'] / n * 100:10.1f}% {st['jump2'] / n * 100:10.1f}% {st['climb'] / n * 100:6.1f}% {st['descent'] / n * 100:7.1f}% {st['family'] / n * 100:10.1f}% {never * 100:15.0f}% of {len(keys_t):,}")
    _tail(ed)


def _tail(ed):
    if ed.get("edited"):
        print(f"   among functions EDITED in the interval: {ed['edited']:,} units, shape moved in {ed['edited_moved'] / ed['edited'] * 100:.1f}%, family changed in {ed['edited_family'] / ed['edited'] * 100:.1f}%   (temporal-crucible CHG-2 units: 17.8% moved)")


if __name__ == "__main__":
    main()
