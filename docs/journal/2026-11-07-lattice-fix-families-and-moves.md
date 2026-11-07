---
date: 2026-11-07
title: Do fix kinds live in different shape families, and do lattice moves predict regressions? (LAT, draft)
type: confirmatory
status: draft
verdict: pending
theme: fingerprints
ids: LAT-F1..F3, LAT-M1..M3
docs: docs/lat_hypotheses.md
links: 
takehome: Registered (draft): whether CVE fixes concentrate in the private-C upper rungs, and whether lattice moves (jumps, half-steps) add regression recall beyond churn. The prior for the moves is null (CHG-2).
---

# Do fix kinds live in different shape families, and do lattice moves predict regressions? (LAT, draft)

## Question

Does the lattice carry information about fixes? (1) Do the four fix kinds land in different families and rungs? (2) Does how a function moves on the lattice predict regressions beyond churn?

## Why we asked

FIXK showed class-specific signatures; CHG-2 showed raw change features add nothing to churn. LAT tests whether structuring change by the lattice changes that.

## What we did

Draft registration: frozen inputs (tree data hash a27d2c93f817), the FIXK commit set for F, CHG-2 units and baseline for M, a size placebo, a permutation and a shuffle control, and a sensitivity run without the signals affected by gitgalaxy#8010 and #8016.

## What we found

Not run. No outcome data has been read.

## Take-home

Pending.

## What it changed

Awaiting owner OK. Then the scorer is committed, the study runs, and this entry is updated with verdicts.
