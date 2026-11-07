---
date: 2026-11-07
title: The fingerprint lattice: family trees and a chance model (exploratory)
type: exploratory
status: scored
verdict: n/a
theme: fingerprints
ids: 
docs: docs/fingerprint_trees_exploratory.md; docs/lattice_null_exploratory.md; docs/kwp_hypotheses.md
links: 
takehome: Common shapes grow one keyword family at a time (196 of 199 tree edges), and real code builds about half the mid-size shapes chance would: role conflicts are the holes, paired constructs the attractions.
---

# The fingerprint lattice: family trees and a chance model (exploratory)

## Question

Do the shapes form a family tree, and is the space of shapes sparser than chance?

## Why we asked

The top shapes formed two ladders, which suggested a heritability lattice.

## What we did

Growth tree (each of the top 200 shapes under its most common sub-shape, with alternative parents drawn), similarity families (Jaccard, average linkage), and an independent-signals null with size-dependent per-language rates on a 2M-function sample.

## What we found

- 196/199 growth edges add exactly one signal; 148 shapes have alternative one-step parents.
- Families: public/general 17.5% (504 repos), private C + pointers 15.8% (356 repos, Linux 34%), bare one-step, annotated/test.
- Null: 0.63× as many distinct shapes overall, about 0.5× at 4–11 signals, more than chance above 12.
- No forbidden pairs. Holes: public + private 0.22×, tests + private 0.24×. Attractions: emitters + listeners 10×, alloc + cleanup 5×.
- 66% of one-step neighbours exist (null 73%).

## Take-home

The lattice is a normally connected space with strongly favoured regions, not a sparse skeleton. The raw combinatorial space is not a yardstick; only a null model says what is missing.

## What it changed

Draft, built with rules before gitgalaxy#8024 and #8016; rebuild after the rescan. Registered follow-up: LAT.
