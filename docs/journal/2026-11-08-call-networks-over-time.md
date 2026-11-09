---
date: 2026-11-08
title: How do call networks change over a codebase's life?
type: confirmatory
status: registered
verdict: pending
theme: natural-history
ids: CGT-1..5
docs: docs/cgt_hypotheses.md
links: gitgalaxy#7533; temporal-crucible#90
takehome: One sentence a newcomer can quote. Write it once the study is scored; keep it honest about evidence level.
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

Pending.

## Take-home

Pending.

## What it changed

Pending.
