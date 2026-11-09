#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""CGR (docs/cgr_hypotheses.md): run the CGT, CGN and CGK scorers unchanged on the replication set, apply the
replication pass rules (observed directions, >= 75% of evaluable repos), and score L1-L3 and M1.

    SFS_SRC=... <venv>/bin/python tools/cgr_eval.py --data CGR_BUILD_OUT --gg GG --py ENGINE_PY \
        --original-cgk CGK_RESULT_JSON > cgr.json
"""
from __future__ import annotations

import argparse
import collections
import contextlib
import io
import json
import math
import pickle
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).parent))
import cgk_eval as K  # noqa: E402
import cgn_eval as N  # noqa: E402
import cgr_build as B  # noqa: E402
import cgt_eval as G  # noqa: E402
import nh_eval as NH  # noqa: E402
import sfs_eval as S  # noqa: E402
from _engine import POOL_DIR, REPO_ROOT  # noqa: E402

REPOS = tuple(B.LANG)
C_REPOS = ("libgit2", "postgres", "libxml2", "redis")
NON_C = ("prometheus", "commons-lang", "sphinx", "ripgrep")
YEAR = G.YEAR


def patch(data: Path, repos):
    for r in REPOS:
        S.DBS[r] = data / "dbs" / f"{r}.db"
        NH.DBS[r] = data / "dbs" / f"{r}.db"
    G.REPOS = tuple(repos)
    G.CEXT = (".c", ".h", ".cc", ".cpp", ".cxx", ".hh", ".hpp", ".go", ".java", ".py", ".rs")
    orig = G.cgt3_sample.__wrapped__ if hasattr(G.cgt3_sample, "__wrapped__") else G.cgt3_sample

    def sample(r, rng):
        if (REPO_ROOT / "events" / f"{r}.json").exists():
            return orig(r, rng)
        xc = json.loads((REPO_ROOT / "events" / f"{r}_xc.json").read_text())["events"]
        out = {}
        for c in G.CLASSES[:4]:
            shas = sorted({e["sha"] for e in xc if e.get("class") == c and any(G.is_c(f) for f in e.get("c_files", []))})
            rng.shuffle(shas)
            out[c] = shas
        out["control"] = []
        return out
    sample.__wrapped__ = orig
    G.cgt3_sample = sample


def run(mod, argv):
    buf = io.StringIO()
    old = sys.argv
    sys.argv = ["x", *argv]
    try:
        with contextlib.redirect_stdout(buf):
            mod.main()
    finally:
        sys.argv = old
    return json.loads(buf.getvalue())


def p_obs(res, observed_greater):
    z = res.get("z")
    if z is None:
        return None
    return float(norm.sf(z) if observed_greater else norm.cdf(z))


def rule(passes, evaluable):
    return "supported" if evaluable and passes >= math.ceil(0.75 * evaluable) else "not supported"


def logit(X, y, iters=50):
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ b))
        W = p * (1 - p)
        H = X.T @ (X * W[:, None]) + 1e-8 * np.eye(X.shape[1])
        step = np.linalg.solve(H, X.T @ (y - p))
        b += step
        if np.abs(step).max() < 1e-8:
            break
    p = 1 / (1 + np.exp(-X @ b))
    cov = np.linalg.inv(X.T @ (X * (p * (1 - p))[:, None]) + 1e-8 * np.eye(X.shape[1]))
    return b, np.sqrt(np.diag(cov))


def m1(scratch):
    rows = []
    for ri, r in enumerate(REPOS):
        nets = G.snapshot_networks(r, scratch)
        prs = pickle.loads((scratch / f"pairs_{r}.pkl").read_bytes())
        xc = json.loads((REPO_ROOT / "events" / f"{r}_xc.json").read_text())["events"]
        if not xc:
            continue
        fixes = collections.defaultdict(list)
        for e in xc:
            for f in e.get("c_files", []):
                fixes[f].append(e["ct"])
        lo, hi = min(e["ct"] for e in xc), max(e["ct"] for e in xc)
        yi = list(range(0, len(nets), 4))
        for k, i in enumerate(yi):
            if k == 0:
                continue
            n, t = nets[i], nets[i]["ct"]
            if t - YEAR < lo or t + YEAR > hi:
                continue
            per, _, _ = G.numstat(POOL_DIR / r, nets[yi[k - 1]]["sha"], n["sha"])
            rew = set()
            for p in prs:
                if t - YEAR < p["t1"] <= t:
                    rew |= set(p["rewired_files"])
            files = sorted({p for p, _ in n["nodes"]})
            idx = {f: j for j, f in enumerate(files)}
            nbr = collections.defaultdict(set)
            rr, cc = [], []
            for x, y in n["edges"]:
                if x[0] != y[0]:
                    nbr[x[0]].add(y[0])
                    nbr[y[0]].add(x[0])
                    rr.append(idx[x[0]])
                    cc.append(idx[y[0]])
            M = csr_matrix((np.ones(len(rr)), (rr, cc)), shape=(len(files), len(files)))
            _, lab = connected_components(M, directed=True, connection="strong")
            scc = collections.Counter(lab)
            coup = {f: len(nbr[f]) for f in files}
            thr = np.quantile(list(coup.values()), 0.8) if coup else 0
            size = collections.Counter(p for p, _ in n["nodes"])
            for f in files:
                prior = int(any(t - YEAR < c <= t for c in fixes.get(f, ())))
                y = int(any(t < c <= t + YEAR for c in fixes.get(f, ())))
                rows.append((ri, int(f in rew), int(coup[f] >= thr and coup[f] > 0), int(scc[lab[idx[f]]] >= 2),
                             math.log1p(size[f]), math.log1p(per.get(f, 0)), prior, y))
    if not rows:
        return {"verdict": "not evaluable"}
    A = np.array(rows, float)
    repos_used = sorted({int(x) for x in A[:, 0]})
    dummies = np.stack([(A[:, 0] == ri).astype(float) for ri in repos_used], axis=1)
    X = np.column_stack([A[:, 1:7], dummies])
    b, se = logit(X, A[:, 7])
    names = ["rewired", "coupled", "cycle", "log_functions", "log_churn", "prior_fix"]
    out = {"file_years": len(rows), "positives": int(A[:, 7].sum())}
    for i, nm in enumerate(names):
        z = b[i] / se[i]
        out[nm] = {"or": float(math.exp(b[i])), "z": float(z), "p_one_sided": float(norm.sf(z))}
    for nm in ("rewired", "coupled", "cycle"):
        out[nm]["carries"] = bool(out[nm]["or"] > 1 and out[nm]["p_one_sided"] < 0.01 / 3)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--gg", type=Path, required=True)
    ap.add_argument("--py", required=True)
    ap.add_argument("--original-cgk", type=Path, required=True)
    a = ap.parse_args()
    scratch = a.data / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    patch(a.data, REPOS)
    cgt = run(G, ["--gg", str(a.gg), "--py", a.py, "--scratch", str(scratch)])
    cgn = run(N, ["--scratch", str(scratch)])
    cgk = run(K, ["--scratch", str(scratch)])
    res = {"raw": {"cgt": cgt, "cgn": cgn, "cgk": cgk}}
    v = {}
    # CGT
    pr = cgt["CGT-1"]["per_repo"]
    ev = [r for r, x in pr.items() if x["pairs"] >= 20]
    v["R-CGT-1a"] = rule(sum(pr[r]["median_r"] < 0.02 for r in ev), len(ev))
    v["R-CGT-1b"] = rule(sum(pr[r]["top_decile_share_R"] >= 0.40 for r in ev), len(ev))
    v["R-CGT-1c"] = rule(sum(pr[r]["gini_diff_lo"] > 0 for r in ev), len(ev))
    v["R-CGT-2a"] = cgt["CGT-2"]["2a"]["verdict"]
    v["R-CGT-2b"] = cgt["CGT-2"]["2b"]["verdict"]
    v["R-CGT-3a"] = cgt["CGT-3"]["3a"]["verdict"]
    h = cgt["CGT-3"]["3b"]
    p = p_obs(h, True)
    n_l = cgt["CGT-3"]["commits"].get("latent", 0)
    v["R-CGT-3b"] = ("not evaluable" if n_l < 30 else "supported" if p is not None and p < 0.005 and h["or"] > 1 else "not supported")
    v["R-CGT-4"] = cgt["CGT-4"]["verdict"]
    v["R-CGT-5"] = cgt["CGT-5"]["verdict"]
    # CGN
    A1 = cgn["A"]["A1"]["per_repo"]
    v["R-CGN-A1"] = rule(sum(x["pass"] for x in A1.values()), len(A1))
    v["R-CGN-A2"] = cgn["A"]["A2"]["verdict"]
    A3 = cgn["A"]["A3"]["per_repo"]
    v["R-CGN-A3"] = rule(sum(x["pass"] for x in A3.values()), len(A3))
    Bp = cgn["B"]["per_repo"]
    for k in ("B1", "B2", "B3"):
        v[f"R-CGN-{k}"] = rule(sum(x[k]["pass"] for x in Bp.values()), len(Bp))
    v["R-CGN-C1"] = cgn["C"]["C1"]["verdict"]
    c2 = cgn["C"]["C2"]
    p = p_obs(c2, False)
    v["R-CGN-C2"] = "supported" if p is not None and p < 0.0025 and c2["or"] < 1 else "not supported"
    v["R-CGN-C3"] = cgn["C"]["C3"]["verdict"]
    v["R-CGN-C4"] = cgn["C"]["C4"]["verdict"]
    v["R-CGN-D1"] = cgn["D"]["D1"]["verdict"]
    v["R-CGN-D2"] = cgn["D"]["D2"]["verdict"]
    v["R-CGN-E1"] = cgn["E"]["E1"]["verdict"]
    # CGK (observed directions)
    for kk, greater, alpha in (("K1", True, 0.0033), ("K2", False, 0.0033), ("H1", False, 0.01)):
        x = cgk[kk]
        p = p_obs(x, greater)
        ok = p is not None and p < alpha and ((x["or"] > 1) if greater else (x["or"] < 1))
        v[f"R-CGK-{kk}"] = "not evaluable" if x["exposed"] < 30 else ("supported" if ok else "not supported")
    v["R-CGK-K3"] = cgk["K3"]["verdict"]
    want = {"F3": "enriched", "F5": "depleted", "F8": "depleted", "F11": "enriched"}
    v["R-CGK-F-extrinsic"] = {k: cgk["F"][k]["call"] for k in want}
    v["R-CGK-F-extrinsic-verdict"] = "supported" if all(cgk["F"][k]["call"] == c for k, c in want.items()) else "not supported"
    orig = json.loads(a.original_cgk.read_text())
    v["R-CGK-KS-agreement"] = {k: {"original": orig["KS"][k]["call"], "replication": cgk["KS"][k]["call"]}
                               for k in orig["KS"] if orig["KS"][k]["call"] in ("enriched", "depleted")}
    # L1, L2: per-repo screen
    per = {}
    for r in REPOS:
        G.REPOS = (r,)
        per[r] = run(K, ["--scratch", str(scratch)])["KS"]
    G.REPOS = REPOS

    def enriched(ks, sig):
        x = ks.get(f"{sig}|hub", {})
        return x.get("z") is not None and x["or"] is not None and x["or"] > 1 and norm.sf(x["z"]) < 0.05

    l1 = {r: {s: enriched(per[r], s) for s in ("arch_api", "struct_args", "struct_branch")} for r in REPOS}
    v["CGR-L1"] = rule(sum(all(x.values()) for x in l1.values()), len(REPOS))
    l2c = {r: enriched(per[r], "state_pointers") for r in C_REPOS}
    l2n = {r: enriched(per[r], "state_pointers") for r in ("commons-lang", "sphinx")}
    v["CGR-L2"] = "supported" if sum(l2c.values()) >= 3 and not any(l2n.values()) else "not supported"
    # L3: sign agreement of the original significant cells in the pooled non-C repos
    G.REPOS = NON_C
    nonc = run(K, ["--scratch", str(scratch)])["KS"]
    G.REPOS = REPOS
    sig_cells = [k for k, x in orig["KS"].items() if x["call"] in ("enriched", "depleted")]
    agree = [k for k in sig_cells if nonc.get(k, {}).get("or") and
             (math.log(nonc[k]["or"]) > 0) == (orig["KS"][k]["call"] == "enriched")]
    v["CGR-L3"] = {"cells": len(sig_cells), "same_sign": len(agree), "share": len(agree) / len(sig_cells) if sig_cells else None,
                   "verdict": "supported" if sig_cells and len(agree) / len(sig_cells) >= 0.6 else "not supported"}
    res["language"] = {"L1_per_repo": l1, "L2_C": l2c, "L2_java_python": l2n,
                       "pointers_hub_or": {r: per[r].get("state_pointers|hub", {}).get("or") for r in REPOS},
                       "nonC_screen": nonc}
    res["M1"] = m1(scratch)
    v["CGR-M1"] = {k: res["M1"][k].get("carries") for k in ("rewired", "coupled", "cycle")} if "rewired" in res["M1"] else "not evaluable"
    res["verdicts"] = v
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
