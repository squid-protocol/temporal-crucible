---
date: 2026-11-08
title: Does a COBOL program's call network survive into its Java port?
type: confirmatory
status: scored
verdict: mixed
theme: provenance
ids: WIRE-H1..H3
docs: docs/wire_hypotheses.md; docs/wire.md
links: gitgalaxy#7532; gitgalaxy#7533
takehome: A COBOL program's paragraph call network survives mechanical translation and alone finds a port's own source 24% of the time (sfs 2.4%, chance 0.7%), but GitGalaxy cannot read it through the translator's dispatcher, which half the ports use.
---

<!--
Header fields (one per line, `key: value`; lists use `;`):
  date      the day the entry was opened (registration day for confirmatory work)
  type      confirmatory | exploratory | engine-finding | program
  status    draft | registered | scored | superseded
  verdict   supported | replicated | mixed | not-supported | inconclusive | pending | n/a   (a draft is always pending)
  theme     provenance | coupling | natural-history | defect-prediction | keyword-grammar | fingerprints | comments | engine | program
  ids       register ids exactly as in docs/HYPOTHESES.md's first column, e.g. KWP-H1..H3
  docs      repo paths of the registration and result docs, e.g. docs/kwp_hypotheses.md; docs/kwp.md
  links     issues / PRs, e.g. gitgalaxy#8024; temporal-crucible#85
Then: python tools/journal.py build   (CI runs `check`)
-->

## Question

When a COBOL program is translated to Java, does its call network (which paragraph performs which) survive in a form
GitGalaxy can read on both sides, and can that network alone find a port's own COBOL source?

## Why we asked

- In the DOOM study (exploratory), the wiring between the original's game areas separated ports and translations
  from redesigns, and translations that kept the design from ones that rewired.
- gitgalaxy#7532: whole-program fingerprints could not pick a det-port's own source (1-3 of 124), because det Java is
  mechanical. The call network might carry what the fingerprint loses.
- Priors: structured ports should pass (direct calls); dispatch ports should fail (calls routed through a
  dispatcher); name-free identification is uncertain (small programs share shapes).

## What we did

Registered in `docs/wire_hypotheses.md` before any scorer or measurement: det ports of every equivalence case at
gitgalaxy 8f96d76ba in both styles, the translator's `/** PARAGRAPH. */` map as truth, map-permutation null,
Weisfeiler-Lehman graph similarity for name-free identification.

## What we found

- **WIRE-H3 supported:** with names discarded, the call network ranks a structured port's own COBOL source first for
  33 of 138 programs (24%); chance 0.7%, p 0.0001; sfs whole-program fingerprints managed 3 of 124.
- **WIRE-H1 not supported:** mean match 0.52 against 0.08 shuffled, but only 41% of programs beat their own null.
  Post-hoc (exploratory): 57 of 125 "structured" ports silently keep the dispatcher (all of CBSA and GenApp); the 68
  truly structured ones match 0.95 and 76% beat the null; small programs (3-5 paragraphs) cannot beat it at all.
- **WIRE-H2 not supported, as predicted:** dispatch ports read as no paragraph calls at all; resolving `perform(a, b)`
  with a parser (descriptive) gives a 0.69 match, so the wiring is there and the engine cannot see it.
- The model-refined ports drop the translator's paragraph headers, so they cannot be traced.

## Take-home

A COBOL program's design (which paragraph performs which) survives mechanical translation and identifies the port's
source ten times better than whole-program fingerprints. GitGalaxy cannot yet read it through a dispatcher.

## What it changed

- The DOOM wiring idea now has a registered, positive result on a second corpus (identification), and a measured
  blind spot (dispatchers).
- Follow-ups: an engine issue to resolve the translator's `perform(int, int)` idiom; keep paragraph headers through
  refinement; H1 re-registered on truly structured ports with a power floor, on new cases only.
