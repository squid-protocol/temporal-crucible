---
date: 2026-11-06
title: Does a function's change in shape predict regressions? (CHG, CHG-2)
type: confirmatory
status: scored
verdict: not-supported
theme: defect-prediction
ids: CHG-H1..H5; CHG2-H1..H2
docs: docs/chg_hypotheses.md; docs/chg.md; docs/chg2_hypotheses.md; docs/chg2.md
links: temporal-crucible#77; temporal-crucible#78
takehome: Shape change looked like a 2.9× regression signal, but it is edit size: engine change features lower churn's recall (41.3% to 38.7%).
---

# Does a function's change in shape predict regressions? (CHG, CHG-2)

## Question

Do functions whose structure changes in an edit attract regression fixes, beyond plain editing?

## Why we asked

If structure helps anywhere with defects, it should be in how code changes rather than in what it is.

## What we did

Function-level fix mapping across 5 C repos (curl, openssl, harfbuzz, nDPI, libarchive): 1.5M function × interval units. CHG used MH rate ratios; the name-join gate was amended (A1) before the claims. CHG-2 ran a head-to-head against a churn-only ranking, forward and leave-one-repo-out.

## What we found

- CHG ✓: shape-changed vs untouched RR 2.88; vs edited-same-shape 1.42 (lo 1.02).
- CHG-2 ✗ (both): churn alone catches 41% forward / 37% LORO of regressions in 20% of LOC; adding engine features gives −2.6 / −2.9 points.
- Young code is not more regression-prone once matched (CHG H4/H5 ✗).

## Take-home

The engine adds nothing to regression ranking beyond churn. "3% of functions carry 21% of regressions" was mostly churn.

## What it changed

Regression prediction moved to "not what the engine is for". The lattice-move study (LAT-M) re-tests this with lattice-structured change and states this null as its prior.
