---
date: 2026-11-08
title: Does the engine's own resolved call graph agree with compiler-grade oracles?
type: confirmatory
status: scored
verdict: mixed
theme: engine
ids: ACC2-H1, H3, G
docs: docs/acc2_hypotheses.md; docs/acc2.md
links: temporal-crucible#102
takehome: The engine's own resolver fixes Java hubs on an unseen repo (Jaccard 0.67 vs 0.26 name-based) but not on overload-heavy commons-lang; C passes again; Go and Python remain unevaluated, so the many-labs gate admits only C for now.
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

Does GitGalaxy's own resolved call graph (receiver, overload, class and import resolution) agree with compiler-grade oracles where the name-based graph did not?

## Why we asked

ACC validated C but failed Java hubs and could not evaluate Go and Python; the engine's resolver was never tested.

## What we did

Registered in `docs/acc2_hypotheses.md`.

## What we found

C passes again. Java: commons-io passes with the resolved graph (hub Jaccard 0.67 vs 0.26 name-based); commons-lang fails on same-arity overloads. Go: a scorer template bug (token offsets); Python: PyCG fails on sphinx in every subpackage.

## Take-home

The resolver is the right graph for Java; the gate admits only C until Go is measured correctly and Java overloads are resolved.

## What it changed

ACC-3 (Go, corrected template) next; an engine issue for same-arity overload resolution; LAWS uses the resolved graph.
