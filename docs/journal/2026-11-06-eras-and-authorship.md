---
date: 2026-11-06
title: Regimes and authorship in GitGalaxy's own history (GG, FLT)
type: confirmatory
status: scored
verdict: mixed
theme: natural-history
ids: GG-H1..H3; FLT-H1..H3
docs: docs/gg_hypotheses.md; docs/flt_hypotheses.md
links: temporal-crucible#75; temporal-crucible#76
takehome: Development regimes leave a structural mark (Gemini-era vs Claude-era AUC 0.877), but the autonomous fleet does not write measurably differently from interactive sessions.
---

# Regimes and authorship in GitGalaxy's own history (GG, FLT)

## Question

Can GitGalaxy tell apart the eras of its own development, and the code written by the autonomous fleet vs interactive sessions?

## Why we asked

The engine had never been pointed at its own history, which has known regime changes.

## What we did

Scanned GitGalaxy's history. GG classified eras against within-era placebos; FLT attributed code to the fleet or to interactive sessions and compared their structure, including inside tools/.

## What we found

- GG-H1 ✓: eras are distinguishable (AUC 0.877 vs placebos about 0.7). Claude-era code is small, typed, branch-dense helpers.
- FLT ✗ (all three): fleet vs interactive AUC 0.640, below within-group drift (about 0.70). FLT also reversed an exploratory GG note: interactive sessions, not the fleet, wrote most of tools/.

## Take-home

Regimes are visible in structure; individual authors (fleet vs human-steered) are not. The era bundles model, tooling and workflow, so do not credit the model alone.

## What it changed

Codebase biography became one of the engine's defensible uses (see TAKEHOMES).
