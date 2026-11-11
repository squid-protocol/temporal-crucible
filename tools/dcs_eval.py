#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""DCS (docs/dcs_hypotheses.md): among danger-commented births, does anything the engine measures at birth separate
the functions that needed a CVE fix within 5 years from the ones that stayed safe? Two stages. Engine venv:

    E=<gitgalaxy worktree>
    GITGALAXY_PATH=$E PYTHONPATH=$E SFS_SRC=<popan>/structural-fingerprint-scanner/src \\
        <venv>/bin/python tools/dcs_eval.py stage1     # discovery only -> docs/dcs_discovery.md, docs/dcs_models.json
    # commit both files, then:
        <venv>/bin/python tools/dcs_eval.py stage2     # frozen models on confirmation -> docs/dcs.md

Stage 1 drops every confirmation function right after the outcome-blind split, before any outcome or feature is
read. Stage 2 refuses to run unless docs/dcs_models.json is committed and unmodified, and it never refits.
Cohort, fix mapping and comments are DC-2's (dc_eval.comment_task, chg_eval.map_fix, ints_eval.lives); the lattice
family is LAT's (lat_eval.Lattice.assign over chg2_eval.SIG presence). Aggregates only.
"""
from __future__ import annotations

import argparse
import bisect
import datetime as dt
import hashlib
import json
import multiprocessing
import os
import pathlib
import sqlite3
import subprocess
import sys
import time
from collections import Counter, defaultdict

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import rankdata

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, REPO_ROOT  # noqa: E402
from chg2_eval import SIG, select  # noqa: E402
from chg_eval import fix_events, map_fix  # noqa: E402
from dc_eval import comment_task  # noqa: E402
from ints_eval import REPOS, YEAR, lives  # noqa: E402
from lat_eval import TREES_SHA, Lattice  # noqa: E402
from nh_eval import DBS  # noqa: E402

SEED, ITERS = 2982, 2000
HORIZON = 5 * YEAR
ALPHA = 0.01 / 4
MIN_CASES = 20
NULL_BAND = 0.02
MIN_NZ = 0.005
NFOLD = 5
CGRID = np.logspace(-3, 2, 11)
MODELS = ("B", "T", "F", "C", "ALL")
CLAIMS = {"T": "DCS-T", "F": "DCS-F", "C": "DCS-C", "ALL": "DCS-ALL"}
MODELS_PATH = DOCS_DIR / "dcs_models.json"
DISC_PATH = DOCS_DIR / "dcs_discovery.md"
CONF_PATH = DOCS_DIR / "dcs.md"
# registration: comment-derived columns define the cohort and are 0 in these pre-#8200 DBs; def_shape is empty
DROP_COMMENT = {"state_graveyard", "sec_dead_code", "def_doc", "def_ownership", "state_planned_debt",
                "state_fragile_debt", "is_documented", "def_shape"}
T_PREFIX = ("struct_", "def_", "state_", "arch_", "threat_", "sec_")
T_EXTRA = ("bitwise_ops", "complexity", "args", "token_mass", "keyword_density", "func_z_score")
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:6.0f}s] {m}", flush=True)


def day(ct):
    return dt.datetime.fromtimestamp(ct, dt.timezone.utc).strftime("%Y-%m-%d")


# ------------------------------------------------------------------ cohort (DC-2's), outcome, split
def cohort():
    """Every commented birth (C/C++, born after the first snapshot, loc >= 3), with its first CVE fix while alive."""
    ev, last = [], {}
    for r in REPOS:
        e, last[r] = fix_events(r)
        ev += [x for x in e if x[3] == "latent"]
    with multiprocessing.get_context("fork").Pool(8) as p:
        hits = [h for hs in p.imap_unordered(map_fix, ev, chunksize=8) for h in hs]
    log(f"CVE-fix hits {len(hits):,}")
    U = []
    for r in REPOS:
        snaps, ids_at, info = lives(r)
        cts = [s["ct"] for s in snaps]
        first, file_cve = {}, defaultdict(list)
        for (_r, path, nm, ct, klass) in (h for h in hits if h[0] == r):
            if klass != "latent":
                continue
            file_cve[path].append(ct)
            j = bisect.bisect_right(cts, ct) - 1
            if j < 0:
                continue
            fid = None
            for jj in (j, j + 1):
                if jj < len(ids_at) and fid is None:
                    for cand in ((path, nm), (path, nm.split("::")[-1])):
                        if cand in ids_at[jj]:
                            fid = ids_at[jj][cand]
                            break
            if fid is not None and (fid not in first or ct < first[fid]):
                first[fid] = ct
        for v in file_cve.values():
            v.sort()
        groups = defaultdict(list)
        for fid, inf in info.items():
            if inf["birth_k"] > 0 and inf["loc"] >= 3:
                groups[(snaps[inf["birth_k"]]["sha"], inf["key"][0])].append(inf["key"][1])
        with multiprocessing.get_context("fork").Pool(8) as p:
            cm = {(rr, sha, path): out for rr, sha, path, out in
                  p.imap_unordered(comment_task, [(r, sha, path, names) for (sha, path), names in groups.items()],
                                   chunksize=4)}
        for fid, inf in info.items():
            if inf["birth_k"] == 0 or inf["loc"] < 3:
                continue
            b = cts[inf["birth_k"]]
            death = cts[inf["last_k"] + 1] if inf["last_k"] + 1 < len(cts) else float("inf")
            end = min(death, last[r])
            if end <= b:
                continue
            sha = snaps[inf["birth_k"]]["sha"]
            c = cm.get((r, sha, inf["key"][0]), {}).get(inf["key"][1])
            if c is None or c[0] < 1:
                continue
            fl = first.get(fid)
            U.append({"r": r, "file": inf["key"][0], "name": inf["key"][1], "sha": sha, "b": b, "death": death,
                      "loc": inf["loc"], "danger": bool(c[1]), "eligible": b + HORIZON <= last[r],
                      "prior": bisect.bisect_left(file_cve.get(inf["key"][0], []), b) > 0,
                      "_fl": fl if fl is not None and b < fl <= end else None})
        log(f"{r}: commented births {sum(1 for u in U if u['r'] == r):,}")
    return U


def split(U):
    """Outcome-blind: per repo, median birth time of the eligible danger-commented births."""
    med = {r: float(np.median([u["b"] for u in U if u["r"] == r and u["eligible"] and u["danger"]])) for r in REPOS}
    for u in U:
        u["half"] = "disc" if u["b"] < med[u["r"]] else "conf"
    return med


def outcome(u):
    """1 = first CVE fix within 5 years of birth; 0 = alive at birth + 5 y with none; -1 = died earlier without one."""
    h = u["b"] + HORIZON
    if u["_fl"] is not None and u["_fl"] <= h:
        return 1
    return 0 if u["death"] > h else -1


# ------------------------------------------------------------------ features at the birth snapshot
def columns():
    have = None
    for r in REPOS:
        con = sqlite3.connect(f"file:{DBS[r]}?mode=ro", uri=True)
        cols = {c[1]: c[2] for c in con.execute("PRAGMA table_info(function_data)")}
        con.close()
        have = cols if have is None else {k: v for k, v in have.items() if k in cols}
    tcols = sorted(c for c, t in have.items() if t in ("INTEGER", "REAL") and c not in DROP_COMMENT
                   and not c.startswith("lit_") and (c.startswith(T_PREFIX) or c in T_EXTRA))
    return tcols, sorted(set(SIG)), set(have)


def read_rows(units, tcols, sigcols, have):
    want = sorted(set(tcols) | {c for c in sigcols if c in have} |
                  {"func_archetype", "calls_out_to", "func_pagerank", "func_fan_in", "func_fan_out", "is_public"})
    need = defaultdict(set)
    for u in units:
        need[(u["r"], u["sha"])].add((u["file"], u["name"]))
    out = {}
    cons = {r: sqlite3.connect(f"file:{DBS[r]}?mode=ro", uri=True) for r in REPOS}
    sel = ", ".join(f"f.{c}" for c in want)
    for (r, sha), keys in need.items():
        rows = cons[r].execute(f"SELECT fd.file_path, f.func_name, f.start_line, {sel} FROM function_data f "
                               "JOIN file_data fd ON f.file_id = fd.id WHERE fd.commit_hash = ? "
                               "AND fd.language IN ('c','cpp') AND f.func_name IS NOT NULL AND f.func_name != ''",
                               (sha,)).fetchall()
        d = {}
        for row in sorted(rows, key=lambda x: (x[0], x[1], x[2] or 0)):  # ints_eval.lives' tie rule
            d.setdefault((row[0], row[1]), row)
        for k in keys:
            if k in d:
                out[(r, sha) + k] = dict(zip(want, d[k][3:]))
    for c in cons.values():
        c.close()
    return out


def ncallees(s):
    try:
        return len(set(json.loads(s))) if s else 0
    except (ValueError, TypeError):
        return 0


def assemble(units, rows, L, tcols, sigcols, arch_levels):
    """All candidate features, by name ('B:', 'T:', 'F:', 'C:' prefixes)."""
    loc = np.array([u["loc"] for u in units], float)
    R = [rows[(u["r"], u["sha"], u["file"], u["name"])] for u in units]
    g = lambda c: np.array([float(x.get(c) or 0) for x in R])  # noqa: E731
    F = {"B:log_loc": np.log(loc), "B:prior_cve_file": np.array([float(u["prior"]) for u in units])}
    for r in REPOS:
        F[f"B:repo={r}"] = np.array([float(u["r"] == r) for u in units])
    for c in tcols:  # registration: each signal ÷ loc
        F[f"T:{c}/loc"] = g(c) / loc
    P = np.array([[(x.get(c) or 0) > 0 for c in sigcols] for x in R], bool).reshape(len(R), len(sigcols))
    fam, k, _ = L.assign(P, sigcols)
    for f in range(int(L.fam.max()) + 1):
        F[f"F:lat_family={'F' + str(f) if f else 'unassigned'}"] = (fam == f).astype(float)
    F["F:lat_rung"] = k.astype(float)
    arch = np.array([x.get("func_archetype") or "none" for x in R])
    for a in arch_levels:
        F[f"F:archetype={a}"] = (arch == a).astype(float)
    F["C:log1p_pagerank"] = np.log1p(g("func_pagerank"))
    F["C:log1p_fan_in"] = np.log1p(g("func_fan_in"))
    F["C:log1p_fan_out"] = np.log1p(g("func_fan_out"))
    F["C:log1p_distinct_callees"] = np.log1p([ncallees(x.get("calls_out_to")) for x in R])
    F["C:is_public"] = (g("is_public") > 0).astype(float)
    return F, fam, k, arch


def family_cols(names, fam):
    base = [n for n in names if n.startswith("B:")]
    if fam == "B":
        return base
    pre = ("T:", "F:", "C:") if fam == "ALL" else (fam + ":",)
    return base + [n for n in names if n.startswith(pre)]


# ------------------------------------------------------------------ models
def auc(y, s):
    n1 = y.sum()
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return np.nan
    r = rankdata(s)
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def fit_logit(X, y, C):
    """L2-penalised logistic regression (sklearn's convention: loss + ||w||^2 / 2C; intercept unpenalised)."""
    def f(w):
        z = X @ w[1:] + w[0]
        pr = expit(z)
        g = np.r_[np.sum(pr - y), X.T @ (pr - y)]
        g[1:] += w[1:] / C
        return np.sum(np.logaddexp(0, z) - y * z) + 0.5 * np.sum(w[1:] ** 2) / C, g
    return minimize(f, np.zeros(X.shape[1] + 1), jac=True, method="L-BFGS-B", options={"maxiter": 10000}).x


def scaler(X):
    mu, sd = X.mean(0), X.std(0)
    return mu, np.where(sd > 0, sd, 1.0)


def predict(m, X):
    return ((X - np.array(m["mu"])) / np.array(m["sd"])) @ np.array(m["coef"]) + m["intercept"]


def choose_C(X, y, fold):
    best = None
    for C in CGRID:  # ascending, strict improvement -> ties keep the stronger penalty
        aucs = []
        for k in range(NFOLD):
            tr, te = fold != k, fold == k
            if y[te].min() == y[te].max() or y[tr].min() == y[tr].max():
                continue
            mu, sd = scaler(X[tr])
            w = fit_logit((X[tr] - mu) / sd, y[tr], C)
            aucs.append(auc(y[te], ((X[te] - mu) / sd) @ w[1:] + w[0]))
        m = float(np.mean(aucs))
        if best is None or m > best[1] + 1e-12:
            best = (float(C), m)
    return best


def file_folds(groups):
    ug = np.unique(groups)
    perm = np.random.default_rng(SEED).permutation(len(ug))
    fold_of = {ug[i]: j % NFOLD for j, i in enumerate(perm)}
    return np.array([fold_of[g] for g in groups])


# ------------------------------------------------------------------ exploratory helpers
def mh_or(e, y, st):
    """Mantel-Haenszel OR with the Robins-Breslow-Greenland variance of log OR."""
    _, si = np.unique(st, return_inverse=True)
    a, b = np.bincount(si, e * y), np.bincount(si, e * (1 - y))
    c, d = np.bincount(si, (1 - e) * y), np.bincount(si, (1 - e) * (1 - y))
    n = a + b + c + d
    ok = n > 1
    a, b, c, d, n = a[ok], b[ok], c[ok], d[ok], n[ok]
    R, S, P, Q = a * d / n, b * c / n, (a + d) / n, (b + c) / n
    if R.sum() == 0 or S.sum() == 0:
        return np.nan, np.nan
    v = (P * R).sum() / (2 * R.sum() ** 2) + (P * S + Q * R).sum() / (2 * R.sum() * S.sum()) + \
        (Q * S).sum() / (2 * S.sum() ** 2)
    return float(R.sum() / S.sum()), float(np.sqrt(v))


def exposure_threshold(x):
    med = float(np.median(x))
    return med if med > 0 else 0.0


def strata(units):
    return np.array([f"{u['r']}|{int(np.floor(np.log10(u['loc']) / 0.1))}" for u in units])


def shallow_tree(X, y, names, depth=3, min_leaf=20):
    out = []

    def gini(v):
        p = v.mean()
        return 2 * p * (1 - p)

    def grow(idx, d, label):
        yy = y[idx]
        out.append(f"{'    ' * d}- {label}n = {len(idx):,}, cases {int(yy.sum())} ({yy.mean():.1%})")
        if d == depth or yy.sum() in (0, len(yy)):
            return
        best = None
        for j in range(X.shape[1]):
            x = X[idx, j]
            for t in np.unique(np.quantile(x, np.linspace(0.05, 0.95, 19))):
                left = x <= t
                nl = int(left.sum())
                if nl < min_leaf or len(x) - nl < min_leaf:
                    continue
                gg = (nl * gini(yy[left]) + (len(x) - nl) * gini(yy[~left])) / len(x)
                if best is None or gg < best[0]:
                    best = (gg, j, t, left)
        if best is None or best[0] >= gini(yy) - 1e-9:
            return
        _, j, t, left = best
        grow(idx[left], d + 1, f"`{names[j]}` ≤ {t:.4g}: ")
        grow(idx[~left], d + 1, f"`{names[j]}` > {t:.4g}: ")

    grow(np.arange(len(y)), 0, "")
    return out


def engine_commit():
    e = os.environ.get("GITGALAXY_PATH", "")
    try:
        return subprocess.run(["git", "-C", e, "rev-parse", "--short=12", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


# ------------------------------------------------------------------ Stage 1
def stage1(force):
    if MODELS_PATH.exists() and not force:
        raise SystemExit(f"{MODELS_PATH} exists; Stage 1 would overwrite frozen models (use --force before Stage 2 only)")
    L = Lattice()
    U = cohort()
    med = split(U)
    counts = {r: {"commented": sum(1 for u in U if u["r"] == r),
                  "danger": sum(1 for u in U if u["r"] == r and u["danger"]),
                  "eligible": sum(1 for u in U if u["r"] == r and u["danger"] and u["eligible"]),
                  "conf_n": sum(1 for u in U if u["r"] == r and u["danger"] and u["eligible"] and u["half"] == "conf")}
              for r in REPOS}
    # blindness: everything from here on sees discovery danger-commented eligible births only
    D = [u for u in U if u["danger"] and u["eligible"] and u["half"] == "disc"]
    del U
    for u in D:
        u["y"] = outcome(u)
    early = Counter(u["r"] for u in D if u["y"] < 0)
    D = [u for u in D if u["y"] >= 0]
    tcols, sigcols, have = columns()
    rows = read_rows(D, tcols, sigcols, have)
    miss = Counter(u["r"] for u in D if (u["r"], u["sha"], u["file"], u["name"]) not in rows)
    D = [u for u in D if (u["r"], u["sha"], u["file"], u["name"]) in rows]
    arch_all = Counter(x.get("func_archetype") or "none" for x in rows.values())
    arch_levels = sorted(arch_all)
    F, fam, k, arch = assemble(D, rows, L, tcols, sigcols, arch_levels)
    y = np.array([float(u["y"]) for u in D])
    nz = {n: float((v != 0).mean()) for n, v in F.items()}
    dropped = sorted(n for n in F if not n.startswith("B:") and nz[n] < MIN_NZ)
    names = [n for n in F if n not in dropped]
    log(f"discovery: {len(D):,} functions, {int(y.sum())} cases; features kept {len(names)}, dropped {len(dropped)}")
    groups = np.array([f"{u['r']}:{u['file']}" for u in D])
    fold = file_folds(groups)
    models = {}
    for m in MODELS:
        cols = family_cols(names, m)
        X = np.column_stack([F[c] for c in cols])
        C, cv = choose_C(X, y, fold)
        mu, sd = scaler(X)
        w = fit_logit((X - mu) / sd, y, C)
        models[m] = {"features": cols, "mu": mu.tolist(), "sd": sd.tolist(), "coef": w[1:].tolist(),
                     "intercept": float(w[0]), "C": C, "cv_auc": cv}
        models[m]["insample_auc"] = auc(y, predict(models[m], X))
        log(f"model {m}: {len(cols)} features, C {C:g}, CV AUC {cv:.3f}")
    # descriptive control (not a claim): B alone refitted at each family model's C, so Stage 2 can tell a lift
    # that comes from the family's features from one that comes from shrinking B's own coefficients
    Xb = np.column_stack([F[c] for c in models["B"]["features"]])
    mub, sdb = scaler(Xb)
    for m in MODELS[1:]:
        w = fit_logit((Xb - mub) / sdb, y, models[m]["C"])
        models[f"B@{m}"] = {"features": models["B"]["features"], "mu": mub.tolist(), "sd": sdb.tolist(),
                            "coef": w[1:].tolist(), "intercept": float(w[0]), "C": models[m]["C"], "cv_auc": None}
        models[f"B@{m}"]["insample_auc"] = auc(y, predict(models[f"B@{m}"], Xb))

    # univariate screen
    st = strata(D)
    screen = []
    for n in names:
        if n.startswith("B:"):
            continue
        thr = exposure_threshold(F[n])
        e = (F[n] > thr).astype(float)
        orr, se = mh_or(e, y, st)
        z = np.log(orr) / se if np.isfinite(orr) and orr > 0 and se > 0 else np.nan
        screen.append({"feature": n, "thr": thr, "or": orr, "se": se, "z": z,
                       "exp_cases": int((e * y).sum()), "exp_n": int(e.sum())})
    screen.sort(key=lambda s: -abs(s["z"]) if np.isfinite(s["z"]) else 0)

    spec = {"registration": "docs/dcs_hypotheses.md", "seed": SEED, "horizon_years": 5, "repos": list(REPOS),
            "split_median_ct": med, "tcols": tcols, "sigcols": sigcols, "arch_levels": arch_levels,
            "trees_sha": TREES_SHA, "dropped_low_prevalence": dropped, "min_nonzero_share": MIN_NZ,
            "engine": engine_commit(), "n_discovery": len(D), "cases_discovery": int(y.sum()),
            "screen": [{k_: (v if not isinstance(v, float) or np.isfinite(v) else None) for k_, v in s.items()}
                       for s in screen],
            "models": models}
    MODELS_PATH.write_text(json.dumps(spec, indent=1) + "\n")
    sha = hashlib.sha256(MODELS_PATH.read_bytes()).hexdigest()[:12]

    Lr = ["# DCS Stage 1 — discovery (EXPLORATORY; no verdicts)", "",
          "Registration `docs/dcs_hypotheses.md`. This report and `docs/dcs_models.json` (sha256 "
          f"`{sha}`) are committed before Stage 2 reads any confirmation function. Nothing here is a verdict.", "",
          "## Cohort and split", "",
          "| repo | commented births | danger-commented | eligible (5-y horizon) | split date (median birth) | "
          "discovery: cases / controls / early deaths (excl.) | confirmation functions (not read) |",
          "|---|---:|---:|---:|---|---|---:|"]
    for r in REPOS:
        dr = [u for u in D if u["r"] == r]
        Lr.append(f"| {r} | {counts[r]['commented']:,} | {counts[r]['danger']:,} | {counts[r]['eligible']:,} | "
                  f"{day(med[r])} | {sum(u['y'] for u in dr)} / {sum(1 - u['y'] for u in dr):,} / {early[r]} | "
                  f"{counts[r]['conf_n']:,} |")
    Lr += ["", f"- discovery: **{len(D):,}** functions, **{int(y.sum())}** cases ({y.mean():.1%}); "
           f"birth rows missing from the scan DB: {dict(miss) or 'none'}",
           "- outcome: case = first CVE (`latent`) fix ≤ birth + 5 y; control = alive at birth + 5 y without one; "
           "functions that died earlier without one are excluded (Stage 2 sensitivity counts them as controls).",
           f"- engine `{spec['engine']}`; lattice `{TREES_SHA}`; seed {SEED}.", "",
           "## Features", "",
           f"- T (telemetry ÷ loc): {sum(1 for n in names if n.startswith('T:'))} kept; "
           f"F (lattice family, rung, archetype): {sum(1 for n in names if n.startswith('F:'))} kept; "
           f"C (call graph): {sum(1 for n in names if n.startswith('C:'))} kept; B: "
           + ", ".join(n for n in names if n.startswith("B:")),
           f"- dropped by the outcome-blind < {MIN_NZ:.1%} non-zero rule ({len(dropped)}): "
           + (", ".join(f"`{n}`" for n in dropped) or "none"), "",
           "## Models (frozen for Stage 2)", "",
           "| model | features | C (5-fold file-grouped CV) | CV AUC | CV lift over B | in-sample AUC |",
           "|---|---:|---:|---:|---:|---:|"]
    for m in MODELS:
        md = models[m]
        Lr.append(f"| {'B' if m == 'B' else 'B + ' + m} | {len(md['features'])} | {md['C']:g} | {md['cv_auc']:.3f} | "
                  f"{md['cv_auc'] - models['B']['cv_auc']:+.3f} | {md['insample_auc']:.3f} |")
    Lr += ["", "Descriptive controls (frozen too, never a claim): B alone refitted at each family model's C, "
           "in-sample AUC " + ", ".join(f"B@{m} (C {models[m]['C']:g}) {models['B@' + m]['insample_auc']:.3f}"
                                        for m in MODELS[1:]), "",
           "Largest standardized coefficients (excluding B):", ""]
    for m in MODELS[1:]:
        md = models[m]
        top = sorted(((c, w) for c, w in zip(md["features"], md["coef"]) if not c.startswith("B:")),
                     key=lambda t: -abs(t[1]))[:8]
        Lr.append(f"- **{m}**: " + ", ".join(f"`{c}` {w:+.2f}" for c, w in top))
    Lr += ["", "## Univariate screen (MH OR, strata repo × 0.1-decade loc; exposure = above the discovery median, "
           "or > 0 when the median is 0; 95% RGB CI; uncorrected, many tests)", "",
           "| feature | exposed (cases / n) | OR [95% CI] | z |", "|---|---|---|---:|"]
    for s in screen[:25]:
        if not np.isfinite(s["z"]):
            continue
        lo, hi = s["or"] * np.exp(-1.96 * s["se"]), s["or"] * np.exp(1.96 * s["se"])
        Lr.append(f"| `{s['feature']}` | {s['exp_cases']} / {s['exp_n']:,} | {s['or']:.2f} [{lo:.2f}, {hi:.2f}] | "
                  f"{s['z']:+.1f} |")
    nfin = sum(1 for s in screen if np.isfinite(s["z"]))
    Lr += ["", f"Features screened: {nfin}; |z| ≥ 1.96: {sum(1 for s in screen if np.isfinite(s['z']) and abs(s['z']) >= 1.96)} "
           f"(≈ {0.05 * nfin:.0f} expected by chance).", "",
           "## Distributions, cases vs controls", "",
           "| LAT family | cases | controls |", "|---|---:|---:|"]
    for f in sorted(set(fam.tolist()), key=lambda f: -(fam == f).sum()):
        Lr.append(f"| {'F' + str(f) if f else 'unassigned'} | {((fam == f) & (y == 1)).sum() / max(y.sum(), 1):.1%} | "
                  f"{((fam == f) & (y == 0)).sum() / max((1 - y).sum(), 1):.1%} |")
    Lr += ["", "| rung band | cases | controls |", "|---|---:|---:|"]
    bd = np.where(k <= 3, 0, np.where(k <= 5, 1, 2))
    for b_, nm in enumerate(("k ≤ 3", "k 4–5", "k ≥ 6")):
        Lr.append(f"| {nm} | {((bd == b_) & (y == 1)).sum() / max(y.sum(), 1):.1%} | "
                  f"{((bd == b_) & (y == 0)).sum() / max((1 - y).sum(), 1):.1%} |")
    Lr += ["", "| archetype | cases | controls |", "|---|---:|---:|"]
    for a in sorted(set(arch.tolist()), key=lambda a: -(arch == a).sum()):
        Lr.append(f"| {a} | {((arch == a) & (y == 1)).sum() / max(y.sum(), 1):.1%} | "
                  f"{((arch == a) & (y == 0)).sum() / max((1 - y).sum(), 1):.1%} |")
    tcols_t = [n for n in names if not n.startswith("B:repo")]
    Lr += ["", "## Shallow tree (depth 3, leaves ≥ 20; Gini; all kept features + log loc + prior CVE file)", ""]
    Lr += shallow_tree(np.column_stack([F[n] for n in tcols_t]), y, tcols_t)
    Lr += ["", f"Runtime {time.time() - T0:.0f}s."]
    DISC_PATH.write_text("\n".join(Lr) + "\n")
    print("\n".join(Lr))
    return 0


# ------------------------------------------------------------------ Stage 2
def frozen_commit():
    rels = [str(p.relative_to(REPO_ROOT)) for p in (MODELS_PATH, DISC_PATH)]
    for rel in rels:
        if subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=REPO_ROOT, capture_output=True).returncode:
            raise SystemExit(f"{rel} is not committed: commit the Stage 1 outputs before Stage 2")
    if subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *rels], cwd=REPO_ROOT).returncode:
        raise SystemExit("Stage 1 outputs differ from the committed version: Stage 2 needs the frozen models")
    return subprocess.run(["git", "log", "-1", "--format=%h %cs", "--", rels[0]], cwd=REPO_ROOT, capture_output=True,
                          text=True).stdout.strip()


def clusters(units):
    cl = np.array([f"{u['r']}:{u['file']}" for u in units])
    _, ci = np.unique(cl, return_inverse=True)
    order = np.argsort(ci, kind="stable")
    return np.split(order, np.flatnonzero(np.diff(ci[order])) + 1)


def score_set(spec, units, rows, L, y):
    F, *_ = assemble(units, rows, L, spec["tcols"], spec["sigcols"], spec["arch_levels"])
    return {m: predict(md, np.column_stack([F[c] for c in md["features"]])) for m, md in spec["models"].items()}, F


def boot_lifts(y, S, groups, rng):
    out = {m: [] for m in MODELS[1:]}
    for _ in range(ITERS):
        pick = np.concatenate([groups[j] for j in rng.integers(0, len(groups), len(groups))])
        yy = y[pick]
        a0 = auc(yy, S["B"][pick])
        for m in MODELS[1:]:
            out[m].append(auc(yy, S[m][pick]) - a0)
    return {m: np.array(v, float) for m, v in out.items()}


def stage2():
    frozen = frozen_commit()
    spec = json.loads(MODELS_PATH.read_text())
    sha = hashlib.sha256(MODELS_PATH.read_bytes()).hexdigest()[:12]
    L = Lattice()
    U = cohort()
    med = split(U)
    for r in REPOS:
        assert abs(med[r] - spec["split_median_ct"][r]) < 1e-6, f"split for {r} does not reproduce Stage 1"
    for u in U:
        u["y"] = outcome(u) if u["eligible"] else None
    sets = {"disc": [u for u in U if u["danger"] and u["eligible"] and u["half"] == "disc" and u["y"] >= 0],
            "conf": [u for u in U if u["danger"] and u["eligible"] and u["half"] == "conf" and u["y"] >= 0],
            "conf_sens": [u for u in U if u["danger"] and u["eligible"] and u["half"] == "conf"],
            "plain": [u for u in U if not u["danger"] and u["eligible"] and u["half"] == "conf" and u["y"] >= 0]}
    have = columns()[2]
    rows = read_rows([u for s in sets.values() for u in s], spec["tcols"], spec["sigcols"], have)
    miss = {k: sum(1 for u in v if (u["r"], u["sha"], u["file"], u["name"]) not in rows) for k, v in sets.items()}
    sets = {k: [u for u in v if (u["r"], u["sha"], u["file"], u["name"]) in rows] for k, v in sets.items()}
    Y = {k: np.array([float(u["y"] == 1) for u in v]) for k, v in sets.items()}
    SC, FF = {}, {}
    for k, v in sets.items():
        SC[k], FF[k] = score_set(spec, v, rows, L, Y[k])
    rep = {m: auc(Y["disc"], SC["disc"][m]) for m in MODELS}
    repro = max(abs(rep[m] - spec["models"][m]["insample_auc"]) for m in MODELS)
    log(f"discovery reproduces in-sample AUCs within {repro:.2e}; confirmation {len(sets['conf']):,} functions, "
        f"{int(Y['conf'].sum())} cases")

    y = Y["conf"]
    n_cases = int(y.sum())
    A = {m: auc(y, SC["conf"][m]) for m in MODELS}
    rng = np.random.default_rng(SEED)
    BL = boot_lifts(y, SC["conf"], clusters(sets["conf"]), rng)
    res = {}
    for m in MODELS[1:]:
        b = BL[m][np.isfinite(BL[m])]
        lift = A[m] - A["B"]
        lo1 = float(np.quantile(b, ALPHA))
        lo2, hi2 = float(np.quantile(b, 0.005)), float(np.quantile(b, 0.995))
        if n_cases < MIN_CASES:
            call = "underpowered"
        elif lift > 0 and lo1 > 0:
            call = "SUPPORTED"
        elif -NULL_BAND <= lo2 and hi2 <= NULL_BAND:
            call = "not supported — replicated null"
        else:
            call = "not supported — inconclusive"
        res[m] = (lift, lo1, lo2, hi2, call)

    Lr = ["# DCS — danger comments that stayed safe vs ones that got CVEs: a code signature at birth? (SCORED)", "",
          f"Registration `docs/dcs_hypotheses.md`. Frozen models `docs/dcs_models.json` (sha256 `{sha}`, committed "
          f"{frozen}); discovery report `docs/dcs_discovery.md` (exploratory). Aggregates only.", "",
          "## Confirmation set", "",
          f"- **{len(sets['conf']):,}** danger-commented functions born on or after each repo's split date "
          f"(" + ", ".join(f"{r} {day(med[r])}" for r in REPOS) + f"), **{n_cases}** cases ({y.mean():.1%}); "
          f"early deaths excluded {len(sets['conf_sens']) - len(sets['conf']):,}; birth rows missing {miss['conf_sens']}",
          "- per repo (cases / functions): " + ", ".join(
              f"{r} {int(sum(Y['conf'][i] for i, u in enumerate(sets['conf']) if u['r'] == r))} / "
              f"{sum(1 for u in sets['conf'] if u['r'] == r):,}" for r in REPOS),
          f"- power rule (≥ {MIN_CASES} cases): **{'met' if n_cases >= MIN_CASES else 'NOT met — every claim underpowered'}**",
          f"- Stage 1 models reproduce their discovery in-sample AUCs within {repro:.1e}.", "",
          f"## Registered claims (lift = AUC(B + family) − AUC(B); file-cluster bootstrap {ITERS}, seed {SEED}; "
          f"one-sided α = 0.01/4)", "",
          f"AUC(B) = **{A['B']:.3f}**.", "",
          "| id | model | AUC | lift | one-sided lower bound (α = 0.0025) | two-sided 99% CI | call |",
          "|---|---|---:|---:|---:|---|---|"]
    for m in MODELS[1:]:
        lift, lo1, lo2, hi2, call = res[m]
        Lr.append(f"| **{CLAIMS[m]}** | B + {m} | {A[m]:.3f} | **{lift:+.3f}** | {lo1:+.3f} | [{lo2:+.3f}, {hi2:+.3f}] | "
                  f"**{call}** |")
    Lr += ["", "Supported iff lift > 0 and the one-sided lower bound > 0. A failed claim is a replicated null iff its "
           f"99% CI lies inside ±{NULL_BAND}; otherwise inconclusive.", "", "## Descriptive (no verdicts)", ""]
    Lr.append("- Shrinkage control: lift of each family model over B refitted at that model's C (same data, same "
              "penalty, no family features): " + ", ".join(
                  f"{m} {A[m] - auc(y, SC['conf']['B@' + m]):+.3f} (B@{m} AUC {auc(y, SC['conf']['B@' + m]):.3f})"
                  for m in MODELS[1:]))
    loc = np.array([u["loc"] for u in sets["conf"]], float)
    Lr.append("- Recall of cases at the top 20% of lines reviewed (effort-aware, score ÷ loc as in EA/CHG-2): "
              + ", ".join(f"{m} {(y * select(expit(SC['conf'][m]), loc, 0.20)).sum() / max(n_cases, 1):.1%}"
                          for m in MODELS))
    yp = Y["plain"]
    Ap = {m: auc(yp, SC["plain"][m]) for m in MODELS}
    Lr.append(f"- Same frozen models on **plain-commented** confirmation functions ({len(sets['plain']):,}, "
              f"{int(yp.sum())} cases): AUC B {Ap['B']:.3f}; lifts "
              + ", ".join(f"{m} {Ap[m] - Ap['B']:+.3f}" for m in MODELS[1:]))
    ys = Y["conf_sens"]
    As = {m: auc(ys, SC["conf_sens"][m]) for m in MODELS}
    BLs = boot_lifts(ys, SC["conf_sens"], clusters(sets["conf_sens"]), np.random.default_rng(SEED))
    Lr.append(f"- Sensitivity, early deaths counted as controls ({len(sets['conf_sens']):,} functions, "
              f"{int(ys.sum())} cases): AUC B {As['B']:.3f}; lifts " + ", ".join(
                  f"{m} {As[m] - As['B']:+.3f} (lower {np.nanquantile(BLs[m], ALPHA):+.3f})" for m in MODELS[1:]))
    st = strata(sets["conf"])
    kept, flipped, nan = [], [], 0
    for s in [s for s in spec["screen"] if s["z"] is not None][:15]:
        x = FF["conf"][s["feature"]]
        orr, _ = mh_or((x > s["thr"]).astype(float), y, st)
        if not np.isfinite(orr) or orr <= 0:
            nan += 1
            continue
        (kept if np.sign(np.log(orr)) == np.sign(s["z"]) else flipped).append(f"`{s['feature']}` {s['or']:.2f}→{orr:.2f}")
    Lr.append(f"- Discovery screen's top 15 features in confirmation (MH OR, same exposure thresholds): kept sign "
              f"{len(kept)}, flipped {len(flipped)}, not estimable {nan}")
    Lr.append("  - kept: " + (", ".join(kept) or "none"))
    Lr.append("  - flipped: " + (", ".join(flipped) or "none"))
    Lr += ["", f"Runtime {time.time() - T0:.0f}s · engine `{engine_commit()}` · seed {SEED}."]
    CONF_PATH.write_text("\n".join(Lr) + "\n")
    print("\n".join(Lr))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=("stage1", "stage2", "smoke"))
    ap.add_argument("--force", action="store_true", help="stage1: overwrite uncommitted Stage 1 outputs")
    a = ap.parse_args()
    if a.stage == "stage1":
        return stage1(a.force)
    if a.stage == "stage2":
        return stage2()
    # smoke: cohort + split + discovery features for one repo, no outputs written
    global REPOS
    REPOS = ("curl",)
    U = cohort()
    split(U)
    D = [u for u in U if u["danger"] and u["eligible"] and u["half"] == "disc"]
    tcols, sigcols, have = columns()
    rows = read_rows(D, tcols, sigcols, have)
    F, fam, k, arch = assemble([u for u in D if (u["r"], u["sha"], u["file"], u["name"]) in rows], rows, Lattice(),
                               tcols, sigcols, ["none"])
    log(f"smoke: curl commented {len(U):,}, discovery danger {len(D):,}, rows {len(rows):,}, features {len(F)}, "
        f"T cols {len(tcols)}, unassigned {(fam == 0).mean():.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
