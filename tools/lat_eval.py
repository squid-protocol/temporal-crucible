#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAT-F1..F3 and LAT-M1..M3 (docs/lat_hypotheses.md, incl. Amendment 0): the fingerprint lattice vs fix kinds
and regressions. Engine venv, engine pinned on PYTHONPATH:

    E=<gitgalaxy-worktrees>/tc-rescan-32619e4a5
    PYTHONPATH=$E SFS_SRC=<popan>/structural-fingerprint-scanner/src $E/.venv-tc/bin/python tools/lat_eval.py [F|M|all]
"""
from __future__ import annotations

import bisect
import hashlib
import json
import multiprocessing
import pathlib
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402
from chg_eval import CEXT, CPPEXT, FILE_HDR, HUNK, REPOS, WINDOW, _fname, _git, _parser, fix_events, map_fix  # noqa: E402
from gr_eval import crucible_grammar, fit_p  # noqa: E402

SEED, ITERS, NPERM, NPLAC = 2982, 2000, 2000, 200
TREES = DOCS_DIR / "fingerprint_trees_exploratory.json"
TREES_SHA = "a27d2c93f817"
CRUCIBLE = POOL_DIR / "kw_scan" / "data_galaxy_master.db"
CLASSES = ("latent", "regression", "extrinsic", "other-fix")
EXCL = ("tests/", "docs/", ".github/", "scripts/")
SENS = {"def_safety", "state_pointers", "def_sync_locks", "arch_io", "arch_concurrency", "state_memory_alloc", "def_cleanup"}
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:6.0f}s] {m}", flush=True)


# ------------------------------------------------------------------ frozen lattice
class Lattice:
    def __init__(self):
        raw = TREES.read_bytes()
        assert hashlib.sha256(raw).hexdigest().startswith(TREES_SHA), "frozen tree data changed"
        D = json.loads(raw)
        self.sets = [frozenset(s["signals"]) for s in D["shapes"]]
        self.n = np.array([s["n"] for s in D["shapes"]], float)
        n = len(self.sets)
        J = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                u = len(self.sets[i] | self.sets[j])
                J[i, j] = J[j, i] = 1 - (len(self.sets[i] & self.sets[j]) / u if u else 1)
        self.fam = fcluster(linkage(squareform(J, checks=False), method="average"), 14, criterion="maxclust")
        for f in D["families"]:  # the recomputed families must be the frozen ones
            got = sorted(int(i) + 1 for i in np.flatnonzero(self.fam == f["family"]))
            assert all(m in got for m in f["members"]), f"family F{f['family']} does not reproduce"
        self.U = sorted(set().union(*self.sets))

    def assign(self, P, cols, drop=frozenset()):
        """P: bool (N x len(cols)) presence; returns family (0 = unassigned), k, and whether the shape is one of the 200
        or one signal away from one (on the available signal set)."""
        avail = [c for c in cols if c in self.U and c not in drop]
        ix = [cols.index(c) for c in avail]
        X = P[:, ix].astype(np.int32)
        S = np.array([[c in s for c in avail] for s in self.sets], np.int32)
        keys, inv = np.unique(X, axis=0, return_inverse=True)
        inter = keys @ S.T
        union = keys.sum(1)[:, None] + S.sum(1)[None, :] - inter
        jac = np.where(union > 0, inter / np.maximum(union, 1), 1.0)
        order = np.argsort(-self.n, kind="stable")  # ties -> more common shape
        jo = jac[:, order]
        pick = order[np.argmax(jo, axis=1)]
        fam_k = np.where(jac.max(1) > 0, self.fam[pick], 0)
        ham = np.abs(keys[:, None, :] - S[None, :, :]).sum(2)
        near = (ham <= 1).any(1)
        inv = inv.ravel()
        return fam_k[inv], X.sum(1), near[inv]


def mh(e, y, st):
    _, si = np.unique(st, return_inverse=True)
    a, b = np.bincount(si, y * e), np.bincount(si, y * (1 - e))
    n1, n0 = np.bincount(si, e), np.bincount(si, 1 - e)
    ok = (n1 > 0) & (n0 > 0)
    N = n1 + n0
    den = np.sum(b[ok] * n1[ok] / N[ok])
    return np.sum(a[ok] * n0[ok] / N[ok]) / den if den > 0 else np.inf


def mh_ci(e, y, st, cl, rng, alpha=0.01):
    rr = mh(e, y, st)
    _, ci = np.unique(cl, return_inverse=True)
    order = np.argsort(ci, kind="stable")
    groups = np.split(order, np.flatnonzero(np.diff(ci[order])) + 1)
    bs = []
    for _ in range(ITERS):
        pick = np.concatenate([groups[k] for k in rng.integers(0, len(groups), len(groups))])
        bs.append(mh(e[pick], y[pick], st[pick]))
    bs = np.array(bs)
    bs = bs[np.isfinite(bs)]
    return rr, float(np.quantile(bs, alpha)), float(np.quantile(bs, 1 - alpha))


def cramers_v(a, b):
    _, ai = np.unique(a, return_inverse=True)
    _, bi = np.unique(b, return_inverse=True)
    T = np.zeros((ai.max() + 1, bi.max() + 1))
    np.add.at(T, (ai, bi), 1)
    E = T.sum(1, keepdims=True) * T.sum(0, keepdims=True) / T.sum()
    chi = np.sum((T - E) ** 2 / np.where(E > 0, E, 1))
    return float(np.sqrt(chi / (T.sum() * max(min(T.shape) - 1, 1))))


def band(k):
    return np.where(k <= 3, 0, np.where(k <= 5, 1, 2))


# ------------------------------------------------------------------ LAT-F
_W = {}


def _worker():
    if not _W:
        from gitgalaxy.core.prism import Prism
        from gitgalaxy.recorders import record_keeper as RK
        from gitgalaxy.standards.gitgalaxy_config import LEXICAL_FAMILY_HEURISTICS
        from gitgalaxy.standards.language_standards import LANGUAGE_DEFINITIONS as LD
        m = dict(re.findall(r'"([a-z_0-9]+)": "([a-z_0-9]+)"', pathlib.Path(RK.__file__).read_text()))
        _W["prism"] = Prism(LEXICAL_FAMILY_HEURISTICS, LD)
        _W["rules"] = {lg: {k: v for k, v in LD[lg]["rules"].items() if hasattr(v, "search") and not k.startswith("_")} for lg in ("c", "cpp")}
        _W["col"] = lambda k: m.get(k, k)
    return _W


def f_task(t):
    r, sha, ct, klass = t
    W = _worker()
    repo = POOL_DIR / r
    parent = _git(repo, "rev-parse", "-q", "--verify", f"{sha}^").strip()
    if not parent:
        return []
    lines = defaultdict(set)
    cur = None
    for ln in _git(repo, "diff", "-U0", "--no-color", "--no-renames", parent, sha).splitlines():
        m = FILE_HDR.match(ln)
        if m:
            p = m.group(1)
            cur = p if p and p.endswith(CEXT + CPPEXT) and not p.startswith(EXCL) else None
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
        lg = "c" if path.endswith(CEXT) and r != "harfbuzz" else "cpp"
        tree = _parser(lg).parse(src)
        text = src.decode("utf-8", "replace").split("\n")
        stack, seen = [tree.root_node], set()
        while stack:
            nd = stack.pop()
            if nd.type == "function_definition":
                nm = _fname(nd)
                a, b = nd.start_point[0] + 1, nd.end_point[0] + 1
                if nm and nm not in seen and any(a <= l <= b for l in ls):
                    seen.add(nm)
                    body = "\n".join(text[a - 1:b])
                    try:
                        code = W["prism"].split_streams(body, lg)["code_stream"]
                    except Exception:
                        code = body
                    pres = frozenset(W["col"](k) for k, rx in W["rules"][lg].items() if rx.search(code))
                    out.append((r, sha, path, nm, klass, b - a + 1, pres))
                continue
            stack.extend(nd.children)
    return out


def run_F(L, rng, out):
    ev = []
    for r in REPOS:
        e, _ = fix_events(r)
        ev += [x for x in e if x[3] in CLASSES]
    log(f"F: fix commits {len(ev):,}")
    with multiprocessing.get_context("fork").Pool(8) as p:
        U = [u for us in p.imap_unordered(f_task, ev, chunksize=4) for u in us]
    log(f"F: touched functions {len(U):,}")
    cols = sorted(set().union(*(u[6] for u in U)) | set(L.U))
    P = np.array([[c in u[6] for c in cols] for u in U], bool)
    C = np.array([u[4] for u in U])
    loc = np.array([max(u[5], 1) for u in U], float)
    rep = np.array([u[0] for u in U])
    st = np.array([f"{r}|{int(np.floor(np.log10(x) / 0.2))}" for r, x in zip(rep, loc)])
    cl = np.array([f"{u[0]}:{u[2]}" for u in U])
    res = {}
    for tag, drop in (("main", frozenset()), ("sensitivity", frozenset(SENS))):
        fam, k, _ = L.assign(P, cols, drop)
        # F1
        m = (C == "latent") | (C == "other-fix")
        y = ((fam == 8) & (k >= 6)).astype(float)
        rr, lo, hi = mh_ci((C[m] == "latent").astype(float), y[m], st[m], cl[m], rng)
        # F2
        cat = fam * 3 + band(k)
        v_obs = cramers_v(C, cat)
        _, si = np.unique(st, return_inverse=True)
        so = np.argsort(si, kind="stable")
        groups = np.split(so, np.flatnonzero(np.diff(si[so])) + 1)
        ge = 0
        for _ in range(NPERM):
            Cp = C.copy()
            for g in groups:
                if len(g) > 1:
                    Cp[g] = C[g][rng.permutation(len(g))]
            ge += cramers_v(Cp, cat) >= v_obs
        p2 = (1 + ge) / (1 + NPERM)
        # F3 placebo: per-repo, per-signal logistic presence in standardised log size
        avail = [c for c in cols if c in L.U and c not in drop]
        ix = [cols.index(c) for c in avail]
        Pr = {}
        for r in np.unique(rep):
            w = rep == r
            z = np.log10(loc[w])
            z = (z - z.mean()) / (z.std() + 1e-9)
            Pr[r] = (w, np.column_stack([fit_p(P[w][:, j].astype(float), z) if 0 < P[w][:, j].mean() < 1 else
                                         np.full(w.sum(), P[w][:, j].mean()) for j in ix]))
        pv = []
        for _ in range(NPLAC):
            Ps = np.zeros((len(U), len(avail)), bool)
            for r, (w, pr) in Pr.items():
                Ps[w] = rng.random(pr.shape) < pr
            f_s, k_s, _ = L.assign(Ps, avail)
            pv.append(cramers_v(C, f_s * 3 + band(k_s)))
        p99 = float(np.quantile(pv, 0.99))
        res[tag] = {"F1": (rr, lo, hi, y[m][C[m] == "latent"].mean(), y[m][C[m] == "other-fix"].mean()),
                    "F2": (v_obs, p2), "F3": (v_obs, p99, float(np.mean(pv))), "fam": fam, "k": k}
        log(f"F {tag}: F1 RR {rr:.2f} [{lo:.2f}, {hi:.2f}]; F2 V {v_obs:.3f} p {p2:.4f}; F3 placebo p99 {p99:.3f}")
    a = res["main"]
    v1 = "SUPPORTED" if a["F1"][0] >= 1.25 and a["F1"][1] > 1 else "not supported"
    v2 = "SUPPORTED" if a["F2"][1] < 0.01 else "not supported"
    v3 = "SUPPORTED" if a["F3"][0] > a["F3"][1] else "not supported"
    s = res["sensitivity"]
    s1 = "SUPPORTED" if s["F1"][0] >= 1.25 and s["F1"][1] > 1 else "not supported"
    s2 = "SUPPORTED" if s["F2"][1] < 0.01 else "not supported"
    s3 = "SUPPORTED" if s["F3"][0] > s["F3"][1] else "not supported"
    frag = lambda x, y_: "" if x == y_ else " — **fragile** (flips under sensitivity)"  # noqa: E731
    out += ["## LAT-F — fix kinds × pre-fix family and rung", "",
            f"- touched functions (commit × function, parent blob): {len(U):,} — " + ", ".join(f"{c} {int((C == c).sum()):,}" for c in CLASSES),
            f"- unassigned (no signal shared with any of the 200 shapes): {(a['fam'] == 0).mean():.1%}", "",
            "| claim | result | verdict | sensitivity (without #8010/#8016 signals) |", "|---|---|---|---|",
            f"| **LAT-F1** latent-CVE in private-C upper rungs (F8 ∧ k ≥ 6) vs other-fix | {a['F1'][3]:.1%} vs {a['F1'][4]:.1%}; MH RR **{a['F1'][0]:.2f}** [{a['F1'][1]:.2f}, {a['F1'][2]:.2f}] (99%) | **{v1}** | RR {s['F1'][0]:.2f} [{s['F1'][1]:.2f}, {s['F1'][2]:.2f}] → {s1}{frag(v1, s1)} |",
            f"| **LAT-F2** fix classes differ by family × rung beyond size (within-stratum permutation) | Cramér's V **{a['F2'][0]:.3f}**, p = {a['F2'][1]:.4f} | **{v2}** | V {s['F2'][0]:.3f}, p {s['F2'][1]:.4f} → {s2}{frag(v2, s2)} |",
            f"| **LAT-F3** not a size artefact (size-only placebo, {NPLAC} draws) | observed V {a['F3'][0]:.3f} vs placebo 99th pct {a['F3'][1]:.3f} (mean {a['F3'][2]:.3f}) | **{v3}** | {s['F3'][0]:.3f} vs {s['F3'][1]:.3f} → {s3}{frag(v3, s3)} |",
            "", "### Descriptive — family share by fix class (main)", "", "| family | " + " | ".join(CLASSES) + " |", "|---|" + "---:|" * len(CLASSES)]
    fam = a["fam"]
    for f in sorted(set(fam), key=lambda f: -(fam == f).sum())[:10]:
        out.append(f"| F{f} | " + " | ".join(f"{((fam == f) & (C == c)).sum() / max((C == c).sum(), 1):.1%}" for c in CLASSES) + " |")
    out += ["", "| rung band | " + " | ".join(CLASSES) + " |", "|---|" + "---:|" * len(CLASSES)]
    bd = band(a["k"])
    for b_, nm in enumerate(("k ≤ 3", "k 4–5", "k ≥ 6")):
        out.append(f"| {nm} | " + " | ".join(f"{((bd == b_) & (C == c)).sum() / max((C == c).sum(), 1):.1%}" for c in CLASSES) + " |")
    out.append("")


# ------------------------------------------------------------------ LAT-M
def run_M(L, rng, out):
    import chg2_eval as C2
    W_ = crucible_grammar(CRUCIBLE)
    partners = defaultdict(set)
    for (a_, b_), v in W_.items():
        if v > 0:
            partners[a_].add(b_)
            partners[b_].add(a_)
    ev, last_ct = [], {}
    for r in REPOS:
        e, last_ct[r] = fix_events(r)
        ev += [x for x in e if x[3] == "regression"]
    jobs, loaded, sigs = [], {}, {}
    for r in REPOS:
        snaps, per, nsig = C2.load(r)
        con = sqlite3.connect(f"file:{C2.DBS[r]}?mode=ro", uri=True)
        have = {c[1] for c in con.execute("PRAGMA table_info(function_data)")}
        con.close()
        sigs[r] = [c for c in C2.SIG if c in have]
        loaded[r] = (snaps, per)
        c0, c1 = snaps[0]["ct"], snaps[-1]["ct"]
        for line in _git(POOL_DIR / r, "log", "--first-parent", "--format=%H %ct", "HEAD").splitlines():
            h, ct = line.split()
            if c0 < int(ct) <= c1:
                jobs.append((r, h, int(ct)))
    log(f"M: regression events {len(ev)}; commits to map {len(jobs):,}")
    with multiprocessing.get_context("fork").Pool(8) as p:
        hits = [h for hs in p.imap_unordered(map_fix, ev, chunksize=4) for h in hs]
        churn = list(p.imap_unordered(C2.map_churn, jobs, chunksize=16))
    cidx = defaultdict(list)
    for r, ct, d in churn:
        for (path, nm), w in d.items():
            cidx[(r, path, nm)].append((ct, w))
            if "::" in nm:
                cidx[(r, path, nm.split("::")[-1])].append((ct, w))
    for v in cidx.values():
        v.sort()
    base, A, B, Ys, CL, RP, CT1, REPU = [], [], [], [], [], [], [], []
    for r in REPOS:
        snaps, per = loaded[r]
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
        sg = sigs[r]
        for k1, _k0, key, a, b in C2.transitions(snaps, per):
            c0, c1 = cts[k1 - 1], cts[k1]
            loc = float(b[0])
            if c1 + WINDOW > last_ct[r] or loc < 1:
                continue
            v = ridx.get(key, [])
            i = bisect.bisect_right(v, c1)
            y = 1.0 if i < len(v) and v[i] <= c1 + WINDOW else 0.0
            cv = cidx.get((r,) + key, [])
            lo_, hi_ = bisect.bisect_right(cv, (c0, 1 << 60)), bisect.bisect_right(cv, (c1, 1 << 60))
            base.append([np.log1p(hi_ - lo_), np.log1p(sum(w for _, w in cv[lo_:hi_])), np.log10(loc)])
            A.append({c for c, x in zip(sg, a[4]) if x > 0})
            B.append({c for c, x in zip(sg, b[4]) if x > 0})
            Ys.append(y)
            CL.append(f"{r}:{key[0]}")
            RP.append(REPOS.index(r))
            CT1.append(c1)
            REPU.append(f"{r}:{key[0]}:{key[1]}")
        log(f"M: {r} units so far {len(Ys):,}")
    X0 = np.array(base)
    y, CL, RP, CT1 = np.array(Ys), np.array(CL), np.array(RP), np.array(CT1)
    loc = 10 ** X0[:, 2]
    cols = sorted(set(C2.SIG))
    PA = np.array([[c in s for c in cols] for s in A], bool)
    PB = np.array([[c in s for c in cols] for s in B], bool)
    res = {}
    for tag, drop in (("main", frozenset()), ("sensitivity", frozenset(SENS))):
        U_ = [c for c in cols if c in L.U and c not in drop]
        ui = [cols.index(c) for c in U_]
        a_, b_ = PA[:, ui], PB[:, ui]
        fa, ka, _ = L.assign(PA, cols, drop)
        fb, kb, nearb = L.assign(PB, cols, drop)
        gained = b_ & ~a_
        step = (a_ != b_).sum(1)
        pm = [[U_.index(q) for q in partners.get(c, ()) if q in U_] for c in U_]
        half = np.zeros(len(y))
        for j, ps in enumerate(pm):
            if ps:
                half += gained[:, j] & ~b_[:, ps].any(1)
        F = np.column_stack([step > 0, step, step >= 2, kb > ka, kb < ka, fa != fb, half, ~nearb]).astype(float)
        X = np.column_stack([X0, F])
        B0, M2 = [0, 1, 2], list(range(X.shape[1]))
        churn = X0[:, 1]
        cd = np.full(len(y), -1)
        nz = churn > 0
        cd[nz] = np.minimum((np.argsort(np.argsort(churn[nz])) * 10 // nz.sum()), 9)
        sb = np.floor(X0[:, 2] / 0.2).astype(int)

        def evaluate(Xm, tr, te):
            p0, _ = C2.train_predict(Xm, y, tr, te, B0, rng)
            p1, _ = C2.train_predict(Xm, y, tr, te, M2, rng)
            return C2.select(p0, loc[te], 0.20), C2.select(p1, loc[te], 0.20)

        def both(Xm):
            tr, te = CT1 < C2.SPLIT, CT1 >= C2.SPLIT
            s0, s1 = evaluate(Xm, tr, te)
            yt = y[te]
            fwd = ((yt * s0).sum() / yt.sum(), (yt * s1).sum() / yt.sum(), C2.boot_diff(CL[te], yt, s1, s0, rng), int(yt.sum()))
            S0, S1, YY, CC = [], [], [], []
            for i in range(len(REPOS)):
                tr, te = RP != i, RP == i
                if y[te].sum() == 0:
                    continue
                a0, a1 = evaluate(Xm, tr, te)
                S0.append(a0); S1.append(a1); YY.append(y[te]); CC.append(CL[te])
            S0, S1, YY, CC = map(np.concatenate, (S0, S1, YY, CC))
            loro = ((YY * S0).sum() / YY.sum(), (YY * S1).sum() / YY.sum(), C2.boot_diff(CC, YY, S1, S0, rng), int(YY.sum()))
            return fwd, loro
        fwd, loro = both(X)
        # M3: permute lattice features jointly within churn decile x size bin
        Xp = X.copy()
        strat = cd * 1000 + sb
        for s in np.unique(strat):
            g = np.flatnonzero(strat == s)
            if len(g) > 1:
                Xp[g, 3:] = X[g][rng.permutation(len(g)), 3:]
        pf, pl = both(Xp)
        # M2: half-steps among edited units
        e = (half >= 1).astype(float)
        st = np.array([f"{r}|{c}|{s}" for r, c, s in zip(RP, cd, sb)])
        rr, lo, hi = mh_ci(e[nz], y[nz], st[nz], CL[nz], rng)
        res[tag] = {"fwd": fwd, "loro": loro, "pf": pf, "pl": pl, "M2": (rr, lo, hi, int(e[nz].sum()), int((e[nz] * y[nz]).sum())),
                    "F": F, "fa": fa, "fb": fb, "a": a_, "b": b_, "U": U_}
        log(f"M {tag}: fwd {fwd[1] - fwd[0]:+.3f} (lo {fwd[2]:+.3f}); loro {loro[1] - loro[0]:+.3f} (lo {loro[2]:+.3f}); "
            f"M3 {pf[1] - pf[0]:+.3f}/{pl[1] - pl[0]:+.3f}; M2 RR {rr:.2f} [{lo:.2f}, {hi:.2f}]")
    a = res["main"]

    def vm1(d):
        f, l_ = d["fwd"], d["loro"]
        return "SUPPORTED" if (f[1] - f[0] >= 0.02 and f[2] > 0 and l_[1] - l_[0] >= 0.02 and l_[2] > 0) else "not supported"
    ctrl = abs(a["pf"][1] - a["pf"][0]) < 0.01 and abs(a["pl"][1] - a["pl"][0]) < 0.01
    v1 = vm1(a) if ctrl else "VOID (M3 control failed)"
    v2 = ("SUPPORTED" if a["M2"][0] >= 1.25 and a["M2"][1] > 1 else "not supported") if ctrl else "VOID (M3 control failed)"
    s = res["sensitivity"]
    s1 = vm1(s)
    s2 = "SUPPORTED" if s["M2"][0] >= 1.25 and s["M2"][1] > 1 else "not supported"
    frag = lambda x, y_: "" if x == y_ or x.startswith("VOID") else " — **fragile**"  # noqa: E731
    f, l_ = a["fwd"], a["loro"]
    out += ["## LAT-M — lattice moves vs regressions (CHG-2 units)", "",
            f"- units {len(y):,}; regression-hit {int(y.sum()):,}; edited (churn > 0) {int(nz.sum()):,}; lattice signals available {len(a['U'])}", "",
            "| claim | result | verdict | sensitivity |", "|---|---|---|---|",
            f"| **LAT-M1** lattice moves add recall@20% beyond churn (forward **and** LORO, ≥ +2.0 pt, lo > 0) | forward B0 {f[0]:.1%} → M2 {f[1]:.1%} (**{f[1] - f[0]:+.1%}**, lo {f[2]:+.1%}; {f[3]} pos); LORO {l_[0]:.1%} → {l_[1]:.1%} (**{l_[1] - l_[0]:+.1%}**, lo {l_[2]:+.1%}; {l_[3]} pos) | **{v1}** | fwd {s['fwd'][1] - s['fwd'][0]:+.1%} (lo {s['fwd'][2]:+.1%}), LORO {s['loro'][1] - s['loro'][0]:+.1%} (lo {s['loro'][2]:+.1%}) → {s1}{frag(v1, s1)} |",
            f"| **LAT-M2** half-step edits precede regressions (edited units) | {a['M2'][3]:,} half-step units, {a['M2'][4]} regression-hit; MH RR **{a['M2'][0]:.2f}** [{a['M2'][1]:.2f}, {a['M2'][2]:.2f}] (99%) | **{v2}** | RR {s['M2'][0]:.2f} [{s['M2'][1]:.2f}, {s['M2'][2]:.2f}] → {s2}{frag(v2, s2)} |",
            f"| **LAT-M3** control: permuted lattice features add ~nothing (\\|diff\\| < 1 pt) | forward {a['pf'][1] - a['pf'][0]:+.1%}, LORO {a['pl'][1] - a['pl'][0]:+.1%} | **{'PASS' if ctrl else 'FAIL — M results void'}** | — |",
            "", "### Descriptive (main)", ""]
    F = a["F"]
    moved = F[:, 0] > 0
    life = defaultdict(list)
    for u, mv in zip(REPU, moved):
        life[u].append(mv)
    never = np.mean([not any(v) for v in life.values()])
    out += [f"- units whose shape moved: {moved.mean():.1%} (of edited units: {moved[nz].mean():.1%}); functions whose shape never moved over all their intervals: **{never:.1%}** of {len(life):,}",
            f"- among moves: single-signal steps {np.mean(F[moved, 1] == 1):.1%}, jumps (≥ 2) {np.mean(F[moved, 2] > 0):.1%}; climbs {np.mean(F[moved, 3] > 0):.1%}, descents {np.mean(F[moved, 4] > 0):.1%}; family changes {np.mean(F[moved, 5] > 0):.1%}; half-step present {np.mean(F[moved, 6] > 0):.1%}; end shape off-lattice {np.mean(F[:, 7] > 0):.1%} of all units",
            f"- regression rate: moved {y[moved].mean():.2%} vs unmoved-but-edited {y[nz & ~moved].mean():.2%} vs untouched {y[~nz].mean():.2%}"]
    ga = Counter()
    U_ = a["U"]
    gm = a["b"] & ~a["a"]
    lm = a["a"] & ~a["b"]
    for j, c in enumerate(U_):
        ga[f"+{c}"] = int(gm[:, j].sum())
        ga[f"−{c}"] = int(lm[:, j].sum())
    out.append("- commonest single-signal moves: " + ", ".join(f"{k} {v:,}" for k, v in ga.most_common(10)))
    T = Counter((int(x), int(z)) for x, z in zip(a["fa"][moved], a["fb"][moved]) if x != z)
    out.append("- commonest family changes: " + ", ".join(f"F{x}→F{z} {n:,}" for (x, z), n in T.most_common(8)))
    out.append("")


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    rng = np.random.default_rng(SEED)
    L = Lattice()
    log(f"lattice: {len(L.sets)} shapes, {len(L.U)} signals, families reproduce")
    out = ["# LAT-F1..F3, LAT-M1..M3 — the fingerprint lattice vs fix kinds and regressions (SCORED)", "",
           "Registration: `docs/lat_hypotheses.md` (with Amendment 0). Aggregates only.", ""]
    if which in ("F", "all"):
        run_F(L, rng, out)
    if which in ("M", "all"):
        run_M(L, rng, out)
    out += [f"Runtime {time.time() - T0:.0f}s · seed {SEED} · {ITERS} file-cluster bootstrap rounds · {NPERM} permutations · {NPLAC} placebo draws."]
    (DOCS_DIR / ("lat.md" if which == "all" else f"lat_{which}.md")).write_text("\n".join(out) + "\n")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
