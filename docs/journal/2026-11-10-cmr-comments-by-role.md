---
date: 2026-11-10
title: Do comments sit differently by call-graph role, and does that change what they predict? (CMR)
type: confirmatory
status: scored
verdict: mixed
theme: comments
ids: CMR-P1..P2, CMR-FD, CMR-FC
docs: docs/cmr_hypotheses.md; docs/cmr.md
links: temporal-crucible#127; temporal-crucible#134
takehome: Comments sit by call-graph role (hubs explained more, the periphery less but with more warnings), but no role changes what a danger comment predicts.
---

## Question

Do comments, and danger comments, cluster in hubs, orchestrators or the periphery of the call graph? Does what a
danger comment predicts (CVE, regression or extrinsic fix) change with the function's role?

## Why we asked

CGK found sharp role profiles, and that extrinsic fixes map onto network position. DC-2 found danger comments
predict CVE fixes. No study has crossed the two.

## What we did

Registered: [`../cmr_hypotheses.md`](../cmr_hypotheses.md).

## What we found

48,214 function births in five repos, each with its role at birth. Comparisons are at equal size.
- **Hubs are more often commented** (1.33 ✓).
- **Peripheral functions are less often commented** (0.87 ✓). When they are, the comment is more often a warning
  (1.25 ✓).
- **Orchestrators' comments are less often danger-worded** (0.60 ✓).
- The other two placement cells are not significant: whether orchestrators are commented, and whether hubs'
  comments are danger-worded.
- **No role changes the comment → fix link** for CVE, regression or extrinsic fixes. Of 18 cells, 10 are not
  significant and 8 are underpowered.

## Take-home

Where comments go follows a function's job. The most-called code is explained most. Private low-level code is
explained least, but warned about most. That placement does not make danger comments more or less predictive in any
role.

## What it changed

- Comment placement is a size-independent part of each role's profile, alongside CGK's keyword profiles.
- DC-2's danger → CVE link looks role-independent at this power. A role × class interaction would need far more
  hubs, either from later-life roles or from more repos.
- The raw orchestrator shares reverse within size strata. Any comment-density reading by role must be
  size-stratified.
