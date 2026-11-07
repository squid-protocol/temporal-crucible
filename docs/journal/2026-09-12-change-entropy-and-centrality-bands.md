---
date: 2026-09-12
title: Change-entropy variants and centrality by file size (HV, C-H)
type: confirmatory
status: scored
verdict: inconclusive
theme: defect-prediction
ids: HV-H1; HV-H2; C-H1; C-H2
docs: docs/hcm_variants.md; docs/centrality_bands.md
links: gitgalaxy#2982; temporal-crucible#24; temporal-crucible#25
takehome: Among 36 change-entropy (Hassan HCM) variants, none clears the size wall in 3 of 4 LOC bands; the best, HCM1_LD_30, beat a line count only as a discounted best-of-36 result; small-file centrality could not be evaluated on CVE labels (1 and 4 positives).
---

# Change-entropy variants and centrality by file size (HV, C-H)

## Question

Two candidates to beat a line count:
- **Change entropy** (Hassan's HCM: was the file changed while edits were scattered across the codebase?). Does any variant clear the size wall in at least 3 of 4 LOC bands (HV-H1)? Does the best variant beat LOC pooled (HV-H2)?
- **Centrality** (PageRank, popularity). Does it beat LOC in small files (C-H1)? Does its lift fall monotonically with size (C-H2)?

## Why we asked

repowise-bench reported change entropy as its strongest process predictor, with the same size-confound wall seen here. The small-file regime was the place centrality might help, where a line count has nothing to say.

## What we did

- **HV.** 36 HCM variants (attribution × decay × period) plus repowise's flavour, evaluated size-orthogonally on curl CVE labels. Registered on the epic before the run.
- **C-H.** PageRank, popularity and related measures, scored by LOC band, with a power rule of at least 20 positives per band.

## What we found

- **HV-H1 not supported.** The best variant, `HCM1_LD_30`, clears 2 of 4 bands (Q3 0.771, Q4 0.803), the same monotone wall shape as repowise's.
- **HV-H2 supported as computed, but discounted.** Lift +0.0238 (lo +0.0050), but it is the best of 36, chosen and tested on the same data.
- **Robust family pattern:** the top 8 are all HCM1 (share-weighted), and 30-day periods beat longer ones. HCM2 and HCM3 at 180 days are worse than a line count. repowise's shipped shape ranked about 6th.
- **C-H1 not evaluable on curl.** The ≤ 22-LOC band has 1 CVE positive and 23–48 has 4, so the power rule refuses verdicts. Without it, the result would have been an AUC of 0.999 off one positive.
- **C-H2 suggestive, no verdict.** PageRank lift +0.458 → +0.320 → +0.154 → −0.271, monotone, but the small end is unpowered.
- **Solid negative:** in files over 108 LOC (433 positives), PageRank is far worse than LOC (0.525 vs 0.796).

## Take-home

Change entropy's edge over size was real-looking but selected. Centrality's small-file story could not be tested with CVE labels. Both needed fresh labels.

## What it changed

- The out-of-selection validation was registered as B-H3, and the small-band centrality test as B-H1/B-H2, on curl bug labels that land in small files (see the bug-label entry).
- The power rule became standard.
- The engine's change-entropy column was later built to match `HCM1_LD_30` exactly (FWD).
