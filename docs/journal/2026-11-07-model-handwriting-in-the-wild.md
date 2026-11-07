---
date: 2026-11-07
title: Does model handwriting survive inside a shared codebase? (WILD)
type: confirmatory
status: scored
verdict: not-supported
theme: natural-history
ids: WILD-H1..H2, WILD-C1
docs: docs/wild_hypotheses.md; docs/wild.md
links: squid-protocol/agent-habits
takehome: Inside GitGalaxy's shared codebase, Sonnet- and Opus-written functions are barely distinguishable (AUC 0.57, inside the commit-permutation null): the lab's strong model handwriting mostly vanishes under a codebase's conventions.
---


## Question

In the lab each model writes recognisably. Inside one shared codebase, with house rules, linters and review, can you still tell which model wrote a function?

## Why we asked

agent-habits (lab) found model handwriting at 83–84%; FLT found the fleet and interactive sessions indistinguishable in GitGalaxy (AUC 0.64, below placebo). GitGalaxy's commit trailers name the model, which allows a direct test in one codebase and era. Prior: conventions likely dominate.

## What we did

Born Python functions in single-model Sonnet 5.5 / Opus 5.5 commits on GitGalaxy main (2026-10-03..11-07). Features: lattice signals plus agent-habits-style habits. H1: stratified AUC by directory × size with a week-blocked commit permutation. H2: context vs model distance ratio. C1: a pseudo-model control. See `wild_hypotheses.md`.

## What we found

- **H1 ✗:** stratified AUC 0.572; the week-blocked commit-permutation null reaches 0.557 (99th percentile 0.582);
  p 0.089.
- **H2 ✗ as registered:** context/model distance ratio 0.922 (99% CI 0.897–0.946). The direction is right but the
  registered < 0.90 bar is missed.
- **C1:** passed (0.482).
- **Data:** 13,145 born functions from 2,016 commits.
- **Descriptive:** Sonnet's new functions are smaller, have fewer docstrings (32% vs 44%), fewer calls and less
  nesting. The family mix is identical.

## Take-home

- Model handwriting is a property of a model writing alone.
- Inside a shared codebase, in one era, conventions and review make Sonnet and Opus code nearly indistinguishable,
  function by function. This matches FLT.

## What it changed

- Forensic attribution of individual functions inside team codebases is not supported by structure alone. Lab-style
  identification (whole programs written autonomously) remains promising: round 3 tests it on fresh runs.
- Attribution claims need commit-blocked nulls: clustered labels alone inflate AUC to about 0.56.
