#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""WH-H1..H3 (docs/silent_hypotheses.md § WH): where (pre-commit location history) + how (change signature) for silent
CVE-fix detection. Aggregates public; candidates private. Engine venv.

    <engine venv>/bin/python tools/wh_eval.py
"""
from __future__ import annotations

import json
import multiprocessing
import pathlib
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402
from chg_eval import CEXT, CPPEXT, fix_events  # noqa: E402
from fort_eval import task as fort_task  # noqa: E402
from fortv_fixk_eval import C_RULES, CPP_RULES, EXCL, RULES  # noqa: E402
from hunk_grammar import parse_diff_sections  # noqa: E402
from silent_eval import REPOS, SEC, auc, fit  # noqa: E402

SEED, ITERS, ALPHA = 2982, 2000, 0.01 / 3
PRIVATE = POOL_DIR / "vz_private" / "wh_candidates.json"


def feat(t):
    r, sha, ct, klass = t
    repo = POOL_DIR / r
    d = subprocess.run(["git", "-C", str(repo), "diff", "-U0", f"{sha}^", sha], capture_output=True)
    if d.returncode != 0:
        return None
    secs = [s for s in parse_diff_sections(d.stdout.decode("utf-8", "replace"))
            if s["path"].endswith(CEXT + CPPEXT) and not s["path"].startswith(EXCL)]
    if not secs:
        return None
    net = dict.fromkeys(RULES, 0)
    nl = 0
    for s in secs:
        rules = C_RULES if s["path"].endswith(CEXT) and r != "harfbuzz" else CPP_RULES
        nl += s["n_added"] + s["n_removed"]
        for k in RULES:
            rk = rules.get(k, C_RULES[k])
            if hasattr(rk, "findall"):
                net[k] += len(rk.findall(s["added_text"])) - len(rk.findall(s["removed_text"]))
    subj = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%s", sha], capture_output=True, text=True, errors="replace").stdout.strip()
    return {"r": r, "sha": sha, "ct": ct, "klass": klass, "subj": subj, "nl": nl, "nf": len(secs), "net": net,
            "files": sorted({s["path"] for s in secs})}


def main() -> int:
    t0 = time.time()
    ev = []
    for r in REPOS:
        e, _ = fix_events(r)
        ev += [x for x in e if x[3] in ("latent", "other-fix")]
    with multiprocessing.get_context("fork").Pool(8) as p:
        rows = [x for x in p.imap_unordered(feat, ev, chunksize=8) if x]
        touches = [u for us in p.imap_unordered(fort_task, ev, chunksize=8) for u in us]
    print(f"commits {len(rows):,}; touches {len(touches):,} ({time.time() - t0:.0f}s)", flush=True)
    g = defaultdict(lambda: [0.0, 0.0])
    for u in touches:
        g[u[1]][0] += u[6]
        g[u[1]][1] += u[5]
    # location history, strictly earlier commits, per repo
    for r in REPOS:
        rr = sorted((x for x in rows if x["r"] == r), key=lambda x: (x["ct"], x["sha"]))
        sec_seen, fix_seen = defaultdict(int), defaultdict(int)
        i = 0
        while i < len(rr):
            j = i
            while j < len(rr) and rr[j]["ct"] == rr[i]["ct"]:
                j += 1
            for x in rr[i:j]:  # same timestamp: none sees the others
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
    size = np.c_[np.log10([max(x["nl"], 1) for x in rows]), np.log10([max(x["nf"], 1) for x in rows])]
    where = np.c_[np.log1p([x["prior_sec"] for x in rows]), [1.0 if x["prior_sec"] > 0 else 0.0 for x in rows],
                  np.log1p([x["prior_fix"] for x in rows]), [x["defended"] for x in rows]]
    how = np.c_[[[1.0 if x["net"][k] >= 1 else 0.0 for k in RULES] for x in rows], [[1.0 if x["net"][k] <= -1 else 0.0 for k in RULES] for x in rows]]
    sets = {"SIZE": size, "WHERE": np.c_[size, where], "HOW": np.c_[how, size], "WHERE+HOW": np.c_[how, size, where]}
    sc = {k: np.full(len(rows), np.nan) for k in sets}
    for hold in REPOS:
        tr, te = R != hold, R == hold
        for k, X in sets.items():
            mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
            b = fit((X[tr] - mu) / sd, y[tr])
            sc[k][te] = ((X[te] - mu) / sd) @ b[1:] + b[0]
    em = ~secw & np.isfinite(sc["SIZE"])
    idx = np.flatnonzero(em)
    A = {k: auc(sc[k][em], y[em]) for k in sets}
    rng = np.random.default_rng(SEED)
    d1, d2 = [], []
    for _ in range(ITERS):
        i = rng.choice(idx, len(idx), replace=True)
        a_wh = auc(sc["WHERE+HOW"][i], y[i])
        d1.append(a_wh - auc(sc["HOW"][i], y[i]))
        d2.append(a_wh - auc(sc["WHERE"][i], y[i]))
    lo1, lo2 = float(np.nanquantile(d1, ALPHA)), float(np.nanquantile(d2, ALPHA))

    def enrich(sel, key, frac=0.10):
        top = exp = 0.0
        for hold in REPOS:
            ii = sel[R[sel] == hold]
            if len(ii) < 20 or y[ii].sum() == 0:
                continue
            k = max(1, int(round(frac * len(ii))))
            top += y[ii[np.argsort(-sc[key][ii])][:k]].sum()
            exp += frac * y[ii].sum()
        return top / exp if exp else float("nan")
    e3 = enrich(idx, "WHERE+HOW")
    be = [enrich(rng.choice(idx, len(idx), replace=True), "WHERE+HOW") for _ in range(ITERS)]
    lo3 = float(np.nanquantile(be, ALPHA))
    base = y[em].mean()
    prec = {}
    for frac in (0.01, 0.05, 0.10):
        tp = n = 0
        for hold in REPOS:
            ii = idx[R[idx] == hold]
            k = max(1, int(round(frac * len(ii))))
            top = ii[np.argsort(-sc["WHERE+HOW"][ii])][:k]
            tp += y[top].sum()
            n += k
        prec[frac] = tp / n
    cands = []
    for hold in REPOS:
        m = em & (R == hold)
        pos = sc["WHERE+HOW"][m & (y == 1)]
        if len(pos):
            thr = np.median(pos)
            cands += [{"repo": rows[i]["r"], "sha": rows[i]["sha"], "subject": rows[i]["subj"], "score": float(sc["WHERE+HOW"][i])}
                      for i in np.flatnonzero(m & (y == 0) & (sc["WHERE+HOW"] > thr))]
    PRIVATE.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE.write_text(json.dumps({"note": "PRIVATE (historical); do not publish", "candidates": sorted(cands, key=lambda c: -c["score"])}, indent=1))
    L = ["# WH-H1..H3 — where + how for silent CVE-fix detection (SCORED; aggregates only)", "",
         f"- commits {len(rows):,}; silent CVE fixes {int(y[em].sum())}; ordinary fixes {int((1 - y[em]).sum()):,}; base rate {base:.2%}", "",
         "| model | held-out AUC |", "|---|---:|"] + [f"| {k} | {v:.3f} |" for k, v in A.items()] + [
         "", "| claim | result | verdict |", "|---|---|---|",
         f"| **WH-H1** location adds to the signature | WHERE+HOW − HOW = {A['WHERE+HOW'] - A['HOW']:+.3f} (lo {lo1:+.3f}) | **{'SUPPORTED' if A['WHERE+HOW'] > A['HOW'] and lo1 > 0 else 'not supported'}** |",
         f"| **WH-H2** the signature adds to location | WHERE+HOW − WHERE = {A['WHERE+HOW'] - A['WHERE']:+.3f} (lo {lo2:+.3f}) | **{'SUPPORTED' if A['WHERE+HOW'] > A['WHERE'] and lo2 > 0 else 'not supported'}** |",
         f"| **WH-H3** usable: top-10% enrichment | **{e3:.2f}×** (lo {lo3:.2f}) | **{'SUPPORTED' if lo3 > 1.5 else 'not supported'}** |",
         "", "Precision in the top fraction (WHERE+HOW) vs base rate " + f"{base:.2%}: " + ", ".join(f"top {int(f * 100)}% {p_:.1%} ({p_ / base:.1f}×)" for f, p_ in prec.items()),
         "", "Per held-out repo AUC (SIZE / WHERE / HOW / WHERE+HOW):"]
    for hold in REPOS:
        m = em & (R == hold)
        L.append(f"- {hold}: " + " / ".join(f"{auc(sc[k][m], y[m]):.3f}" for k in sets))
    L += [f"- unlabelled ordinary fixes above the median silent CVE fix: **{len(cands):,}** (private)", "", f"Runtime {time.time() - t0:.0f}s · seed {SEED}."]
    (DOCS_DIR / "wh.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
