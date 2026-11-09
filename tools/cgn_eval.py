#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""CGN-A1..E1 (docs/cgn_hypotheses.md): hubs, efficiency, bad shapes, concurrency and dead code in call networks.

    SFS_SRC=<popan>/structural-fingerprint-scanner/src <venv>/bin/python tools/cgn_eval.py --scratch CGT_SCRATCH > cgn.json

Reuses cgt_eval's cached snapshot networks under --scratch (same networks as CGT). Aggregates only.
"""
from __future__ import annotations

import argparse
import collections
import json
import pickle
import sqlite3
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from scipy.stats import kendalltau, spearmanr

sys.path.insert(0, str(Path(__file__).parent))
import cgt_eval as G  # noqa: E402
import sfs_eval as S  # noqa: E402
from _engine import POOL_DIR, REPO_ROOT  # noqa: E402

SEED, YEAR = 2982, G.YEAR


def indeg(net):
    d = collections.Counter(b for _, b in net["edges"])
    return {n: d.get(n, 0) for n in net["nodes"]}


def hubs(deg, top=0.01):
    vals = sorted(deg.values(), reverse=True)
    if not vals:
        return set(), 0
    k = max(3, int(round(top * len(vals))))
    thr = vals[min(k, len(vals)) - 1]
    return {n for n, v in deg.items() if v >= thr and v > 0}, thr


def pct_threshold(deg, q):
    vals = np.array(list(deg.values()), float)
    return np.quantile(vals, q) if len(vals) else 0


def rename_map(r, a, b):
    return G.renames(POOL_DIR / r, a, b)


def mv(rn, n):
    return (rn.get(n[0], n[0]), n[1])


def attrs(r, shas):
    """sha -> {(path, name): (loc, is_public, concurrency)}"""
    con = sqlite3.connect(f"file:{S.DBS[r]}?mode=ro", uri=True)
    want = set(shas)
    files = collections.defaultdict(dict)
    for fid, path, sha in con.execute("SELECT id, file_path, commit_hash FROM file_data"):
        if sha in want and path and G.is_c(path):
            files[sha][fid] = path
    out = {}
    for sha in shas:
        d = {}
        ids = list(files.get(sha, {}))
        for i in range(0, len(ids), 900):
            ch = ids[i:i + 900]
            q = ("SELECT file_id, func_name, loc, COALESCE(is_public,0), COALESCE(arch_concurrency,0), "
                 f"COALESCE(def_sync_locks,0) FROM function_data WHERE file_id IN ({','.join('?' * len(ch))})")
            for fid, name, loc, pub, conc, locks in con.execute(q, ch):
                if name and (loc or 0) >= 3:
                    d[(files[sha][fid], str(name).split("::")[-1])] = (loc, int(pub or 0), int((conc or 0) > 0 or (locks or 0) > 0))
        out[sha] = d
    con.close()
    return out


def core_numbers(nodes, edges):
    adj = collections.defaultdict(set)
    for a, b in edges:
        if a != b:
            adj[a].add(b)
            adj[b].add(a)
    deg = {n: len(adj[n]) for n in nodes}
    core, bins = {}, collections.defaultdict(set)
    for n, d in deg.items():
        bins[d].add(n)
    k = 0
    remaining = set(nodes)
    while remaining:
        while not bins[k]:
            k += 1
        n = bins[k].pop()
        core[n] = k
        remaining.discard(n)
        for m in adj[n]:
            if m in remaining and deg[m] > k:
                bins[deg[m]].discard(m)
                deg[m] -= 1
                bins[deg[m]].add(m)
    return core


def quint(vals):
    return np.quantile(vals, [0.2, 0.4, 0.6, 0.8]) if len(vals) else np.array([])


def qof(qs, v):
    return int(np.searchsorted(qs, v, side="right"))


def cmh_report(strata, greater, alpha):
    h = G.cmh([tuple(s) for s in strata], greater=greater)
    exp = sum(s[0] + s[1] for s in strata)
    ok = h["p"] is not None and h["p"] < alpha and (h["or"] > 1 if greater else h["or"] < 1)
    return {**h, "exposed": exp, "verdict": "not evaluable" if exp < 30 else ("supported" if ok else "not supported")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    a = ap.parse_args()
    rng = np.random.default_rng(SEED)
    res = {}
    A1, A2b, A3, B, Cst, C4st, Dst, Est = {}, [], {}, {}, collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0, 0])), collections.defaultdict(lambda: [0, 0, 0, 0]), collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0, 0])), collections.defaultdict(lambda: [0, 0, 0, 0])
    for r in G.REPOS:
        nets = G.snapshot_networks(r, a.scratch)
        prs = pickle.loads((a.scratch / f"pairs_{r}.pkl").read_bytes())
        deg = [indeg(n) for n in nets]
        hubset = [hubs(d)[0] for d in deg]
        # identity chain across quarters (renames carried) -> birth index; A2; ages for E1
        chain_rn = [rename_map(r, t0["sha"], t1["sha"]) for t0, t1 in zip(nets, nets[1:])]
        ident = [{n: n for n in nets[0]["nodes"]}]
        for i, rn in enumerate(chain_rn):
            prev = {mv(rn, n): cid for n, cid in ident[-1].items()}
            ident.append({n: prev.get(n, n) for n in nets[i + 1]["nodes"]})
        birth, hub_at = {}, {}
        for i, idm in enumerate(ident):
            for n, cid in idm.items():
                birth.setdefault(cid, i)
                if n in hubset[i]:
                    hub_at.setdefault(cid, i)
        for cid, h in hub_at.items():
            if birth[cid] > 0:
                A2b.append(h - birth[cid] <= 8)
        # A1: yearly pairs 5 years apart
        yi = list(range(0, len(nets), 4))
        share_num = share_den = 0
        rhos = []
        for k, i in enumerate(yi):
            if k + 5 >= len(yi):
                break
            j = yi[k + 5]
            rn = rename_map(r, nets[i]["sha"], nets[j]["sha"])
            top5 = pct_threshold(deg[j], 0.95)
            for h in hubset[i]:
                m = mv(rn, h)
                if m in deg[j]:
                    share_den += 1
                    share_num += deg[j][m] >= top5 and deg[j][m] > 0
            common = [(deg[i][n], deg[j][mv(rn, n)]) for n in deg[i] if mv(rn, n) in deg[j]]
            if len(common) > 10:
                rhos.append(float(spearmanr(*zip(*common)).statistic))
        A1[r] = {"surviving_hubs": share_den, "still_top5": share_num / share_den if share_den else None,
                 "median_spearman_5y": float(np.median(rhos)) if rhos else None, "pairs": len(rhos)}
        A1[r]["pass"] = bool(A1[r]["still_top5"] is not None and A1[r]["still_top5"] >= 0.5 and
                             A1[r]["median_spearman_5y"] is not None and A1[r]["median_spearman_5y"] >= 0.5)
        # A3: preferential attachment, percentile of new-edge targets among persisting nodes at t
        pcts, null_pools = [], []
        for i, (t0, t1) in enumerate(zip(nets, nets[1:])):
            rn = chain_rn[i]
            n0 = {mv(rn, n) for n in t0["nodes"]}
            P = n0 & t1["nodes"]
            if len(P) < 10:
                continue
            d0 = {mv(rn, n): v for n, v in deg[i].items()}
            e0 = {(mv(rn, x), mv(rn, y)) for x, y in t0["edges"]}
            new = [b for (x, b) in t1["edges"] - e0 if x in P and b in P]
            if not new:
                continue
            vals = np.array(sorted(d0.get(n, 0) for n in P), float)
            def pr(v):
                lo, hi = np.searchsorted(vals, v, "left"), np.searchsorted(vals, v, "right")
                return (lo + hi) / 2 / len(vals)
            pcts += [pr(d0.get(b, 0)) for b in new]
            null_pools.append((vals, len(new)))
        obs = float(np.mean(pcts)) if pcts else None
        ge = 0
        for _ in range(2000):
            sim = []
            for vals, k in null_pools:
                pick = rng.choice(vals, k)
                lo, hi = np.searchsorted(vals, pick, "left"), np.searchsorted(vals, pick, "right")
                sim.append(((lo + hi) / 2 / len(vals)).sum())
            ge += (sum(sim) / max(len(pcts), 1)) >= obs
        p3 = (1 + ge) / 2001
        A3[r] = {"new_edges": len(pcts), "mean_target_percentile": obs, "p": p3,
                 "pass": bool(obs is not None and obs > 0.55 and p3 < 0.0033)}
        # B: yearly trends
        Q, X, H, T = [], [], [], []
        for i in yi:
            n = nets[i]
            und = {tuple(sorted((x, y))) for x, y in n["edges"] if x != y}
            m = len(und)
            if m == 0:
                continue
            comm = lambda node: node[0].rsplit("/", 1)[0] if "/" in node[0] else "."  # noqa: E731
            dc, ec = collections.Counter(), collections.Counter()
            for x, y in und:
                dc[comm(x)] += 1
                dc[comm(y)] += 1
                if comm(x) == comm(y):
                    ec[comm(x)] += 1
            Q.append(sum(ec[c] / m - (dc[c] / (2 * m)) ** 2 for c in dc))
            X.append(sum(1 for x, y in n["edges"] if x[0] != y[0]) / len(n["edges"]))
            hs = hubset[i]
            H.append(sum(1 for _, y in n["edges"] if y in hs) / len(n["edges"]))
            T.append(n["ct"])
        def trend(v, alt):
            t = kendalltau(T, v, alternative=alt)
            return {"tau": float(t.statistic), "p": float(t.pvalue), "pass": bool(t.pvalue < 0.05)}
        B[r] = {"years": len(T), "B1": trend(Q, "greater"), "B2": trend(X, "less"), "B3": trend(H, "greater"),
                "Q_first_last": [Q[0], Q[-1]] if Q else None, "cross_first_last": [X[0], X[-1]] if X else None}
        # attributes for D (latest) and E (yearly)
        need = sorted({nets[i]["sha"] for i in yi} | {nets[-1]["sha"]})
        att = attrs(r, need)
        # C1-C3: file-years
        xc = json.loads((REPO_ROOT / "events" / f"{r}_xc.json").read_text())["events"]
        fixes = collections.defaultdict(list)
        for e in xc:
            for f in e.get("c_files", []):
                fixes[f].append((e["ct"], e.get("class")))
        lo, hi = min(e["ct"] for e in xc), max(e["ct"] for e in xc)
        units = []
        for k, i in enumerate(yi):
            n = nets[i]
            t = n["ct"]
            if k == 0 or t - YEAR < lo or t + YEAR > hi:
                continue
            per, _, _ = G.numstat(POOL_DIR / r, nets[yi[k - 1]]["sha"], n["sha"])
            files = sorted({p for p, _ in n["nodes"]})
            fix_ = {f: f for f in files}
            size = collections.Counter(p for p, _ in n["nodes"])
            fe = collections.defaultdict(set)
            for x, y in n["edges"]:
                if x[0] != y[0]:
                    fe[x[0]].add(y[0])
            idx = {f: j for j, f in enumerate(files)}
            rows_, cols_ = [], []
            for f, ts in fe.items():
                for g in ts:
                    rows_.append(idx[f])
                    cols_.append(idx[g])
            M = csr_matrix((np.ones(len(rows_)), (rows_, cols_)), shape=(len(files), len(files)))
            _, lab = connected_components(M, directed=True, connection="strong")
            sccsize = collections.Counter(lab)
            nbr = collections.defaultdict(set)
            for f, ts in fe.items():
                for g in ts:
                    nbr[f].add(g)
                    nbr[g].add(f)
            coup = {f: len(nbr[f]) for f in files}
            cthr = np.quantile(list(coup.values()), 0.8) if coup else 0
            callee = collections.defaultdict(set)
            for x, y in n["edges"]:
                callee[x].add(y)
            sig = collections.defaultdict(set)
            for x, cs in callee.items():
                if len(cs) >= 3:
                    sig[frozenset(cs)].add(x[0])
            dup = {f for fs in sig.values() if len(fs) > 1 for f in fs}
            for f in files:
                prior = int(any(t - YEAR < ct <= t for ct, _ in fixes.get(f, ())))
                y = int(any(t < ct <= t + YEAR for ct, _ in fixes.get(f, ())))
                units.append((f, size[f], per.get(f, 0), prior, y, sccsize[lab[idx[f]]] >= 2, f in dup,
                              coup[f] >= cthr and coup[f] > 0))
        if units:
            qs, qc = quint([u[1] for u in units]), quint([u[2] for u in units])
            for f, sz, ch, prior, y, cyc, dupf, cp in units:
                key = (r, qof(qs, sz), qof(qc, ch), prior)
                for name, ex in (("C1", cyc), ("C2", dupf), ("C3", cp)):
                    s = Cst[name][key]
                    if ex:
                        s[0 if y else 1] += 1
                    else:
                        s[2 if y else 3] += 1
        # C4: fix units -> regression share by coupling at the snapshot before the fix
        cts = [n["ct"] for n in nets]
        coup_cache = {}
        c4 = []
        for e in xc:
            k = int(np.searchsorted(cts, e["ct"], side="left")) - 1
            if k < 0:
                continue
            if k not in coup_cache:
                n = nets[k]
                nbr = collections.defaultdict(set)
                for x, y in n["edges"]:
                    if x[0] != y[0]:
                        nbr[x[0]].add(y[0])
                        nbr[y[0]].add(x[0])
                fl = {p for p, _ in n["nodes"]}
                cp = {f: len(nbr[f]) for f in fl}
                thr = np.quantile(list(cp.values()), 0.8) if cp else 0
                coup_cache[k] = (cp, thr, collections.Counter(p for p, _ in n["nodes"]))
            cp, thr, sz = coup_cache[k]
            for f in e.get("c_files", []):
                if f in cp:
                    c4.append((sz[f], cp[f] >= thr and cp[f] > 0, e.get("class") == "regression"))
        if c4:
            qs = quint([u[0] for u in c4])
            for sz, ex, y in c4:
                s = C4st[(r, qof(qs, sz))]
                if ex:
                    s[0 if y else 1] += 1
                else:
                    s[2 if y else 3] += 1
        # D: latest snapshot
        n = nets[-1]
        at = att[n["sha"]]
        d = deg[-1]
        core = core_numbers(n["nodes"], n["edges"])
        p90, cmed = pct_threshold(d, 0.90), np.median(list(core.values())) if core else 0
        lq = quint([at[x][0] for x in n["nodes"] if x in at])
        for x in n["nodes"]:
            if x not in at:
                continue
            loc, pub, conc = at[x]
            key = (r, qof(lq, loc))
            for name, y in (("D1", d[x] >= p90 and d[x] > 0), ("D2", core.get(x, 0) >= cmed)):
                s = Dst[name][key]
                if conc:
                    s[0 if y else 1] += 1
                else:
                    s[2 if y else 3] += 1
        # E1: yearly t, outcome absent at t + 8 quarters
        for i in yi:
            j = i + 8
            if j >= len(nets):
                break
            rn = rename_map(r, nets[i]["sha"], nets[j]["sha"])
            at_i = att[nets[i]["sha"]]
            cand = [x for x in nets[i]["nodes"] if x in at_i and at_i[x][1] == 0]
            if not cand:
                continue
            lq = quint([at_i[x][0] for x in cand])
            for x in cand:
                age = (i - birth[ident[i][x]]) / 4
                band = 0 if age < 1 else 1 if age < 3 else 2 if age < 6 else 3
                gone = mv(rn, x) not in nets[j]["nodes"]
                s = Est[(r, qof(lq, at_i[x][0]), band)]
                if deg[i][x] == 0:
                    s[0 if gone else 1] += 1
                else:
                    s[2 if gone else 3] += 1
        print(f"{r} done", file=sys.stderr, flush=True)
    a1p = sum(v["pass"] for v in A1.values())
    a2 = float(np.mean(A2b)) if A2b else None
    a3p = sum(v["pass"] for v in A3.values())
    res["A"] = {"A1": {"per_repo": A1, "repos_pass": a1p, "verdict": "supported" if a1p >= 4 else "not supported"},
                "A2": {"hubs_born_in_window": len(A2b), "share_within_8q": a2,
                       "verdict": "supported" if a2 is not None and a2 >= 0.5 else "not supported"},
                "A3": {"per_repo": A3, "repos_pass": a3p, "verdict": "supported" if a3p >= 4 else "not supported"}}
    res["B"] = {"per_repo": B}
    for k in ("B1", "B2", "B3"):
        n_ = sum(v[k]["pass"] for v in B.values())
        res["B"][k] = {"repos_pass": n_, "verdict": "supported" if n_ >= 4 else "not supported"}
    res["C"] = {k: cmh_report(list(Cst[k].values()), True, 0.0025) for k in ("C1", "C2", "C3")}
    res["C"]["C4"] = cmh_report(list(C4st.values()), True, 0.0025)
    res["D"] = {k: cmh_report(list(Dst[k].values()), False, 0.005) for k in ("D1", "D2")}
    res["E"] = {"E1": cmh_report(list(Est.values()), True, 0.01)}
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
