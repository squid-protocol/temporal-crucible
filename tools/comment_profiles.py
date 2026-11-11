#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Comment profiles of whole files and whole systems (EXPLORATORY, outcome-blind).

For every C/C++ file at every quarterly snapshot (walks/<repo>_quarterly.json), one profile, read from git with the
engine's positional comment stream (CMT-G validated) and rules:
  - code lines; body comment lines (the top-of-file comment banner, i.e. comments before the first code line, is
    counted separately as `banner`);
  - danger lines (DC's lexicon, dc_eval.DANGER); debt lines (TODO / FIXME / HACK / XXX);
  - commented-out code (engine `dead_code` rule; ~93% precise after gitgalaxy#8255, docs/dead_code_panel.md);
  - functions, and functions with a comment block directly above (DC's header walk).
Each distinct blob is profiled once. No fix, CVE or other outcome is read: a later registration can use these
profiles without having seen any outcome.

    GITGALAXY_PATH=$E PYTHONPATH=$E <venv>/bin/python tools/comment_profiles.py --out <scratch> [--repos ...]
    -> <scratch>/comment_profiles.json.gz (rows) and docs/comment_profiles_exploratory.md
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import multiprocessing
import pathlib
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from chg_eval import CEXT, CPPEXT, _fname, _parser  # noqa: E402
from dc_eval import DANGER  # noqa: E402

SEED = 2982
DEFAULT_REPOS = ("curl", "openssl", "ndpi", "harfbuzz", "libarchive")
EXCL = re.compile(r"(^|/)(tests?|docs?|fuzz|fuzzing|scripts|examples?|\.github)/")
DEBT = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
MARK = re.compile(r"[/*\s]")
FEATS = ("density", "danger_share", "debt_kloc", "dead_kloc", "header_cov")
T0 = time.time()
_W = {}


def log(m):
    print(f"[{time.time() - T0:6.0f}s] {m}", flush=True)


def git(repo, *a, text=True):
    p = subprocess.run(["git", "-C", str(repo), *a], capture_output=True)
    return p.stdout.decode("utf-8", "replace") if text else p.stdout


def lang(r, path):
    return "c" if path.endswith(CEXT) and r != "harfbuzz" else "cpp"


def worker():
    if not _W:
        from gitgalaxy.core.prism import Prism
        from gitgalaxy.standards.gitgalaxy_config import LEXICAL_FAMILY_HEURISTICS
        from gitgalaxy.standards.language_standards import LANGUAGE_DEFINITIONS as LD
        _W["prism"] = Prism(LEXICAL_FAMILY_HEURISTICS, LD)
        _W["dead"] = {lg: LD[lg]["rules"]["dead_code"] for lg in ("c", "cpp")}
    return _W


def profile(t):
    r, path, blob = t
    W = worker()
    raw = git(POOL_DIR / r, "cat-file", "-p", blob, text=False)
    if not raw:
        return blob, None
    txt = raw.decode("utf-8", "replace")
    lg = lang(r, path)
    try:
        pos_text = W["prism"].split_positional_comment_stream(txt, lg)
    except Exception:
        return blob, None
    pos, lines = pos_text.split("\n"), txt.split("\n")
    n = len(lines)
    is_c = [i < len(pos) and bool(pos[i].strip()) for i in range(n)]
    # a code line has something left after removing its comment text and comment markers
    is_code = [bool(lines[i].strip()) and (not is_c[i] or MARK.sub("", lines[i]) != MARK.sub("", pos[i]))
               for i in range(n)]
    first_code = next((i for i in range(n) if is_code[i]), n)
    body = [i for i in range(first_code, n) if is_c[i]]
    out = {"code": sum(is_code), "banner": sum(1 for i in range(first_code) if is_c[i]), "comment": len(body),
           "danger": sum(1 for i in body if DANGER.search(pos[i])),
           "debt": sum(1 for i in body if DEBT.search(pos[i])),
           "dead": sum(1 for _ in W["dead"][lg].finditer(pos_text))}
    funcs = hdr = 0
    try:
        stack = [_parser(lg).parse(raw).root_node]
        while stack:
            nd = stack.pop()
            if nd.type == "function_definition":
                if _fname(nd):
                    funcs += 1
                    a = nd.start_point[0]
                    i = a - 1
                    while i >= 0 and not lines[i].strip():
                        i -= 1
                    hdr += i >= 0 and is_c[i] and not is_code[i]
                continue
            stack.extend(nd.children)
    except Exception:
        pass
    out.update(funcs=funcs, headed=int(hdr))
    return blob, out


def snapshots(r):
    revs = json.loads((REPO_ROOT / "walks" / f"{r}_quarterly.json").read_text())["revisions"]
    out, seen = [], set()
    for s in revs:
        if s.get("status", "ok") != "ok" or s["sha"] in seen:
            continue
        seen.add(s["sha"])
        ct = git(POOL_DIR / r, "show", "-s", "--format=%ct", s["sha"]).strip()
        if ct:
            out.append((s["sha"], int(ct)))
    return sorted(out, key=lambda x: x[1])


def tree(t):
    r, sha = t
    files = []
    for ln in git(POOL_DIR / r, "ls-tree", "-r", sha).splitlines():
        meta, path = ln.split("\t", 1)
        if path.endswith(CEXT + CPPEXT) and not EXCL.search(path) and meta.split()[1] == "blob":
            files.append((path, meta.split()[2]))
    return r, sha, files


# ------------------------------------------------------------------ analysis helpers
def rates(p):
    code = max(p["code"], 1)
    return {"density": p["comment"] / code, "danger_share": p["danger"] / max(p["comment"], 1),
            "debt_kloc": 1000 * p["debt"] / code, "dead_kloc": 1000 * p["dead"] / code,
            "header_cov": p["headed"] / p["funcs"] if p["funcs"] else np.nan}


def kmeans(X, k, rng, iters=100, inits=10):
    best = None
    for _ in range(inits):
        C = X[rng.choice(len(X), k, replace=False)]
        for _ in range(iters):
            lab = np.argmin(((X[:, None, :] - C[None]) ** 2).sum(2), 1)
            Cn = np.array([X[lab == j].mean(0) if (lab == j).any() else C[j] for j in range(k)])
            if np.allclose(Cn, C):
                break
            C = Cn
        sse = ((X - C[lab]) ** 2).sum()
        if best is None or sse < best[0]:
            best = (sse, C, lab)
    return best[1], best[2]


def silhouette(X, lab, rng, m=2500):
    idx = rng.choice(len(X), min(m, len(X)), replace=False)
    Xs, ls = X[idx], lab[idx]
    D = np.sqrt(((Xs[:, None, :] - Xs[None]) ** 2).sum(2))
    s = []
    for i in range(len(Xs)):
        same = ls == ls[i]
        same[i] = False
        if not same.any():
            continue
        a = D[i, same].mean()
        b = min(D[i, ls == j].mean() for j in np.unique(ls) if j != ls[i])
        s.append((b - a) / max(a, b))
    return float(np.mean(s))


def year(ct):
    return dt.datetime.fromtimestamp(ct, dt.timezone.utc).year


# ------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--repos", nargs="+", default=list(DEFAULT_REPOS))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    snaps = {r: snapshots(r) for r in a.repos}
    with multiprocessing.get_context("fork").Pool(8) as p:
        trees = list(p.imap_unordered(tree, [(r, s) for r in a.repos for s, _ in snaps[r]], chunksize=4))
    blobs = {}
    for r, sha, files in trees:
        for path, b in files:
            blobs.setdefault(b, (r, path, b))
    log(f"snapshots {sum(len(v) for v in snaps.values())}; file versions {sum(len(f) for *_, f in trees):,}; "
        f"distinct blobs {len(blobs):,}")
    with multiprocessing.get_context("fork").Pool(8) as p:
        prof = dict(p.imap_unordered(profile, list(blobs.values()), chunksize=16))
    log(f"profiled {sum(v is not None for v in prof.values()):,} blobs ({sum(v is None for v in prof.values())} failed)")
    ct_of = {(r, s): c for r in a.repos for s, c in snaps[r]}
    rows = [{"r": r, "sha": sha, "ct": ct_of[(r, sha)], "path": path, **prof[b]}
            for r, sha, files in trees for path, b in files if prof.get(b)]
    with gzip.open(a.out / "comment_profiles.json.gz", "wt") as f:
        json.dump(rows, f)
    log(f"rows {len(rows):,}")

    by = defaultdict(list)
    for x in rows:
        by[(x["r"], x["ct"])].append(x)
    rng = np.random.default_rng(SEED)
    L = ["# Comment profiles of whole files and whole systems (EXPLORATORY)", "",
         "**Status: exploratory, outcome-blind.** No fix, CVE or other outcome was read, so a later registration can "
         "use these profiles. Script: `tools/comment_profiles.py`. C/C++ files only; paths under tests/, docs/, "
         "fuzz/, scripts/, examples/ (at any depth) excluded. Comment lines come from the engine's positional "
         "comment stream (CMT-G: ~99% precise). **Body** comments exclude the top-of-file banner (comments before "
         "the first code line, usually the license).", "",
         f"- repos {', '.join(a.repos)}; quarterly snapshots {sum(len(v) for v in snaps.values())}; file versions "
         f"{len(rows):,}; distinct blobs {len(blobs):,}", "",
         "Measures: **density** = body comment lines ÷ code lines; **danger share** = share of body comment lines "
         "with a DC-lexicon word; **debt** = TODO/FIXME/HACK/XXX lines per 1,000 code lines; **dead** = engine "
         "`dead_code` matches per 1,000 code lines; **header coverage** = share of functions with a comment block "
         "directly above.", "",
         "## 1. Each system over time (whole repo, last snapshot of every 3rd year)", ""]
    for r in a.repos:
        L += [f"**{r}**", "", "| year | files | code lines | density | banner lines / file | danger share | debt / kloc | "
              "dead / kloc | header coverage |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        last_of_year = {}
        for s, c in snaps[r]:
            last_of_year[year(c)] = c
        yrs = sorted(last_of_year)
        pick = yrs[::3] + ([yrs[-1]] if (len(yrs) - 1) % 3 else [])
        for y in pick:
            xs = by[(r, last_of_year[y])]
            if not xs:
                continue
            S = {k: sum(x[k] for x in xs) for k in ("code", "comment", "banner", "danger", "debt", "dead", "funcs",
                                                    "headed")}
            L.append(f"| {y} | {len(xs):,} | {S['code']:,} | {S['comment'] / S['code']:.3f} | "
                     f"{S['banner'] / len(xs):.1f} | {S['danger'] / max(S['comment'], 1):.1%} | "
                     f"{1000 * S['debt'] / S['code']:.2f} | {1000 * S['dead'] / S['code']:.2f} | "
                     f"{S['headed'] / max(S['funcs'], 1):.0%} |")
        L.append("")

    # latest snapshot per repo
    latest = {r: by[(r, snaps[r][-1][1])] for r in a.repos}
    L += ["## 2. Each system's voice at its latest snapshot (per-file medians [IQR], files with ≥ 50 code lines)", "",
          "| repo | files | " + " | ".join(FEATS) + " |", "|---|---:|" + "---|" * len(FEATS)]
    for r in a.repos:
        R = [rates(x) for x in latest[r] if x["code"] >= 50]
        cells = []
        for f in FEATS:
            v = np.array([z[f] for z in R], float)
            v = v[np.isfinite(v)]
            q = np.quantile(v, [0.25, 0.5, 0.75]) if len(v) else [np.nan] * 3
            cells.append(f"{q[1]:.3g} [{q[0]:.3g}, {q[2]:.3g}]")
        L.append(f"| {r} | {len(R):,} | " + " | ".join(cells) + " |")
    L += ["", "Most common danger words in body comments are not listed: the profile counts lines, not words.", "",
          "## 3. How much does each measure depend on file size? (Spearman ρ with log code lines, latest snapshot)", "",
          "| repo | " + " | ".join(FEATS) + " |", "|---|" + "---:|" * len(FEATS)]
    for r in a.repos:
        xs = [x for x in latest[r] if x["code"] >= 50]
        sz = np.log([x["code"] for x in xs])
        R = [rates(x) for x in xs]
        cells = []
        for f in FEATS:
            v = np.array([z[f] for z in R], float)
            ok = np.isfinite(v)
            cells.append(f"{spearmanr(sz[ok], v[ok])[0]:+.2f}" if ok.sum() > 10 else "n/a")
        L.append(f"| {r} | " + " | ".join(cells) + " |")

    # cultures: pooled latest snapshots
    pool = [(r, x) for r in a.repos for x in latest[r] if x["code"] >= 50 and x["funcs"] > 0]
    Z = np.array([[rates(x)[f] for f in FEATS] for _, x in pool], float)
    Zt = np.log1p(np.where(np.isfinite(Z), Z, 0) * np.array([10, 10, 1, 1, 10]))
    mu, sd = Zt.mean(0), Zt.std(0) + 1e-9
    X = (Zt - mu) / sd
    sil = {}
    for k in range(2, 7):
        C, lab = kmeans(X, k, np.random.default_rng(SEED))
        sil[k] = (silhouette(X, lab, np.random.default_rng(SEED)), C, lab)
    kb = max(sil, key=lambda k: sil[k][0])
    s_b, C, lab = sil[kb]
    L += ["", f"## 4. File cultures (k-means on the five rates, log-scaled and standardized; files with ≥ 50 code lines "
          f"and ≥ 1 function at each repo's latest snapshot; n = {len(pool):,})", "",
          "Silhouette by k: " + ", ".join(f"k={k} {v[0]:.2f}" for k, v in sil.items())
          + f". Best k = **{kb}** (silhouette {s_b:.2f}; above ~0.5 is clear structure, ~0.25 weak).", "",
          "| culture | files | median code lines | " + " | ".join(FEATS) + " (medians) | "
          + " | ".join(a.repos) + " |", "|---|---:|---:|" + "---:|" * (len(FEATS) + len(a.repos))]
    order = np.argsort([-np.median(Z[lab == j, 0]) for j in range(kb)])
    for rank, j in enumerate(order):
        m = lab == j
        med = [np.nanmedian(Z[m, i]) for i in range(len(FEATS))]
        reps = [sum(1 for (r, _), mm in zip(pool, m) if mm and r == rr) / max(sum(1 for r, _ in pool if r == rr), 1)
                for rr in a.repos]
        L.append(f"| C{rank + 1} | {int(m.sum()):,} | {int(np.median([x['code'] for (_, x), mm in zip(pool, m) if mm])):,} | "
                 + " | ".join(f"{v:.3g}" for v in med) + " | " + " | ".join(f"{v:.0%}" for v in reps) + " |")
    L += ["", "Repo columns: the share of that repo's files in each culture.", ""]

    # persistence: the same files about 4 years earlier, assigned to the nearest culture centroid
    L += ["## 5. Do files keep their culture? (same path ~4 years before the latest snapshot, nearest centroid)", ""]
    stay, tot = Counter(), Counter()
    cur = {(r, x["path"]): j for (r, x), j in zip(pool, lab)}
    for r in a.repos:
        target = snaps[r][-1][1] - 4 * 365.25 * 86400
        s_old = min(snaps[r], key=lambda s: abs(s[1] - target))
        for x in by[(r, s_old[1])]:
            if (r, x["path"]) not in cur or x["code"] < 50 or not x["funcs"]:
                continue
            z = np.array([rates(x)[f] for f in FEATS], float)
            zt = (np.log1p(np.where(np.isfinite(z), z, 0) * np.array([10, 10, 1, 1, 10])) - mu) / sd
            j_old = int(np.argmin(((C - zt) ** 2).sum(1)))
            tot[r] += 1
            stay[r] += j_old == cur[(r, x["path"])]
    L.append("- same culture then and now: " + ", ".join(f"{r} {stay[r] / tot[r]:.0%} of {tot[r]:,}"
                                                         for r in a.repos if tot[r]))
    base = {r: max(Counter(j for (rr, _), j in zip(pool, lab) if rr == r).values()) /
            max(sum(1 for rr, _ in pool if rr == r), 1) for r in a.repos}
    L.append("- for scale, the share in each repo's largest culture today (a no-information baseline): "
             + ", ".join(f"{r} {base[r]:.0%}" for r in a.repos))

    # neglect: code grows, body comments do not
    L += ["", "## 6. Comment neglect: files whose code grew ≥ 20% in a year while their body comments did not grow", "",
          "| repo | file-years with ≥ 20% code growth | of those, comments flat or shrinking |", "|---|---:|---:|"]
    for r in a.repos:
        last_of_year = {}
        for s, c in snaps[r]:
            last_of_year[year(c)] = c
        yrs = sorted(last_of_year)
        g = flat = 0
        for y0, y1 in zip(yrs, yrs[1:]):
            prev = {x["path"]: x for x in by[(r, last_of_year[y0])]}
            for x in by[(r, last_of_year[y1])]:
                p0 = prev.get(x["path"])
                if p0 and p0["code"] >= 50 and x["code"] >= 1.2 * p0["code"]:
                    g += 1
                    flat += x["comment"] <= p0["comment"]
        L.append(f"| {r} | {g:,} | {flat / g:.0%} |" if g else f"| {r} | 0 | n/a |")
    L += ["", f"Runtime {time.time() - T0:.0f}s · seed {SEED}."]
    (DOCS_DIR / "comment_profiles_exploratory.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
