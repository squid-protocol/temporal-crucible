---
date: 2026-11-08
title: Hubs, efficiency, bad shapes and dead code in call networks over time
type: confirmatory
status: scored
verdict: mixed
theme: natural-history
ids: CGN-A1..E1
docs: docs/cgn_hypotheses.md; docs/cgn.md
links: temporal-crucible#92
takehome: Hubs are a stable skeleton that grows rich-get-richer; networks centralise and drift toward more cross-file wiring rather than optimising; files in call cycles or with heavy coupling get more later fixes beyond size, churn and their own fix history.
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

- **Hubs (✓ A1-A3):** 76-100% of surviving hubs are still top-5% central five years on; most hubs are made within two
  years of birth; new calls go to already-central functions (70th-83rd percentile targets).
- **Efficiency (✗ B1, ✗ B2, ✓ B3):** no sign of optimisation. Directory modularity falls in OpenSSL and libarchive;
  cross-file wiring rises in curl, libarchive and nDPI; networks centralise in four of five repos.
- **Bad shapes (✓ C1, ✓ C3, ✗ C2, ✗ C4):** beyond file size, churn and prior fixes, files in call cycles get 1.20x and
  highly coupled files 1.76x the later fixes; duplicated wiring goes with fewer fixes (0.86x); coupled files' fixes are
  not more often regressions.
- **Concurrency (✗ D1, ✓ D2):** concurrency code sits at the network periphery (0.24x odds of being in the core); too
  rare in these C libraries (48 functions) to test hub avoidance.
- **Dead code (✓ E1):** uncalled private functions are deleted slightly sooner (1.08x).

## Take-home

Call networks grow around a stable skeleton of hubs that get richer; they centralise and drift toward more
cross-file wiring rather than optimising; and cycles and heavy coupling mark files that will need more fixes, beyond
size, churn and their own history.

## What it changed

- With CGT-4, three network signals (rewiring, cycles, coupling) now survive the controls that sank earlier structural
  predictors here: leads to replicate on unseen repos (CGN-CR), not yet claims.
- The owner's optimisation idea is not supported on these repos; Lehman-style drift fits better.
