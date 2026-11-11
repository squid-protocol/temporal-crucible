---
date: 2026-11-10
title: Do functions whose header comment goes stale get more CVE fixes? (COM-H4)
type: confirmatory
status: registered
verdict: pending
theme: comments
ids: COM-H4a..H4b
docs: docs/com_hypotheses.md
links: temporal-crucible#118
takehome: Registered, not yet scored.
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

Pending.

## Take-home

Pending.

## What it changed

Pending.
