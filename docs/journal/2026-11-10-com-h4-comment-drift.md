---
date: 2026-11-10
title: Do functions whose header comment goes stale get more CVE fixes? (COM-H4)
type: confirmatory
status: scored
verdict: not-supported
theme: comments
ids: COM-H4a..H4b
docs: docs/com_hypotheses.md; docs/com_h4.md
links: temporal-crucible#118; temporal-crucible#122; temporal-crucible#123
takehome: A header comment left untouched while the code keeps changing does not mark CVE risk; if anything those functions got fewer CVE fixes (0.67, CI 0.42–1.06, inconclusive).
---

## Question

When a function's code keeps changing but the comment above it never does, is that function more likely to need a
CVE fix than an equally busy function whose comment was kept up?

## Why we asked

- DC-2 showed that what comments say at birth predicts CVEs (danger words, 1.45×). Nobody here has asked whether the
  comments are kept current.
- Stale comments are linked to bugs in the literature: Tan et al. 2007 (iComment), and at file grain Ibrahim et al.
  2012.
- Wave A (temporal-crucible#118) checked the comment instruments this reads on curl.

## What we did

Registered only: [`../com_hypotheses.md`](../com_hypotheses.md).
- Units are function-quarters in curl, OpenSSL, nDPI and harfbuzz, using INT-S's function lives.
- "Drifted" means the body was edited in ≥ 2 of the last 8 quarters and the header text never changed. "Maintained"
  means the same editing, but the header changed at least once.
- The test is an MH rate ratio of CVE fixes, stratified by size, edit count and prior CVEs in the file, with a
  file-cluster bootstrap and α = 0.01/2.

## What we found

- 153,695 at-risk function-quarters: 31,979 drifted, 8,034 maintained (the rest had no header).
- **COM-H4a not supported, inconclusive.** The CVE rate ratio, drifted vs maintained, was **0.67** [0.42, 1.06]:
  the wrong direction. Three of four repos point below 1.
- **COM-H4b not supported** (0.75).
- **Frozen headers are normal.** 66–85% of headed functions that were edited repeatedly never touched the header in
  2 years.
- **Instrument audit:** 10 of 10 sampled calls correct.

## Take-home

A stale header comment is not a CVE warning sign at function grain in these four C/C++ repos. If anything, functions
whose header gets rewritten see more CVE fixes, plausibly because both follow attention.

## What it changed

- The comment-update line of Ibrahim et al. (2012) does not carry over to CVE fixes at function grain here.
- **Exploratory idea, not tested:** header edits track security attention. It would need a prior-fix-in-function
  stratum on unseen repos.
- DCS (registered the same day) stays the open comment study.
