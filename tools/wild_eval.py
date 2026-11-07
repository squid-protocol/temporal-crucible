#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""WILD-H1..H2, WILD-C1 (docs/wild_hypotheses.md): model handwriting inside GitGalaxy's own codebase.

    E=<gitgalaxy-worktrees>/batch-b64f42bfcfb7
    cd $E && PYTHONPATH=$E <full_precision venv>/bin/python <tc>/tools/wild_eval.py --repo <gitgalaxy checkout with origin/main>
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import multiprocessing
import pathlib
import re
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.optimize import minimize
from scipy.spatial.distance import squareform
from scipy.stats import rankdata

TC = pathlib.Path(__file__).resolve().parents[1]
DOCS = TC / "docs"
SEED, NPERM, NBOOT, MAXPAIRS = 2982, 1000, 1000, 200_000
START, END = "2026-10-03", "2026-11-07"
MODELS = {"Claude Sonnet 5.5": 1, "Claude Opus 5.5": 0}
EXCL = re.compile(r"_generated|vendor|third_party|_pb2")
T0 = time.time()
REPO = None


def log(m):
    print(f"[{time.time() - T0:6.0f}s] {m}", flush=True)


def git(*a, text=True):
    r = subprocess.run(["git", "-C", str(REPO), *a], capture_output=True)
    return r.stdout.decode("utf-8", "replace") if text else r.stdout


# ------------------------------------------------------------------ lattice (frozen)
def lattice():
    raw = (DOCS / "fingerprint_trees_exploratory.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest().startswith("a27d2c93f817")
    D = json.loads(raw)
    sets = [frozenset(s["signals"]) for s in D["shapes"]]
    nn = np.array([s["n"] for s in D["shapes"]], float)
    n = len(sets)
    J = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            u = len(sets[i] | sets[j])
            J[i, j] = J[j, i] = 1 - (len(sets[i] & sets[j]) / u if u else 1)
    fam = fcluster(linkage(squareform(J, checks=False), method="average"), 14, criterion="maxclust")
    U = sorted(set().union(*sets))
    return U, np.array([[c in s for c in U] for s in sets], np.int32), fam, np.argsort(-nn, kind="stable")


# ------------------------------------------------------------------ per-commit extraction
_W = {}


def worker():
    if not _W:
        import tree_sitter_language_pack as tslp
        from gitgalaxy.core.prism import Prism
        from gitgalaxy.recorders import record_keeper as RK
        from gitgalaxy.standards.gitgalaxy_config import LEXICAL_FAMILY_HEURISTICS
        from gitgalaxy.standards.language_standards import LANGUAGE_DEFINITIONS as LD
        m = dict(re.findall(r'"([a-z_0-9]+)": "([a-z_0-9]+)"', pathlib.Path(RK.__file__).read_text()))
        _W["parser"] = tslp.get_parser("python")
        _W["prism"] = Prism(LEXICAL_FAMILY_HEURISTICS, LD)
        _W["rules"] = {m.get(k, k): v for k, v in LD["python"]["rules"].items() if hasattr(v, "search") and not k.startswith("_")}
    return _W


def functions(src: bytes):
    """qualified name -> node, for top-level functions and class methods (nested functions skipped)."""
    W = worker()
    out = {}
    root = W["parser"].parse(src).root_node

    def walk(node, prefix, in_func):
        for ch in node.children:
            n = ch.child_by_field_name("definition") if ch.type == "decorated_definition" else ch
            if n is None:
                continue
            if n.type == "function_definition":
                if not in_func:
                    nm = n.child_by_field_name("name")
                    if nm is not None:
                        out.setdefault(prefix + nm.text.decode("utf-8", "replace"), n)
            elif n.type == "class_definition":
                nm = n.child_by_field_name("name")
                body = n.child_by_field_name("body")
                if nm is not None and body is not None and not in_func:
                    walk(body, prefix + nm.text.decode("utf-8", "replace") + ".", False)
    walk(root, "", False)
    return out


def habits(n, text_lines):
    loc = n.end_point[0] - n.start_point[0] + 1
    body = n.child_by_field_name("body")
    doc = 0
    if body is not None and body.children:
        f = body.children[0]
        doc = int(f.type == "string" or (f.type == "expression_statement" and bool(f.children) and f.children[0].type == "string"))
    comments = sum(1 for ln in text_lines if ln.strip().startswith("#"))
    cnt = defaultdict(int)
    depth = 0
    stack = [(n, 0)]
    while stack:
        x, d = stack.pop()
        cnt[x.type] += 1
        dd = d + (x.type in ("if_statement", "for_statement", "while_statement", "try_statement", "with_statement"))
        depth = max(depth, dd)
        stack.extend((c, dd) for c in x.children)
    return [np.log2(max(loc, 1)), doc, comments / max(loc, 1), cnt["return_statement"], cnt["while_statement"], cnt["call"], depth], loc


def task(t):
    sha, label, week = t
    W = worker()
    out = []
    for ln in git("diff", "--name-status", "-M", f"{sha}^", sha).splitlines():
        parts = ln.split("\t")
        st, path = parts[0], parts[-1]
        old = parts[1] if st.startswith("R") else path
        if not path.endswith(".py") or not path.startswith(("gitgalaxy/", "tests/")) or EXCL.search(path) or st.startswith("D"):
            continue
        new = git("show", f"{sha}:{path}", text=False)
        if not new:
            continue
        prev = git("show", f"{sha}^:{old}", text=False) if not st.startswith("A") else b""
        fn_new = functions(new)
        fn_old = set(functions(prev)) if prev else set()
        lines = new.decode("utf-8", "replace").split("\n")
        for q, n in fn_new.items():
            if q in fn_old:
                continue
            tl = lines[n.start_point[0]:n.end_point[0] + 1]
            h, loc = habits(n, tl)
            if loc < 3:
                continue
            body = "\n".join(tl)
            try:
                code = W["prism"].split_streams(body, "python")["code_stream"]
            except Exception:
                code = body
            pres = sorted(c for c, rx in W["rules"].items() if rx.search(code))
            d = "/".join(path.split("/")[:2])
            out.append((sha, label, week, d, pres, h, loc))
    return out


# ------------------------------------------------------------------ statistics
def fit(X, y, lam=1.0):
    def f(b):
        z = X @ b[1:] + b[0]
        p = 1 / (1 + np.exp(-np.clip(z, -30, 30)))
        loss = -np.sum(y * np.log(p + 1e-12) + (1 - y) * np.log(1 - p + 1e-12)) + lam * np.sum(b[1:] ** 2)
        g = p - y
        return loss, np.r_[g.sum(), X.T @ g + 2 * lam * b[1:]]
    return minimize(f, np.zeros(X.shape[1] + 1), jac=True, method="L-BFGS-B").x


def oof(X, y, commit, rng):
    uc = np.unique(commit)
    fold = dict(zip(uc, rng.permutation(len(uc)) % 5))
    fo = np.array([fold[c] for c in commit])
    s = np.zeros(len(y))
    for k in range(5):
        tr, te = fo != k, fo == k
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
        b = fit((X[tr] - mu) / sd, y[tr])
        s[te] = ((X[te] - mu) / sd) @ b[1:] + b[0]
    return s


def strat_auc(s, y, strata):
    num = den = 0.0
    for g in np.unique(strata):
        m = strata == g
        n1, n0 = int(y[m].sum()), int((1 - y[m]).sum())
        if n1 == 0 or n0 == 0:
            continue
        r = rankdata(s[m])
        auc = (r[y[m] == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
        num += auc * n1 * n0
        den += n1 * n0
    return num / den if den else float("nan")


def week_permute(commit_label, commit_week, rng):
    out = dict(commit_label)
    byw = defaultdict(list)
    for c, w in commit_week.items():
        byw[w].append(c)
    for cs in byw.values():
        for c, v in zip(cs, rng.permutation([commit_label[c] for c in cs])):
            out[c] = v
    return out


def main() -> int:
    global REPO
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    a = ap.parse_args()
    REPO = pathlib.Path(a.repo)
    rng = np.random.default_rng(SEED)
    U, S, fam, order = lattice()
    commits = []
    for ln in git("log", "origin/main", "--first-parent", f"--since={START} 00:00", f"--until={END} 23:59:59",
                  "--format=%H|%cs|%(trailers:key=Co-Authored-By,valueonly,separator=;)").splitlines():
        sha, day, tr = ln.split("|", 2)
        ms = set(m.strip() for m in re.findall(r"Claude (?:Sonnet|Opus|Haiku|Fable) [0-9.]+", tr))
        if len(ms) == 1 and next(iter(ms)) in MODELS:
            iso = dt.date.fromisoformat(day).isocalendar()
            commits.append((sha, MODELS[next(iter(ms))], f"{iso[0]}-{iso[1]:02d}"))
    log(f"labelled commits {len(commits):,} (Sonnet {sum(c[1] for c in commits):,}, Opus {sum(1 - c[1] for c in commits):,})")
    with multiprocessing.get_context("fork").Pool(8) as p:
        res = list(p.imap_unordered(task, commits, chunksize=4))
    keep = [r for r in res if 0 < len(r) <= 300]
    bulk = sum(1 for r in res if len(r) > 300)
    R = [u for r in keep for u in r]
    log(f"born functions {len(R):,} from {len(keep):,} commits (bulk commits excluded {bulk})")
    commit = np.array([u[0] for u in R])
    y = np.array([u[1] for u in R], float)
    week = {u[0]: u[2] for u in R}
    directory = np.array([u[3] for u in R])
    P = np.array([[c in u[4] for c in U] for u in R], np.int32)
    H = np.array([u[5] for u in R], float)
    inter = P @ S.T
    union = P.sum(1)[:, None] + S.sum(1)[None, :] - inter
    jac = np.where(union > 0, inter / np.maximum(union, 1), 1.0)
    fm = np.where(jac.max(1) > 0, fam[order[np.argmax(jac[:, order], axis=1)]], 0)
    k = P.sum(1)
    band = np.where(k <= 3, 0, np.where(k <= 5, 1, 2))
    X = np.column_stack([P, np.eye(15)[fm], k, np.eye(3)[band], H]).astype(float)
    sizeband = np.floor(H[:, 0]).astype(int)
    strata = np.array([f"{d}|{s}" for d, s in zip(directory, sizeband)])
    # H1
    s = oof(X, y, commit, rng)
    auc = strat_auc(s, y, strata)
    clab = {c: y[commit == c][0] for c in np.unique(commit)}
    ge = 0
    null = []
    for i in range(NPERM):
        lp = week_permute(clab, week, rng)
        yp = np.array([lp[c] for c in commit])
        v = strat_auc(oof(X, yp, commit, rng), yp, strata)
        null.append(v)
        ge += v >= auc
        if i % 100 == 99:
            log(f"H1 permutations {i + 1}")
    p1 = (1 + ge) / (1 + NPERM)
    # C1: split Sonnet commits into two pseudo-models within week
    sm = y == 1
    sc = sorted({c for c in commit[sm]})
    byw = defaultdict(list)
    for c in sc:
        byw[week[c]].append(c)
    pseudo = {}
    for cs in byw.values():
        for c, v in zip(cs, rng.permutation(np.arange(len(cs)) % 2)):
            pseudo[c] = float(v)
    yc = np.array([pseudo[c] for c in commit[sm]])
    auc_c = strat_auc(oof(X[sm], yc, commit[sm], rng), yc, strata[sm])
    # H2: context vs model distances
    Z = (X - X.mean(0)) / (X.std(0) + 1e-9)
    idx_by = defaultdict(list)
    for i, (d, b, m) in enumerate(zip(directory, sizeband, y)):
        idx_by[(b, d, m)].append(i)
    idx_by = {key: np.array(v) for key, v in idx_by.items()}
    by_band_model = defaultdict(list)
    for (b, d, m), v in idx_by.items():
        by_band_model[(b, m)].append((d, v))

    def sample_pairs(allow, n):
        A_, B_ = [], []
        tries = 0
        while len(A_) < n and tries < n * 20:
            tries += 1
            i = allow[rng.integers(len(allow))]
            b, d, m = sizeband[i], directory[i], y[i]
            if arm == "ctx":
                pool = idx_by.get((b, d, 1 - m))
            else:
                opts = [v for dd, v in by_band_model[(b, m)] if dd != d]
                pool = opts[rng.integers(len(opts))] if opts else None
            if pool is None or len(pool) == 0:
                continue
            pool = pool[inset[pool]] if inset is not None else pool
            if len(pool) == 0:
                continue
            A_.append(i)
            B_.append(pool[rng.integers(len(pool))])
        A_, B_ = np.array(A_), np.array(B_)
        return np.sqrt(((Z[A_] - Z[B_]) ** 2).sum(1)) if len(A_) else np.array([np.nan])
    inset = None
    arm = "ctx"
    dctx = sample_pairs(np.arange(len(y)), MAXPAIRS)
    arm = "mod"
    dmod = sample_pairs(np.arange(len(y)), MAXPAIRS)
    ratio = float(np.median(dctx) / np.median(dmod))
    uc = np.unique(commit)
    cidx = {c: np.flatnonzero(commit == c) for c in uc}
    boots = []
    for i in range(NBOOT):
        pick = np.concatenate([cidx[c] for c in rng.choice(uc, len(uc), replace=True)])
        inset = np.zeros(len(y), bool)
        inset[pick] = True
        arm = "ctx"
        a_ = sample_pairs(pick, 20_000)
        arm = "mod"
        b_ = sample_pairs(pick, 20_000)
        boots.append(np.median(a_) / np.median(b_))
        if i % 200 == 199:
            log(f"H2 bootstrap {i + 1}")
    boots = np.array(boots)
    boots = boots[np.isfinite(boots)]
    hi = float(np.quantile(boots, 0.99))
    lo = float(np.quantile(boots, 0.01))
    v1 = "SUPPORTED" if auc >= 0.60 and p1 < 0.01 else "not supported"
    v2 = "SUPPORTED" if ratio < 0.90 and hi < 1 else "not supported"
    vc = "PASS" if auc_c < 0.55 else "FAIL — H1 void"
    if vc != "PASS":
        v1 = "VOID (C1 failed)"
    L = ["# WILD-H1..H2, WILD-C1 — model handwriting inside GitGalaxy's own codebase (SCORED)", "",
         f"- window {START} .. {END}; labelled single-model commits with born Python functions: {len(keep):,} "
         f"(bulk > 300 excluded: {bulk}); born functions (loc ≥ 3): {len(R):,} — Sonnet 5.5 {int(y.sum()):,}, Opus 5.5 {int((1 - y).sum()):,}",
         f"- strata (directory × size band) with both models: {sum(1 for g in np.unique(strata) if 0 < y[strata == g].mean() < 1)}", "",
         "| claim | result | verdict |", "|---|---|---|",
         f"| **WILD-H1** structure separates Sonnet from Opus beyond directory × size | stratified AUC **{auc:.3f}**; week-blocked commit permutation null median {np.median(null):.3f}, 99th pct {np.quantile(null, 0.99):.3f}; p = {p1:.4f} | **{v1}** |",
         f"| **WILD-H2** context dominates (same dir/different model vs same model/different dir) | median distance ratio **{ratio:.3f}** (99% CI {lo:.3f}–{hi:.3f}); medians {np.median(dctx):.2f} vs {np.median(dmod):.2f} | **{v2}** |",
         f"| **WILD-C1** pseudo-model control (Sonnet commits split in two) | stratified AUC {auc_c:.3f} (bar < 0.55) | **{vc}** |", ""]
    # descriptive
    names = [f"has {c}" for c in U] + [f"family F{f}" for f in range(15)] + ["rung k"] + ["band ≤3", "band 4–5", "band ≥6"] + \
            ["log2 loc", "docstring", "comment lines / loc", "returns", "whiles", "calls", "nesting depth"]
    mu, sd = X.mean(0), X.std(0) + 1e-9
    b = fit((X - mu) / sd, y)
    top = np.argsort(-np.abs(b[1:]))[:10]
    L += ["## Descriptive", "",
          "- largest standardised coefficients (positive = more Sonnet): " + ", ".join(f"{names[j]} {b[1 + j]:+.2f}" for j in top),
          "", "| | Sonnet 5.5 | Opus 5.5 |", "|---|---:|---:|"]
    for j, nm in [(-7, "median lines (2^log2)"), (-6, "docstring"), (-5, "comment lines / loc"), (-4, "returns"), (-3, "whiles"), (-2, "calls"), (-1, "nesting depth")]:
        f_ = (lambda v: f"{2 ** np.median(v):.0f}") if j == -7 else (lambda v: f"{np.mean(v):.2f}")
        L.append(f"| {nm} | {f_(H[y == 1][:, j])} | {f_(H[y == 0][:, j])} |")
    L.append(f"| rung k (median) | {np.median(k[y == 1]):.0f} | {np.median(k[y == 0]):.0f} |")
    for f in (7, 8, 6):
        L.append(f"| family F{f} share | {np.mean(fm[y == 1] == f):.1%} | {np.mean(fm[y == 0] == f):.1%} |")
    L += ["", f"- lab comparison (agent-habits, sfs): same model/same job 0.32 vs different model/same job 0.62 (ratio 0.52); here the context/model ratio is {ratio:.2f}",
          "", f"Runtime {time.time() - T0:.0f}s · seed {SEED} · {NPERM} permutations · {NBOOT} bootstrap rounds."]
    (DOCS / "wild.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
