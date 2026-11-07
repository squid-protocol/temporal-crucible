---
date: 2026-11-06
title: Finding silent security patches: signature vs history (SILENT, WH)
type: confirmatory
status: scored
verdict: mixed
theme: defect-prediction
ids: SIL-H1..H2; WH-H1..H3
docs: docs/silent_hypotheses.md; docs/silent.md; docs/wh.md
links: temporal-crucible#84
takehome: To find unannounced security fixes, history (where past CVE fixes and fix activity were) beats the change signature: AUC 0.720, top-10% enrichment 2.93×.
---

# Finding silent security patches: signature vs history (SILENT, WH)

## Question

Can we spot security fixes that were never announced as such?

## Why we asked

Silent patches matter for downstream users who track versions, not commits.

## What we did

SILENT fitted change signatures to held-out repos. WH added location and history features and compared them with the signature.

## What we found

- SIL-H1 ✓ weak: held-out AUC 0.569 vs size 0.507 (defensive rules alone 0.572). SIL-H2 ✗.
- WH-H1 ✓ (+0.111), WH-H3 ✓ (top-10% 2.93×, lo 2.37). WH-H2 ✗: adding the signature *lowers* AUC (−0.039).

## Take-home

History beats structure again: where fixes happened before predicts where silent fixes are; how the change looks adds nothing.

## What it changed

Consistent with the program's standing result (recidivism). Structure stays descriptive.
