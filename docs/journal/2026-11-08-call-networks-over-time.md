---
date: 2026-11-08
title: How do call networks change over a codebase's life?
type: confirmatory
status: scored
verdict: mixed
theme: natural-history
ids: CGT-1..5
docs: docs/cgt_hypotheses.md; docs/cgt.md
links: gitgalaxy#7533; temporal-crucible#90
takehome: Call networks are static most quarters and change in jumps, but the jumps mostly track code volume; CVE fixes rewire calls more than other fixes (extrinsic fixes least), and rewired files attract more later fixes beyond churn and partly beyond size.
---

<!--
Header fields (one per line, `key: value`; lists use `;`):
  date      the day the entry was opened (registration day for confirmatory work)
  type      confirmatory | exploratory | engine-finding | program
  status    draft | registered | scored | superseded
  verdict   supported | replicated | mixed | not-supported | inconclusive | pending | n/a   (a draft is always pending)
  theme     provenance | coupling | natural-history | defect-prediction | keyword-grammar | fingerprints | comments | engine | program
  ids       register ids exactly as in docs/HYPOTHESES.md's first column, e.g. KWP-H1..H3
  docs      repo paths of the registration and result docs, e.g. docs/kwp_hypotheses.md; docs/kwp.md
  links     issues / PRs, e.g. gitgalaxy#8024; temporal-crucible#85
Then: python tools/journal.py build   (CI runs `check`)
-->

## Question

Do call networks stay static and change in jumps? What do the jumps coincide with: releases, new features? Do fixes,
CVE or regression, change the call graph? Does the call network identify a project across eras?

## Why we asked

WIRE showed the call network is the design layer that survives translation. The owner's hypothesis: networks stay
static and jump when features arrive. Priors: keyword-mix drift comes in spurts (SIG-H2); CVE fixes are surgical,
regression fixes add functions and state (FORT); structure-vs-fixes results usually reduce to churn.

## What we did

Registered in `docs/cgt_hypotheses.md` before any call-network statistic: 390 quarterly snapshots of five C repos,
rewiring among persisting functions vs growth vs churn, release and new-file coincidence, fix-commit scans by class,
file-quarter later-fix test, name-free identification across eras.

## What we found

- **Static, with jumps (✓ 1a, ✓ 1b):** a typical quarter rewires 0.1-1.4% of the edges among functions that persist;
  the busiest tenth of quarters carries 46-77% of all rewiring in four repos (harfbuzz 34%). Networks mostly grow:
  rewiring is about a fifth of growth.
- **Not beyond code volume (✗ 1c):** rewiring is burstier than line churn only in curl and libarchive.
- **No clear coincidence (✗ 2a, ✗ 2b):** release quarters lean higher (p 0.03, bar 0.005); new files do not go with
  rewiring of existing code.
- **Fixes (✗ 3a, ✗ 3b):** regressions 39%, CVE fixes 28%, other fixes 23%, extrinsic 14% add or remove an internal
  call. At equal size CVE fixes rewire *more* than other fixes, the opposite of the registered direction; extrinsic
  fixes are the quiet ones (descriptive).
- **Later fixes (✓ 4):** rewired files get a fix in the next year more often than equally churned files (OR 2.02).
  Post-hoc (exploratory): with file size also controlled, OR 1.34, still far beyond chance.
- **Identity (✓ 5):** 390 of 390 snapshots matched their own project across 5+ years; easy here (keyword mix 99%).

## Take-home

Call networks are mostly static and change in jumps, but the jumps mostly follow code volume. Fixes do change call
graphs (CVE fixes more than other fixes; platform fixes least), and a file whose wiring changed is more likely to
need a fix within a year, beyond churn and partly beyond size.

## What it changed

- First structural signal in this programme to survive churn and (post-hoc) size for later fixes: a lead, not a
  claim, until the recidivism control and an unseen repo (CGT-4R).
- FORT's "CVE fixes are surgical" holds for statements, not for calls.
- Follow-ups: CGT-4R, CGT-3R (unseen repos), CGT-5H (identification among related codebases), CGT-6 (GitGalaxy PRs).
