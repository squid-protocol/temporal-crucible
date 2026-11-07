---
date: 2026-11-07
title: Do fix kinds live in different shape families, and do lattice moves predict regressions? (LAT)
type: confirmatory
status: scored
verdict: mixed
theme: fingerprints
ids: LAT-F1..F3, LAT-M1..M3
docs: docs/lat_hypotheses.md; docs/lat.md
links: 
takehome: Fix kinds sit in different shape families beyond size, modestly (V 0.07; regression fixes hit simpler, lower-rung functions), but lattice moves add nothing to regression prediction beyond churn; 71% of functions never change shape.
---

# Do fix kinds live in different shape families, and do lattice moves predict regressions? (LAT)

## Question

Does the lattice carry information about fixes? (1) Do the four fix kinds land in different families and rungs? (2) Does how a function moves on the lattice predict regressions beyond churn?

## Why we asked

FIXK showed class-specific signatures; CHG-2 showed raw change features add nothing to churn. LAT tests whether structuring change by the lattice changes that.

## What we did

Registration: frozen inputs (tree data hash a27d2c93f817), the FIXK commit set for F, CHG-2 units and baseline for M, a size placebo, a permutation and a shuffle control, and a sensitivity run without the signals affected by gitgalaxy#8010 and #8016.

## What we found

**LAT-F** (60,380 functions touched by 23,737 classified fixes in 5 C repos):
- F2 ✓ and F3 ✓: fix classes differ by family × rung (Cramér's V 0.068, permutation p 0.0005; size-only placebo
  99th percentile 0.043).
- Regression fixes hit lower-rung, simpler functions (k ≤ 5: 18.5% vs 7.9%) and the private-C family more.
- F1 ✗: CVE fixes are barely over-represented in the private-C upper rungs (RR 1.08, bar 1.25).

**LAT-M** (1,526,252 function × interval units, 1,188 regressions):
- M1 ✗: lattice-move features add +0.5 points forward and +0.0 points leave-one-repo-out to churn's recall@20%.
- M2 ✗: underpowered, only 5 half-step regressions.
- M3: the permutation control passed.

All verdicts are unchanged without the signals affected by gitgalaxy#8010 / #8016.

**Descriptive:**
- 70.9% of functions never change shape; 82% of edits keep the shape.
- Moves are mostly single-signal steps (68%).
- Shape-moving edits have a lower regression rate (0.28%) than edits that keep the shape (0.38%).

## Take-home

- The lattice describes fixes: each kind of fix tends to land on a different kind of function, beyond size.
- It does not predict regressions: churn already holds that signal.
- Most functions keep one shape for life.

## What it changed

- The "lattice as risk signal" line is closed, consistent with CHG-2. The lattice stays a descriptive and
  stratifying tool (e.g. family-adjusted baselines).
- Next candidates: AI-written code on the lattice (GitGalaxy's own scans), and the "constrained middle" (which
  combinations code avoids, and whether they behave like rules).
