#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Author-level model of the LABELLING PROCESS -- who announces fixes, and how reliable their messages are.

    python tools/author_model.py --repo curl                 # per-author rates and the tau decomposition
    python tools/author_model.py --repo curl --audit-queue 25  # commits where our label is least trustworthy

**What this models, and what it does not.** It models *announcement behaviour*: the probability that a given
author says "fix" when committing. That is a property of writing habits, and it is exactly what the bias
analysis needs, because `hr1_bias.py` showed the artefact is driven by heterogeneity in announcement
propensity and could only measure the FILE-level part of it.

It does **not** model defect-proneness. "Who writes buggy code" is not identifiable from this data: author
assignment is confounded with subsystem, seniority, era, review intensity and task difficulty, and the only
signal we have for "bug" is the same label whose reliability varies by author. Any such number would measure
the labelling process and get reported as a property of a person, which is the exact error this programme has
spent the day correcting -- with the added problem that it is about people.

Three outputs, all about evidence quality:

1. **Per-author announcement rate** -- labelled-fix share of that author's commits.
2. **The tau decomposition** -- how much announcement spread is between AUTHORS versus between FILES. The
   curl bias analysis used a file-level tau of 0.36 and recorded that the true spread must be higher because
   author variation adds to it. This measures that addition, and the combined figure is what the null should
   be run at.
**Ethics.** Author identities are never printed. Gold & Krinke (EMSE 27:17, 2022) document that repository
*metadata* about named people is the part of MSR work that raises ethics issues most sharply, and that the
community practice is to anonymise and to publish aggregates. In a small project a pseudonymous index is still
re-identifiable from a commit count, so this tool reports the DISTRIBUTION of announcement rates and the
variance components, and nothing that points at a person.

3. **An audit queue** -- commits where the cheap label is least trustworthy, ranked. This is where an
   expensive reader (a human, or a diff-reading model) buys the most information per unit of effort: a
   substantial change by an author who never announces is where our label is most likely wrong.
"""
from __future__ import annotations

import argparse, math, sqlite3, statistics as st, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

STUDY = Path("/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot")


def load(repo: str):
    h = sqlite3.connect(f"file:{STUDY/'history'/f'{repo}.db'}?mode=ro", uri=True)
    rows = list(h.execute("select sha, author, subject, fix, ct from commit_ where merge=0 and bot=0"))
    touch: dict[str, int] = {}
    for sha, in h.execute("select sha from touch"):
        touch[sha] = touch.get(sha, 0) + 1
    h.close()
    strong: set[str] = set()
    m = STUDY / "meta" / f"{repo}.db"
    if m.exists():
        c = sqlite3.connect(f"file:{m}?mode=ro", uri=True)
        for sha, kind in c.execute("select sha, kind from link where kind in ('revert','cve','issue_fix')"):
            strong.add(sha)
        c.close()
    return rows, touch, strong


def spread(groups: dict[str, tuple[int, int]], min_n: int) -> tuple[float, int]:
    """between-group spread of the fix rate, binomial sampling component removed (delta method)"""
    g = {k: v for k, v in groups.items() if v[1] >= min_n}
    if len(g) < 10:
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
    ap.add_argument("--repo", default="curl")
    ap.add_argument("--min-commits", type=int, default=15)
    ap.add_argument("--audit-queue", type=int, default=0)
    a = ap.parse_args()
    rows, touch, strong = load(a.repo)

    by_author: dict[str, tuple[int, int]] = {}
    for sha, author, subj, fix, ct in rows:
        k, n = by_author.get(author, (0, 0))
        by_author[author] = (k + (1 if fix else 0), n + 1)
    tau_a, n_a = spread(by_author, a.min_commits)

    # file-level spread, the figure hr1_bias.py used
    h = sqlite3.connect(f"file:{STUDY/'history'/f'{a.repo}.db'}?mode=ro", uri=True)
    fixset = {s for s, in h.execute("select sha from commit_ where fix=1 and merge=0 and bot=0")}
    byfile: dict[str, tuple[int, int]] = {}
    for path, sha in h.execute("select t.path, t.sha from touch t join commit_ c on c.sha=t.sha "
                               "where c.merge=0 and c.bot=0"):
        k, n = byfile.get(path, (0, 0))
        byfile[path] = (k + (1 if sha in fixset else 0), n + 1)
    h.close()
    tau_f, n_f = spread(byfile, a.min_commits)
    combined = math.sqrt((0 if tau_a != tau_a else tau_a ** 2) + (0 if tau_f != tau_f else tau_f ** 2))

    print(f"{a.repo}: {len(rows):,} commits, {len(by_author):,} authors "
          f"({n_a} with >= {a.min_commits} commits)\n")
    print(f"  announcement spread BETWEEN AUTHORS   tau_author = {tau_a:.2f}   ({n_a} authors)")
    print(f"  announcement spread BETWEEN FILES     tau_file   = {tau_f:.2f}   ({n_f} files)")
    print(f"  combined (independent components)     tau        = {combined:.2f}")
    print(f"  spread between a 90th- and 10th-percentile unit: {math.exp(2*1.2816*combined):.1f}x\n")

    # ETHICS (Gold & Krinke, EMSE 27:17, 2022): this is repository METADATA about named people, and the
    # community standard is to publish aggregate variance components, never author identifiers. A per-repo
    # pseudonymous index is NOT enough on its own -- in a small project, "author with 17 commits who never
    # says fix" is a very short list -- so identities are never printed and only the DISTRIBUTION is shown.
    rates = sorted(k / n for au, (k, n) in by_author.items() if n >= a.min_commits)
    if rates:
        q = lambda f: rates[min(len(rates) - 1, int(f * len(rates)))]
        print(f"  announcement-rate distribution over {len(rates)} authors (no identities, by design):")
        print(f"    min {rates[0]:.2f}   p25 {q(.25):.2f}   median {q(.5):.2f}   p75 {q(.75):.2f}   "
              f"max {rates[-1]:.2f}")
        print(f"    authors who never announce a fix: {sum(1 for r in rates if r == 0)} of {len(rates)}")

    if a.audit_queue:
        rate = {au: (k / n if n else 0) for au, (k, n) in by_author.items()}
        # least-trustworthy first: a substantial change, NOT keyword-labelled, by an author who rarely
        # announces, with no structured evidence either way. That is where a reader learns the most.
        # Rank by UNCERTAINTY, not by size. The first cut of this queue sorted by "most files touched" and
        # surfaced HTTP/3 support and a REUSE-compliance sweep -- large commits that are confidently NOT
        # fixes, so a reader learns nothing. The fixes the label actually misses are small and terse
        # ("urlapi: avoid derefencing a possible NULL pointer", 1 file). So: prefer few files, and push
        # obvious feature work down.
        import re as _re
        FEATURE = _re.compile(r"\b(add(s|ed|ing)?|support|implement\w*|introduc\w+|new |rename|"
                              r"refactor\w*|cleanup|copyright|licen[cs]e|spelling|wording)\b", _re.I)
        cand = []
        for sha, au, subj, fix, ct in rows:
            if fix or sha in strong:
                continue
            nf = touch.get(sha, 0)
            if not 1 <= nf <= 4:                       # the size band the missed fixes actually live in
                continue
            feat = 1 if FEATURE.search(subj or "") else 0
            cand.append((feat, rate.get(au, 0), nf, sha, subj or ""))
        cand.sort(key=lambda x: (x[0], x[1], x[2]))
        cand = [(r, nf, sha, subj) for _f, r, nf, sha, subj in cand]
        print(f"\n  AUDIT QUEUE -- {a.audit_queue} commits where the cheap label is least trustworthy")
        print(f"  (unlabelled, no structured evidence, by authors who seldom announce)\n")
        for r, nf, sha, subj in cand[:a.audit_queue]:
            # the author's rate is shown as context for the ranking; the author is not named
            print(f"    [{r:.2f} announce, {nf:2} files] {sha[:10]} {subj[:82]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
