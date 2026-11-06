#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""SRCH-H1..H3: does who finds a CVE set how old the code it fixes is? (docs/srch_hypotheses.md)

    python tools/srch_eval.py --curl-vuln <curl vuln.json>
"""
from __future__ import annotations

import argparse
import glob
import json
import multiprocessing
import pathlib
import random
import re
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from age_eval import fix_age  # noqa: E402

EXTS = {"curl": (".c", ".h"), "openssl": (".c", ".h"), "ndpi": (".c", ".h"),
        "harfbuzz": (".c", ".h", ".cc", ".hh", ".cpp", ".hpp"), "libxml2": (".c", ".h"), "file": (".c", ".h"), "libexif": (".c", ".h")}
NEW_FUZZ = ("libxml2", "file", "libexif")
FUZZ_REGIME = ("ndpi", "harfbuzz", "libxml2", "file", "libexif")
FUZZ_RX = re.compile(r"oss-?fuzz|libfuzzer|fuzz", re.I)
SEED, ITERS, CAP, MIN_N = 2982, 5000, 300, 10
ALPHA = 0.01 / 3
SECJSON = POOL_DIR / "openssl-release-metadata" / "secjson"


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def head_of(r):
    p = REPO_ROOT / "walks" / f"{r}_quarterly.json"
    if p.exists():
        return json.loads(p.read_text())["events_head"]
    return _git(POOL_DIR / r, "rev-parse", "HEAD").strip()


def touched(r, sha):
    return [f for f in _git(POOL_DIR / r, "-c", "core.quotepath=off", "diff-tree", "--no-commit-id", "--name-only", "-r", sha).splitlines()
            if f.endswith(EXTS[r])]


def cves(r, curl_fuzz_ids):
    repo = POOL_DIR / r
    out = []
    credit = {}
    if r == "openssl":
        for f in glob.glob(str(SECJSON / "*.json")):
            j = json.loads(open(f).read())
            credit[j.get("cveMetadata", {}).get("cveId")] = bool(FUZZ_RX.search(json.dumps(j.get("containers", {}).get("cna", {}).get("credits", []))))
    head = head_of(r)
    for e in json.loads((REPO_ROOT / "events" / f"{r}.json").read_text())["events"]:
        if e["class"] != "security-fix" or str(e.get("on_master", True)) == "False":
            continue
        if subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", e["sha"], head]).returncode != 0:
            continue
        ct = _git(repo, "show", "-s", "--format=%ct", e["sha"]).strip()
        files = touched(r, e["sha"])
        if not ct or not files:
            continue
        if r == "openssl":
            src = "fuzzer" if credit.get(e.get("cve")) else "human"
        elif r == "curl":
            src = "fuzzer" if e["id"] in curl_fuzz_ids else "human"
        else:
            src = "fuzzer"  # OSS-Fuzz OSV events
        out.append((r, e["sha"], int(ct), files, src))
    return out


def ordinary(r, exclude):
    repo = POOL_DIR / r
    raw = _git(repo, "-c", "core.quotepath=off", "log", "--no-merges", "--name-only", "--format=%x00%H %ct", head_of(r))
    pool = []
    for chunk in raw.split("\x00")[1:]:
        h, _, rest = chunk.partition("\n")
        sha, ct = h.split()
        files = [f for f in rest.splitlines() if f.strip().endswith(EXTS[r])]
        if 1 <= len(files) <= 50 and sha not in exclude:
            pool.append((r, sha, int(ct), files, "ordinary"))
    rng = random.Random(SEED)
    return rng.sample(sorted(pool), CAP) if len(pool) > CAP else pool


def job(t):
    r, sha, ct, files, src = t
    x = fix_age((r, sha, ct, files))
    return (r, src, x["age"]) if x and x.get("age") is not None else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--curl-vuln", type=pathlib.Path, required=True)
    a = ap.parse_args()
    t0 = time.time()
    vuln = json.loads(a.curl_vuln.read_text())
    curl_fuzz = {v["id"] for v in vuln if FUZZ_RX.search(json.dumps(v.get("credits", [])) + v.get("details", ""))}
    curl_fuzz_ids = {"CURL-" + x for x in curl_fuzz} | curl_fuzz
    tasks = []
    for r in EXTS:
        cv = cves(r, curl_fuzz_ids)
        tasks += cv + ordinary(r, {t[1] for t in cv})
    print(f"{len(tasks)} commits to blame ({time.time() - t0:.0f}s)", flush=True)
    with multiprocessing.get_context("fork").Pool(8) as p:
        res = [x for x in p.imap_unordered(job, tasks, chunksize=4) if x]
    cell = {}
    for r, src, age in res:
        cell.setdefault((r, src), []).append(np.log10(max(age, 0.01)))
    cell = {k: np.array(v) for k, v in cell.items()}
    rng = np.random.default_rng(SEED)
    med = lambda v: float(np.median(v))  # noqa: E731

    def boot_ratio(r, src):
        a_, b_ = cell[(r, src)], cell[(r, "ordinary")]
        return np.array([med(a_[rng.integers(0, len(a_), len(a_))]) - med(b_[rng.integers(0, len(b_), len(b_))]) for _ in range(ITERS)])

    def ok(r, src):
        return len(cell.get((r, src), [])) >= MIN_N and len(cell.get((r, "ordinary"), [])) >= MIN_N

    L = ["# SRCH-H1..H3 — who finds a CVE vs the age of the code it fixes (SCORED)", "",
         f"- curl advisories crediting fuzzing: {sorted(curl_fuzz)}", "",
         "## Per repo (descriptive)", "", "| repo | ordinary commits: median age (n) | CVE fixes, fuzzer-found: age (n), ratio | CVE fixes, human-found: age (n), ratio |",
         "|---|---:|---|---|"]
    for r in EXTS:
        o = cell.get((r, "ordinary"))
        def c(src):
            v = cell.get((r, src))
            return f"{10 ** med(v):,.0f} d ({len(v)}), ×{10 ** (med(v) - med(o)):.2f}" if v is not None and len(v) and o is not None else "—"
        L.append(f"| {r} | {10 ** med(o):,.0f} d ({len(o)}) | {c('fuzzer')} | {c('human')} |")
    # H1
    rs1 = [r for r in NEW_FUZZ if ok(r, "fuzzer")]
    b1 = np.mean([boot_ratio(r, "fuzzer") for r in rs1], axis=0)
    e1 = float(np.mean([med(cell[(r, 'fuzzer')]) - med(cell[(r, 'ordinary')]) for r in rs1]))
    hi1 = float(np.quantile(b1, 1 - ALPHA))
    # H2 (openssl within-repo)
    f2, h2 = cell.get(("openssl", "fuzzer"), np.array([])), cell.get(("openssl", "human"), np.array([]))
    if len(f2) >= MIN_N and len(h2) >= MIN_N:
        b2 = np.array([med(f2[rng.integers(0, len(f2), len(f2))]) - med(h2[rng.integers(0, len(h2), len(h2))]) for _ in range(ITERS)])
        e2, hi2 = med(f2) - med(h2), float(np.quantile(b2, 1 - ALPHA))
        v2 = "SUPPORTED" if e2 < 0 and hi2 < 0 else "not supported"
    else:
        e2, hi2, v2 = float("nan"), float("nan"), f"not evaluable (fuzzer n = {len(f2)})"
    # H3
    fz = [r for r in FUZZ_REGIME if ok(r, "fuzzer")]
    hu = [r for r in ("curl", "openssl") if ok(r, "human")]
    bf = np.mean([boot_ratio(r, "fuzzer") for r in fz], axis=0)
    bh = np.mean([boot_ratio(r, "human") for r in hu], axis=0)
    e3 = float(np.mean([med(cell[(r, 'fuzzer')]) - med(cell[(r, 'ordinary')]) for r in fz]) -
               np.mean([med(cell[(r, 'human')]) - med(cell[(r, 'ordinary')]) for r in hu]))
    hi3 = float(np.quantile(bf - bh, 1 - ALPHA))
    L += ["", "## Claims (log₁₀ ratios; ×factor in brackets)", "", "| claim | repos | effect | upper bound (α = 0.0033) | verdict |", "|---|---|---:|---:|---|",
          f"| **SRCH-H1** fuzzer-found CVE fixes vs ordinary commits (unseen repos) | {', '.join(rs1)} | {e1:+.3f} (×{10 ** e1:.2f}) | {hi1:+.3f} | **{'SUPPORTED' if e1 < 0 and hi1 < 0 else 'not supported'}** |",
          f"| **SRCH-H2** openssl: fuzzer-credited vs human-credited CVE fixes | openssl ({len(f2)} vs {len(h2)}) | {e2:+.3f} (×{10 ** e2:.2f}) | {hi2:+.3f} | **{v2}** |",
          f"| **SRCH-H3** fuzzer-regime ratio − human-regime ratio | fuzzer: {', '.join(fz)}; human: {', '.join(hu)} | {e3:+.3f} (×{10 ** e3:.2f}) | {hi3:+.3f} | **{'SUPPORTED' if e3 < 0 and hi3 < 0 else 'not supported'}** |",
          "", f"Runtime {time.time() - t0:.0f}s · {len(res)} commits measured · bootstrap {ITERS} rounds within repo, seed {SEED}."]
    (DOCS_DIR / "srch.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
