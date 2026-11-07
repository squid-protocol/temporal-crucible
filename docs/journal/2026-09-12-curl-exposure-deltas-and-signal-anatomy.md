---
date: 2026-09-12
title: Do CVE fixes move curl's exposure scores, and what does a vulnerable function look like? (H1–H3, D-H, R2-H1)
type: confirmatory
status: scored
verdict: mixed
theme: defect-prediction
ids: H1; H2; H3; D-H1; D-H2; D-H1′; R2-H1
docs: docs/exposure_history_report.md; docs/signal_anatomy.md; docs/ndpi_signal_anatomy.md; docs/ndpi_stage2.md
links: gitgalaxy#2982
takehome: On curl, security fixes do not lower aggregate structural exposure (p=0.77) and introducing commits do not raise it; only the safety_score vector moved its assumed way (p=0.0072, curl only), and the function-level guard-deficit and danger-density ideas did not hold.
---

# Do CVE fixes move curl's exposure scores, and what does a vulnerable function look like? (H1–H3, D-H, R2-H1)

## Question

- **File grain:** do commits that fix a security bug lower a file's GitGalaxy structural exposure, and do vulnerability-introducing commits raise it?
- **Vectors:** which per-vector scores carry any movement?
- **Function grain:** are vulnerable functions under-guarded relative to their danger, or danger-dense at equal length?

## Why we asked

GitGalaxy reported `risk_*` exposure vectors named for what they should mark. This was the first test of whether they mean that, on curl's 25-year CVE history: the opening arc of the first validation program.

## What we did

- **Events.** Event-pair scans (parent and child of each event) with history ablated, so events cannot predict themselves. 182 security-fix, 118 introducing and 168 size-matched control events were analysed, with rename tracking.
- **H1/H2:** one-sided Mann-Whitney on the event-median structural delta, α = 0.01. **H3:** the per-vector table.
- **Signal anatomy:** per-signal deltas for fixes vs controls, and implicated functions vs same-file siblings with a length-matched gate.
- **Phase D (pre-registered):** D-H1, the vulnerable function's guard rate is below that of length-matched siblings. D-H2, the fix closes the gap.
- **For repo #2 (nDPI) only**, because they were post hoc on curl: D-H1′ (the branch-per-danger guard rate, the C idiom) and R2-H1 (danger density at equal length; the curl read was p=0.032, below α).

## What we found

- **H1 not supported:** p=0.77, n=182/168.
- **H2 not supported:** right direction (+0.007 vs +0.000), but p=0.023 against α 0.01.
- **H3:** `safety_score` p=0.0072 is the one vector moving its assumed direction. `tech_debt` (p=0.0011) was diagnosed as a density-denominator artifact. About half of fixes *raise* exposure, because added guard code reads as complexity.
- The fix "grammar" was visible: fixes net-add `state_pointers` (p=0.0001) and `struct_branch` (p=0.0004) vs controls. See the fix-shape entry.
- Implicated functions are long: they are more complex than their siblings, but no more complex than length-matched siblings (p=0.72). Length dominates.
- **D-H1 and D-H2 not supported:** the metric is degenerate, with a median of 0 on both sides, because C carries no `def_safety` vocabulary at function grain.
- **D-H1′ not supported on nDPI:** 0.634 vs 0.600, the wrong direction, p=0.75. It is non-degenerate, so a real no.
- **R2-H1 not supported on nDPI:** 19.0 vs 20.0, p=0.47. The curl suggestion did not replicate.

## Take-home

A fix does not visibly lower a file's exposure score. The one vector that moved (a net credit/debit score, not a density) did so on curl only. Below file grain, length explains the vulnerable function.

## What it changed

It set the program's pattern: aggregate exposure ≈ size, and per-vector meaning lives in the delta, not the standing level. `safety_score`'s curl result was carried to nDPI as N-H3 and failed there. See the nDPI battery entry and the program overview.
