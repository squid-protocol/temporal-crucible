---
date: 2026-11-06
title: Finding copies of code: forks, rewrites and vendoring (UT, LAY, VZ)
type: confirmatory
status: scored
verdict: supported
theme: provenance
ids: UT-H1..H3; LAY-H1..H3; VZ-H1..H3
docs: docs/ut_hypotheses.md; docs/lay_hypotheses.md; docs/vz_hypotheses.md
links: temporal-crucible#79; temporal-crucible#80; temporal-crucible#81
takehome: A layered fingerprint (call set + control-flow skeleton + profile) finds copies the coarse one misses: fork copies 46% to 80%, C to C++ BoringSSL 29% to 94%, vendored zlib 91%.
---

# Finding copies of code: forks, rewrites and vendoring (UT, LAY, VZ)

## Question

Can GitGalaxy recognise the same code after it has been forked, rewritten in another language or vendored into another project?

## Why we asked

Provenance ("trust the code, not the label") is a supply-chain use case the engine might uniquely serve.

## What we did

UT tried the coarse fingerprint on forks. LAY added call-set and control-flow layers, scored as recall@1. VZ applied the fused fingerprint to zlib vendored in 12 host projects, without using names.

## What we found

- UT ✗: the coarse fingerprint finds 12.5% of name-found fork copies and none in C++ BoringSSL.
- LAY ✓ (all three): recall@1 46% → 69% → 80%; BoringSSL 29% → 94%.
- VZ-H1 ✓: 91% vs 68% (98% on same-name copies). 11 of the 13 "renamed" copies were an artefact (`_tr_tally` became a macro).

## Take-home

Identity and copy-finding work, with the layered fingerprint. This is one of the engine's strongest, most defensible uses.

## What it changed

Follow-ups: the patch-status studies below, a renamed-copy benchmark large enough to register, and LAY on a second fork family.
