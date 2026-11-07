---
date: 2026-11-07
title: The keyword grammar at population scale (KW-P)
type: confirmatory
status: scored
verdict: replicated
theme: keyword-grammar
ids: KWP-H1..H3
docs: docs/kwp_hypotheses.md; docs/kwp.md
links: temporal-crucible#85
takehome: The crucible's keyword grammar holds across 2.9M functions in 22 languages and inside 97% of individual repos, well beyond size (r 0.235 vs size placebo −0.006).
---

# The keyword grammar at population scale (KW-P)

## Question

Does the grammar found in the curated crucible hold in the wild?

## Why we asked

The crucible is small and curated; a full rescan of the corpus (745 targets, 8.17M functions, engine b64f42bf) made a population test possible.

## What we did

Population functions excluding crucible-source repos (2,889,002 functions, 22 languages). Tests: sign agreement with the crucible pairs, cross-language correlation against a shuffle and a size placebo, and repo × language units.

## What we found

- H1 ✓: 78% of 420 language × pair signs (p 1e-32).
- H2 ✓: cross-language r 0.235 vs size placebo −0.006.
- H3 ✓: 97% of 174 repo × language units follow it.
- The defensive-control core is universal; the grammar is weak in CSS, YAML, Fortran and COBOL.

## Take-home

Code is built from a shared keyword grammar, like building codes: the same rules hold across languages and inside individual projects.

## What it changed

Opened the fingerprint, archetype-anatomy and lattice work (exploratory) and the OUT test.
