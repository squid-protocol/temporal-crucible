#!/usr/bin/env python3
"""AIADOPT (exploratory): is code written with AI help followed by fixes more often?

    python tools/aiadopt_eval.py trend                 # fix-class mix by year, and AI-marker uptake
    python tools/aiadopt_eval.py repos                 # per-repo crude and matched rate ratios
    python tools/aiadopt_eval.py pooled                # one Mantel-Haenszel ratio over every repo

**Exploratory. No verdicts, no registered hypothesis, no p-value is claimed.** It exists to find out
whether the question is answerable with the data already on disk, and what it would take to answer it
properly. Numbers from this tool are not program results and must not be quoted as such.

The exposure is a commit whose message carries an AI trailer (`Co-authored-by: Claude`, Copilot,
`Generated with Claude Code`). That is a FLOOR, not the adoption rate: most AI use leaves no trace,
and whether a trace is left is a project convention -- harfbuzz marks 11% of its commits, curl 0.3%.
Cross-repo comparisons of the raw share therefore measure conventions, not adoption, which is why
`repos` and `pooled` always stratify by repo.

The outcome is: a classed fix commit (tools/xc_harvest.py) touches one of the same files within
WINDOW days. Every commit is required to have a full WINDOW of follow-up, so the comparison is not
decided by how recent a commit is.

Matching, because this program's bar is lift over size and never a raw rate: strata are
repo x commit size (lines changed) x top-level area x breadth (>3 files). A Mantel-Haenszel ratio
pools them, and only cells holding BOTH arms can contribute.

What it cannot do, stated here so no reading of the output forgets it: AI assistance is chosen, not
assigned. If people reach for a tool on the code they already find hairy, the exposure is confounded
by indication and no amount of matching on size fixes that. Treat every number here as descriptive.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import json
import math
import os
import subprocess
import sys
from pathlib import Path

POOL = Path(os.environ.get("TC_POOL", "/srv/storage_16tb/projects/temporal-crucible-pool"))
EVENTS = Path("events")
AI_MARKERS = ("co-authored-by: claude", "copilot", "generated with [claude", "claude code")
WINDOW_DAYS = 90
SINCE = "2024-06-01"          # the exposure window; AI trailers are absent before 2025 in this corpus
TREND_SINCE = "2018-01-01"
REPOS = ("harfbuzz", "openssl", "curl", "ndpi", "redis", "libgit2", "libxml2", "postgres",
         "prometheus", "sphinx", "ripgrep", "commons-lang", "libarchive")


def is_ai(body: str) -> bool:
    low = body.lower()
    return any(m in low for m in AI_MARKERS)


def size_bin(lines: int) -> int:
    return 0 if lines <= 20 else 1 if lines <= 100 else 2 if lines <= 500 else 3


def fix_events(repo: str) -> list[tuple[int, set[str]]]:
    f = EVENTS / f"{repo}_xc.json"
    if not f.exists():
        return []
    d = json.loads(f.read_text())
    ev = d["events"] if isinstance(d, dict) and "events" in d else d
    return sorted(((int(e["ct"]), set(e.get("c_files") or [])) for e in ev if e.get("ct")),
                  key=lambda t: t[0])


def commits(repo: str, since: str = SINCE):
    """(ct, body, files, lines) per non-merge commit, from one git pass."""
    p = POOL / repo
    if not (p / ".git").exists():
        return
    out = subprocess.run(["git", "-C", str(p), "log", f"--since={since}", "--no-merges",
                          "--format=%x00%H%x1f%ct%x1f%b%x1e", "--numstat"],
                         capture_output=True).stdout.decode("utf-8", "replace")
    for chunk in out.split("\x00")[1:]:
        head, _, stat = chunk.partition("\x1e")
        sha, _, rest = head.partition("\x1f")
        ct, _, body = rest.partition("\x1f")
        if not ct.strip().isdigit():
            continue
        files, lines = set(), 0
        for ln in stat.split("\n"):
            parts = ln.split("\t")
            if len(parts) == 3:
                files.add(parts[2])
                for v in parts[:2]:
                    if v.isdigit():
                        lines += int(v)
        if files:
            yield int(ct), body, files, lines


def build_cells(repos, window_days: int = WINDOW_DAYS) -> dict:
    """stratum -> [ai_n, ai_events, plain_n, plain_events]."""
    win = window_days * 86400
    cells: dict = collections.defaultdict(lambda: [0, 0, 0, 0])
    for repo in repos:
        fixes = fix_events(repo)
        if not fixes:
            continue
        rows = list(commits(repo))
        if not rows:
            continue
        head_ct = max(r[0] for r in rows)
        for ct, body, files, lines in rows:
            if ct > head_ct - win:        # not enough follow-up: excluded from BOTH arms
                continue
            hit = any(fct > ct and fct <= ct + win and (ff & files) for fct, ff in fixes)
            cell = cells[(repo, size_bin(lines), sorted(files)[0].split("/")[0], len(files) > 3)]
            if is_ai(body):
                cell[0] += 1
                cell[1] += hit
            else:
                cell[2] += 1
                cell[3] += hit
    return cells


def mantel_haenszel(cells: dict) -> dict:
    """MH rate ratio with a 95% CI. Only cells holding both arms contribute."""
    num = den = varlog = 0.0
    ai = aih = pl = plh = used = 0
    for an, ah, pn, ph in cells.values():
        ai += an
        aih += ah
        pl += pn
        plh += ph
        if an and pn:
            n = an + pn
            num += ah * pn / n
            den += ph * an / n
            varlog += (ah + ph) * an * pn / n ** 2
            used += 1
    if not (num and den):
        return {"ai": ai, "ai_events": aih, "plain": pl, "plain_events": plh, "cells": used,
                "rr": float("nan"), "lo": float("nan"), "hi": float("nan"), "z": float("nan")}
    rr = num / den
    se = math.sqrt(varlog / (num * den))
    return {"ai": ai, "ai_events": aih, "plain": pl, "plain_events": plh, "cells": used, "rr": rr,
            "lo": rr * math.exp(-1.96 * se), "hi": rr * math.exp(1.96 * se),
            "z": math.log(rr) / se if se else float("nan"),
            "crude": (aih / ai) / (plh / pl) if ai and pl and plh else float("nan")}


def cmd_trend(a) -> int:
    rows = collections.defaultdict(collections.Counter)
    for repo in REPOS:
        for e in ({"ct": c, "class": k} for c, k in
                  ((e["ct"], e.get("class")) for e in
                   (json.loads((EVENTS / f"{repo}_xc.json").read_text()).get("events", [])
                    if (EVENTS / f"{repo}_xc.json").exists() else []) if e.get("ct"))):
            y = datetime.datetime.fromtimestamp(int(e["ct"]), datetime.UTC).year
            if 2018 <= y <= 2026:
                rows[y][e["class"]] += 1
                rows[y]["all"] += 1
    ai = collections.Counter()
    tot = collections.Counter()
    for repo in REPOS:
        for ct, body, _f, _l in commits(repo, since=TREND_SINCE):
            y = datetime.datetime.fromtimestamp(ct, datetime.UTC).year
            tot[y] += 1
            ai[y] += is_ai(body)
    print(f"{'year':5} {'fixes':>7} {'latent%':>8} {'regr%':>7} {'extrin%':>8} {'other%':>7} "
          f"{'AI-marked':>10} {'of commits':>11}")
    for y in sorted(rows):
        r = rows[y]
        n = r["all"]
        share = f"{ai[y] / tot[y]:.2%}" if tot[y] else "-"
        print(f"{y:5} {n:7} {r['latent'] / n:8.2%} {r['regression'] / n:7.2%} "
              f"{r['extrinsic'] / n:8.2%} {r['other-fix'] / n:7.2%} {ai[y]:10} {share:>11}")
    return 0


def _line(name: str, m: dict) -> str:
    power = "" if m["ai_events"] >= 20 else "  UNDERPOWERED"
    return (f"{name:13} {m['ai']:5} {m['ai_events']:6} {m['plain']:7} {m.get('crude', float('nan')):6.2f}x "
            f"{m['rr']:7.2f}x [{m['lo']:.2f}, {m['hi']:.2f}] {m['cells']:5}{power}")


def cmd_repos(a) -> int:
    print(f"{'repo':13} {'AI n':>5} {'AI ev':>6} {'plain':>7} {'crude':>7} {'matched':>8} "
          f"{'95% CI':>14} {'cells':>5}")
    for repo in REPOS:
        cells = build_cells([repo], a.window)
        if not cells:
            continue
        m = mantel_haenszel(cells)
        if m["ai"]:
            print(_line(repo, m))
    print(f"\noutcome: a classed fix touches the same files within {a.window} days")
    print("matched on commit size x area x breadth; exploratory, no verdicts")
    return 0


def cmd_pooled(a) -> int:
    m = mantel_haenszel(build_cells(REPOS, a.window))
    print(f"POOLED over {len(REPOS)} repos, Mantel-Haenszel, strata = repo x size x area x breadth")
    print(f"  AI-marked {m['ai']} commits ({m['ai_events']} followed by a fix); "
          f"plain {m['plain']} ({m['plain_events']})")
    print(f"  crude ratio   {m['crude']:.2f}x")
    print(f"  matched RR    {m['rr']:.3f}x  95% CI [{m['lo']:.2f}, {m['hi']:.2f}]  z={m['z']:+.2f}  "
          f"{m['cells']} cells")
    print(f"  reading: {'consistent with no effect' if m['lo'] <= 1 <= m['hi'] else 'excludes 1.0'}"
          f" -- exploratory, and the exposure is chosen rather than assigned")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("step", choices=("trend", "repos", "pooled"))
    ap.add_argument("--window", type=int, default=WINDOW_DAYS, help="follow-up days (default 90)")
    a = ap.parse_args()
    return {"trend": cmd_trend, "repos": cmd_repos, "pooled": cmd_pooled}[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
