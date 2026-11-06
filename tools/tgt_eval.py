#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""TGT-H1..H3: does the named platform's conditional density find the files its fix touches?
(docs/tgt_hypotheses.md, registered 2026-11-06)

    python tools/tgt_eval.py
"""
from __future__ import annotations

import json
import multiprocessing
import pathlib
import re
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).parent / "exploratory"))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from frec_eval import auc  # noqa: E402
from xc_envcond import PATTERNS  # noqa: E402

REPOS = {"curl": (".c", ".h"), "ndpi": (".c", ".h"), "openssl": (".c", ".h"),
         "harfbuzz": (".c", ".h", ".cc", ".hh", ".cpp", ".hpp"), "libarchive": (".c", ".h")}
FAMILIES = {  # family: (subject regex, macro regex) -- registered table, verbatim
    "windows": (r"windows|win32|win64|wince|mingw|cygwin|msys|msvc|visual studio|uwp",
                r"_WIN32|WIN32|_WIN64|_WIN32_WINNT|_WIN32_WCE|_MSC_VER|__MINGW32__|__MINGW64__|__CYGWIN__|WINAPI_FAMILY"),
    "apple": (r"macos|mac os|osx|darwin|apple|ios|xcode", r"__APPLE__|__MACH__|TARGET_OS_\w+"),
    "bsd": (r"freebsd|netbsd|openbsd|dragonfly", r"__FreeBSD__|__NetBSD__|__OpenBSD__|__DragonFly__"),
    "solaris": (r"solaris|illumos|sunos", r"__sun|__sun__|__SVR4"),
    "aix": (r"aix", r"_AIX"),
    "hpux": (r"hp-ux|hpux", r"__hpux"),
    "vms": (r"vms|openvms", r"__VMS"),
    "android": (r"android", r"__ANDROID__"),
    "gcc": (r"gcc", r"__GNUC__|__GNUC_MINOR__"),
    "clang": (r"clang", r"__clang__|__clang_major__"),
}
COND = r"^\s*#\s*(?:if|ifdef|ifndef|elif)\b.*"
SUBJ = {f: re.compile(rf"\b(?:{s})\b", re.I) for f, (s, _) in FAMILIES.items()}
MAC = {f: re.compile(rf"\b(?:{m})\b") for f, (_, m) in FAMILIES.items()}
P_RE = re.compile(PATTERNS["P"])
FAM_GREP = COND + r"\b(?:" + "|".join(m for _, m in FAMILIES.values()) + r")\b"
SEED, ITERS, ALPHA, MIN_N, EQUIV = 2982, 5000, 0.01 / 3, 30, 0.02


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def one(task):
    repo_name, exts, e, fam, pool_fams = task
    repo = POOL_DIR / repo_name
    parent = _git(repo, "rev-parse", "--verify", "-q", f"{e['sha']}^").strip()
    if not parent:
        return None
    globs = [f"*{x}" for x in exts]
    files = [p for p in _git(repo, "-c", "core.quotepath=off", "ls-tree", "-r", "--name-only", parent).splitlines()
             if p.endswith(exts)]
    if len(files) < 2:
        return None
    lines = {}
    for ln in _git(repo, "-c", "core.quotepath=off", "grep", "-c", "", parent, "--", *globs).splitlines():
        _, _, rest = ln.partition(":")
        p, _, n = rest.rpartition(":")
        if n.isdigit():
            lines[p] = int(n)
    fam_c = {f: defaultdict(int) for f in pool_fams}
    p_c = defaultdict(int)
    out = _git(repo, "-c", "core.quotepath=off", "grep", "-n", "--null", "-P", "-e", PATTERNS["P"], "-e", FAM_GREP,
               parent, "--", *globs)
    # with --null the output is "<rev>:<path>\0<lineno>\0<text>"
    for rec in out.splitlines():
        parts = rec.split("\0")
        if len(parts) < 3:
            continue
        path = parts[0].split(":", 1)[1] if ":" in parts[0] else parts[0]
        text = parts[2]
        if P_RE.search(text):
            p_c[path] += 1
        for f in pool_fams:
            if re.search(COND, text) and MAC[f].search(text):
                fam_c[f][path] += 1
    touched = set(e["c_files"])
    y = np.array([1.0 if p in touched else 0.0 for p in files])
    if y.sum() == 0 or y.sum() == len(y):
        return None
    loc = np.array([float(max(lines.get(p, 0), 1)) for p in files])
    s = {f: np.array([fam_c[f].get(p, 0) for p in files], dtype=float) / loc for f in pool_fams}
    sp = np.array([p_c.get(p, 0) for p in files], dtype=float) / loc
    a_f, a_p, a_size = auc(s[fam], y), auc(sp, y), auc(loc, y)
    others = [auc(s[g], y) for g in pool_fams if g != fam]
    k = max(1, int(round(0.10 * len(files))))
    top = set(np.argsort(-s[fam], kind="stable")[:k])
    all_top = all(i in top for i in np.flatnonzero(y))
    return {"repo": repo_name, "sha": e["sha"], "family": fam, "n": len(files), "pos": int(y.sum()),
            "h1": a_f - a_p, "h2": a_f - a_size, "h3": a_f - float(np.mean(others)) if others else float("nan"),
            "auc_f": a_f, "auc_p": a_p, "auc_size": a_size, "all_top10": all_top}


def main() -> int:
    t0 = time.time()
    tasks_raw = []
    for r, exts in REPOS.items():
        for e in json.loads((REPO_ROOT / "events" / f"{r}_xc.json").read_text())["events"]:
            if e["class"] != "extrinsic":
                continue
            fams = [f for f, rx in SUBJ.items() if rx.search(e["subject"])]
            if len(fams) == 1:
                tasks_raw.append((r, exts, e, fams[0]))
    pool_fams = sorted({t[3] for t in tasks_raw})
    tasks = [(r, exts, e, f, pool_fams) for r, exts, e, f in tasks_raw]
    print(f"{len(tasks)} single-family extrinsic commits; families {pool_fams}", flush=True)
    with multiprocessing.get_context("fork").Pool(6) as p:
        res = [x for x in p.imap_unordered(one, tasks, chunksize=4) if x]
    print(f"{len(res)} qualifying ({time.time() - t0:.0f}s)", flush=True)

    rng_seq = iter(np.random.SeedSequence(SEED).spawn(4))
    by_repo = defaultdict(list)
    for x in res:
        by_repo[x["repo"]].append(x)
    L = ["# TGT-H1..H3 — targeted platform coupling (SCORED)", "",
         f"- {len(tasks)} extrinsic commits naming exactly one platform family; **{len(res)} qualify** (≥ 1 touched and ≥ 1 untouched candidate in the parent tree)",
         f"- families in the pool: {', '.join(pool_fams)}", "",
         "| claim | what | n | mean | lo (α=0.0033) | 90% CI | verdict |", "|---|---|---:|---:|---:|---|---|"]
    what = {"h1": "named platform − generic measure (AUC)", "h2": "named platform − size (AUC)",
            "h3": "named platform − wrong platforms (AUC)"}
    for c, key in (("TGT-H1", "h1"), ("TGT-H2", "h2"), ("TGT-H3", "h3")):
        groups = {r: np.array([x[key] for x in xs if not np.isnan(x[key])]) for r, xs in by_repo.items()}
        allx = np.concatenate([g for g in groups.values() if len(g)])
        rng = np.random.default_rng(next(rng_seq))
        if len(allx) < MIN_N:
            L.append(f"| **{c}** | {what[key]} | {len(allx)} | {allx.mean():+.3f} | — | — | **not evaluable** |")
            continue
        boots = np.empty(ITERS)
        for i in range(ITERS):
            boots[i] = np.concatenate([g[rng.integers(0, len(g), len(g))] for g in groups.values() if len(g)]).mean()
        lo, ci = float(np.quantile(boots, ALPHA)), (float(np.quantile(boots, 0.05)), float(np.quantile(boots, 0.95)))
        v = ("SUPPORTED" if allx.mean() > 0 and lo > 0 else
             "replicated null (equivalence)" if -EQUIV < ci[0] and ci[1] < EQUIV else "not supported (inconclusive)")
        L.append(f"| **{c}** | {what[key]} | {len(allx)} | {allx.mean():+.3f} | {lo:+.3f} | [{ci[0]:+.3f}, {ci[1]:+.3f}] | **{v}** |")
    L += ["", "## Descriptive", "", "| repo | commits | AUC named | AUC generic | AUC size | all touched files in top 10% by named |",
          "|---|---:|---:|---:|---:|---:|"]
    for r, xs in by_repo.items():
        L.append(f"| {r} | {len(xs)} | {np.mean([x['auc_f'] for x in xs]):.3f} | {np.mean([x['auc_p'] for x in xs]):.3f} | "
                 f"{np.mean([x['auc_size'] for x in xs]):.3f} | {np.mean([x['all_top10'] for x in xs]):.0%} |")
    fams = defaultdict(list)
    for x in res:
        fams[x["family"]].append(x)
    L += ["", "| family | commits | AUC named | AUC generic | AUC size | named − wrong platforms |", "|---|---:|---:|---:|---:|---:|"]
    for f, xs in sorted(fams.items(), key=lambda kv: -len(kv[1])):
        L.append(f"| {f} | {len(xs)} | {np.mean([x['auc_f'] for x in xs]):.3f} | {np.mean([x['auc_p'] for x in xs]):.3f} | "
                 f"{np.mean([x['auc_size'] for x in xs]):.3f} | {np.nanmean([x['h3'] for x in xs]):+.3f} |")
    L += ["", f"Runtime {time.time() - t0:.0f}s · stratified commit bootstrap, {ITERS} rounds, seed {SEED}."]
    (DOCS_DIR / "tgt.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
