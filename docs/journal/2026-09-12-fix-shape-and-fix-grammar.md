---
date: 2026-09-12
title: What shape is a fix? Reverts, follow-ups and curl's fix grammar (W1, G)
type: confirmatory
status: scored
verdict: mixed
theme: defect-prediction
ids: W1-H1; W1-H2; W1-H3; G-H1; G-H2
docs: docs/wave1_hypotheses.md; docs/signal_anatomy.md; docs/grammar_floor.md; docs/hunk_grammar.md; docs/keyword_pools_explore.md
links: gitgalaxy#2982; temporal-crucible#1
takehome: curl's security fixes have a recognisable shape (branch and pointer additions without new allocations) that is not a fix-size artifact, but it does not travel to nDPI's fuzzer-found fixes at any size floor; reverts read as net removal, a clean instrument check.
---

# What shape is a fix? Reverts, follow-ups and curl's fix grammar (W1, G)

## Question

- Do commit classes have distinct structural shapes in the engine's keyword deltas?
- **Wave 1 (curl):** are reverts net-removal (W1-H1)? Do fixes that later needed a follow-up look thinner (W1-H2)? Do CVE follow-ups carry the fix grammar (W1-H3)?
- **After nDPI's grammar failure:** is curl's fix grammar a fix-size artifact (G-H2)? Does it return on nDPI above a size floor (G-H1)?

## Why we asked

curl's security fixes net-add `struct_branch` and `state_pointers` against controls (signal anatomy). Wave 1 tested whether other commit classes behave as the instrument predicts. nDPI then failed to replicate the grammar (N-GRAM, N-FIXSHAPE). Its fixes are tiny (median net-LOC +1 vs curl's +6), so fix size was the obvious confound.

## What we did

- **Wave 1.** curl, 105 reverts, 15 CVE follow-ups and the fix and control events. Signal-anatomy deltas and the fix-shaped composite, α = 0.01, registered before the batch.
- **G-H1 / G-H2.** Registered on gitgalaxy#2982 before any floor-restricted statistic. Only the fix-size distributions were inspected to set the floors. Both repos were restricted to fixes at net-LOC of 5, 10 and 20 or more.
- **Exploratory alongside (no verdicts):** hunk-grain grammar (patch lines only) and the keyword-pools exploration.

## What we found

- **W1-H1 supported:** revert median net-LOC −1.0 (sign p=5.4e-05), net-grammar −1.0 (p=9.2e-05).
- **W1-H2 not supported:** wrong direction. Fixes that needed a follow-up are fix-shaped at 0.71 (10/14), against 0.65 for fixes that stuck (Fisher p=0.77).
- **W1-H3 not supported:** follow-ups are thin at 0.20 (3/15), below controls (0.45). They are administrative (build, cmake, test), not added security logic. n=15.
- **G-H2 supported:** curl's grammar persists at net-LOC ≥ 5 (branch p=0.0001) and ≥ 10 (p=0.0008). It thins only at ≥ 20, where the sample halves.
- **G-H1 not supported:** no floor revives the grammar on nDPI. At ≥ 10, the composite is 68% for fixes vs 67% for controls. Fix size is not the explanation.
- **Exploratory, hunk grain:** scoring only typed lines, an ordinary C bug fix looks like a CVE fix. What survives is fix-vs-nonfix, not a security-specific grammar.
- **Exploratory, allocations:** half of vulnerability-introducing patches add allocations (51%), against about 1 in 15 fixes.

## Take-home

The fix grammar is real but narrow. It belongs to human-reported CVE fixes in curl, not to code in general. The most plausible remaining explanation is the discovery process, which can only be tested inside one repo.

## What it changed

- X-H1 (unpaired allocation marks introducing commits) and X-H2 (a fix-grammar gradient on openssl) were registered for unseen data and are still open.
- The hunk-grain evidence revised X-H2's stated prior before openssl ran.
- Phase M (M-H1..M-H3, multi-label signatures) stays pending.
- The November fortification and fix-signature work (FORT, FIXK) revisited fix shape at function grain.
