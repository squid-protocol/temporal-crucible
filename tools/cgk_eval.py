#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""CGK (docs/cgk_hypotheses.md): keywords vs network roles, hub structure, fix classes vs network position.

    SFS_SRC=<popan>/structural-fingerprint-scanner/src <venv>/bin/python tools/cgk_eval.py --scratch CGT_SCRATCH > cgk.json

Reuses cgt_eval's cached networks. Aggregates only.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

sys.path.insert(0, str(Path(__file__).parent))
import cgn_eval as N  # noqa: E402
import cgt_eval as G  # noqa: E402
import sfs_eval as S  # noqa: E402
from _engine import REPO_ROOT  # noqa: E402

LATTICE = Path("/srv/storage_16tb/projects/popan-worktrees/r3-lattice/agent-habits-round3/lattice_shapes.json")


def signals():
    raw = LATTICE.read_bytes()
    assert hashlib.sha256(raw).hexdigest().startswith("a27d2c93f817ac25")
    D = json.loads(raw)
    return sorted(set().union(*[set(s["signals"]) for s in D["shapes"]]))


def fattrs(r, sha, U):
    con = sqlite3.connect(f"file:{S.DBS[r]}?mode=ro", uri=True)
    files = {fid: p for fid, p, c in con.execute("SELECT id, file_path, commit_hash FROM file_data") if c == sha and p and G.is_c(p)}
    out = {}
    ids = list(files)
    cols = ", ".join(f"COALESCE({u},0)" for u in U)
    for i in range(0, len(ids), 900):
        ch = ids[i:i + 900]
        q = (f"SELECT file_id, func_name, loc, COALESCE(complexity,0), COALESCE(is_public,0), COALESCE(func_archetype,''), {cols} "
             f"FROM function_data WHERE file_id IN ({','.join('?' * len(ch))})")
        for row in con.execute(q, ch):
            fid, name, loc = row[0], row[1], row[2]
            if name and (loc or 0) >= 3:
                out[(files[fid], str(name).split("::")[-1])] = {"loc": loc, "cx": row[3], "pub": int(row[4] or 0),
                                                                "arch": row[5], "sig": [int((v or 0) > 0) for v in row[6:]]}
    con.close()
    return out


def top_set(d, q):
    vals = np.array([v for v in d.values() if v > 0], float)
    if not len(vals):
        return set()
    thr = np.quantile(vals, q)
    return {n for n, v in d.items() if v > 0 and v >= thr}


def add(st, key, exposed, outcome):
    s = st[key]
    if exposed:
        s[0 if outcome else 1] += 1
    else:
        s[2 if outcome else 3] += 1


def two_sided(strata, alpha):
    h = G.cmh([tuple(s) for s in strata], greater=True)
    exp = sum(s[0] + s[1] for s in strata)
    if h["p"] is None:
        return {**h, "exposed": exp, "call": "not evaluable"}
    p2 = min(1.0, 2 * min(h["p"], 1 - h["p"]))
    call = ("not evaluable" if exp < 30 else "enriched" if p2 < alpha and h["or"] > 1 else
            "depleted" if p2 < alpha and h["or"] < 1 else "n.s.")
    return {"or": h["or"], "z": h["z"], "p_two_sided": p2, "exposed": exp, "call": call}


def one_sided(strata, greater, alpha):
    h = G.cmh([tuple(s) for s in strata], greater=greater)
    exp = sum(s[0] + s[1] for s in strata)
    ok = h["p"] is not None and h["p"] < alpha and (h["or"] > 1 if greater else h["or"] < 1)
    return {**h, "exposed": exp, "verdict": "not evaluable" if exp < 30 else ("supported" if ok else "not supported")}


def file_metrics(net):
    deg = N.indeg(net)
    h1 = top_set(deg, 0.99)
    files = sorted({p for p, _ in net["nodes"]})
    idx = {f: i for i, f in enumerate(files)}
    nbr = collections.defaultdict(set)
    rows, cols = [], []
    for x, y in net["edges"]:
        if x[0] != y[0]:
            nbr[x[0]].add(y[0])
            nbr[y[0]].add(x[0])
            rows.append(idx[x[0]])
            cols.append(idx[y[0]])
    M = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(files), len(files)))
    _, lab = connected_components(M, directed=True, connection="strong")
    scc = collections.Counter(lab)
    coup = {f: len(nbr[f]) for f in files}
    cthr = np.quantile(list(coup.values()), 0.8) if coup else 0
    core = N.core_numbers(net["nodes"], net["edges"])
    cmed = np.median(list(core.values())) if core else 0
    fcore = collections.defaultdict(list)
    for n, c in core.items():
        fcore[n[0]].append(c)
    hubfile = {n[0] for n in h1}
    size = collections.Counter(p for p, _ in net["nodes"])
    return {f: {"hub": f in hubfile, "coupled": coup[f] >= cthr and coup[f] > 0, "cycle": scc[lab[idx[f]]] >= 2,
                "periph": float(np.median(fcore[f])) < cmed if fcore[f] else False, "size": size[f]} for f in files}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    a = ap.parse_args()
    U = signals()
    mk = lambda: collections.defaultdict(lambda: [0, 0, 0, 0])  # noqa: E731
    K1, K2, K3, H1 = mk(), mk(), mk(), mk()
    KS = {(u, role): mk() for u in U for role in ("hub", "orch", "periph")}
    fam_hub = collections.Counter()
    fam_non = collections.Counter()
    arch_hub, arch_non = collections.Counter(), collections.Counter()
    F = {k: mk() for k in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11")}
    for r in G.REPOS:
        nets = G.snapshot_networks(r, a.scratch)
        net = nets[-1]
        at = fattrs(r, net["sha"], U)
        din = N.indeg(net)
        dout = collections.Counter(x for x, _ in net["edges"])
        dout = {n: dout.get(n, 0) for n in net["nodes"]}
        hub, orch = top_set(din, 0.90), top_set(dout, 0.90)
        core = N.core_numbers(net["nodes"], net["edges"])
        cmed = np.median(list(core.values())) if core else 0
        nodes = [n for n in net["nodes"] if n in at]
        lq = N.quint([at[n]["loc"] for n in nodes])
        dens = [at[n]["cx"] / at[n]["loc"] for n in nodes]
        dmed = np.median(dens) if dens else 0
        for n in nodes:
            x = at[n]
            key = (r, N.qof(lq, x["loc"]))
            hi_cx = x["cx"] / x["loc"] >= dmed
            add(K1, key, n in hub, hi_cx)
            add(K2, key, n in orch, hi_cx)
            add(K3, key, n in hub, x["pub"] == 1)
            add(H1, key, n in hub, sum(x["sig"]) <= 3)
            for u, v in zip(U, x["sig"]):
                add(KS[(u, "hub")], key, n in hub, v)
                add(KS[(u, "orch")], key, n in orch, v)
                add(KS[(u, "periph")], key, core.get(n, 0) < cmed, v)
            (fam_hub if n in hub else fam_non)[sum(x["sig"])] += 1
            (arch_hub if n in hub else arch_non)[x["arch"] or "?"] += 1
        # F: fixes vs the file's network position at the snapshot before the fix
        xc = json.loads((REPO_ROOT / "events" / f"{r}_xc.json").read_text())["events"]
        cts = [n_["ct"] for n_ in nets]
        cache, units = {}, []
        for e in xc:
            k = int(np.searchsorted(cts, e["ct"], side="left")) - 1
            if k < 0 or e.get("class") not in ("latent", "regression", "extrinsic", "other-fix"):
                continue
            if k not in cache:
                cache[k] = file_metrics(nets[k])
            fm = cache[k]
            for f in e.get("c_files", []):
                if f in fm:
                    units.append((e["class"], fm[f]))
        if units:
            qs = N.quint([u[1]["size"] for u in units])
            grid = {"latent": {"hub": "F1", "coupled": "F4", "cycle": "F6", "periph": "F9"},
                    "regression": {"hub": "F2", "cycle": "F7", "periph": "F10"},
                    "extrinsic": {"hub": "F3", "coupled": "F5", "cycle": "F8", "periph": "F11"}}
            for cls, fmx in units:
                key = (r, N.qof(qs, fmx["size"]))
                for c2, cells in grid.items():
                    if cls not in (c2, "other-fix"):
                        continue
                    for metric, fid in cells.items():
                        add(F[fid], key, fmx[metric], cls == c2)
        print(f"{r} done", file=sys.stderr, flush=True)
    res = {"K1": one_sided(list(K1.values()), False, 0.0033), "K2": one_sided(list(K2.values()), True, 0.0033),
           "K3": one_sided(list(K3.values()), True, 0.0033), "H1": one_sided(list(H1.values()), True, 0.01)}
    alpha = 0.01 / 78
    res["KS"] = {f"{u}|{role}": two_sided(list(st.values()), alpha) for (u, role), st in KS.items()}
    res["KS_summary"] = {role: {c: sorted(k.split("|")[0] for k, v in res["KS"].items() if k.endswith(role) and v["call"] == c)
                                for c in ("enriched", "depleted")} for role in ("hub", "orch", "periph")}
    res["H_descriptive"] = {"rung_hub": dict(sorted(fam_hub.items())), "rung_nonhub": dict(sorted(fam_non.items())),
                            "archetype_hub_top": arch_hub.most_common(6), "archetype_nonhub_top": arch_non.most_common(6)}
    # F: exposure = network position; outcome = fix is the class (vs other-fix); interpret OR>1 as "the class lands
    # in such files more than other fixes do"
    res["F"] = {k: two_sided(list(v.values()), 0.01 / 11) for k, v in F.items()}
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
