---
date: 2026-11-06
title: Is a vendored copy patched? Reading the code instead of the version string (VZ-T, SEM, CMB, SEM-3)
type: confirmatory
status: scored
verdict: mixed
theme: provenance
ids: VZT-H1..H2; SEM-H1..H3; CMB-H1..H3; S3-H1..H2
docs: docs/vzt_hypotheses.md; docs/sem_hypotheses.md; docs/cmb_hypotheses.md; docs/sem3_hypotheses.md
links: temporal-crucible#81
takehome: Code-reading patch checks work for libraries whose security fixes are surgical (zlib: 0 of 1,229 wrong, 30/30 on modified copies) and fail for refactoring-fix libraries (expat).
---

# Is a vendored copy patched? Reading the code instead of the version string (VZ-T, SEM, CMB, SEM-3)

## Question

Given a vendored copy, can we tell from its code which security fixes it contains, better than its version string?

## Why we asked

Version strings lie in vendored, backported or modified copies.

## What we did

Per-fix code-line signatures were checked against host histories with known truth (VZ-T), then semantic checks (SEM-1 to SEM-3) and a combined checker (CMB). Modified copies were blind-audited by agents, with labels hash-locked before scoring. Per-host specifics are kept private (vz_private/).

## What we found

- zlib: 0 wrong calls in 1,229 decided verbatim cases (all misses are abstentions). On modified copies it beats closest-version 30/30, 19/20 and 30/30.
- expat: line and SEM checks call about 25% of old verbatim copies "patched". SEM-3 cuts that to 4.9% but still fails. Blind audit 1/29 vs closest-version 28/29.
- SEM-1 was unusable (227 false "patched" from non-new guard fragments).

## Take-home

Supply-chain patch checking is real but narrow: use code reading for surgical-fix libraries and closest-version matching for refactoring-fix ones.

## What it changed

Proposed "fingerprint finds, model judges": blind auditor agents judged refactored fixes where text rules failed. An OSV-scanner head-to-head was skipped by owner decision.
