#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""CHG2-H1..H2: engine change features vs a churn-only baseline for regression ranking (docs/chg2_hypotheses.md).
Run with the engine venv (tree-sitter-language-pack, numpy, scipy):

    SFS_SRC=<popan>/structural-fingerprint-scanner/src <engine venv>/bin/python tools/chg2_eval.py
"""
from __future__ import annotations

import bisect
import datetime as dt
import multiprocessing
import os
import pathlib
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, os.environ["SFS_SRC"])
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402
from chg_eval import CEXT, CPPEXT, FILE_HDR, REPOS, WINDOW, _fname, _git, _parser, fix_events, map_fix  # noqa: E402
from nh_eval import DBS, snapshots  # noqa: E402
from structural_fingerprint.reference import load_reference  # noqa: E402

SEED, ITERS, ALPHA, MIN_POS = 2982, 2000, 0.01 / 2, 100
SPLIT = dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc).timestamp()
HUNK2 = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,(\d+))? @@")
SIG = list(load_reference("structure").signal_columns)


# ------------------------------------------------------------------------------------------------ churn per commit
def map_churn(task):
    r, sha, ct = task
    repo = POOL_DIR / r
    parent = _git(repo, "rev-parse", "-q", "--verify", f"{sha}^").strip()
    if not parent:
        return r, ct, {}
    anchors = defaultdict(list)
    cur = None
    for ln in _git(repo, "diff", "-U0", "--no-color", "--no-renames", parent, sha).splitlines():
        m = FILE_HDR.match(ln)
        if m:
            cur = m.group(1) if m.group(1) and m.group(1).endswith(CEXT + CPPEXT) else None
            continue
        if cur:
            h = HUNK2.match(ln)
            if h:
                s = int(h.group(1))
                n_old = int(h.group(2)) if h.group(2) is not None else 1
                n_new = int(h.group(3)) if h.group(3) is not None else 1
                anchors[cur].append((max(s, 1), n_old + n_new))
    out = {}
    for path, an in anchors.items():
        src = _git(repo, "show", f"{parent}:{path}", text=False)
        if not src:
            continue
        tree = _parser("c" if path.endswith(CEXT) and r != "harfbuzz" else "cpp").parse(src)
        spans, stack = [], [tree.root_node]
        while stack:
            n = stack.pop()
            if n.type == "function_definition":
                nm = _fname(n)
                if nm:
                    spans.append((n.start_point[0] + 1, n.end_point[0] + 1, nm))
            stack.extend(n.children)
        for line, w in an:
            for a, b, nm in spans:
                if a <= line <= b:
                    out[(path, nm)] = out.get((path, nm), 0) + w
                    break
    return r, ct, out


# ------------------------------------------------------------------------------------------------ transitions + features
def load(r):
    snaps = snapshots(r)
    con = sqlite3.connect(f"file:{DBS[r]}?mode=ro", uri=True)
    have = {c[1] for c in con.execute("PRAGMA table_info(function_data)")}
    sig = [c for c in SIG if c in have]
    per = []
    for s in snaps:
        rows = con.execute("SELECT fd.file_path, f.func_name, f.start_line, f.loc, f.complexity, f.func_archetype, f.func_fan_in, "
                           + ", ".join("f." + c for c in sig) + " FROM function_data f JOIN file_data fd ON f.file_id = fd.id "
                           "WHERE fd.commit_hash = ? AND fd.language IN ('c','cpp') AND f.func_name IS NOT NULL AND f.func_name != ''",
                           (s["sha"],)).fetchall()
        d = {}
        for row in sorted(rows, key=lambda x: (x[0], x[1], x[2] or 0)):
            d.setdefault((row[0], row[1]), (row[3] or 0, row[4] or 0, row[5] or "", row[6] or 0, tuple(float(v or 0) for v in row[7:])))
        per.append(d)
    con.close()
    return snaps, per, len(sig)


def transitions(snaps, per):
    prev, prev_ids, nxt, out = None, {}, 0, []
    for k, d in enumerate(per):
        cur, moved = {}, {}
        if prev is not None:
            vn, nn = defaultdict(list), defaultdict(list)
            for key in prev:
                if key not in d:
                    vn[key[1]].append(key)
            for key in d:
                if key not in prev:
                    nn[key[1]].append(key)
            moved = {nn[n][0]: vn[n][0] for n in nn if len(nn[n]) == 1 and len(vn.get(n, [])) == 1}
        for key in d:
            if prev is not None and key in prev:
                cur[key] = prev_ids[key]
            elif key in moved:
                cur[key] = prev_ids[moved[key]]
            else:
                cur[key] = nxt
                nxt += 1
        if prev is not None:
            inv = {v: key for key, v in prev_ids.items()}
            for key, f in cur.items():
                if f in inv:
                    out.append((k, inv[f], key, prev[inv[f]], d[key]))
        prev, prev_ids = d, cur
    return out


# ------------------------------------------------------------------------------------------------ model + evaluation
def fit(X, y, w, lam=1.0):
    def f(b):
        z = X @ b[1:] + b[0]
        p = 1 / (1 + np.exp(-np.clip(z, -30, 30)))
        loss = -np.sum(w * (y * np.log(p + 1e-12) + (1 - y) * np.log(1 - p + 1e-12))) + lam * np.sum(b[1:] ** 2)
        g = w * (p - y)
        return loss, np.r_[g.sum(), X.T @ g + 2 * lam * b[1:]]
    return minimize(f, np.zeros(X.shape[1] + 1), jac=True, method="L-BFGS-B").x


def train_predict(X, y, tr, te, cols, rng):
    pos = np.where(tr & (y == 1))[0]
    neg = np.where(tr & (y == 0))[0]
    neg = rng.choice(neg, size=max(len(neg) // 10, 1), replace=False)
    idx = np.r_[pos, neg]
    w = np.r_[np.ones(len(pos)), np.full(len(neg), 10.0)]
    Xs = X[:, cols]
    mu, sd = Xs[idx].mean(0), Xs[idx].std(0) + 1e-9
    b = fit((Xs[idx] - mu) / sd, y[idx], w)
    z = ((Xs[te] - mu) / sd) @ b[1:] + b[0]
    return 1 / (1 + np.exp(-np.clip(z, -30, 30))), b


def select(score, loc, frac):
    order = np.argsort(-score / loc, kind="stable")
    cum = np.cumsum(loc[order])
    sel = np.zeros(len(score), bool)
    sel[order[cum <= frac * loc.sum()]] = True
    return sel


def boot_diff(cl, y, s1, s0, rng):
    _, ci = np.unique(cl, return_inverse=True)
    nC = ci.max() + 1
    Y, D = np.bincount(ci, y, nC), np.bincount(ci, y * (s1.astype(float) - s0), nC)
    out = []
    for _ in range(ITERS):
        w = rng.multinomial(nC, np.full(nC, 1 / nC))
        out.append((w @ D) / max(w @ Y, 1e-9))
    return float(np.quantile(out, ALPHA))


def main() -> int:
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    # labels (CHG, amendment A1 join)
    ev, last_ct = [], {}
    for r in REPOS:
        e, last_ct[r] = fix_events(r)
        ev += [x for x in e if x[3] == "regression"]
    jobs = []
    loaded = {}
    for r in REPOS:
        snaps, per, nsig = load(r)
        loaded[r] = (snaps, per, nsig)
        c0, c1 = snaps[0]["ct"], snaps[-1]["ct"]
        for line in _git(POOL_DIR / r, "log", "--first-parent", "--format=%H %ct", "HEAD").splitlines():
            h, ct = line.split()
            if c0 < int(ct) <= c1:
                jobs.append((r, h, int(ct)))
    print(f"regression events {len(ev)}; commits to map {len(jobs):,} ({time.time() - t0:.0f}s)", flush=True)
    with multiprocessing.get_context("fork").Pool(8) as p:
        hits = [h for hs in p.imap_unordered(map_fix, ev, chunksize=4) for h in hs]
        churn = list(p.imap_unordered(map_churn, jobs, chunksize=16))
    print(f"churn mapped ({time.time() - t0:.0f}s)", flush=True)
    cidx = defaultdict(list)  # (r, path, name) -> [(ct, lines)]
    for r, ct, d in churn:
        for (path, nm), w in d.items():
            cidx[(r, path, nm)].append((ct, w))
            if "::" in nm:
                cidx[(r, path, nm.split("::")[-1])].append((ct, w))
    for v in cidx.values():
        v.sort()
    rows, Ys, CL, RP, CT1 = [], [], [], [], []
    for r in REPOS:
        snaps, per, nsig = loaded[r]
        cts = [s["ct"] for s in snaps]
        names = [set(d) for d in per]
        ridx = defaultdict(list)
        for (_r, path, nm, ct, _k) in (h for h in hits if h[0] == r):
            j = bisect.bisect_right(cts, ct) - 1
            if j < 0:
                continue
            key = None
            for jj in (j, j + 1):
                if jj < len(names):
                    for cand in ((path, nm), (path, nm.split("::")[-1])):
                        if key is None and cand in names[jj]:
                            key = cand
            ridx[key or (path, nm)].append(ct)
        for v in ridx.values():
            v.sort()
        for k1, _k0key, key, a, b in transitions(snaps, per):
            c0, c1 = cts[k1 - 1], cts[k1]
            loc = float(b[0])
            if c1 + WINDOW > last_ct[r] or loc < 1:
                continue
            v = ridx.get(key, [])
            i = bisect.bisect_right(v, c1)
            y = 1.0 if i < len(v) and v[i] <= c1 + WINDOW else 0.0
            cv = cidx.get((r,) + key, [])
            lo_, hi_ = bisect.bisect_right(cv, (c0, 1 << 60)), bisect.bisect_right(cv, (c1, 1 << 60))
            ncom, nlin = hi_ - lo_, sum(w for _, w in cv[lo_:hi_])
            shape = 1.0 if (a[1] != b[1] or a[2] != b[2]) else 0.0
            dsig = [np.log1p(abs(x1 - x0)) for x0, x1 in zip(a[4], b[4])]
            dsig += [0.0] * (len(SIG) - len(dsig))
            rows.append([np.log1p(ncom), np.log1p(nlin), np.log10(loc),
                         shape, 1.0 if a[2] != b[2] else 0.0, float(b[1] - a[1]), abs(float(b[1] - a[1])),
                         np.log10(max(loc, 1)) - np.log10(max(a[0], 1)), np.log1p(b[3]), b[1] / loc] + dsig)
            Ys.append(y)
            CL.append(f"{r}:{key[0]}")
            RP.append(REPOS.index(r))
            CT1.append(c1)
        print(f"{r}: units so far {len(Ys):,} ({time.time() - t0:.0f}s)", flush=True)
    X = np.array(rows, float)
    y, CL, RP, CT1 = np.array(Ys), np.array(CL), np.array(RP), np.array(CT1)
    loc = 10 ** X[:, 2]
    names = ["log1p commits", "log1p churn lines", "log10 loc", "shape changed", "archetype changed", "Δcomplexity", "|Δcomplexity|",
             "Δlog loc", "log1p fan-in", "complexity/loc"] + [f"|Δ{s}|" for s in SIG]
    B0 = [0, 1, 2]
    M1 = list(range(X.shape[1]))
    L = ["# CHG2-H1..H2 — engine change features vs churn for regression ranking (SCORED)", "",
         f"- units {len(y):,}; regression-hit units {int(y.sum()):,}; units with churn > 0: {int((X[:, 0] > 0).sum()):,}; "
         f"churn-mapped commits {len(jobs):,}", ""]

    def evaluate(tr, te, tag):
        p0, _ = train_predict(X, y, tr, te, B0, rng)
        p1, b1 = train_predict(X, y, tr, te, M1, rng)
        out = {}
        for frac in (0.05, 0.10, 0.20):
            s0, s1 = select(p0, loc[te], frac), select(p1, loc[te], frac)
            sz = select(-loc[te], loc[te], frac)
            out[frac] = (s0, s1, sz)
        return out, b1

    # H1: forward
    tr, te = CT1 < SPLIT, CT1 >= SPLIT
    res1, b1 = evaluate(tr, te, "fwd")
    yt = y[te]
    L += ["| claim | test positives | recall@20% B0 churn | recall@20% M1 churn+engine | difference | lo (α 0.01/2) | verdict |", "|---|---:|---:|---:|---:|---:|---|"]
    def verdict(npos, d, lo):
        return "not evaluable" if npos < MIN_POS else ("SUPPORTED" if d > 0 and lo > 0 else "not supported")
    s0, s1, sz = res1[0.20]
    r0, r1 = (yt * s0).sum() / yt.sum(), (yt * s1).sum() / yt.sum()
    lo1 = boot_diff(CL[te], yt, s1, s0, rng)
    L.append(f"| **CHG2-H1** forward (train < 2020, test ≥ 2020) | {int(yt.sum()):,} | {r0:.1%} | {r1:.1%} | {r1 - r0:+.1%} | {lo1:+.1%} | **{verdict(yt.sum(), r1 - r0, lo1)}** |")
    desc = [f"- forward, size-only ordering recall@20%: {(yt * sz).sum() / yt.sum():.1%}; "
            + "; ".join(f"@{int(f * 100)}%: B0 {(yt * res1[f][0]).sum() / yt.sum():.1%}, M1 {(yt * res1[f][1]).sum() / yt.sum():.1%}" for f in (0.05, 0.10))]
    # H2: leave one repo out
    S0, S1, SZ, YY, CC, fold = [], [], [], [], [], []
    for i, r in enumerate(REPOS):
        tr, te = RP != i, RP == i
        if y[te].sum() == 0:
            fold.append(f"{r}: no positives")
            continue
        res, _ = evaluate(tr, te, r)
        a0, a1, az = res[0.20]
        yy = y[te]
        S0.append(a0); S1.append(a1); SZ.append(az); YY.append(yy); CC.append(CL[te])
        fold.append(f"{r} ({int(yy.sum())} pos): B0 {(yy * a0).sum() / yy.sum():.1%}, M1 {(yy * a1).sum() / yy.sum():.1%}, size-only {(yy * az).sum() / yy.sum():.1%}")
    S0, S1, SZ, YY, CC = map(np.concatenate, (S0, S1, SZ, YY, CC))
    q0, q1 = (YY * S0).sum() / YY.sum(), (YY * S1).sum() / YY.sum()
    lo2 = boot_diff(CC, YY, S1, S0, rng)
    L.append(f"| **CHG2-H2** leave-one-repo-out (pooled) | {int(YY.sum()):,} | {q0:.1%} | {q1:.1%} | {q1 - q0:+.1%} | {lo2:+.1%} | **{verdict(YY.sum(), q1 - q0, lo2)}** |")
    L += ["", "## Descriptive", ""] + desc + [f"- leave-one-repo-out, size-only ordering recall@20%: {(YY * SZ).sum() / YY.sum():.1%}"]
    L += [f"- fold {f}" for f in fold]
    top = sorted(zip(names, b1[1:]), key=lambda t: -abs(t[1]))[:12]
    L += ["", "M1 standardised coefficients (forward fit, largest 12): " + ", ".join(f"{n} {v:+.2f}" for n, v in top),
          "", f"Runtime {time.time() - t0:.0f}s · seed {SEED} · {ITERS} file-cluster bootstrap rounds (selections fixed)."]
    (DOCS_DIR / "chg2.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
