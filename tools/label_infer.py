#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Inferred fix probability from author habits, anchored on structurally-labelled fixes.

    python tools/label_infer.py --repo curl                 # per-author keyword recall, measured on anchors
    python tools/label_infer.py --repo curl --pools         # where an LLM should sample, and why

**The circularity problem, and the way out.** We cannot estimate "how often does author A say 'fix' when
fixing" from the keyword label itself -- that is the label grading its own homework. But we have fixes
labelled by MECHANISM rather than by prose:

    T1 revert    `This reverts commit <sha>`
    T2 fixref    `Fixes #N` / `Resolves #N`
    T3 cve       a CVE id

Those are ANCHORS. Among an author's anchor fixes, the share the keyword gate ALSO catches is that author's
keyword recall -- measured against a denominator that does not depend on whether they write "fix". That is a
direct, non-circular estimate of announcement propensity.

**Only T1 and T3 are used by default, and measurement showed why.** T2 (`Fixes #N`) contains a fix word, so
the keyword gate catches it partly BY CONSTRUCTION. Measured: on postgres the keyword gate catches 96% of
prose anchors against 44% of mechanism anchors; on curl the gap runs the other way (26% vs 57%, because
curl puts `Fixes #N` in the body where a subject-only gate never sees it). Either way the prose anchor
measures the overlap of two text rules, not recall. `--prose-anchors` enables it for comparison only.

Mechanism anchors are themselves a subpopulation -- reverts and CVE fixes are not typical fixes -- so this
estimates recall ON THAT SUBPOPULATION, not globally.

**Then the inversion.** This is positive-unlabelled learning with a non-constant label frequency (Bekker &
Davis). For an unlabelled commit by author a with recall r_a, the chance it is really a fix rises as r_a
falls: a commit from someone who announces 90% of the time and did not announce is probably not a fix; the
same commit from someone who never announces carries almost no information either way.

    P(fix | not keyword-labelled, author a)  =  p_a (1 - r_a) / (p_a (1 - r_a) + (1 - p_a))

where p_a is the author's underlying fix rate, estimated from the anchors and shrunk toward the repo mean.

**And the sampling pools.** The right place to spend an LLM (or a human) is where uncertainty x volume is
greatest -- not where the label is confidently wrong, and not where it is confidently right.
"""
from __future__ import annotations

import argparse, math, sqlite3, statistics as st
from pathlib import Path

STUDY = Path("/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot")


def gather(repo: str, prose_ok: bool = False):
    h = sqlite3.connect(f"file:{STUDY/'history'/f'{repo}.db'}?mode=ro", uri=True)
    rows = list(h.execute("select sha, author, fix from commit_ where merge=0 and bot=0"))
    h.close()
    anchors: dict[str, str] = {}
    m = STUDY / "meta" / f"{repo}.db"
    if m.exists():
        c = sqlite3.connect(f"file:{m}?mode=ro", uri=True)
        kinds = ("revert", "cve", "issue_fix") if prose_ok else ("revert", "cve")
        for sha, kind in c.execute(
                "select sha, kind from link where kind in ('revert','cve','issue_fix')"):
            if kind not in kinds:
                continue
            if kind in ("revert", "cve") or sha not in anchors:
                anchors[sha] = kind
        c.close()
    return rows, anchors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="curl")
    ap.add_argument("--min-anchors", type=int, default=5)
    ap.add_argument("--pools", action="store_true")
    ap.add_argument("--prose-anchors", action="store_true",
                    help="also use `Fixes #N` as an anchor -- WEAKER: it contains a fix word, so "
                         "the keyword gate partly catches it by construction (postgres 0.96 vs 0.44)")
    a = ap.parse_args()
    rows, anchors = gather(a.repo, a.prose_anchors)

    comp: dict[str, int] = {}
    for k in anchors.values():
        comp[k] = comp.get(k, 0) + 1
    per: dict[str, list[int]] = {}
    tot: dict[str, int] = {}
    for sha, author, fix in rows:
        tot[author] = tot.get(author, 0) + 1
        if sha in anchors:
            per.setdefault(author, []).append(1 if fix else 0)

    usable = {au: v for au, v in per.items() if len(v) >= a.min_anchors}
    pooled_r = (sum(sum(v) for v in per.values()) / sum(len(v) for v in per.values())) if per else 0.0
    print(f"{a.repo}: {len(rows):,} commits, {len(anchors):,} anchor fixes "
          f"({', '.join(f'{k} {v:,}' for k, v in sorted(comp.items()))})")
    print(f"  mechanism-only anchors (revert+cve): {comp.get('revert',0)+comp.get('cve',0):,}"
          f"   prose anchor (issue_fix): {comp.get('issue_fix',0):,}")
    print(f"  pooled keyword recall measured on anchors: {pooled_r:.3f}")
    print(f"  authors with >= {a.min_anchors} anchors: {len(usable)}\n")

    if usable:
        # James-Stein style shrinkage toward the pooled rate; an author with few anchors moves little
        K = 10.0
        est = {au: (sum(v) + K * pooled_r) / (len(v) + K) for au, v in usable.items()}
        vals = sorted(est.values())
        q = lambda f: vals[min(len(vals) - 1, int(f * len(vals)))]
        print("  per-author keyword recall, shrunk toward the pooled rate (no identities):")
        print(f"    min {vals[0]:.2f}   p25 {q(.25):.2f}   median {q(.5):.2f}   p75 {q(.75):.2f}   "
              f"max {vals[-1]:.2f}")
        raw = sorted(sum(v) / len(v) for v in usable.values())
        print(f"    (unshrunk spread was {raw[0]:.2f} to {raw[-1]:.2f} -- shrinkage is doing real work)")

    if a.pools:
        # Inferred P(fix) for UNLABELLED commits, by the author's measured recall
        print("\n  WHERE TO SAMPLE -- unlabelled commits, bucketed by the author's measured recall\n")
        print(f"    {'author recall band':24}{'unlabelled commits':>20}{'inferred P(fix)':>18}  priority")
        band_rows: dict[str, list[int]] = {}
        p_rate = {au: (sum(v) / len(v) if v else pooled_r) for au, v in per.items()}
        base = sum(1 for _s, _a, f in rows if f) / max(len(rows), 1)
        for sha, author, fix in rows:
            if fix or sha in anchors:
                continue
            r = None
            if author in usable:
                r = (sum(per[author]) + 10.0 * pooled_r) / (len(per[author]) + 10.0)
            band = ("unknown (too few anchors)" if r is None else
                    "recall < 0.20" if r < 0.20 else
                    "recall 0.20-0.40" if r < 0.40 else
                    "recall 0.40-0.60" if r < 0.60 else "recall >= 0.60")
            band_rows.setdefault(band, []).append(1)
        order = ["recall < 0.20", "recall 0.20-0.40", "recall 0.40-0.60", "recall >= 0.60",
                 "unknown (too few anchors)"]
        for band in order:
            n = len(band_rows.get(band, []))
            if not n:
                continue
            r_mid = {"recall < 0.20": 0.10, "recall 0.20-0.40": 0.30, "recall 0.40-0.60": 0.50,
                     "recall >= 0.60": 0.75}.get(band)
            if r_mid is None:
                pf, pri = None, "measure first"
            else:
                pf = base * (1 - r_mid) / (base * (1 - r_mid) + (1 - base))
                pri = ("HIGHEST -- many commits, label least informative" if r_mid <= 0.2
                       else "high" if r_mid <= 0.4 else "low -- label is already informative here")
            print(f"    {band:24}{n:>20,}{(f'{pf:.3f}' if pf is not None else '   --   '):>18}  {pri}")
        print(f"\n    base rate (keyword-labelled share of all commits): {base:.3f}")
        print("    P(fix) is for a commit the keyword gate did NOT label; it rises as the author's")
        print("    recall falls, because a non-announcement from a non-announcer carries little evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
