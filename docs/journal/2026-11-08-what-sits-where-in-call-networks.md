---
date: 2026-11-08
title: What kind of code sits where in the call network, and where do fix classes land?
type: confirmatory
status: registered
verdict: pending
theme: fingerprints
ids: CGK-K1..F11
docs: docs/cgk_hypotheses.md
links: temporal-crucible#94
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

Which keyword signals go with hubs, orchestrators and the network's periphery? Do hubs have a specific shape? Do the
three fix classes (regression, CVE, extrinsic) land in files with different network positions?

## Why we asked

CGN showed hubs are a stable skeleton and that coupling and cycles go with later fixes. The owner asked what kind of
code sits in those positions, and whether the programme's fix-class model maps onto the network.

## What we did

Registered in `docs/cgk_hypotheses.md` before any statistic: size-stratified CMH on the latest snapshots for
complexity, publicness and a 26-signal x 3-role screen; low-rung lattice shapes in hubs; a Bonferroni grid of fix
class x file network position.

## What we found

Pending.

## Take-home

Pending.

## What it changed

Pending.
