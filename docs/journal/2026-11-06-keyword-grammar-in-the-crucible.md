---
date: 2026-11-06
title: Is there a keyword grammar of functions? (KW, KW-R, GR)
type: confirmatory
status: scored
verdict: mixed
theme: keyword-grammar
ids: KW-H1..H3; GR-H1..H4
docs: docs/kw_hypotheses.md; docs/kw.md; docs/gr_hypotheses.md; docs/gr.md
links: temporal-crucible#83
takehome: A keyword grammar exists beyond size in the curated crucible (32 consensus pairs, signs hold in 69% of C-repo pairs), but breaking it does not mark CVE-prone code.
---

# Is there a keyword grammar of functions? (KW, KW-R, GR)

## Question

Do the engine's keyword signals co-occur in functions according to rules shared across languages, beyond what function size explains?

## Why we asked

If code has a grammar of constructs, deviations from it might mark unusual or risky code.

## What we did

The crucible was scanned (many languages). Presence was modelled against a logistic size model, with pair association as log observed / expected. Tested against a label shuffle and a size-only placebo; GR then tested the consensus pairs on 5 C repos and against CVE outcomes.

## What we found

- KW ✗ as registered: the cross-language r of 0.17 beats the shuffle but not the size placebo (0.24). Decile and compositional methods failed the placebo.
- KW-R and GR: under a presence + per-signal size model, 32 consensus pairs over 15 signals hold; GR-H1 ✓ signs hold in 69% of pairs in the C repos (p 0.0006).
- GR-H2 reversed: atypical functions get *fewer* CVE fixes.

## Take-home

The grammar is real once size is modelled properly. Its deviations are not a bug signal (nor, later, an outlier signal: OUT).

## What it changed

Led to the population-scale test (KW-P) and to the fingerprint and lattice work.
