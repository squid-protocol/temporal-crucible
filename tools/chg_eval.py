#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""CHG-H1..H5: fingerprint change and code age vs later regression fixes (docs/chg_hypotheses.md).
Run with the engine venv (tree-sitter-language-pack + numpy):

    <engine venv>/bin/python tools/chg_eval.py
"""
from __future__ import annotations

import bisect
import json
import multiprocessing
import pathlib
import re
import sqlite3
import subprocess
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from nh_eval import DBS, snapshots  # noqa: E402

REPOS = ("curl", "openssl", "harfbuzz", "ndpi", "libarchive")
CEXT = (".c", ".h")
CPPEXT = (".cc", ".cpp", ".cxx", ".hh", ".hpp", ".hxx")
YEAR, DAY, WINDOW = 365.25 * 86400, 86400, 180 * 86400
SEED, ITERS, ALPHA, MIN_EV = 2982, 2000, 0.01 / 5, 30
AGES = ("young", "1-3y", "old", "unknown")
STATES = ("untouched", "edited", "shape")
FILE_HDR = re.compile(r"^--- (?:a/(.*)|/dev/null)$")
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+")
NAME_TYPES = {"identifier", "field_identifier", "qualified_identifier", "destructor_name", "operator_name", "template_function"}


def _git(repo, *a, text=True):
    return subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", *a], capture_output=True, text=text,
                          **({"errors": "replace"} if text else {})).stdout


# ------------------------------------------------------------------------------------------------ fix -> functions
_PARSERS = {}


def _parser(lang):
    if lang not in _PARSERS:
        import tree_sitter_language_pack as tslp
        _PARSERS[lang] = tslp.get_parser(lang)
    return _PARSERS[lang]


def _fname(node):
    d = node.child_by_field_name("declarator")
    while d is not None:
        if d.type in NAME_TYPES:
            return d.text.decode("utf-8", "replace")
        nxt = d.child_by_field_name("declarator")
        if nxt is None:
            for c in d.children:
                if c.type in NAME_TYPES:
                    return c.text.decode("utf-8", "replace")
            return None
        d = nxt
    return None


def map_fix(task):
    r, sha, ct, klass = task
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
        src = _git(repo, "show", f"{parent}:{path}", text=False)
        if not src:
            continue
        tree = _parser("c" if path.endswith(CEXT) and r != "harfbuzz" else "cpp").parse(src)
        spans = []
        stack = [tree.root_node]
        while stack:
            n = stack.pop()
            if n.type == "function_definition":
                nm = _fname(n)
                if nm:
                    spans.append((n.start_point[0] + 1, n.end_point[0] + 1, nm))
            stack.extend(n.children)
        hit = {nm for a, b, nm in spans for l in ls if a <= l <= b}
        out += [(r, path, nm, ct, klass) for nm in hit]
    return out


def fix_events(r):
    xc = json.loads((REPO_ROOT / "events" / f"{r}_xc.json").read_text())["events"]
    ev, lat = [], set()
    if r == "harfbuzz":
        for e in json.loads((REPO_ROOT / "events" / "harfbuzz.json").read_text())["events"]:
            if e["class"] == "security-fix":
                ct = _git(POOL_DIR / r, "show", "-s", "--format=%ct", e["sha"]).strip()
                if ct:
                    ev.append((r, e["sha"], int(ct), "latent"))
                    lat.add(e["sha"])
    for e in xc:
        if e["sha"] in lat:
            continue
        k = e["class"]
        if k == "regression":
            k = "regression" if e["why"] == "regression word" else "regression-linked"
        ev.append((r, e["sha"], e["ct"], k))
    return ev, max(e["ct"] for e in xc)


# ------------------------------------------------------------------------------------------------ transitions
def transitions(r):
    snaps = snapshots(r)
    con = sqlite3.connect(f"file:{DBS[r]}?mode=ro", uri=True)
    per = []
    for s in snaps:
        rows = con.execute("SELECT fd.file_path, f.func_name, f.start_line, f.loc, f.complexity, f.func_archetype "
                           "FROM function_data f JOIN file_data fd ON f.file_id = fd.id WHERE fd.commit_hash = ? "
                           "AND fd.language IN ('c','cpp') AND f.func_name IS NOT NULL AND f.func_name != ''", (s["sha"],)).fetchall()
        d = {}
        for path, name, _st, loc, cx, arch in sorted(rows, key=lambda x: (x[0], x[1], x[2] or 0)):
            d.setdefault((path, name), (loc or 0, cx or 0, arch or ""))
        per.append(d)
    con.close()
    birth, nxt, prev, prev_ids = {}, 0, None, {}
    T = []  # (k1, key at k1, state, age class, loc at k1)
    t0 = snaps[0]["ct"]
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
                birth[nxt] = k
                nxt += 1
        if prev is not None:
            inv = {v: key for key, v in prev_ids.items()}
            ct1 = snaps[k]["ct"]
            for key, f in cur.items():
                if f not in inv:
                    continue
                a, b = prev[inv[f]], d[key]
                state = 2 if (a[1] != b[1] or a[2] != b[2]) else 1 if a[0] != b[0] else 0
                if birth[f] == 0:
                    ac = 2 if (ct1 - t0) / YEAR >= 3 else 3
                else:
                    age = (ct1 - snaps[birth[f]]["ct"]) / YEAR
                    ac = 0 if age < 1 else 1 if age < 3 else 2
                T.append((k, key, state, ac, b[0]))
        prev, prev_ids = d, cur
    return snaps, per, T


# ------------------------------------------------------------------------------------------------ statistics
def mh_boot(cl, st, e, y, rng):
    """Mantel-Haenszel RR (exposed e=1 vs e=0) with a cluster bootstrap over cl. Returns rr, lo, a, b, n1, n0."""
    keys, inv_c = np.unique(cl, return_inverse=True)
    _, inv_s = np.unique(st, return_inverse=True)
    nS = inv_s.max() + 1
    cell = inv_c * nS + inv_s
    u, ci = np.unique(cell, return_inverse=True)
    A = np.bincount(ci, weights=y * e)
    B = np.bincount(ci, weights=y * (1 - e))
    N1 = np.bincount(ci, weights=e)
    N0 = np.bincount(ci, weights=1 - e)
    cc, ss = u // nS, u % nS

    def rr(w):
        a, b = np.bincount(ss, w * A, nS), np.bincount(ss, w * B, nS)
        n1, n0 = np.bincount(ss, w * N1, nS), np.bincount(ss, w * N0, nS)
        N = n1 + n0
        ok = (n1 > 0) & (n0 > 0)
        num, den = np.sum(a[ok] * n0[ok] / N[ok]), np.sum(b[ok] * n1[ok] / N[ok])
        return num / den if den > 0 else np.inf
    base = rr(np.ones(len(u)))
    nC = len(keys)
    bs = []
    for _ in range(ITERS):
        wc = rng.multinomial(nC, np.full(nC, 1 / nC)).astype(float)
        bs.append(rr(wc[cc]))
    return base, float(np.quantile(bs, ALPHA)), int((y * e).sum()), int((y * (1 - e)).sum()), int(e.sum()), int((1 - e).sum())


def mh_point(st, e, y):
    _, si = np.unique(st, return_inverse=True)
    a, b = np.bincount(si, y * e), np.bincount(si, y * (1 - e))
    n1, n0 = np.bincount(si, e), np.bincount(si, 1 - e)
    ok = (n1 > 0) & (n0 > 0)
    N = n1 + n0
    den = np.sum(b[ok] * n1[ok] / N[ok])
    return np.sum(a[ok] * n0[ok] / N[ok]) / den if den else float("nan")


def main() -> int:
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    all_ev, last_ct = [], {}
    for r in REPOS:
        ev, last_ct[r] = fix_events(r)
        all_ev += ev
    print(f"fix events {len(all_ev):,}: {Counter(e[3] for e in all_ev)}", flush=True)
    with multiprocessing.get_context("fork").Pool(8) as p:
        hits = [h for hs in p.imap_unordered(map_fix, all_ev, chunksize=8) for h in hs]
    print(f"function hits {len(hits):,} ({time.time() - t0:.0f}s)", flush=True)
    # transitions + gate
    data, gate_ok, gate_n = {}, 0, 0
    idx = defaultdict(list)  # (r, path, name) -> [(ct, class)]
    for r in REPOS:
        snaps, per, T = transitions(r)
        cts = [s["ct"] for s in snaps]
        names = [{k for k in d} for d in per]
        resolved = 0
        for (rr_, path, nm, ct, klass) in (h for h in hits if h[0] == r):
            j = bisect.bisect_right(cts, ct) - 1
            if j < 0:
                continue
            gate_n += 1
            key = (path, nm) if (path, nm) in names[j] else (path, nm.split("::")[-1]) if (path, nm.split("::")[-1]) in names[j] else None
            if key is None:
                key = (path, nm)
            else:
                gate_ok += 1
                resolved += 1
            idx[(r,) + key].append((ct, klass))
        data[r] = (snaps, T)
        print(f"{r}: {len(snaps)} snapshots, {len(T):,} transitions, {resolved:,} resolved hits ({time.time() - t0:.0f}s)", flush=True)
    for v in idx.values():
        v.sort()
    g = gate_ok / max(gate_n, 1)
    L = ["# CHG-H1..H5 — fingerprint change and code age vs later regression fixes (SCORED)", "",
         f"**Gate G-JOIN:** {gate_ok:,} / {gate_n:,} fix→function hits match an engine function at the preceding snapshot = **{g:.1%}** → "
         f"**{'PASS' if g >= 0.8 else 'FAIL'}** (gate ≥ 80%)", ""]
    if g < 0.8:
        (DOCS_DIR / "chg.md").write_text("\n".join(L) + "\n")
        print("\n".join(L))
        return 1
    # unit table
    CLS = ("regression", "other-fix", "latent", "extrinsic", "regression-linked")
    R, F, S, A, LB, Y = [], [], [], [], [], {c: [] for c in CLS}
    for r in REPOS:
        snaps, T = data[r]
        for k1, key, state, ac, loc in T:
            c1 = snaps[k1]["ct"]
            if c1 + WINDOW > last_ct[r] or loc < 1:
                continue
            got = set()
            v = idx.get((r,) + key)
            if v:
                i = bisect.bisect_right(v, (c1, "￿"))
                while i < len(v) and v[i][0] <= c1 + WINDOW:
                    got.add(v[i][1])
                    i += 1
            R.append(REPOS.index(r))
            F.append(f"{r}:{key[0]}")
            S.append(state)
            A.append(ac)
            LB.append(int(np.floor(np.log10(loc) / 0.1)))
            for c in CLS:
                Y[c].append(1.0 if c in got else 0.0)
    R, S, A, LB = np.array(R), np.array(S), np.array(A), np.array(LB)
    F = np.array(F)
    Y = {c: np.array(v) for c, v in Y.items()}
    L.append(f"- units (function × quarter, full 180-day window): **{len(S):,}**; states {dict(Counter(STATES[s] for s in S))}; "
             f"ages {dict(Counter(AGES[a] for a in A))}")
    L.append(f"- units hit in window: " + ", ".join(f"{c} {int(Y[c].sum()):,}" for c in CLS))
    L += ["", "| claim | comparison | events (exposed / reference) | MH RR | lo (α 0.01/5, file-cluster bootstrap) | verdict |", "|---|---|---:|---:|---:|---|"]
    st_age = R * 10_000 + LB * 10 + A
    st_state = R * 10_000 + LB * 10 + S
    anyfix = (Y["regression"] + Y["other-fix"]) > 0
    claims = [
        ("CHG-H1", "shape-changed vs untouched → regression", (S == 2) | (S == 0), (S == 2), st_age, Y["regression"]),
        ("CHG-H2", "shape-changed vs edited-same-shape → regression", (S == 2) | (S == 1), (S == 2), st_age, Y["regression"]),
        ("CHG-H3", "regression share of fixed: shape vs untouched", ((S == 2) | (S == 0)) & anyfix, (S == 2), st_age, Y["regression"]),
        ("CHG-H4", "young vs old → regression", (A == 0) | (A == 2), (A == 0), st_state, Y["regression"]),
        ("CHG-H5", "regression share of fixed: young vs old", ((A == 0) | (A == 2)) & anyfix, (A == 0), st_state, Y["regression"]),
    ]
    per_repo = []
    for cid, what, m, ex, st, y in claims:
        rr, lo, a, b, n1, n0 = mh_boot(F[m], st[m], ex[m].astype(float), y[m], rng)
        ok = a >= MIN_EV and b >= MIN_EV
        v = ("SUPPORTED" if rr > 1 and lo > 1 else "not supported") if ok else "not evaluable"
        L.append(f"| **{cid}** | {what} | {a:,} / {b:,} (n {n1:,} / {n0:,}) | **{rr:.2f}** | {lo:.2f} | **{v}** |")
        dirs = []
        for i, r in enumerate(REPOS):
            mm = m & (R == i)
            if (y[mm] * ex[mm]).sum() >= 5 and (y[mm] * (1 - ex[mm])).sum() >= 5:
                dirs.append(f"{r} {mh_point(st[mm], ex[mm].astype(float), y[mm]):.2f}")
            else:
                dirs.append(f"{r} (few)")
        per_repo.append(f"- **{cid}** per repo: " + ", ".join(dirs))
    L += ["", "## Per repo (MH point estimates, descriptive)", ""] + per_repo
    L += ["", "## Crude 180-day hit rates per 1,000 function-quarters (descriptive)", "",
          "| group | n | " + " | ".join(CLS) + " |", "|---|---:|" + "---:|" * len(CLS)]
    for label, m in [(f"state: {STATES[s]}", S == s) for s in range(3)] + [(f"age: {AGES[a]}", A == a) for a in range(4)]:
        L.append(f"| {label} | {int(m.sum()):,} | " + " | ".join(f"{1000 * Y[c][m].mean():.2f}" for c in CLS) + " |")
    L += ["", "Regression share among fixed units (regression / (regression or other-fix)):"]
    for label, m in [(f"{STATES[s]}", S == s) for s in range(3)] + [(f"{AGES[a]}", A == a) for a in range(4)]:
        mm = m & anyfix
        L.append(f"- {label}: {Y['regression'][mm].mean():.1%} of {int(mm.sum()):,}")
    L += ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED} · {ITERS} file-cluster bootstrap rounds."]
    (DOCS_DIR / "chg.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
