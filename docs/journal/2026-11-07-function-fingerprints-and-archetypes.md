---
date: 2026-11-07
title: What the commonest function fingerprints are (exploratory)
type: exploratory
status: scored
verdict: n/a
theme: fingerprints
ids: 
docs: docs/arch_anatomy_exploratory.md; docs/top_signatures_exploratory.md; docs/kwp_hypotheses.md
links: temporal-crucible#85
takehome: Code is built from a few hundred keyword combinations plus a long tail. The commonest are tiny universal "bricks" (one-step, public one-step, public setter) and C dialect shapes (driver functions, static pointer helpers) concentrated in a few OS repos.
---

# What the commonest function fingerprints are (exploratory)

## Question

What do functions actually look like, as exact combinations of keyword families, and how do those combinations relate to archetypes?

## Why we asked

KW-P showed the grammar; this looks at the building blocks themselves.

## What we did

Exact signal-presence signatures over 6.94M population functions (loc ≥ 3). Measured the distribution, archetype anatomy (absences, near-universals, within-archetype grammar) and the top 6 shapes with real code examples and rule matches.

## What we found

- 314,979 distinct signatures: 205 cover half of all functions, and 57% are singletons.
- Archetypes are gradients, not exclusive types; the grammar holds within 12 of 14 archetypes.
- Top shapes: #1 one-step function (2.6%, 386 repos), #2 public one-step (2.5%), #5 public setter (1.2%), and C shapes #3 driver (77% one repo), #4 static pointer helper, #6 COM method.
- Reading them closely exposed misleading signal names and rule leaks (see the engine entry).

## Take-home

There are two ladders: a public/OO ladder found everywhere, and a private-C ladder concentrated in OS-scale repos. Function-weighted rankings reflect corpus composition.

## What it changed

Led to the signal-name audit and engine fixes, the family trees and the LAT registration.
