---
date: 2026-11-07
title: Are there higher-order building codes? The constrained middle (exploratory)
type: exploratory
status: scored
verdict: n/a
theme: keyword-grammar
ids:
docs: docs/constrained_middle_exploratory.md; docs/lattice_null_exploratory.md
links:
takehome: The rules code follows are pairwise. Of 2,791 three-signal combinations, only one is avoided beyond what its pairs explain, and it is not universal; the lattice's missing middle is pair constraints (role conflicts, paired constructs) multiplied out.
---

# Are there higher-order building codes? The constrained middle (exploratory)

## Question

Real code builds only about half the mid-size shapes chance predicts. Is that because of genuine three-way rules
(combinations avoided even though each pair is fine), or because of the pairwise constraints we already know?

## Why we asked

- The lattice null found strong pair-level holes (public + private, tests + private) and attractions (alloc + cleanup,
  emitters + listeners).
- If higher-order rules existed and held across languages, they would be literal "building codes": a candidate
  linter.

## What we did

- **Sample:** 2.0M population functions (loc ≥ 3); 27 signals with 2–98% presence.
- **Null:** independent signals, with per-language, size-dependent rates; exact expected triple counts.
- **Candidates:** triples with observed/expected < 0.25 where every pair of the triple is built at ≥ 0.5 of chance.
- **Universality:** each candidate checked per language (≥ 30k functions) and per large repo (≥ 20k).

## What we found

- **Only 1 of 2,791 triples is a higher-order hole:** branches + struct/class declarations + decorators/attributes,
  0.24×. It holds in only 3 of 6 languages and 5 of 10 large repos, so it is not universal.
- **All 20 strongly avoided triples contain a pair hole.** The strongest triple attractions are the alloc + cleanup
  pair plus a third signal (7–10×).

## Take-home

- The keyword "building codes" are pairwise: which constructs exclude each other (roles) and which come together
  (paired constructs).
- There is no separate higher-order rulebook. The missing middle of the lattice is those pair constraints multiplied
  out.

## What it changed

- A "building code" linter would be a pair-rule checker.
- But OUT showed that rule-breakers are mostly ordinary code, so such a linter describes rather than detects.
- Closes the higher-order-rules question at this signal resolution.
