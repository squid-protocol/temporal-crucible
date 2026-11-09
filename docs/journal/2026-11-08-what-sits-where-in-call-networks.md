---
date: 2026-11-08
title: What kind of code sits where in the call network, and where do fix classes land?
type: confirmatory
status: scored
verdict: mixed
theme: fingerprints
ids: CGK-K1..F11
docs: docs/cgk_hypotheses.md; docs/cgk.md
links: temporal-crucible#94
takehome: Hubs are public, decision-dense entry points and workhorses, not simple utilities; callers of many are straight-line glue; the periphery is private, low-level code; and only extrinsic fixes map onto the network, landing in peripheral files that host hubs.
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

- **Hubs (✓ K3, ✗ K1, ✗ H1):** the most-called functions are 6x more often public, more decision-dense per line than
  same-size functions (opposite of the registered direction), and built from rich shapes (rungs 5-9), not bricks.
  Archetypes: parameter forwarders, compute cores, many-argument workhorses, defensive guards.
- **Orchestrators (✗ K2):** functions that call many are less decision-dense: straight-line, stateful glue
  (pointers, state changes, casts, safety checks).
- **Periphery:** globals, private scope, bit operations, memory allocation, unsafe constructs.
- **Fix classes:** extrinsic fixes land in peripheral files that host hubs (wrapper and compatibility layers) and
  avoid coupled and cyclic files; CVE fixes and regressions show no network preference at the bar.

## Take-home

Network position has a clear keyword profile: hubs are public decision-makers, orchestrators are glue, the
periphery is private low-level code. Of the three fix classes, only platform-driven (extrinsic) fixes have a network
signature.

## What it changed

- Two registered directions came out reversed (K1, K2, H1): the "hubs are simple helpers" intuition is wrong for these
  C libraries.
- Extrinsic work joins library coupling (LIB) as a place where the outside world touches the network: a lead to
  replicate.
