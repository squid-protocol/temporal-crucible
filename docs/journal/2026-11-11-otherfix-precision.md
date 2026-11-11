---
date: 2026-11-11
title: Is a fix-like message actually a fix? (other-fix precision audit)
type: exploratory
status: scored
verdict: n/a
theme: defect-prediction
ids:
docs: docs/otherfix_audit.md
links: temporal-crucible#96
takehome: The never-audited other-fix class carries 85-97% of the outcome mass and was 0.73 precise on C but 0.38 outside it, because Go, Java, Python and Rust projects say "fix" for lint, mypy, javadoc and typos; requiring the fix word in the commit SUBJECT rather than the body, plus test/doc path and refactor/prose exclusions, lifts it to 0.76 pooled and 7 of 8 repos over the gate, and closes the language gap (C 0.75 vs non-C 0.77).
---

# Is a fix-like message actually a fix? (other-fix precision audit)

## Question

`other-fix` is `xc_harvest.py`'s residual class and carries 85-97% of the outcome mass in every repo,
making it the de facto dependent variable of every file-year model in the programme. `xc_label_audit.md`
never covered it. How often is a fix-like message actually a defect fix?

## Why we asked

CEIL found that `other-fix` dominates M1's outcome and is unaudited, and that the non-C half of the CGR
panel realised less of its attainable signal than the C half. CGR's own caveat says its non-C fix labels
rest on unaudited keyword rules.

## What we did

Seeded random sample (seed 2982), 30 `other-fix` events per repo across the 8 CGR repos, judged from the
commit subject against one criterion: does this commit repair behaviour that was wrong? Docs, javadoc,
comments, prose typos, tests-only, lint, style, checkstyle, mypy, type annotations, build, deps,
features, refactors and cosmetic changes count as not a fix. Sampler: `tools/otherfix_sample.py`.

## What we found

- **Precision splits on language, hard.** libxml2 0.80, postgres 0.77, redis 0.73 (PASS); libgit2 0.63,
  sphinx 0.60, prometheus 0.40, commons-lang 0.27, ripgrep 0.27 (FAIL against the 0.70 gate).
- **C pooled 0.733 (3 of 4 pass); non-C pooled 0.383 (0 of 4 pass).** Pooled unweighted 0.558; weighted
  by outcome mass **0.682**, just under the gate.
- **The cause is community vocabulary, not a coding error.** Outside C, "fix" mostly introduces
  non-behavioural change: `fix lint error` and `fix httpNoBody issues from gocritic` (prometheus),
  `[javadoc] Fix ...` and `Fix Checkstyle` (commons-lang), `Fix mypy violations` (sphinx), and `doc: fix
  typo` over and over (ripgrep). A language-blind keyword gate inherits each community's vocabulary.
- Same failure mode and same magnitude as `extrinsic` round 1 (0.30-0.40, FAIL), which rule v2 lifted to
  0.90-1.00 — so the precedent says a tightened rule can fix it.
- `other-fix` is **not** a dumping ground: non-fix-like commits are dropped outright (23,371 in postgres).
  The bucket design is sound; only the gate's precision outside C is the problem.

## Take-home

The residual `other-fix` class carries 85-97% of the outcome mass in every repo and had never been
audited; its precision is 0.73 pooled on C but 0.38 outside C, because Go, Java, Python and Rust projects
say "fix" for lint, mypy, javadoc and typos far more than C projects do.

## Round 2 — the rule, tightened and re-audited

Built `tools/fixlike_v2.py` and scored three rule levels on the 240 round-1 judgments as a development
set, then on a fresh confirmatory sample (seed 2984, 25 per repo, all 480 seen commits excluded):

- **The decisive rule was not the one expected.** Path and prose exclusions (v2, v3) only reached 0.66
  pooled and still failed 5 of 8 repos. What mattered was **requiring the fix word in the commit
  SUBJECT**: v1 matched subject *or body*, so plain feature commits whose body said "fixes #123" were
  kept. That one change (v3c) took pooled precision to **0.761** and put **7 of 8 repos over the gate**.
- **The language gap closed**: C 0.750 vs non-C 0.773, against 0.733 vs 0.383 under v1. Rule C was
  designed on round 1 and tested on a later sample, so this is out-of-sample.
- Cost: 44.6% of events dropped, which is about **22% of real fixes for about 69% of the noise**.
- **The development estimate was optimistic by ~0.17** (0.932 dev vs 0.761 confirmatory) — the rule is
  tuned, so quote 0.761.
- **libgit2 fails all three rounds** (0.63 / 0.60 / 0.60) on build and warning churn that reads like a
  bug fix. Several are cheap regex misses (bare `Fix warnings`, plural `broken tests`, `misspelling`,
  `linting`, `Javadocs`, `PEP8`), deliberately left unfixed so as not to overfit the round-3 test set;
  they are candidate amendment 3 for a fresh round-4 sample.

## What it changed

- **`FIXLIKE` v3c is the rule to use**, written non-destructively to `events/<repo>_xc2.json` so every
  published v1 result stays reproducible.
- The 5-language scope is restored for the seven repos that clear the gate; **libgit2 carries a 0.60
  caveat** and v1-based file-year results should still be quoted C-only until re-run on the v3c events.
- CGR's 5-language replication now rests on a *measured* 0.38-precision outcome outside C. Its
  conclusion probably survives — the non-C network effects were larger, and noise attenuates — but the
  noise is not random (docs, lint and test commits concentrate in doc/test paths and churned files, which
  can inflate churn, author and coupling associations), so the non-C effect sizes are not trustworthy.
- Next: tighten `FIXLIKE` to require a behavioural fix word and exclude docs/test/lint/build/feature
  markers, consider excluding commits touching only test or doc trees, then re-harvest and re-audit.
