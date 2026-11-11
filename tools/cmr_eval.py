#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""CMR (docs/cmr_hypotheses.md): comments and danger comments by call-graph role, and the comment -> first-fix
rate ratio inside vs outside each role, per fix class. Engine venv.

    <engine venv>/bin/python tools/cmr_eval.py --scratch <CGT scratch with net_<repo>.pkl>

Roles: CGK's rules (hub / orchestrator = top 10% of in- / out-degree > 0; periphery = k-core below the snapshot
median) on CGT's network at the function's birth snapshot. Comments at birth: DC's comment_task, unchanged.
Aggregates only; writes docs/cmr.md.
"""
from __future__ import annotations

import argparse
import bisect
import collections
import multiprocessing
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import cgn_eval as N  # noqa: E402
import cgt_eval as G  # noqa: E402
from _engine import DOCS_DIR  # noqa: E402
from cgk_eval import top_set, two_sided  # noqa: E402
from chg_eval import fix_events, map_fix  # noqa: E402
from dc_eval import comment_task  # noqa: E402
from ints_eval import YEAR, lives  # noqa: E402

REPOS = ("curl", "openssl", "ndpi", "harfbuzz", "libarchive")
ROLES = ("hub", "orch", "periph")
FCLS = ("latent", "regression", "extrinsic")
ALL_CLS = ("latent", "other-fix", "regression", "extrinsic")
SEED, ITERS = 2982, 2000
ALPHA_P, ALPHA_F = 0.01 / 6, 0.01 / 9
MIN_EV = 20


def roles_of(net):
    din = N.indeg(net)
    dout = collections.Counter(x for x, _ in net["edges"])
    dout = {n: dout.get(n, 0) for n in net["nodes"]}
    hub, orch = top_set(din, 0.90), top_set(dout, 0.90)
    core = N.core_numbers(net["nodes"], net["edges"])
    cmed = np.median(list(core.values())) if core else 0
    return {n: (n in hub, n in orch, core.get(n, 0) < cmed) for n in net["nodes"]}


def mh_codes(e, ev, pt, si, ns):
    """ints_eval.mh_rate with integer strata codes (fast path for the bootstrap)."""
    a, b = np.bincount(si, ev * e, ns), np.bincount(si, ev * (1 - e), ns)
    t1, t0 = np.bincount(si, pt * e, ns), np.bincount(si, pt * (1 - e), ns)
    T = t1 + t0
    ok = (t1 > 0) & (t0 > 0)
    den = np.sum(b[ok] * t1[ok] / T[ok])
    return np.sum(a[ok] * t0[ok] / T[ok]) / den if den > 0 else np.nan


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=pathlib.Path, required=True)
    a = ap.parse_args()
    t0 = time.time()
    ev, last = [], {}
    for r in REPOS:
        e, last[r] = fix_events(r)
        ev += [x for x in e if x[3] in ALL_CLS]
    with multiprocessing.get_context("fork").Pool(8) as p:
        hits = [h for hs in p.imap_unordered(map_fix, ev, chunksize=8) for h in hs]
    print(f"hits {len(hits):,} ({time.time() - t0:.0f}s)", flush=True)
    U, missing = [], collections.Counter()
    for r in REPOS:
        snaps, ids_at, info = lives(r)
        cts = [s["ct"] for s in snaps]
        nets = {n["sha"]: n for n in G.snapshot_networks(r, a.scratch)}
        role_cache = {}

        def role(k, path, nm):
            sha = snaps[k]["sha"]
            if sha not in nets:
                return None
            if sha not in role_cache:
                role_cache[sha] = roles_of(nets[sha])
            return role_cache[sha].get((path, nm.split("::")[-1]))

        first, file_cve = collections.defaultdict(dict), collections.defaultdict(list)
        for (_r, path, nm, ct, klass) in (h for h in hits if h[0] == r):
            if klass == "latent":
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
            if fid is not None and (klass not in first[fid] or ct < first[fid][klass]):
                first[fid][klass] = ct
        for v in file_cve.values():
            v.sort()
        groups = collections.defaultdict(list)
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
            c = cm.get((r, snaps[inf["birth_k"]]["sha"], inf["key"][0]), {}).get(inf["key"][1])
            if c is None:
                missing[(r, "comment")] += 1
                continue
            rb = role(inf["birth_k"], *inf["key"])
            if rb is None:
                missing[(r, "role")] += 1
                continue
            rl = role(inf["last_k"], *inf["key"]) or rb
            prior = bisect.bisect_left(file_cve.get(inf["key"][0], []), b) > 0
            U.append({"r": r, "file": inf["key"][0], "lb": int(np.floor(np.log10(inf["loc"]) / 0.1)), "prior": prior,
                      "loc": inf["loc"], "ncl": c[0], "commented": c[0] >= 1, "danger": bool(c[1]), "words": c[2],
                      "role": rb, "role_last": rl, "pt": (end - b) / YEAR,
                      "ev": {k: v for k, v in first.get(fid, {}).items() if b < v <= end}})
        print(f"{r}: births {sum(1 for u in U if u['r'] == r):,} ({time.time() - t0:.0f}s)", flush=True)

    L = ["# CMR — comments × call-graph role × fix class (SCORED)", "",
         f"- births with comment and role at birth: {len(U):,} (repos {', '.join(REPOS)}); "
         f"skipped: {dict(missing)}",
         "- registration `docs/cmr_hypotheses.md`", "",
         "## Part P — placement (two-sided CMH, strata repo × loc bin, α = 0.01/6)", "",
         "| id | role | OR | z | exposed | call |", "|---|---|---|---|---|---|"]
    res = {}
    for ri, rn in enumerate(ROLES):
        sP1 = collections.defaultdict(lambda: [0, 0, 0, 0])
        sP2 = collections.defaultdict(lambda: [0, 0, 0, 0])
        for u in U:
            key = (u["r"], u["lb"])
            inr = u["role"][ri]
            st = sP1[key]
            st[(0 if u["commented"] else 1) if inr else (2 if u["commented"] else 3)] += 1
            if u["commented"]:
                st2 = sP2[key]
                st2[(0 if u["danger"] else 1) if inr else (2 if u["danger"] else 3)] += 1
        for pid, st in (("CMR-P1", sP1), ("CMR-P2", sP2)):
            h = two_sided(list(st.values()), ALPHA_P)
            res[(pid, rn)] = h
            orv = "n/a" if h.get("or") is None else f"{h['or']:.2f}"
            zv = "n/a" if h.get("z") is None else f"{h['z']:+.1f}"
            L.append(f"| {pid} | {rn} | {orv} | {zv} | {h['exposed']:,} | **{h['call']}** |")
    L += ["", "Exposed = functions in the role (P1) or commented functions in the role (P2); "
          "OR > 1 = more commented (P1) / more danger-worded (P2) in the role.", ""]

    # Part F
    cl = np.array([f"{u['r']}:{u['file']}" for u in U])
    _, ci = np.unique(cl, return_inverse=True)
    grp = [np.flatnonzero(ci == k) for k in range(ci.max() + 1)]
    st_lab = np.array([f"{u['r']}|{u['lb']}|{u['prior']}" for u in U])
    _, si_all = np.unique(st_lab, return_inverse=True)
    ns = int(si_all.max()) + 1
    pt = np.array([u["pt"] for u in U])
    EV = {k: np.array([1.0 if k in u["ev"] else 0.0 for u in U]) for k in ALL_CLS}
    role_m = {rn: np.array([u["role"][i] for u in U]) for i, rn in enumerate(ROLES)}
    role_last = {rn: np.array([u["role_last"][i] for u in U]) for i, rn in enumerate(ROLES)}
    commented = np.array([u["commented"] for u in U])
    danger = np.array([u["danger"] for u in U])
    fams = {"CMR-FD": (commented, danger.astype(float)), "CMR-FC": (np.ones(len(U), bool), commented.astype(float))}

    def cell(fam, rn, k, idx, roles=role_m):
        base, ex = fams[fam]
        m = base[idx]
        e, inr = ex[idx][m], roles[rn][idx][m]
        y, p, s = EV[k][idx][m], pt[idx][m], si_all[idx][m]
        rin = mh_codes(e[inr], y[inr], p[inr], s[inr], ns)
        rout = mh_codes(e[~inr], y[~inr], p[~inr], s[~inr], ns)
        return rin, rout

    full = np.arange(len(U))
    cells = [(fam, rn, k) for fam in fams for rn in ROLES for k in FCLS]
    point = {c: cell(*c, full) for c in cells}
    counts = {}
    for fam, rn, k in cells:
        base, ex = fams[fam]
        m = base
        inr = role_m[rn]
        counts[(fam, rn, k)] = [int((EV[k] * m * inr * (ex == 1)).sum()), int((EV[k] * m * inr * (ex == 0)).sum()),
                                int((EV[k] * m * ~inr * (ex == 1)).sum()), int((EV[k] * m * ~inr * (ex == 0)).sum())]
    rng = np.random.default_rng(SEED)
    boot = {c: [] for c in cells}
    for it in range(ITERS):
        pick = np.concatenate([grp[j] for j in rng.integers(0, len(grp), len(grp))])
        for c in cells:
            rin, rout = cell(*c, pick)
            boot[c].append(rin / rout if rout and rout > 0 and np.isfinite(rin) else np.nan)
        if it % 500 == 499:
            print(f"bootstrap {it + 1} ({time.time() - t0:.0f}s)", flush=True)
    L += ["## Part F — comment → first-fix rate ratio inside vs outside each role "
          f"(interaction = RR_in ÷ RR_out; file-cluster bootstrap {ITERS}; two-sided α = 0.01/9 per family)", "",
          "| id | role | class | RR in role | RR outside | interaction [CI] | events (in: exp/unexp; out: exp/unexp) | call |",
          "|---|---|---|---|---|---|---|---|"]
    for c in cells:
        fam, rn, k = c
        rin, rout = point[c]
        inter = rin / rout if rout and rout > 0 else np.nan
        b = np.array(boot[c], float)
        lo, hi = (float(np.nanquantile(b, ALPHA_F / 2)), float(np.nanquantile(b, 1 - ALPHA_F / 2))) \
            if np.isfinite(b).sum() > 100 else (np.nan, np.nan)
        n = counts[c]
        if min(n) < MIN_EV:
            call = "underpowered"
        elif lo > 1:
            call = "stronger in role"
        elif hi < 1:
            call = "weaker in role"
        else:
            call = "n.s."
        L.append(f"| {fam} | {rn} | {k} | {rin:.2f} | {rout:.2f} | {inter:.2f} [{lo:.2f}, {hi:.2f}] | "
                 f"{n[0]}/{n[1]}; {n[2]}/{n[3]} | **{call}** |")

    L += ["", "## Descriptive (no verdicts)", ""]
    for i, rn in enumerate(ROLES):
        m = role_m[rn]
        loc = np.array([u["loc"] for u in U])
        ncl = np.array([u["ncl"] for u in U])
        L.append(f"- {rn}: {int(m.sum()):,} births; commented {commented[m].mean():.0%} (others "
                 f"{commented[~m].mean():.0%}); danger among commented {danger[m & commented].mean():.0%} (others "
                 f"{danger[~m & commented].mean():.0%}); comment lines per loc {ncl[m].sum() / loc[m].sum():.3f} "
                 f"(others {ncl[~m].sum() / loc[~m].sum():.3f})")
        words = collections.Counter(w for u, x in zip(U, m) if x for w in set(u["words"]))
        L.append(f"  - top danger words: " + ", ".join(f"{w} {c}" for w, c in words.most_common(10)))
    L += ["", "- Role at the function's last live snapshot instead of birth (point interactions):"]
    for c in cells:
        rin, rout = cell(*c, full, roles=role_last)
        L.append(f"  - {c[0]} {c[1]} {c[2]}: {rin / rout if rout else float('nan'):.2f}")
    L += ["", "- Per repo, CMR-FD latent within role (RR in / RR out):"]
    for r in REPOS:
        idx = np.flatnonzero(np.array([u["r"] == r for u in U]))
        parts = []
        for rn in ROLES:
            rin, rout = cell("CMR-FD", rn, "latent", idx)
            parts.append(f"{rn} {rin:.2f}/{rout:.2f}")
        L.append(f"  - {r} ({len(idx):,} births): " + "; ".join(parts))
    L += ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED}."]
    (DOCS_DIR / "cmr.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
