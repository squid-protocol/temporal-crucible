---
date: 2026-11-08
title: Hubs, efficiency, bad shapes and dead code in call networks over time
type: confirmatory
status: registered
verdict: pending
theme: natural-history
ids: CGN-A1..E1
docs: docs/cgn_hypotheses.md
links: temporal-crucible#92
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

Do central functions stay central, and when do hubs appear? Do systems optimise their call graphs over time? Do bad
network shapes (cycles, duplicated wiring, heavy coupling) go with later fixes, and are kinks harder to work out in
tangled code? Does concurrency code avoid the hubs? Does uncalled code die?

## Why we asked

CGT found call networks are static with jumps, and that rewiring marks files needing later fixes. The owner asked
about hubs, efficiency, bad shapes and concurrency. Priors: centrality failed for CVEs; recidivism dominates;
coupling centralisation was project-specific; young functions die faster.

## What we did

Registered in `docs/cgn_hypotheses.md` before any statistic: hub persistence, birth and preferential attachment;
modularity, cross-file share and centralisation trends; file-level cycle, duplication and coupling exposures against
later fixes with size, churn and prior-fix strata; concurrency vs hubs and core; orphan deletion.

## What we found

Pending.

## Take-home

Pending.

## What it changed

Pending.
