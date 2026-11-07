---
date: 2026-09-12
title: Does curl's picture replicate on a second repository? The nDPI battery (N-)
type: confirmatory
status: scored
verdict: mixed
theme: defect-prediction
ids: N-H1; N-H2; N-H3; N-GRAM; N-FIXSHAPE; N-RW1; N-RW2; N-FIRST
docs: docs/HYPOTHESES.md; docs/ndpi_exposure_report.md; docs/ndpi_signal_anatomy.md; docs/ndpi_rw.md; docs/ndpi_stage2.md; docs/grammar_floor.md
links: gitgalaxy#2982; temporal-crucible#12
takehome: On nDPI, recidivism replicated and every structural null held (equivalence-confirmed), but every structural positive from curl (safety_score, the fix grammar, the fix-shaped signature, danger density) failed; the one surviving structure signal for the first CVE was centrality, the hot-files axis.
---

# Does curl's picture replicate on a second repository? The nDPI battery (N-)

## Question

Which of curl's results hold on nDPI, a second C/C++ repo whose CVEs are OSS-Fuzz-found? The battery covered curl's positives, curl's nulls, and a first-CVE test.

## Why we asked

One repo is an anecdote. The battery was registered on gitgalaxy#2982 while the nDPI scan was in flight and before any nDPI result existed. Directions were set to curl's observed direction. A null "replicates" only if it is non-significant and its 95% CI lies inside an equivalence band. A flip to significant would be reported as a new signal.

## What we did

- **Data.** nDPI: 112 security-fix, 68 introduced and 96 control usable events, 555 snapshots, run through curl's unchanged tools.
- **Claims.** N-H1/N-H2 (aggregate exposure), N-H3 (`safety_score`), N-GRAM and N-FIXSHAPE (fix grammar), N-RW1/N-RW2 (review budget, recidivism), N-FIRST (pre-event exposure separates first-CVE files from matched clean ones), plus D-H1′ and R2-H1.
- **Contrasts, not pass/fail:** dwell time, D-H1 verbatim, and the wave-1 classes.
- **Stage 2** added TOST equivalence on the three nulls.

## What we found

- **Nulls replicate, equivalence-confirmed:** N-H1 p=0.70, N-H2 p=0.37, N-RW1 p=0.60, all CIs inside their δ.
- **N-RW2 replicates:** p<1e-4 against exposure and against LOC.
- **curl's structural positives fail:**
  - N-H3 `safety_score` p=0.71, with every vector flat.
  - N-GRAM: branch p=0.28, pointers p=0.079.
  - N-FIXSHAPE: 58/59/59, no differential.
  - R2-H1 p=0.47.
  - D-H1′ goes the wrong way (p=0.75).
  - D-H1/D-H2 are degenerate again.
- **N-FIRST supported, but the mechanism is centrality:** raw AUC 0.755 is inflated by loose size matching. With size divided out, AUC(density) 0.624 and a density win in 78% of pairs survive. That signal is carried by total exposure and centrality against peripheral never-CVE files, not by fine danger structure.

## Take-home

After two repositories, recidivism is the only replicated positive. Structural exposure is a size and activity proxy whose fix signatures are repo- and discovery-specific.

## What it changed

The function-level "CVE profile" was withdrawn as a cross-repo claim. The fix-size explanation of the grammar failure was tested and rejected (G-H1; see the fix-shape entry). Mid-band centrality was registered for repo #3 and later failed there (CEN). The program turned to openssl as repo #3 for the open questions.
