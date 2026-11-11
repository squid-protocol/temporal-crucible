#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""ARG (docs/arg_hypotheses.md): are declared-AI commits named as the cause of a later fix more often than the same
authors' other commits? A living study: re-run whenever the repos are fetched; each run adds the commits whose
follow-up window has closed. Plain git + numpy (no engine):

    python tools/ai_regress.py [--look N]          # -> docs/arg.md (verdict at a scheduled look, tracker always)

Repos and their checkouts are frozen in events/arg_repos.json. A commit is **named as a cause** when a later commit
- reverts it ("This reverts commit <sha>"), or
- names it in a `Fixes: <sha>` trailer, or
- says it regressed / was introduced / broken / caused in / by / since / from <sha>,
within WINDOW days of it. Declared AI uses tools/ai_comments.tool_of.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, REPO_ROOT  # noqa: E402
from ai_comments import tool_of  # noqa: E402

WINDOW = 180 * 86400
SEED, ITERS = 2982, 2000
LOOKS = {1: ("2026-11-11", 0.002), 2: ("2027-05-11", 0.003), 3: ("2027-11-11", 0.005)}
MIN_EV = 20
NULL_BAND = (0.8, 1.25)
SIZE_EDGES = (10, 50, 200, 1000)
LINK = re.compile(r"This reverts commit ([0-9a-f]{7,40})|^\s*Fixes:\s*([0-9a-f]{7,40})|"
                  r"(?:regress\w*|introduced|broken|caused)\s+(?:in|by|since|from|with)\s+(?:commit\s+)?([0-9a-f]{7,40})",
                  re.I | re.M)
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:6.0f}s] {m}", flush=True)


def git(path, *a, inp=None):
    return subprocess.run(["git", "-C", str(path), *a], capture_output=True, input=inp).stdout.decode("utf-8", "replace")


def load(name, path, since):
    """Commits since `since` (and every later commit as a potential linker)."""
    recs = git(path, "log", "--no-merges", f"--since={since}", "--numstat",
               "--format=%x1e%H%x1f%ct%x1f%ae%x1f%B%x1d").split("\x1e")[1:]
    C = []
    for rec in recs:
        head, _, stat = rec.partition("\x1d")
        h, ct, ae, msg = head.split("\x1f", 3)
        lines = 0
        for ln in stat.strip().splitlines():
            p = ln.split("\t")
            if len(p) == 3 and p[0].isdigit() and p[1].isdigit():
                lines += int(p[0]) + int(p[1])
        C.append({"r": name, "sha": h, "ct": int(ct), "author": ae.strip().lower(), "tool": tool_of(msg),
                  "lines": lines, "refs": [x for m in LINK.finditer(msg) for x in m.groups() if x]})
    # resolve referenced shas to full commit ids in one batch
    refs = sorted({x for c in C for x in c["refs"]})
    full = {}
    if refs:
        out = git(path, "cat-file", "--batch-check=%(objectname) %(objecttype)", inp=("\n".join(refs) + "\n").encode())
        for ref, ln in zip(refs, out.splitlines()):
            parts = ln.split()
            if len(parts) == 2 and parts[1] == "commit":
                full[ref] = parts[0]
    named = defaultdict(list)
    for c in C:
        for x in c["refs"]:
            if x in full and full[x] != c["sha"]:
                named[full[x]].append(c["ct"])
    for c in C:
        c["named_at"] = sorted(t for t in named.get(c["sha"], []) if t > c["ct"])
    return C


def sbin(n):
    return sum(n > e for e in SIZE_EDGES)


def mh_rr(e, y, si, ns):
    a, b = np.bincount(si, y * e, ns), np.bincount(si, y * (1 - e), ns)
    n1, n0 = np.bincount(si, e, ns), np.bincount(si, 1 - e, ns)
    N = n1 + n0
    ok = (n1 > 0) & (n0 > 0)
    den = np.sum(b[ok] * n1[ok] / N[ok])
    return np.sum(a[ok] * n0[ok] / N[ok]) / den if den > 0 else np.nan


def analyse(U, alpha, rng):
    e = np.array([bool(u["tool"]) for u in U], float)
    y = np.array([u["y"] for u in U], float)
    _, si = np.unique([f"{u['r']}|{u['author']}|{sbin(u['lines'])}" for u in U], return_inverse=True)
    ns = int(si.max()) + 1 if len(si) else 0
    rr = mh_rr(e, y, si, ns)
    cl = np.array([f"{u['r']}|{u['author']}" for u in U])
    _, ci = np.unique(cl, return_inverse=True)
    order = np.argsort(ci, kind="stable")
    groups = np.split(order, np.flatnonzero(np.diff(ci[order])) + 1)
    bs = []
    for _ in range(ITERS):
        pk = np.concatenate([groups[j] for j in rng.integers(0, len(groups), len(groups))])
        bs.append(mh_rr(e[pk], y[pk], si[pk], ns))
    bs = np.array(bs, float)
    bs = bs[np.isfinite(bs) & (bs > 0)]
    lo, hi = (float(np.quantile(bs, alpha / 2)), float(np.quantile(bs, 1 - alpha / 2))) if len(bs) > 100 else (np.nan, np.nan)
    # informative strata: author x size cells with both AI and other commits
    inf = set(si[e == 1]) & set(si[e == 0])
    m = np.isin(si, list(inf))
    return {"rr": rr, "lo": lo, "hi": hi, "n_ai": int(e.sum()), "n_other": int((1 - e).sum()),
            "ev_ai": int((e * y).sum()), "ev_other": int(((1 - e) * y).sum()),
            "ev_ai_inf": int((e * y * m).sum()), "rate_ai": y[e == 1].mean() if e.sum() else np.nan,
            "rate_other": y[e == 0].mean() if (1 - e).sum() else np.nan}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--look", type=int, choices=sorted(LOOKS), help="score a scheduled look (default: tracker only)")
    ap.add_argument("--fetch", action="store_true", help="git fetch every repo before reading it")
    a = ap.parse_args()
    cfg = json.loads((REPO_ROOT / "events" / "arg_repos.json").read_text())
    U, heads, ends = [], {}, {}
    groups = {"primary": "ARG-1", "secondary": "ARG-2"}
    for spec in [dict(x, group=g) for g in groups for x in cfg[g]]:
        name, path = spec["name"], pathlib.Path(spec["path"])
        if a.fetch:
            subprocess.run(["git", "-C", str(path), "fetch", "-q", "origin", "+refs/heads/*:refs/heads/*"],
                           capture_output=True, timeout=3600)
        C = load(name, path, cfg["since"])
        heads[name] = git(path, "rev-parse", "--short=12", "HEAD").strip()
        end = max(c["ct"] for c in C)
        ends[name] = end
        first_ai = min((c["ct"] for c in C if c["tool"]), default=None)
        n0 = len(U)
        for c in C:
            if first_ai is None or c["ct"] < first_ai or c["ct"] + WINDOW > end:
                continue
            c["y"] = any(t <= c["ct"] + WINDOW for t in c["named_at"])
            c["set"] = spec["group"]
            U.append(c)
        log(f"{name}: commits {len(C):,}; eligible (AI era, full {WINDOW // 86400}-day window) {len(U) - n0:,}; "
            f"AI {sum(1 for c in U[n0:] if c['tool']):,}; named as cause {sum(1 for c in U[n0:] if c['y']):,}")
    look = a.look
    alpha = LOOKS[look][1] if look else 0.01
    L = ["# ARG — are declared-AI commits named as the cause of later fixes more often? (living study)", "",
         f"Registration `docs/arg_hypotheses.md`. Run {dt.datetime.now(dt.timezone.utc).date()}; "
         + ("**scheduled look %d** (two-sided α = %g)" % (look, alpha) if look else "**tracker run, not a scheduled look**")
         + f". Window {WINDOW // 86400} days; author-cluster bootstrap {ITERS}, seed {SEED}. Aggregates only.", "",
         "- repo heads: " + ", ".join(f"{k} `{v}` (data to {dt.datetime.fromtimestamp(ends[k], dt.timezone.utc).date()})"
                                       for k, v in heads.items()), "",
         "## Registered claims (pooled MH risk ratio, strata repo × author × commit size)", "",
         "| id | repos | AI commits (named) | other commits (named) | rate AI / other | RR (within author, size-matched) | "
         f"{100 * (1 - alpha):.1f}% CI | AI events in informative strata | call |", "|---|---|---|---|---|---:|---|---:|---|"]
    for g, cid in groups.items():
        P = [u for u in U if u["set"] == g]
        if not P:
            continue
        res = analyse(P, alpha, np.random.default_rng(SEED))
        if not look:
            call = "tracker run (no verdict)"
        elif res["ev_ai_inf"] < MIN_EV:
            call = "underpowered at this look"
        elif res["lo"] > 1:
            call = "SUPPORTED: named MORE often (final)"
        elif res["hi"] < 1:
            call = "SUPPORTED: named LESS often (final)"
        elif look == 3 and NULL_BAND[0] <= res["lo"] and res["hi"] <= NULL_BAND[1]:
            call = "not supported: no meaningful difference (final)"
        elif look == 3:
            call = "not supported: inconclusive (final)"
        else:
            call = "no verdict yet: continue to the next look"
        L.append(f"| **{cid}** | {g} | {res['n_ai']:,} ({res['ev_ai']}) | {res['n_other']:,} ({res['ev_other']}) | "
                 f"{res['rate_ai']:.2%} / {res['rate_other']:.2%} | **{res['rr']:.2f}** | [{res['lo']:.2f}, {res['hi']:.2f}] | "
                 f"{res['ev_ai_inf']} | **{call}** |")
    L.append("")
    L += ["## Tracker (descriptive, every run)", "",
          "| repo | AI-era commits eligible | AI | named as cause: AI / other | rate AI / other | RR (within author, "
          "size-matched) |", "|---|---:|---:|---|---|---:|"]
    for name in heads:
        R = [u for u in U if u["r"] == name]
        if not R:
            L.append(f"| {name} | 0 | | | | |")
            continue
        x = analyse(R, 0.05, np.random.default_rng(SEED))
        L.append(f"| {name} ({R[0]['set']}) | {len(R):,} | {x['n_ai']:,} | "
                 f"{x['ev_ai']} / {x['ev_other']} | {x['rate_ai']:.2%} / {x['rate_other']:.2%} | {x['rr']:.2f} "
                 f"[{x['lo']:.2f}, {x['hi']:.2f}] |")
    tools = Counter(u["tool"] for u in U if u["tool"])
    L += ["", "- by tool (all repos, raw rate named as cause): " + ", ".join(
        f"{t} {np.mean([u['y'] for u in U if u['tool'] == t]):.2%} of {n:,}" for t, n in tools.most_common()),
        "- rates are per commit within the window; CIs in the tracker are 95% and not for verdicts", "",
        f"Runtime {time.time() - T0:.0f}s."]
    out = DOCS_DIR / "arg.md"
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
