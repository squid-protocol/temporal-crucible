---
date: 2026-11-06
title: Does defensive code at birth protect a function? (INT, INT-S)
type: confirmatory
status: scored
verdict: not-supported
theme: defect-prediction
ids: INT-H1..H2; INTS-H1..H2
docs: docs/int_hypotheses.md; docs/int.md; docs/ints.md
links: temporal-crucible#84
takehome: Functions born with more defensive code get CVE fixes at the same rate as others (whole-life rate ratio 0.96, a fairly tight null).
---

# Does defensive code at birth protect a function? (INT, INT-S)

## Question

Are functions written defensively from the start less likely to need security fixes later?

## Why we asked

A natural intuition, and it would make defensive density a quality metric.

## What we did

Function births were reconstructed from history. INT used a 2-year window; INT-S used a whole-life survival analysis, because CVEs surface years later (SRCH).

## What we found

- INT inconclusive (RR 0.97 [0.46, 1.72]; only 106 events within 2 years).
- INT-S ✗ both: rate ratio 0.96 [0.73, 1.28] over 562 events and 126k function-years; CVE-specific 0.90.

## Take-home

Defensive density at birth is not a protective marker.

## What it changed

Closed the "defensive code as a quality score" line.
