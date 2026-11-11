#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""CEIL (exploratory, docs/ceil.md): how good could a file-year error-prediction model get?

Two jobs on the CGR file-year panel (no rescan; reads the CGR build output):

  1. THETA - a negative-binomial rate model with log(code size) as an EXPOSURE OFFSET
     (so the outcome is a rate per line and the size wall is handled by design, not by a
     covariate), then an oracle-ladder that turns its dispersion into a measured ceiling:
       rung 0  observed   - rank by mu-hat, score against the real labels
       rung 1  oracle-mu  - rank by mu-hat, score against y ~ Poisson(mu-hat)
                            => the ceiling given the rate variation these covariates DO see
       rung 2  oracle-lam - draw the NB latent rate lam = mu * Gamma(1/alpha, alpha),
                            rank by lam, score against y ~ Poisson(lam)
                            => the ceiling if a model recovered ALL rate heterogeneity
     rung 2 < 1.0 is irreducible discovery noise; (rung 2 - rung 1) is the headroom that
     alpha says our covariates are missing.

  2. M1REFIT - CGR-M1 re-fit with the two controls its own write-up flags as missing
     (author count, change coupling) and cluster-robust SEs by file, which M1 lacked
     (its p < 1e-37 came from treating 57k file-years as independent draws).

Exploratory. This does NOT touch the LAWS confirmatory frame or its registered draw.

    OMP_NUM_THREADS=1 <laws-venv>/bin/python tools/ceil_eval.py \
        --data /srv/storage_16tb/projects/gitgalaxy/cgr-study --out docs/ceil.json
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import pickle
import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np
import statsmodels.api as sm
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

sys.path.insert(0, str(Path(__file__).parent))
import cgr_build as B  # noqa: E402
import cgt_eval as G  # noqa: E402
from _engine import POOL_DIR, REPO_ROOT  # noqa: E402

REPOS = tuple(B.LANG)
YEAR = G.YEAR
BIG_COMMIT = 50          # chronometer prototype's co-change gate (mass reformats)
SAMPLE_EVERY = 4         # M1's sampling: every 4th quarterly snapshot ~ yearly
MIN_EXPOSURE = 1.0


# --------------------------------------------------------------------------------- history walk
def hist_window(repo: Path, sha: str, t0: float, t1: float, cache: Path):
    """Distinct authors and distinct co-change partners per file in (t0, t1], ancestors of sha only.

    Walking from `sha` with --until=t1 means nothing at or after the outcome window can enter
    these covariates - the same leakage discipline tools/incremental_value.py used.
    """
    cf = cache / f"hist_{sha}.pkl"
    if cf.exists():
        return pickle.loads(cf.read_bytes())
    raw = G.git(repo, "log", sha, f"--since={int(t0)}", f"--until={int(t1)}", "--no-merges",
                "--name-only", "--pretty=format:@@|%H|%ct|%an")
    authors = collections.defaultdict(set)
    partners = collections.defaultdict(set)
    nfix = collections.Counter()
    cur_author, files = None, []

    def flush():
        keep = [f for f in files if G.is_c(f)]
        for f in keep:
            authors[f].add(cur_author)
            nfix[f] += 1
        if 0 < len(files) <= BIG_COMMIT:
            for f in keep:
                partners[f] |= {g for g in keep if g != f}

    for line in raw.splitlines():
        if line.startswith("@@|"):
            if cur_author is not None:
                flush()
            parts = line.split("|")
            cur_author = parts[3] if len(parts) > 3 else ""
            files = []
        elif line.strip():
            files.append(line.strip())
    if cur_author is not None:
        flush()
    out = ({f: len(v) for f, v in authors.items()},
           {f: len(v) for f, v in partners.items()},
           dict(nfix))
    cf.write_bytes(pickle.dumps(out))
    return out


def file_code_size(db: Path, shas):
    """sum(function loc) and sum(state_safety_neg) per (sha, file_path).

    Mirrors snapshot_networks' own function filter (named, loc >= 3) so the exposure counts
    exactly the code mass whose call network M1 measured.
    """
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    want = set(shas)
    fid2 = {}
    for fid, path, sha in con.execute("SELECT id, file_path, commit_hash FROM file_data"):
        if sha in want and path:
            fid2[fid] = (sha, path)
    loc = collections.Counter()
    unsafe = collections.Counter()
    nfunc = collections.Counter()
    ids = list(fid2)
    for i in range(0, len(ids), 900):
        chunk = ids[i:i + 900]
        q = ("SELECT file_id, func_name, loc, state_safety_neg FROM function_data "
             f"WHERE file_id IN ({','.join('?' * len(chunk))})")
        for fid, name, fl, uns in con.execute(q, chunk):
            if not name or (fl or 0) < 3:
                continue
            key = fid2[fid]
            loc[key] += float(fl or 0)
            unsafe[key] += float(uns or 0)
            nfunc[key] += 1
    con.close()
    return loc, unsafe, nfunc


# --------------------------------------------------------------------------------- panel
# Outcome classes present in the CGR event sets. `latent` is absent here (41 events, libxml2
# only), so the clean-label arm uses `regression` - the class with a PASSING precision audit
# (0.73-0.87) - against `other_fix`, the catch-all that carries ~90% of the outcome mass and
# has never been audited at all. See docs/ceil.md.
CLASS_ARMS = ("all", "regression", "other_fix")
C_REPOS = ("libgit2", "postgres", "libxml2", "redis")

COLS = ("repo", "fileid", "rewired", "coupled", "cycle", "log_functions", "log_churn",
        "log_authors", "log_cochange", "unsafe_dens", "exposure",
        "prior_all", "prior_reg", "prior_oth",
        "y_all", "y_reg", "y_oth")


def build_panel(data: Path, cache: Path):
    scratch = data / "scratch"
    rows = []
    fkey = {}
    meta = {}
    for ri, r in enumerate(REPOS):
        nets = G.snapshot_networks(r, scratch)
        prs = pickle.loads((scratch / f"pairs_{r}.pkl").read_bytes())
        xc = json.loads((REPO_ROOT / "events" / f"{r}_xc.json").read_text())["events"]
        if not xc:
            continue
        fixes = collections.defaultdict(list)
        fixes_reg = collections.defaultdict(list)
        fixes_oth = collections.defaultdict(list)
        for e in xc:
            cl = e.get("class")
            for f in e.get("c_files", []):
                fixes[f].append(e["ct"])
                if cl == "regression":
                    fixes_reg[f].append(e["ct"])
                elif cl == "other-fix":
                    fixes_oth[f].append(e["ct"])
        lo, hi = min(e["ct"] for e in xc), max(e["ct"] for e in xc)
        yi = list(range(0, len(nets), SAMPLE_EVERY))
        used = [i for k, i in enumerate(yi)
                if k and nets[i]["ct"] - YEAR >= lo and nets[i]["ct"] + YEAR <= hi]
        loc, unsafe, nfunc = file_code_size(data / "dbs" / f"{r}.db", [nets[i]["sha"] for i in used])
        n0 = len(rows)
        for k, i in enumerate(yi):
            if not k or i not in used:
                continue
            n, t, sha = nets[i], nets[i]["ct"], nets[i]["sha"]
            per, _, _ = G.numstat(POOL_DIR / r, nets[yi[k - 1]]["sha"], sha)
            auth, part, _ = hist_window(POOL_DIR / r, sha, t - YEAR, t, cache)
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
            def win(d, f, a, b):
                return sum(1 for c in d.get(f, ()) if a < c <= b)

            for f in files:
                ex = max(loc.get((sha, f), 0.0), MIN_EXPOSURE)
                fid = fkey.setdefault((ri, f), len(fkey))
                rows.append((ri, fid,
                             int(f in rew),
                             int(coup[f] >= thr and coup[f] > 0),
                             int(scc[lab[idx[f]]] >= 2),
                             math.log1p(size[f]),
                             math.log1p(per.get(f, 0)),
                             math.log1p(auth.get(f, 0)),
                             math.log1p(part.get(f, 0)),
                             unsafe.get((sha, f), 0.0) / ex,
                             ex,
                             win(fixes, f, t - YEAR, t),
                             win(fixes_reg, f, t - YEAR, t),
                             win(fixes_oth, f, t - YEAR, t),
                             win(fixes, f, t, t + YEAR),
                             win(fixes_reg, f, t, t + YEAR),
                             win(fixes_oth, f, t, t + YEAR)))
        meta[r] = {"snapshots_sampled": len(used), "file_years": len(rows) - n0}
    A = np.array(rows, float)
    return A, meta


# --------------------------------------------------------------------------------- metrics
def auc(score, y):
    y = np.asarray(y) > 0
    if y.all() or not y.any():
        return float("nan")
    rk = np.empty(len(score), float)
    order = np.argsort(score, kind="mergesort")
    s = np.asarray(score)[order]
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        rk[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    npos, nneg = y.sum(), (~y).sum()
    return float((rk[y].sum() - npos * (npos + 1) / 2) / (npos * nneg))


def recall_at_effort(score, ycnt, exposure, frac=0.20):
    """Share of fix events captured inside the top `frac` of total lines reviewed."""
    tot_e, tot_y = exposure.sum(), ycnt.sum()
    if tot_y <= 0:
        return float("nan")
    order = np.argsort(-np.asarray(score), kind="mergesort")
    ce = np.cumsum(exposure[order])
    take = ce <= frac * tot_e
    if not take.any():
        take[0] = True
    return float(ycnt[order][take].sum() / tot_y)


def banded_auc(score, y, exposure, nb=4):
    q = np.quantile(exposure, np.linspace(0, 1, nb + 1))
    out = []
    for b in range(nb):
        m = (exposure >= q[b]) & (exposure <= q[b + 1]) if b == nb - 1 else (exposure >= q[b]) & (exposure < q[b + 1])
        out.append({"band": b + 1, "n": int(m.sum()), "pos": int((np.asarray(y)[m] > 0).sum()),
                    "auc": auc(np.asarray(score)[m], np.asarray(y)[m])})
    return out


# --------------------------------------------------------------------------------- derived columns
DERIVED = ("prior_fix", "log_prior_all", "log_prior_reg", "log_prior_oth", "y_bin")


def augment(A, ci):
    pa, pr, po = A[:, ci["prior_all"]], A[:, ci["prior_reg"]], A[:, ci["prior_oth"]]
    extra = np.column_stack([(pa > 0).astype(float), np.log1p(pa), np.log1p(pr), np.log1p(po),
                             (A[:, ci["y_all"]] > 0).astype(float)])
    A2 = np.column_stack([A, extra])
    ci2 = dict(ci)
    for i, nm in enumerate(DERIVED):
        ci2[nm] = A.shape[1] + i
    return A2, ci2


def subset(A, ci, which):
    cidx = [REPOS.index(r) for r in C_REPOS if r in REPOS]
    if which == "all_repos":
        return A
    m = np.isin(A[:, ci["repo"]].astype(int), cidx)
    return A[m] if which == "c_only" else A[~m]


# --------------------------------------------------------------------------------- 2 - M1 re-fit
M1_TERMS = ["rewired", "coupled", "cycle", "log_functions", "log_churn", "prior_fix"]
NEW_TERMS = ["log_authors", "log_cochange"]


def _dummies(A, c):
    used = sorted({int(x) for x in A[:, c]})
    return np.stack([(A[:, c] == ri).astype(float) for ri in used], axis=1)


def _irls(X, y, iters=60):
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


def _llr(y, Xsmall, Xbig):
    from scipy.stats import chi2
    a = sm.Logit(y, Xsmall).fit(disp=0)
    b = sm.Logit(y, Xbig).fit(disp=0)
    stat = 2 * (b.llf - a.llf)
    df = Xbig.shape[1] - Xsmall.shape[1]
    return {"chi2": float(stat), "df": int(df), "p": float(chi2.sf(stat, df)),
            "pseudo_r2_base": float(a.prsquared), "pseudo_r2_full": float(b.prsquared)}


def m1_refit(A, ci, label):
    y = A[:, ci["y_bin"]]
    D = _dummies(A, ci["repo"])
    out = {"subset": label, "file_years": int(len(A)), "positives": int(y.sum()),
           "n_files": int(len(set(A[:, ci["fileid"]].astype(int))))}
    if y.sum() < 50 or D.shape[1] < 1:
        return {**out, "verdict": "not evaluable"}

    # (a) M1 exactly as published - same hand-rolled IRLS, naive SEs - to prove the frame matches.
    Xa = np.column_stack([A[:, [ci[t] for t in M1_TERMS]], D])
    ba, sea = _irls(Xa, y)
    out["published_spec"] = {t: {"or": float(math.exp(ba[i])), "z": float(ba[i] / sea[i])}
                             for i, t in enumerate(M1_TERMS)}

    # (b) + the two controls CGR's own write-up flags as missing, cluster-robust SEs.
    terms = M1_TERMS + NEW_TERMS
    Xb = np.column_stack([A[:, [ci[t] for t in terms]], D])
    res = {}
    for lab, grp in (("cluster_file", A[:, ci["fileid"]]), ("cluster_repo", A[:, ci["repo"]])):
        m = sm.Logit(y, Xb).fit(disp=0, cov_type="cluster", cov_kwds={"groups": grp.astype(int)})
        cis = m.conf_int()
        res[lab] = {t: {"or": float(math.exp(m.params[i])), "z": float(m.tvalues[i]),
                        "p_two_sided": float(m.pvalues[i]),
                        "ci95": [float(math.exp(cis[i][0])), float(math.exp(cis[i][1]))]}
                    for i, t in enumerate(terms)}
    out["with_controls"] = res

    base = ["log_functions", "log_churn", "prior_fix"] + NEW_TERMS
    Xc = np.column_stack([A[:, [ci[t] for t in base]], D])
    mc = sm.Logit(y, Xc).fit(disp=0, cov_type="cluster", cov_kwds={"groups": A[:, ci["fileid"]].astype(int)})
    out["baseline_only"] = {t: {"or": float(math.exp(mc.params[i])), "z": float(mc.tvalues[i])}
                            for i, t in enumerate(base)}
    out["network_adds_llr"] = _llr(y, Xc, Xb)
    return out


# --------------------------------------------------------------------------------- 1 - theta ceiling
NET_TERMS = ["rewired", "coupled", "cycle"]
PROC_TERMS = ["log_churn", "log_authors", "log_cochange"]
ARM_Y = {"all": ("y_all", "log_prior_all"), "regression": ("y_reg", "log_prior_reg"),
         "other_fix": ("y_oth", "log_prior_oth")}


def rate_terms(arm):
    return NET_TERMS + PROC_TERMS + [ARM_Y[arm][1], "unsafe_dens"]


def _nb(y, X, off):
    """NB2, started from the Poisson fit - without start_params this falls back to Nelder-Mead."""
    pois = sm.GLM(y, X, family=sm.families.Poisson(), offset=off).fit()
    start = np.append(np.asarray(pois.params, float), 1.0)
    m = sm.NegativeBinomial(y, X, offset=off, loglike_method="nb2")
    with np.errstate(all="ignore"):
        try:
            r = m.fit(start_params=start, disp=0, maxiter=400)
            if not np.isfinite(r.params).all() or r.params[-1] <= 0:
                raise ValueError("bad nb2 fit")
        except Exception:
            r = m.fit(start_params=start, method="nm", disp=0, maxiter=12000, xtol=1e-6, ftol=1e-6)
    return r


def theta_probe(A, ci, arm, label, draws=200, seed=2982, loro=False):
    rng = np.random.default_rng(seed)
    terms = rate_terms(arm)
    ycnt = A[:, ci[ARM_Y[arm][0]]]
    ex = A[:, ci["exposure"]]
    off = np.log(ex)
    D = _dummies(A, ci["repo"])
    X = np.column_stack([A[:, [ci[t] for t in terms]], D])

    out = {"subset": label, "arm": arm, "file_years": int(len(A)),
           "fix_events": int(ycnt.sum()), "file_years_with_a_fix": int((ycnt > 0).sum()),
           "exposure_total_lines": float(ex.sum()),
           "note_offset": "log(sum of function loc) as exposure; the rate model carries no size covariate"}
    if ycnt.sum() < 100:
        return {**out, "verdict": "not evaluable"}

    res = _nb(ycnt, X, off)
    alpha = float(res.params[-1])
    beta = np.asarray(res.params[:-1], float)
    mu = np.exp(X @ beta + off)
    out.update({"alpha": alpha, "theta": float(1.0 / alpha) if alpha > 0 else None,
                "converged": bool(getattr(res, "mle_retvals", {}).get("converged", True)),
                "terms": {t: {"irr": float(math.exp(beta[i])), "z": float(res.tvalues[i])}
                          for i, t in enumerate(terms)},
                "var_share_poisson": float(mu.sum() / (mu + alpha * mu ** 2).sum())})

    def score_set(rate, yy):
        """`rate` is an expected COUNT (mu or lam). An oracle ranks by whatever the metric rewards:
        by expected count when the question is "which file-year gets a fix", and by expected count
        PER LINE under a review budget - ranking by raw count there just spends the budget on the
        biggest files, which is the size confound in metric form."""
        dens = rate / ex
        return {"auc": auc(rate, yy),
                "auc_density": auc(dens, yy),
                "recall_at_20pct_lines": recall_at_effort(dens, yy, ex),
                "banded_auc": [b["auc"] for b in banded_auc(rate, yy, ex)]}

    out["rung0_observed_insample"] = score_set(mu, ycnt)

    if loro:
        pred = np.zeros(len(A))
        for ri in sorted({int(x) for x in A[:, ci["repo"]]}):
            te = A[:, ci["repo"]] == ri
            tr = ~te
            Xtr = np.column_stack([A[tr][:, [ci[t] for t in terms]], _dummies(A[tr], ci["repo"])])
            rtr = _nb(ycnt[tr], Xtr, off[tr])
            pr = np.asarray(rtr.params[:-1], float)
            # the held-out repo has no dummy of its own: use the mean trained repo intercept
            pred[te] = np.exp(A[te][:, [ci[t] for t in terms]] @ pr[:len(terms)]
                              + float(np.mean(pr[len(terms):])) + off[te])
        out["rung0_observed_loro"] = score_set(pred, ycnt)

    def ladder(rate_fn):
        acc = collections.defaultdict(list)
        for _ in range(draws):
            lam = rate_fn()
            ysim = rng.poisson(lam)
            if ysim.sum() == 0:
                continue
            s = score_set(lam, ysim)
            acc["auc"].append(s["auc"])
            acc["auc_density"].append(s["auc_density"])
            acc["recall_at_20pct_lines"].append(s["recall_at_20pct_lines"])
            acc["banded_auc"].append(s["banded_auc"])
        o = {}
        for k in ("auc", "auc_density", "recall_at_20pct_lines"):
            v = np.array(acc[k], float)
            o[k] = {"mean": float(np.nanmean(v)), "pct2_5": float(np.nanpercentile(v, 2.5)),
                    "pct97_5": float(np.nanpercentile(v, 97.5))}
        o["banded_auc_mean"] = [float(x) for x in np.nanmean(np.array(acc["banded_auc"], float), axis=0)]
        o["draws"] = len(acc["auc"])
        return o

    out["rung1_oracle_mu"] = ladder(lambda: mu)
    shape = 1.0 / alpha if alpha > 0 else 1e6
    out["rung2_oracle_lambda"] = ladder(lambda: mu * rng.gamma(shape, 1.0 / shape, size=len(mu)))

    # Rarity-adjusted: share of the ATTAINABLE ranking signal the fitted model actually realises.
    # Both terms face the same event rate, so this is comparable across arms with different
    # numbers of positives - which raw AUC levels are not.
    def frac(obs, orc, chance):
        return float((obs - chance) / (orc - chance)) if (orc - chance) > 1e-9 else None
    for rung in ("rung0_observed_insample", "rung0_observed_loro"):
        if rung not in out:
            continue
        # Only `auc` and `recall_at_20pct_lines` have a genuine oracle bound. For a binary
        # "did this file-year get a fix", the Bayes-optimal ranker is the expected count lam
        # (P(y>0) = 1 - exp(-lam) is monotone in lam), so ranking by lam is optimal for AUC;
        # under a line budget the fractional-knapsack optimum is lam/lines, so that is optimal
        # for recall@budget. `auc_density` is neither - the oracle is NOT optimal for it, so a
        # fitted model can exceed it and a ratio against it is not a share of anything. It is
        # reported as a descriptive size-orthogonality check only.
        out[rung]["realized_fraction_vs_oracle_mu"] = {
            "auc": frac(out[rung]["auc"], out["rung1_oracle_mu"]["auc"]["mean"], 0.5),
            "recall_at_20pct_lines": frac(out[rung]["recall_at_20pct_lines"],
                                          out["rung1_oracle_mu"]["recall_at_20pct_lines"]["mean"], 0.20),
            "auc_density": "not a bound - see comment; use the descriptive value"}
    out["headroom_mu_to_lambda"] = {
        "auc": float(out["rung2_oracle_lambda"]["auc"]["mean"] - out["rung1_oracle_mu"]["auc"]["mean"]),
        "auc_density": float(out["rung2_oracle_lambda"]["auc_density"]["mean"]
                             - out["rung1_oracle_mu"]["auc_density"]["mean"]),
        "recall_at_20pct_lines": float(out["rung2_oracle_lambda"]["recall_at_20pct_lines"]["mean"]
                                       - out["rung1_oracle_mu"]["recall_at_20pct_lines"]["mean"])}
    return out


# --------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path, help="CGR build output (dbs/ + scratch/)")
    ap.add_argument("--cache", type=Path, default=Path("/home/joe/.claude/jobs/9045a6ea/tmp/ceil_cache"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--draws", type=int, default=200)
    a = ap.parse_args()
    a.cache.mkdir(parents=True, exist_ok=True)

    # the same global extension patch CGR used, so the file set matches M1's exactly
    G.CEXT = (".c", ".h", ".cc", ".cpp", ".cxx", ".hh", ".hpp", ".go", ".java", ".py", ".rs")
    from sfs_eval import DBS as SDBS
    for r in REPOS:
        SDBS[r] = a.data / "dbs" / f"{r}.db"

    pcache = a.cache / "panel.npz"
    if pcache.exists():
        z = np.load(pcache, allow_pickle=True)
        A, meta = z["A"], json.loads(str(z["meta"]))
    else:
        A, meta = build_panel(a.data, a.cache)
        np.savez(pcache, A=A, meta=json.dumps(meta))
    ci = {c: i for i, c in enumerate(COLS)}
    A, ci = augment(A, ci)
    print(f"panel: {A.shape[0]} file-years, "
          f"{len(set(A[:, ci['fileid']].astype(int)))} files", file=sys.stderr)

    res = {"frame": {"repos": list(REPOS), "c_repos": list(C_REPOS), "per_repo": meta,
                     "sample_every": SAMPLE_EVERY, "outcome": "fix events in (t, t+1y]",
                     "covariate_window": "(t-1y, t]", "draws": a.draws,
                     "exploratory": "not registered; does not touch the LAWS confirmatory frame"},
           "theta_ceiling": {}, "m1_refit": {}}

    # 1 - theta ceiling: primary, then the clean-label arms, then the audited-rule subsets
    plan = [("all_repos", "all", True), ("all_repos", "regression", False),
            ("all_repos", "other_fix", False), ("c_only", "all", False), ("non_c", "all", False),
            ("c_only", "regression", False)]
    for which, arm, loro in plan:
        S = subset(A, ci, which)
        key = f"{which}|{arm}"
        print(f"theta: {key} ({len(S)} rows)", file=sys.stderr)
        res["theta_ceiling"][key] = theta_probe(S, ci, arm, which, draws=a.draws, loro=loro)

    # 2 - M1 re-fit: published frame, plus the C-only / non-C split
    for which in ("all_repos", "c_only", "non_c"):
        print(f"m1_refit: {which}", file=sys.stderr)
        res["m1_refit"][which] = m1_refit(subset(A, ci, which), ci, which)

    a.out.write_text(json.dumps(res, indent=1) + "\n")
    print(f"wrote {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
