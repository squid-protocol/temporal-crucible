#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""CF-H1..H2 (docs/dc_hypotheses.md § CFIX): comment changes of fixes; silent-patch detection with WHERE + comments.
Engine venv.

    <engine venv>/bin/python tools/cfix_eval.py
"""
from __future__ import annotations

import multiprocessing
import pathlib
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402
from chg_eval import CEXT, fix_events  # noqa: E402
from dc_eval import DANGER, prism  # noqa: E402
from fort_eval import mh, task as fort_task  # noqa: E402
from silent_eval import REPOS, SEC, auc, fit  # noqa: E402
from wh_eval import feat  # noqa: E402

SEED, ITERS, ALPHA = 2982, 2000, 0.01 / 2


def comment_lines(raw: bytes, lang):
    if not raw:
        return set()
    try:
        pos = prism().split_positional_comment_stream(raw.decode("utf-8", "replace"), lang)
    except Exception:
        return set()
    return {" ".join(l.split()) for l in pos.split("\n") if len(l.strip()) >= 3}


def ctask(t):
    r, sha, ct, klass = t
    base = feat(t)
    if base is None:
        return None
    repo = POOL_DIR / r
    added, removed = set(), set()
    for path in base["files"]:
        lang = "c" if path.endswith(CEXT) and r != "harfbuzz" else "cpp"
        a = subprocess.run(["git", "-C", str(repo), "show", f"{sha}^:{path}"], capture_output=True).stdout
        b = subprocess.run(["git", "-C", str(repo), "show", f"{sha}:{path}"], capture_output=True).stdout
        pa, pb = comment_lines(a, lang), comment_lines(b, lang)
        added |= pb - pa
        removed |= pa - pb
    dw = sum(len(DANGER.findall(l)) for l in added)
    base.update(c_add=len(added), c_rem=len(removed), c_danger=dw)
    return base


def main() -> int:
    t0 = time.time()
    ev = []
    for r in REPOS:
        e, _ = fix_events(r)
        ev += [x for x in e if x[3] in ("latent", "other-fix")]
    with multiprocessing.get_context("fork").Pool(8) as p:
        rows = [x for x in p.imap_unordered(ctask, ev, chunksize=8) if x]
        touches = [u for us in p.imap_unordered(fort_task, ev, chunksize=8) for u in us]
    print(f"commits {len(rows):,} ({time.time() - t0:.0f}s)", flush=True)
    g = defaultdict(lambda: [0.0, 0.0])
    for u in touches:
        g[u[1]][0] += u[6]
        g[u[1]][1] += u[5]
    for r in REPOS:
        rr = sorted((x for x in rows if x["r"] == r), key=lambda x: (x["ct"], x["sha"]))
        sec_seen, fix_seen = defaultdict(int), defaultdict(int)
        i = 0
        while i < len(rr):
            j = i
            while j < len(rr) and rr[j]["ct"] == rr[i]["ct"]:
                j += 1
            for x in rr[i:j]:
                x["prior_sec"] = sum(sec_seen[f] for f in x["files"])
                x["prior_fix"] = sum(fix_seen[f] for f in x["files"])
            for x in rr[i:j]:
                for f in x["files"]:
                    fix_seen[f] += 1
                    if x["klass"] == "latent":
                        sec_seen[f] += 1
            i = j
    for x in rows:
        gg = g.get(x["sha"], [0.0, 0.0])
        x["defended"] = 100.0 * gg[0] / gg[1] if gg[1] else 0.0
    R = np.array([x["r"] for x in rows])
    y = np.array([1.0 if x["klass"] == "latent" else 0.0 for x in rows])
    secw = np.array([bool(SEC.search(x["subj"])) for x in rows])
    nl = np.array([max(x["nl"], 1) for x in rows], float)
    # ---- CF-H1
    e = y
    adds_d = np.array([1.0 if x["c_danger"] >= 1 else 0.0 for x in rows])
    adds_c = np.array([1.0 if x["c_add"] >= 1 else 0.0 for x in rows])
    st = np.array([f"{r}|{int(np.floor(np.log10(n) / 0.25))}" for r, n in zip(R, nl)])
    rr1 = mh(e, adds_d, st)
    rng = np.random.default_rng(SEED)
    bs = []
    n = len(rows)
    for _ in range(ITERS):
        i = rng.integers(0, n, n)
        bs.append(mh(e[i], adds_d[i], st[i]))
    lo1 = float(np.nanquantile(bs, ALPHA))
    rr_c = mh(e, adds_c, st)
    # ---- CF-H2
    size = np.c_[np.log10(nl), np.log10([max(x["nf"], 1) for x in rows])]
    where = np.c_[np.log1p([x["prior_sec"] for x in rows]), [1.0 if x["prior_sec"] > 0 else 0.0 for x in rows],
                  np.log1p([x["prior_fix"] for x in rows]), [x["defended"] for x in rows]]
    cm = np.c_[adds_c, adds_d, np.log1p([x["c_add"] for x in rows]), np.log1p([x["c_danger"] for x in rows])]
    sets = {"WHERE": np.c_[size, where], "WHERE+CMT": np.c_[size, where, cm], "CMT": np.c_[size, cm]}
    sc = {k: np.full(len(rows), np.nan) for k in sets}
    for hold in REPOS:
        tr, te = R != hold, R == hold
        for k, X in sets.items():
            mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
            b = fit((X[tr] - mu) / sd, y[tr])
            sc[k][te] = ((X[te] - mu) / sd) @ b[1:] + b[0]
    em = ~secw
    idx = np.flatnonzero(em)
    A = {k: auc(sc[k][em], y[em]) for k in sets}
    d = []
    for _ in range(ITERS):
        i = rng.choice(idx, len(idx), replace=True)
        d.append(auc(sc["WHERE+CMT"][i], y[i]) - auc(sc["WHERE"][i], y[i]))
    lo2 = float(np.nanquantile(d, ALPHA))

    def enrich(key):
        top = exp = 0.0
        for hold in REPOS:
            ii = idx[R[idx] == hold]
            k = max(1, int(round(0.10 * len(ii))))
            top += y[ii[np.argsort(-sc[key][ii])][:k]].sum()
            exp += 0.10 * y[ii].sum()
        return top / exp
    silent = (y == 1) & ~secw
    L = ["# CF-H1..H2 — comment changes of fixes; silent-patch detection (SCORED; aggregates only)", "",
         f"- commits {len(rows):,}; CVE {int(y.sum())} (silent {int(silent.sum())}); ordinary (no security words) {int(((y == 0) & ~secw).sum()):,}", "",
         "| claim | result | verdict |", "|---|---|---|",
         f"| **CF-H1** CVE fixes add danger-language comments more than ordinary fixes | adds-danger: CVE {adds_d[y == 1].mean():.1%} vs ordinary {adds_d[y == 0].mean():.1%}; MH RR **{rr1:.2f}** (lo {lo1:.2f}) | **{'SUPPORTED' if rr1 > 1 and lo1 > 1 else 'not supported'}** |",
         f"| **CF-H2** comments add to WHERE for silent patches | AUC WHERE {A['WHERE']:.3f} → WHERE+CMT **{A['WHERE+CMT']:.3f}** ({A['WHERE+CMT'] - A['WHERE']:+.3f}, lo {lo2:+.3f}); CMT alone {A['CMT']:.3f} | **{'SUPPORTED' if A['WHERE+CMT'] > A['WHERE'] and lo2 > 0 else 'not supported'}** |",
         "", "## Descriptive", "",
         f"- adds any comment line: CVE {adds_c[y == 1].mean():.1%} vs ordinary {adds_c[y == 0].mean():.1%}; MH RR {rr_c:.2f}",
         f"- silent CVE fixes that add danger comments: {adds_d[silent].mean():.1%}",
         f"- top-10% enrichment: WHERE {enrich('WHERE'):.2f}×, WHERE+CMT {enrich('WHERE+CMT'):.2f}×",
         "", f"Runtime {time.time() - t0:.0f}s · seed {SEED}."]
    (DOCS_DIR / "cfix.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
