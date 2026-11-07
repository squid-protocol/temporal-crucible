---
date: 2026-11-06
title: Where the outside world touches code: library and platform coupling (LIB, LIB-R, LIB-E, ENV)
type: confirmatory
status: scored
verdict: replicated
theme: coupling
ids: LIB-H1..H3; LIBR-H1..H3, LIBE-H1..H2; ENV-H1..H3
docs: docs/lib_hypotheses.md; docs/librep_hypotheses.md; docs/env_hypotheses.md
links: temporal-crucible#80
takehome: Files that call a library's API receive the work that names that library (replicated, +0.44 over size), and platform conditionals mark where extrinsic fixes land.
---

# Where the outside world touches code: library and platform coupling (LIB, LIB-R, LIB-E, ENV)

## Question

Does a file's coupling to a library or platform predict where library- or platform-driven work lands?

## Why we asked

External change (library upgrades, platform ports) is a large share of maintenance and should leave a structural footprint.

## What we did

Per-file coupling surfaces (includes plus API calls of each dependency) were tested at recall@20% over size, over other libraries' coupling and over file names. LIB-R replicated on unseen repos; LIB-E retested with the engine's own call graph. ENV tested `#ifdef` platform density against extrinsic fixes on unseen repos.

## What we found

- LIB ✓: +0.40 / +0.46 / +0.22 (21 units, 4 repos). LIB-R replicated on PostgreSQL and libgit2: +0.44 / +0.49 / +0.18.
- LIB-E: the engine call graph gets +0.34 over size but is 0.06 behind the regex: it misses `#include` and COM-method coupling.
- ENV ✓: platform conditionals beat size on harfbuzz and libarchive (+0.17 / +0.12), the only metric of 225 screened to pass holdout.
- Correction: LIB's outcome is library-named work, not security fixes.

## Take-home

Coupling surfaces are the engine's best-replicated predictive use: they say where outside change will land.

## What it changed

Engine gaps were filed: `calls_out_to` misses COM-style calls and per-file includes ("engine coupling 2.0").
