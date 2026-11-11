#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""DRP-R / DRP-S (docs/drp_hypotheses.md): do fix commits repay self-admitted debt less often than other commits?
Unseen repos only (libgit2, libxml2, postgres, redis). Debt removals from tools/debt_lifecycle.py's tracker; fix
labels from chg_eval.fix_events; commit size from git --numstat.

    python tools/drp_eval.py      # -> docs/drp.md
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
from chg_eval import fix_events  # noqa: E402
from debt_lifecycle import PATHSPEC, git, keep, track  # noqa: E402

REPOS = ("libgit2", "libxml2", "postgres", "redis")
SEED, ITERS = 2982, 2000
ALPHA = 0.01 / 2
MIN_EV = 30
SIZE_EDGES = (2, 8, 32, 128, 512)
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:6.0f}s] {m}", flush=True)


def sizes(r):
    """In-scope C/C++ lines added + deleted per non-merge commit (commits with none are not units)."""
    out, cur = {}, None
    for ln in git(POOL_DIR / r, "log", "--no-merges", "--numstat", "--format=@@C %H", "--", *PATHSPEC).splitlines():
        if ln.startswith("@@C "):
            cur = ln[4:].strip()
            continue
        parts = ln.split("\t")
        if cur and len(parts) == 3 and keep(parts[2].split(" => ")[-1].rstrip("}")):
            a, d = parts[0], parts[1]
            if a.isdigit() and d.isdigit():
                out[cur] = out.get(cur, 0) + int(a) + int(d)
    return r, {h: n for h, n in out.items() if n > 0}


def mh_rr(e, y, si):
    ns = int(si.max()) + 1
    a, b = np.bincount(si, y * e, ns), np.bincount(si, y * (1 - e), ns)
    n1, n0 = np.bincount(si, e, ns), np.bincount(si, 1 - e, ns)
    N = n1 + n0
    ok = (n1 > 0) & (n0 > 0)
    den = np.sum(b[ok] * n1[ok] / N[ok])
    return np.sum(a[ok] * n0[ok] / N[ok]) / den if den > 0 else np.nan


def boot_upper(e, y, si, rp, rng):
    idx = [np.flatnonzero(rp == k) for k in np.unique(rp)]
    out = []
    for _ in range(ITERS):
        pk = np.concatenate([g[rng.integers(0, len(g), len(g))] for g in idx])
        out.append(mh_rr(e[pk], y[pk], si[pk]))
    out = np.array(out, float)
    out = out[np.isfinite(out)]
    return float(np.quantile(out, 1 - ALPHA)), float(np.quantile(out, ALPHA))


def main() -> int:
    with multiprocessing.get_context("fork").Pool(len(REPOS)) as p:
        tracked = {r: items for r, items, *_ in p.imap_unordered(track, REPOS)}
        sz = dict(p.imap_unordered(sizes, REPOS))
    rows = []
    bulk = Counter()
    for r in REPOS:
        evs, _ = fix_events(r)
        cls = {sha: k for _, sha, _, k in evs}
        rep = Counter(x["end_sha"] for x in tracked[r] if x["end"] is not None and not x["file_deleted"])
        for h, n in rep.items():
            if n >= 5:
                bulk[r] += 1
        for h, n in sz[r].items():
            b = sum(n > c for c in SIZE_EDGES)
            rows.append((r, h in cls, cls.get(h), rep.get(h, 0) > 0, b))
        log(f"{r}: commits {len(sz[r]):,}; fixes {sum(1 for x in rows if x[0] == r and x[1]):,}; repaying "
            f"{sum(1 for x in rows if x[0] == r and x[3]):,}; repaying commits not in units "
            f"{sum(1 for h in rep if h not in sz[r])}")
    rp = np.array([REPOS.index(x[0]) for x in rows])
    e = np.array([x[1] for x in rows], float)
    y = np.array([x[3] for x in rows], float)
    bins = np.array([x[4] for x in rows])
    _, s_r = np.unique(rp, return_inverse=True)
    _, s_s = np.unique(rp * 10 + bins, return_inverse=True)
    ev_fix = int((e * y).sum())
    res = {}
    for cid, si in (("DRP-R", s_r), ("DRP-S", s_s)):
        rr = mh_rr(e, y, si)
        up, lo = boot_upper(e, y, si, rp, np.random.default_rng(SEED))
        call = ("underpowered" if ev_fix < MIN_EV else
                "SUPPORTED" if rr < 1 and up < 1 else "not supported")
        res[cid] = (rr, up, lo, call)
        log(f"{cid}: RR {rr:.3f} (upper {up:.3f}) -> {call}")
    L = ["# DRP — do fix commits repay self-admitted debt less often than other commits? (SCORED)", "",
         "Registration `docs/drp_hypotheses.md` (owner OK 2026-11-11). Repos libgit2, libxml2, postgres, redis. "
         f"Commit bootstrap {ITERS} within repo, seed {SEED}; one-sided α = 0.01/2. Aggregates only.", "",
         f"- units: {len(rows):,} non-merge commits changing in-scope C/C++ lines; fixes {int(e.sum()):,} "
         f"({e.mean():.1%}); repaying commits {int(y.sum()):,} ({y.mean():.1%}); repaying fix commits **{ev_fix}**", "",
         "| id | strata | repay rate: fix commits | other commits | MH RR | one-sided upper bound (α = 0.005) | call |",
         "|---|---|---:|---:|---:|---:|---|",
         f"| **DRP-R** | repo | {y[e == 1].mean():.2%} | {y[e == 0].mean():.2%} | **{res['DRP-R'][0]:.2f}** | "
         f"{res['DRP-R'][1]:.2f} | **{res['DRP-R'][3]}** |",
         f"| **DRP-S** | repo × commit size | — | — | **{res['DRP-S'][0]:.2f}** | {res['DRP-S'][1]:.2f} | "
         f"**{res['DRP-S'][3]}** |", "",
         f"Power rule: ≥ {MIN_EV} repaying fix commits pooled.", "", "## Descriptive (no verdicts)", "",
         "| repo | commits | fixes | repay rate: fix / other | RR raw | RR size-stratified | bulk repayers (≥ 5 lines) |",
         "|---|---:|---:|---|---:|---:|---:|"]
    for k, r in enumerate(REPOS):
        m = rp == k
        _, sr = np.unique(bins[m], return_inverse=True)
        L.append(f"| {r} | {int(m.sum()):,} | {int(e[m].sum()):,} | {y[m & (e == 1)].mean():.2%} / "
                 f"{y[m & (e == 0)].mean():.2%} | {mh_rr(e[m], y[m], np.zeros(int(m.sum()), int)):.2f} | "
                 f"{mh_rr(e[m], y[m], sr):.2f} | {bulk[r]} |")
    L += ["", "- Repay rate by size bin (fix / other): " + "; ".join(
        f"{lab} {y[(bins == b) & (e == 1)].mean():.1%} / {y[(bins == b) & (e == 0)].mean():.1%}"
        for b, lab in enumerate(("1–2", "3–8", "9–32", "33–128", "129–512", "> 512")) if (bins == b).any()),
        "- Repay rate by fix class: " + ", ".join(
            f"{k} {np.mean([x[3] for x in rows if x[2] == k]):.2%} (n {sum(1 for x in rows if x[2] == k):,})"
            for k in sorted({x[2] for x in rows if x[2]})),
        "", f"Runtime {time.time() - T0:.0f}s · seed {SEED}."]
    (DOCS_DIR / "drp.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
