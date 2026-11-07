---
date: 2026-11-06
title: How fixes change defensive code, and what CVE fixes look like (FORT, FORT-V, FIXK)
type: confirmatory
status: scored
verdict: mixed
theme: defect-prediction
ids: FORT-H1..H3; FORTV-H1, FIXK-H1..H3
docs: docs/fort_hypotheses.md; docs/fortv_fixk.md
links: temporal-crucible#84
takehome: CVE fixes add guard clauses 1.88× as often as ordinary fixes, and the three fix kinds have distinct keyword signatures: CVE = branch + pointers + `#define`; regression = new functions, globals, state; extrinsic = macros, asm, imports.
---

# How fixes change defensive code, and what CVE fixes look like (FORT, FORT-V, FIXK)

## Question

Do security fixes change a function's defensive code differently from other fixes, and do fix classes have keyword signatures?

## Why we asked

If CVE fixes have a recognisable shape, that helps triage and silent-patch detection.

## What we did

23,110 classified C/C++ fix commits: latent-CVE 613, regression 644, extrinsic 1,869, other-fix 19,984. Guard clauses were extracted with tree-sitter; per-function signal gains and losses were compared by MH rate ratios with BH correction.

## What we found

- FORT-H1 ✓: CVE fixes add guards 1.88× (20% vs 11%) and remove them more (8% vs 5%): defences get restructured.
- FORT-V inconclusive: 80–84% of new guards extend an already-guarded variable, in every class.
- FIXK ✓✓✓: CVE signature beyond the defensive rules (pointers, metaprogramming, structural keywords gain); a regression signature exists; the two differ (Jaccard 0.17).

## Take-home

Fix kinds leave different structural fingerprints. That is useful for describing and routing fixes, though not on its own for finding unlabelled ones (see SILENT).

## What it changed

Fed SILENT and WH, and is the basis for the LAT-F registration (do fix kinds live in different shape families?).
