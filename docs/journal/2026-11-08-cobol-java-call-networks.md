---
date: 2026-11-08
title: Does a COBOL program's call network survive into its Java port?
type: confirmatory
status: registered
verdict: pending
theme: provenance
ids: WIRE-H1..H3
docs: docs/wire_hypotheses.md
links: gitgalaxy#7532; gitgalaxy#7533
takehome: One sentence a newcomer can quote. Write it once the study is scored; keep it honest about evidence level.
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

Pending.

## Take-home

Pending.

## What it changed

Pending.
