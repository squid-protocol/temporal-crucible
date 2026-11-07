---
date: 2026-09-13
title: Fresh bug labels: does change entropy validate, and does small-file centrality live? (B-H1..B-H3)
type: confirmatory
status: scored
verdict: mixed
theme: defect-prediction
ids: B-H1..B-H3
docs: docs/bh_eval.md; docs/centrality_bands.md; docs/hcm_variants.md
links: gitgalaxy#2982; temporal-crucible#24; temporal-crucible#25
takehome: On 957 fresh curl bug-label events, change entropy (HCM1_LD_30, frozen from the CVE selection) beat a line count out of selection (AUC 0.868 vs 0.830), while small-file centrality died (PageRank inverted, AUC 0.259) and the monotone lift shape failed in 5,000 of 5,000 bootstraps.
---

# Fresh bug labels: does change entropy validate, and does small-file centrality live? (B-H1..B-H3)

## Question

With labels that actually land in small files:
- does centrality beat LOC in the small bands (B-H1)?
- is its lift monotone-decreasing with size (B-H2)?
- does `HCM1_LD_30`, frozen from the CVE selection, beat a line count on fresh labels with no selection problem (B-H3)?

## Why we asked

CVE fixes barely touch small files, so C-H1 was unpowered, and HV-H2's change-entropy win was a best-of-36 result. A fresh label family settles both. Priors on record: B-H1 uncertain, B-H2 expected supported, B-H3 expected shrunken but positive.

## What we did

- Registered on the epic before the sample was drawn (seed 2982).
- The sample was every `regression` commit, 500 uniform `Fixes #` commits and 300 `Bug:` commits: 1,107 events, already-scanned SHAs excluded. 957 were usable, giving 767,591 pooled files and 1,900 positives.
- Both small bands were powered (28 and 42 positives).
- B-H1: Bonferroni over 5 measures × bands. B-H2: 5,000 event bootstraps.

## What we found

- **B-H1 not supported:** PageRank in ≤ 22-LOC files is inverted (AUC 0.259), and 23–48 is not significant.
- **B-H2 not supported, decisively:** a monotone shape appeared in 0 of 5,000 bootstraps. The true shape is an inverted U (−0.047 / +0.017 / +0.145 / −0.253). The CVE-label "perfect monotone" was an artifact of unpowered bands.
- **B-H3 supported:** AUC 0.868 vs LOC 0.830, lift +0.0379 (lo +0.0211). This was the second genuine positive after recidivism, and the first feature to beat a line count out of selection.
- Exploratory (not claimed): the 49–108-LOC mid band carries two robust centrality cells (PageRank +0.145, popularity +0.132).

## Take-home

Fresh labels validated change entropy on curl and killed small-file centrality. The guards (pre-registration and the power rule) did the finding.

## What it changed

- Mid-band centrality was registered for repo #3. It later failed on openssl, harfbuzz and libarchive (CEN).
- Change entropy's replication was owed on repo #3. On nDPI it failed as a forward AUC test (FWD-H3). On openssl it passed effort-aware (EA-H1). See the history forward-tests entry.
