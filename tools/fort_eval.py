#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""FORT-H1..H3 (docs/fort_hypotheses.md): guard clauses before/after each fix, by fix class. Engine venv (tree-sitter).

    <engine venv>/bin/python tools/fort_eval.py
"""
from __future__ import annotations

import multiprocessing
import pathlib
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402
from chg_eval import CEXT, CPPEXT, FILE_HDR, HUNK, REPOS, _fname, _git, _parser, fix_events  # noqa: E402

EXITS = {"return_statement", "goto_statement", "break_statement", "continue_statement"}
SEED, ITERS, ALPHA = 2982, 2000, 0.01 / 3
CLASSES = ("latent", "regression", "other-fix", "extrinsic")


def guards(node):
    g, stack = 0, [node]
    while stack:
        n = stack.pop()
        if n.type == "if_statement" and n.child_by_field_name("alternative") is None:
            c = n.child_by_field_name("consequence")
            if c is not None:
                if c.type in EXITS:
                    g += 1
                elif c.type == "compound_statement":
                    st = [x for x in c.named_children if x.type != "comment"]
                    if 1 <= len(st) <= 3 and st[-1].type in EXITS:
                        g += 1
        stack.extend(n.children)
    return g


def funcs(src: bytes, lang):
    out = []
    stack = [_parser(lang).parse(src).root_node]
    while stack:
        n = stack.pop()
        if n.type == "function_definition":
            nm = _fname(n)
            if nm:
                out.append((n.start_point[0] + 1, n.end_point[0] + 1, nm, guards(n)))
            continue
        stack.extend(n.children)
    return out


def task(t):
    r, sha, ct, klass = t
    repo = POOL_DIR / r
    parent = _git(repo, "rev-parse", "-q", "--verify", f"{sha}^").strip()
    if not parent:
        return []
    lines = defaultdict(set)
    cur = None
    for ln in _git(repo, "diff", "-U0", "--no-color", "--no-renames", parent, sha).splitlines():
        m = FILE_HDR.match(ln)
        if m:
            cur = m.group(1) if m.group(1) and m.group(1).endswith(CEXT + CPPEXT) else None
            continue
        if cur:
            h = HUNK.match(ln)
            if h:
                s, n = int(h.group(1)), int(h.group(2) or 1)
                lines[cur].update(range(s, s + n) if n > 0 else [max(s, 1)])
    out = []
    for path, ls in lines.items():
        lang = "c" if path.endswith(CEXT) and r != "harfbuzz" else "cpp"
        a = _git(repo, "show", f"{parent}:{path}", text=False)
        b = _git(repo, "show", f"{sha}:{path}", text=False)
        if not a or not b:
            continue
        pre = funcs(a, lang)
        post = {}
        for s_, e_, nm, g in funcs(b, lang):
            post.setdefault(nm, g)
        for s_, e_, nm, g in pre:
            if any(s_ <= l <= e_ for l in ls) and nm in post:
                out.append((r, sha, klass, path, nm, e_ - s_ + 1, g, post[nm]))
    return out


def mh(e, y, st):
    _, si = np.unique(st, return_inverse=True)
    a, b = np.bincount(si, y * e), np.bincount(si, y * (1 - e))
    n1, n0 = np.bincount(si, e), np.bincount(si, 1 - e)
    ok = (n1 > 0) & (n0 > 0)
    N = n1 + n0
    den = np.sum(b[ok] * n1[ok] / N[ok])
    return np.sum(a[ok] * n0[ok] / N[ok]) / den if den > 0 else np.inf


def mh_ci(e, y, st, cl, rng):
    rr = mh(e, y, st)
    _, ci = np.unique(cl, return_inverse=True)
    groups = [np.flatnonzero(ci == k) for k in range(ci.max() + 1)]
    bs = []
    for _ in range(ITERS):
        pick = np.concatenate([groups[k] for k in rng.integers(0, len(groups), len(groups))])
        bs.append(mh(e[pick], y[pick], st[pick]))
    bs = np.array(bs)
    bs = bs[np.isfinite(bs)]
    return rr, float(np.quantile(bs, ALPHA)), float(np.quantile(bs, 1 - ALPHA))


def main() -> int:
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    ev = []
    for r in REPOS:
        e, _ = fix_events(r)
        ev += [x for x in e if x[3] in CLASSES]
    print(f"fix events {len(ev):,}: {dict(Counter(x[3] for x in ev))}", flush=True)
    with multiprocessing.get_context("fork").Pool(8) as p:
        U = [u for us in p.imap_unordered(task, ev, chunksize=8) for u in us]
    print(f"touches {len(U):,} ({time.time() - t0:.0f}s)", flush=True)
    R = np.array([u[0] for u in U])
    C = np.array([u[2] for u in U])
    cl = np.array([u[1] for u in U])
    loc = np.array([u[5] for u in U], float)
    g0 = np.array([u[6] for u in U])
    g1 = np.array([u[7] for u in U])
    add = (g1 - g0 >= 1).astype(float)
    pre = (g0 >= 1).astype(float)
    st = np.array([f"{r}|{int(np.floor(np.log10(max(l, 1)) / 0.2))}" for r, l in zip(R, loc)])
    L = ["# FORT-H1..H3 — fortification: guard clauses before and after fixes (SCORED)", "",
         f"- fix-function touches: {len(U):,} — " + ", ".join(f"{k} {int((C == k).sum()):,}" for k in CLASSES), "",
         "| claim | comparison | RR | 99.67% CI | verdict |", "|---|---|---:|---|---|"]
    m1 = (C == "latent") | (C == "other-fix")
    rr1, lo1, hi1 = mh_ci((C[m1] == "latent").astype(float), add[m1], st[m1], cl[m1], rng)
    n_lat = int((C == "latent").sum())
    v1 = "not evaluable" if n_lat < 30 else ("SUPPORTED" if rr1 > 1 and lo1 > 1 else "not supported")
    L.append(f"| **FORT-H1** CVE fixes fortify | P(adds guard) latent vs other-fix | **{rr1:.2f}** | [{lo1:.2f}, {hi1:.2f}] | **{v1}** |")
    m2 = m1 & (add == 1)
    rr2, lo2, hi2 = mh_ci((C[m2] == "latent").astype(float), pre[m2], st[m2], cl[m2], rng)
    n2 = int(((C == "latent") & (add == 1)).sum())
    v2 = ("not evaluable" if n2 < 30 else "SUPPORTED: incompleteness" if rr2 > 1 and lo2 > 1
          else "SUPPORTED: exposure" if rr2 < 1 and hi2 < 1 else "inconclusive")
    L.append(f"| **FORT-H2** guard-adding fixes: was the function already guarded? | P(pre-guarded) latent vs other-fix (n latent {n2}) | **{rr2:.2f}** | [{lo2:.2f}, {hi2:.2f}] | **{v2}** |")
    m3 = (C == "regression") | (C == "other-fix")
    rr3, lo3, hi3 = mh_ci((C[m3] == "regression").astype(float), add[m3], st[m3], cl[m3], rng)
    n_reg = int((C == "regression").sum())
    v3 = "not evaluable" if n_reg < 30 else ("SUPPORTED" if rr3 < 1 and hi3 < 1 else "not supported")
    L.append(f"| **FORT-H3** regression fixes are lexically neutral | P(adds guard) regression vs other-fix | **{rr3:.2f}** | [{lo3:.2f}, {hi3:.2f}] | **{v3}** |")
    L += ["", "## By class (descriptive)", "", "| class | touches | adds guard | removes guard | mean ΔG | pre-guarded | median function loc |", "|---|---:|---:|---:|---:|---:|---:|"]
    for k in CLASSES:
        m = C == k
        if m.sum():
            L.append(f"| {k} | {int(m.sum()):,} | {add[m].mean():.1%} | {((g1 - g0)[m] <= -1).mean():.1%} | {(g1 - g0)[m].mean():+.2f} | {pre[m].mean():.1%} | {np.median(loc[m]):.0f} |")
    L += ["", "Per repo (MH point RR): H1 / H2 / H3"]
    for r in REPOS:
        mr = R == r
        def pt(m, e, y):
            m = m & mr
            return mh(e[m], y[m], st[m]) if m.sum() else float("nan")
        L.append(f"- {r}: {pt(m1, (C == 'latent').astype(float), add):.2f} / {pt(m2, (C == 'latent').astype(float), pre):.2f} / {pt(m3, (C == 'regression').astype(float), add):.2f}")
    me = (C == "latent") | (C == "extrinsic")
    L.append(f"- second comparison, latent vs extrinsic, P(adds guard): {mh((C[me] == 'latent').astype(float), add[me], st[me]):.2f}")
    L += ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED} · {ITERS} commit-cluster bootstrap rounds."]
    (DOCS_DIR / "fort.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
