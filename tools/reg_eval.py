#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""REG-H1/H2: do regression-inducing commits leave co-change partners untouched? (docs/reg_hypotheses.md)

History-only co-change model over the 730 d before each commit; scores computed before the commit is added.
    python tools/reg_eval.py
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time
from collections import Counter, defaultdict, deque

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from frec_eval import auc  # noqa: E402
from nm_screen import strat_auc  # noqa: E402

REPOS = {"curl": (".c", ".h"), "openssl": (".c", ".h"), "harfbuzz": (".c", ".h", ".cc", ".hh", ".cpp", ".hpp"),
         "ndpi": (".c", ".h")}
DAY, HIST, WIN, BINS, MIN_SUP, MIN_CONF, MIN_POS = 86400, 730, 90, 20, 3, 0.5, 30
SEED, ITERS, ALPHA, EQUIV = 2982, 5000, 0.01 / 2, 0.02


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def commits(repo_name):
    repo = POOL_DIR / repo_name
    head = json.loads((REPO_ROOT / "walks" / f"{repo_name}_quarterly.json").read_text())["events_head"]
    exts = REPOS[repo_name]
    raw = _git(repo, "-c", "core.quotepath=off", "log", "--no-merges", "--reverse", "--numstat", "--format=%x00%H %ct", head)
    out = []
    for chunk in raw.split("\x00")[1:]:
        head_line, _, rest = chunk.partition("\n")
        sha, ct = head_line.split()
        files, size = [], 0
        for ln in rest.splitlines():
            parts = ln.split("\t")
            if len(parts) != 3 or not parts[2].endswith(exts):
                continue
            files.append(parts[2])
            size += (int(parts[0]) if parts[0].isdigit() else 0) + (int(parts[1]) if parts[1].isdigit() else 0)
        if 1 <= len(files) <= 50:
            out.append({"sha": sha, "ct": int(ct), "files": sorted(set(files)), "size": size})
    head_ct = int(_git(repo, "show", "-s", "--format=%ct", head).strip())
    return out, head_ct


def score_repo(repo_name):
    cs, head_ct = commits(repo_name)
    links = json.loads((REPO_ROOT / "events" / f"{repo_name}_reg_links.json").read_text())["links"]
    inducing = {x["inducing"] for x in links if 0 < x["fix_ct"] - x["inducing_ct"] <= WIN * DAY}
    start, end = cs[0]["ct"] + HIST * DAY, head_ct - WIN * DAY
    n_f, n_fg = Counter(), defaultdict(Counter)
    window = deque()
    rows = []
    for c in cs:
        while window and window[0]["ct"] < c["ct"] - HIST * DAY:
            old = window.popleft()
            for f in old["files"]:
                n_f[f] -= 1
                for g in old["files"]:
                    if g != f:
                        n_fg[f][g] -= 1
        if start <= c["ct"] <= end:
            T = set(c["files"])
            cco = deg = 0.0
            for f in T:
                nf = n_f[f]
                if nf <= 0:
                    continue
                for g, k in n_fg[f].items():
                    if k >= MIN_SUP and k / nf >= MIN_CONF:
                        conf = k / nf
                        deg += conf
                        if g not in T:
                            cco += conf
            rows.append((c["size"], len(T), cco / len(T), deg / len(T), 1.0 if c["sha"] in inducing else 0.0))
        window.append(c)
        for f in c["files"]:
            n_f[f] += 1
            for g in c["files"]:
                if g != f:
                    n_fg[f][g] += 1
    return np.array(rows, dtype=float)


def strat_boot(size, sc, ctrl, y, bins, rng):
    n = len(y)
    out = np.empty(ITERS)
    for i in range(ITERS):
        idx = rng.integers(0, n, n)
        a, _ = strat_auc(sc[idx], y[idx], bins[idx])
        b, _ = strat_auc(ctrl[idx], y[idx], bins[idx])
        out[i] = a - b
    return out


def main() -> int:
    t0 = time.time()
    per, boots = {}, {"h1": [], "h2": []}
    spawn = iter(np.random.SeedSequence(SEED).spawn(16))
    for r in REPOS:
        A = score_repo(r)
        size, nfiles, cco, deg, y = A.T
        bins = np.minimum(((np.argsort(np.argsort(size, kind="stable")) * BINS) // len(size)), BINS - 1)
        s_cco, _ = strat_auc(cco, y, bins)
        s_size, _ = strat_auc(size, y, bins)
        s_deg, _ = strat_auc(deg, y, bins)
        d = {"n": len(y), "pos": int(y.sum()), "h1": s_cco - s_size, "h2": s_cco - s_deg,
             "auc_size": auc(size, y), "auc_nfiles": auc(nfiles, y), "auc_cco": auc(cco, y), "auc_deg": auc(deg, y),
             "cco_pos": float((cco[y == 1] > 0).mean()), "cco_neg": float((cco[y == 0] > 0).mean())}
        per[r] = d
        if d["pos"] >= MIN_POS:
            boots["h1"].append(strat_boot(size, cco, size, y, bins, np.random.default_rng(next(spawn))))
            boots["h2"].append(strat_boot(size, cco, deg, y, bins, np.random.default_rng(next(spawn))))
        print(f"{r}: {d['n']} commits, {d['pos']} inducing ({time.time() - t0:.0f}s)", flush=True)
    ev = [r for r in REPOS if per[r]["pos"] >= MIN_POS]
    L = ["# REG-H1 / H2 — co-change omission vs regression-inducing commits (SCORED)", "",
         f"- evaluable repos (≥ {MIN_POS} inducing commits): {', '.join(ev)}; co-change window {HIST} d; strong partner = "
         f"support ≥ {MIN_SUP} and confidence ≥ {MIN_CONF}; {BINS} equal-count commit-size bins", "",
         "| claim | what | pooled mean | lo (α=0.005) | 90% CI | verdict |", "|---|---|---:|---:|---|---|"]
    for c, key, w in (("REG-H1", "h1", "stratAUC(omission) − stratAUC(size)"), ("REG-H2", "h2", "stratAUC(omission) − stratAUC(coupled-files placebo)")):
        mean = float(np.mean([per[r][key] for r in ev]))
        b = np.mean(np.vstack(boots[key]), axis=0)
        lo, ci = float(np.quantile(b, ALPHA)), (float(np.quantile(b, 0.05)), float(np.quantile(b, 0.95)))
        v = ("SUPPORTED" if mean > 0 and lo > 0 else
             "replicated null (equivalence)" if -EQUIV < ci[0] and ci[1] < EQUIV else "not supported (inconclusive)")
        L.append(f"| **{c}** | {w} | {mean:+.3f} | {lo:+.3f} | [{ci[0]:+.3f}, {ci[1]:+.3f}] | **{v}** |")
    shown = all(per[r]["h1"] >= 0 for r in ev)
    L += ["", f"Headline rule extra condition (no evaluable repo's H1 point estimate below 0): {'met' if shown else 'NOT met'}", "",
          "## Per repo (descriptive)", "", "| repo | commits | inducing | H1 | H2 | AUC size | AUC files touched | AUC omission | AUC coupled-files | omission > 0: inducing / others |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r, d in per.items():
        L.append(f"| {r} | {d['n']:,} | {d['pos']} | {d['h1']:+.3f} | {d['h2']:+.3f} | {d['auc_size']:.3f} | {d['auc_nfiles']:.3f} | "
                 f"{d['auc_cco']:.3f} | {d['auc_deg']:.3f} | {d['cco_pos']:.0%} / {d['cco_neg']:.0%} |")
    L += ["", f"Runtime {time.time() - t0:.0f}s · commit bootstrap within repo, {ITERS} rounds, seed {SEED}."]
    (DOCS_DIR / "reg.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
