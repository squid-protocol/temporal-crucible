#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Do AGENT-authored commits label their own fixes more consistently than human ones?

    python tools/agent_vs_human.py --repo <path-to-gitgalaxy> [--resolve N]

Everything measured today says the fix label is unreliable because *announcement is a human convention*:
recall 0.26-0.57 depending on the project, between-author spread larger than between-file spread, and some
contributors who never write "fix" at all. If that diagnosis is right, commits written by an agent under a
documented message convention should behave differently -- and gitgalaxy is a repository whose history is
overwhelmingly agent-authored, with a `Co-Authored-By: Claude` trailer marking them.

Three questions, in increasing order of interest:

1. **Announcement RATE** -- do agent commits use fix words at a different rate? (Weakest: a rate difference
   could just mean agents do different work.)
2. **Announcement VARIANCE** -- tau, the between-author spread, computed within each group. This is the one
   that matters: our whole correction machinery exists because tau is large. If agent tau is near zero while
   human tau is ~0.8, the labelling problem is demonstrably a human-convention problem.
3. **Agreement with GROUND TRUTH** -- for commits citing an issue, is that issue actually a bug? That gives
   precision and recall per group, the same quantities we measured on curl. Requires the forge API, so it is
   opt-in via `--resolve`.

"Agents are consistent" is close to tautological -- they follow instructions. The real question is whether
that consistency makes their commits MORE LEGIBLE to the labelling methods this whole programme depends on,
and therefore whether this problem decays as agents write more code.
"""
from __future__ import annotations

import argparse, json, math, re, statistics as st, subprocess, sys
from pathlib import Path

AGENT = re.compile(r"co-authored-by:\s*claude|generated with \[claude", re.I)
FIXWORD = re.compile(r"\b(fix(es|ed|ing)?|bug|defect|crash|broke(n)?|regress\w*|wrong|incorrect|"
                     r"fail(s|ed|ure)?|repair|resolve[sd]?)\b", re.I)
ISSUE = re.compile(r"(?:part of|fixes|closes|resolves)\s+#(\d{1,6})", re.I)
SEP, EOR = "\x01", "\x02"


def harvest(repo: Path):
    out = subprocess.run(["git", "-C", str(repo), "log", "origin/main", "--no-merges",
                          f"--format={SEP}%H%x1f%an <%ae>%x1f%s%x1f%b{EOR}"],
                         capture_output=True, text=True, errors="replace").stdout
    recs = []
    for blob in out.split(EOR):
        blob = blob.strip("\n")
        if not blob.startswith(SEP):
            continue
        parts = blob[1:].split("\x1f")
        if len(parts) < 4:
            continue
        sha, author, subject, body = parts[0], parts[1], parts[2], parts[3]
        text = subject + "\n" + body
        recs.append({"sha": sha, "author": author, "subject": subject, "body": body,
                     "agent": bool(AGENT.search(text)),
                     "says_fix": bool(FIXWORD.search(subject)),
                     "issues": sorted({m.group(1) for m in ISSUE.finditer(text)})})
    return recs


def tau(groups: dict[str, tuple[int, int]], min_n: int = 15) -> tuple[float, int]:
    g = {k: v for k, v in groups.items() if v[1] >= min_n}
    if len(g) < 5:
        return float("nan"), len(g)
    tot = sum(v[1] for v in g.values())
    pbar = sum(v[0] for v in g.values()) / tot if tot else 0
    if not 0 < pbar < 1:
        return float("nan"), len(g)
    logs = [math.log((k + 0.5) / (n + 1.0)) for k, n in g.values()]
    samp = st.mean([(1 - pbar) / (pbar * n) for _, n in g.values()])
    return math.sqrt(max(0.0, st.pstdev(logs) ** 2 - samp)), len(g)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--resolve", type=int, default=0, help="resolve up to N referenced issues via gh")
    ap.add_argument("--slug", default="squid-protocol/gitgalaxy")
    a = ap.parse_args()
    recs = harvest(a.repo)
    ag = [r for r in recs if r["agent"]]
    hu = [r for r in recs if not r["agent"]]
    print(f"{a.repo.name}: {len(recs):,} non-merge commits on origin/main")
    print(f"  agent-authored (Claude trailer): {len(ag):,} ({len(ag)/max(len(recs),1):.0%})")
    print(f"  human-authored:                  {len(hu):,}\n")

    print(f"  {'group':10}{'commits':>9}{'says fix':>10}{'rate':>8}{'cites issue':>13}")
    for name, g in (("agent", ag), ("human", hu)):
        if not g:
            continue
        sf = sum(r["says_fix"] for r in g)
        ci = sum(1 for r in g if r["issues"])
        print(f"  {name:10}{len(g):>9,}{sf:>10,}{sf/len(g):>8.3f}{ci/len(g):>13.0%}")

    # the measurement that matters: between-author spread WITHIN each group
    print(f"\n  {'group':10}{'authors>=15':>13}{'tau (announcement spread)':>28}")
    for name, g in (("agent", ag), ("human", hu)):
        by: dict[str, tuple[int, int]] = {}
        for r in g:
            k, n = by.get(r["author"], (0, 0))
            by[r["author"]] = (k + (1 if r["says_fix"] else 0), n + 1)
        t, na = tau(by)
        print(f"  {name:10}{na:>13}{(f'{t:.2f}' if t == t else 'n/a (too few authors)'):>28}")

    if a.resolve:
        want = []
        for r in recs:
            for i in r["issues"]:
                want.append((r, i))
        seen: dict[str, dict] = {}
        cache = Path("docs/gg_issue_cache.json")
        if cache.exists():
            seen = json.loads(cache.read_text())
        todo = [i for _r, i in want if i not in seen][:a.resolve]
        for i in dict.fromkeys(todo):
            p = subprocess.run(["gh", "issue", "view", i, "--repo", a.slug, "--json",
                                "number,labels,title"], capture_output=True, text=True)
            if p.returncode == 0:
                try:
                    d = json.loads(p.stdout)
                    seen[i] = {"labels": [x["name"] for x in d.get("labels") or []]}
                except Exception:
                    seen[i] = {"labels": []}
            else:
                seen[i] = {"labels": []}
        cache.write_text(json.dumps(seen, indent=1))
        BUG = re.compile(r"\bbug\b|ci-red|defect", re.I)
        print(f"\n  ground truth from {len(seen):,} resolved issues "
              f"({sum(1 for v in seen.values() if any(BUG.search(l) for l in v['labels']))} labelled a bug)\n")
        print(f"  {'group':10}{'cites a bug issue':>19}{'of those, says fix':>21}{'recall':>9}")
        for name, g in (("agent", ag), ("human", hu)):
            rows = [r for r in g if any(i in seen and any(BUG.search(l) for l in seen[i]["labels"])
                                        for i in r["issues"])]
            if not rows:
                print(f"  {name:10}{0:>19}"); continue
            sf = sum(r["says_fix"] for r in rows)
            print(f"  {name:10}{len(rows):>19,}{sf:>21,}{sf/len(rows):>9.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
