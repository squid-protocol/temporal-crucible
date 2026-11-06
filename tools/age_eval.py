#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""AGE-H1..H4: the age signature of fix classes (docs/age_hypotheses.md, registered 2026-11-06).
Fix age = median (fix committer time - blame committer time) over the parent-side lines the fix deletes or modifies.

    python tools/age_eval.py
"""
from __future__ import annotations

import json
import multiprocessing
import pathlib
import random
import re
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402

EXTS = {"curl": (".c", ".h"), "ndpi": (".c", ".h"), "openssl": (".c", ".h"),
        "harfbuzz": (".c", ".h", ".cc", ".hh", ".cpp", ".hpp")}
REG_REPOS = ("curl", "openssl", "harfbuzz")
CAP, MIN_N, SEED, ITERS, DAY = 300, 30, 2982, 5000, 86400
ALPHA = 0.01 / 4
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+")


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def fix_age(task):
    r, sha, ct, files = task
    repo = POOL_DIR / r
    parent = _git(repo, "rev-parse", "-q", "--verify", f"{sha}^").strip()
    if not parent:
        return None
    ages = []
    present = set(_git(repo, "-c", "core.quotepath=off", "ls-tree", "-r", "--name-only", parent, "--", *files).splitlines())
    for f in files:
        if f not in present:
            continue
        ranges = []
        for line in _git(repo, "-c", "core.quotepath=off", "diff", "-U0", parent, sha, "--", f).splitlines():
            m = HUNK.match(line)
            if m:
                start, n = int(m.group(1)), int(m.group(2) or 1)
                if n > 0:
                    ranges.append((start, n))
        if not ranges:
            continue
        args = []
        for s, n in ranges:
            args += ["-L", f"{s},+{n}"]
        out = _git(repo, "-c", "core.quotepath=off", "blame", "--line-porcelain", *args, parent, "--", f)
        ages += [(ct - int(x.split()[1])) / DAY for x in out.splitlines() if x.startswith("committer-time ")]
    if not ages:
        return {"r": r, "sha": sha, "age": None}
    return {"r": r, "sha": sha, "age": float(np.median(ages)), "n_lines": len(ages)}


def events(r):
    exts = EXTS[r]
    xc = json.loads((REPO_ROOT / "events" / f"{r}_xc.json").read_text())["events"]
    out = defaultdict(list)
    lat = set()
    if r == "harfbuzz":
        repo = POOL_DIR / r
        for e in json.loads((REPO_ROOT / "events" / "harfbuzz.json").read_text())["events"]:
            if e["class"] == "security-fix":
                ct = _git(repo, "show", "-s", "--format=%ct", e["sha"]).strip()
                files = [f for f in _git(repo, "-c", "core.quotepath=off", "diff-tree", "--no-commit-id", "--name-only", "-r",
                                         e["sha"]).splitlines() if f.endswith(exts)]
                if ct and files:
                    out["latent"].append((e["sha"], int(ct), files))
                    lat.add(e["sha"])
    for e in xc:
        if e["sha"] in lat:
            continue
        files = [f for f in e["c_files"] if f.endswith(exts)]
        if not files:
            continue
        k = e["class"]
        if k == "regression":
            k = "regression" if e["why"] == "regression word" else "regression-linked (sanity)"
        out[k].append((e["sha"], e["ct"], files))
    rng = random.Random(SEED)
    return {k: (rng.sample(sorted(v), CAP) if len(v) > CAP else sorted(v)) for k, v in out.items()}


def main() -> int:
    t0 = time.time()
    tasks, label = [], {}
    for r in EXTS:
        for k, evs in events(r).items():
            for sha, ct, files in evs:
                tasks.append((r, sha, ct, files))
                label[(r, sha)] = k
    print(f"{len(tasks)} fixes to blame", flush=True)
    with multiprocessing.get_context("fork").Pool(8) as p:
        res = [x for x in p.imap_unordered(fix_age, tasks, chunksize=4) if x]
    cells, pure = defaultdict(list), defaultdict(lambda: [0, 0])
    for x in res:
        k = label[(x["r"], x["sha"])]
        pure[(x["r"], k)][1] += 1
        if x["age"] is None:
            pure[(x["r"], k)][0] += 1
        else:
            cells[(x["r"], k)].append(np.log10(max(x["age"], 0.01)))
    cells = {k: np.array(v) for k, v in cells.items()}
    rng = np.random.default_rng(SEED)

    def effect(cls, base, repos):
        rs = [r for r in repos if len(cells.get((r, cls), [])) >= MIN_N and len(cells.get((r, base), [])) >= MIN_N]
        if not rs:
            return None
        obs = float(np.mean([np.median(cells[(r, cls)]) - np.median(cells[(r, base)]) for r in rs]))
        b = []
        for _ in range(ITERS):
            v = []
            for r in rs:
                a, c = cells[(r, cls)], cells[(r, base)]
                v.append(np.median(a[rng.integers(0, len(a), len(a))]) - np.median(c[rng.integers(0, len(c), len(c))]))
            b.append(np.mean(v))
        b = np.array(b)
        return {"obs": obs, "repos": rs, "lo": float(np.quantile(b, ALPHA)), "hi": float(np.quantile(b, 1 - ALPHA)),
                "ci90": (float(np.quantile(b, 0.05)), float(np.quantile(b, 0.95)))}

    allr = tuple(EXTS)
    h1 = effect("regression", "other-fix", REG_REPOS)
    h2 = effect("latent", "other-fix", allr)
    h3 = effect("latent", "regression", REG_REPOS)
    h4 = effect("extrinsic", "other-fix", allr)
    eq = float(np.log10(1.5))
    fx = lambda d: f"×{10 ** d['obs']:.2f}"  # noqa: E731
    L = ["# AGE-H1..H4 — the age signature of fix classes (SCORED)", "",
         "Effect = median log₁₀(age of changed lines, days), class minus baseline, within repo, averaged over repos; "
         f"shown also as a factor (×). Bounds at α = {ALPHA}.", "",
         "| claim | repos | effect (log₁₀) | factor | bound | 90% CI | verdict |", "|---|---|---:|---:|---:|---|---|"]
    L.append(f"| **AGE-H1** regression vs generic (younger?) | {', '.join(h1['repos'])} | {h1['obs']:+.3f} | {fx(h1)} | hi {h1['hi']:+.3f} | "
             f"[{h1['ci90'][0]:+.3f}, {h1['ci90'][1]:+.3f}] | **{'SUPPORTED' if h1['obs'] < 0 and h1['hi'] < 0 else 'not supported'}** |")
    L.append(f"| **AGE-H2** CVE vs generic (older?) | {', '.join(h2['repos'])} | {h2['obs']:+.3f} | {fx(h2)} | lo {h2['lo']:+.3f} | "
             f"[{h2['ci90'][0]:+.3f}, {h2['ci90'][1]:+.3f}] | **{'SUPPORTED' if h2['obs'] > 0 and h2['lo'] > 0 else 'not supported'}** |")
    if h3:
        L.append(f"| **AGE-H3** CVE vs regression (older?) | {', '.join(h3['repos'])} | {h3['obs']:+.3f} | {fx(h3)} | lo {h3['lo']:+.3f} | "
                 f"[{h3['ci90'][0]:+.3f}, {h3['ci90'][1]:+.3f}] | **{'SUPPORTED' if h3['obs'] > 0 and h3['lo'] > 0 else 'not supported'}** |")
    else:
        L.append("| **AGE-H3** | — | — | — | — | — | **not evaluable** |")
    L.append(f"| **AGE-H4** extrinsic vs generic (no signature: 90% CI within ×1.5) | {', '.join(h4['repos'])} | {h4['obs']:+.3f} | {fx(h4)} | — | "
             f"[{h4['ci90'][0]:+.3f}, {h4['ci90'][1]:+.3f}] | **{'SUPPORTED (no signature)' if -eq < h4['ci90'][0] and h4['ci90'][1] < eq else 'not supported (has a signature or inconclusive)'}** |")
    L += ["", "## Median age of the changed code, in days (descriptive)", "",
          "| repo | generic | regression (word) | regression-linked (sanity) | CVE (latent) | extrinsic | pure-addition share (generic / CVE) |",
          "|---|---:|---:|---:|---:|---:|---|"]
    for r in EXTS:
        def m(k):
            a = cells.get((r, k))
            return f"{10 ** np.median(a):,.0f} ({len(a)})" if a is not None and len(a) else "—"
        def ps(k):
            v = pure.get((r, k))
            return f"{v[0] / v[1]:.0%}" if v and v[1] else "—"
        L.append(f"| {r} | {m('other-fix')} | {m('regression')} | {m('regression-linked (sanity)')} | {m('latent')} | {m('extrinsic')} | "
                 f"{ps('other-fix')} / {ps('latent')} |")
    L += ["", f"Runtime {time.time() - t0:.0f}s · {len(res)} fixes measured · bootstrap {ITERS} rounds within (repo, class), seed {SEED}."]
    (DOCS_DIR / "age.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
