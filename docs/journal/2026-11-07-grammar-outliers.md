---
date: 2026-11-07
title: Are grammar-breaking functions special? (OUT)
type: confirmatory
status: scored
verdict: mixed
theme: keyword-grammar
ids: OUT-H1..H2
docs: docs/out_hypotheses.md; docs/out.md
links: temporal-crucible#85
takehome: Functions that break the grammar are mostly ordinary code (55% vs 64% for controls). They concentrate in test directories, but a "weirdness detector" would not find interesting code.
---

# Are grammar-breaking functions special? (OUT)

## Question

Are the functions that fit the grammar worst generated, vendored, obfuscated or otherwise not ordinary hand-written code?

## Why we asked

If yes, grammar fit would be a cheap triage signal.

## What we did

Grammar fit per function, with outliers = bottom 0.1% within language × size × signal-count strata. H2 used indirect standardisation against path flags. H1 was a blind, code-only agent audit of outliers vs matched controls, with labels hash-locked.

## What we found

- H2 ✓: outliers are 1.51× (lo 1.42) more often in flagged paths, almost all test directories.
- H1 ✗: 55% of outliers vs 64% of controls are ordinary hand-written code (gap 9 points; the bar was 20).
- Engine observation: every `threat_*` function column is zero (explained later by gitgalaxy#8012).

## Take-home

The grammar describes code well, but its outliers are not a useful anomaly signal.

## What it changed

Steered the work towards describing the common shapes (fingerprints) instead of hunting outliers.
