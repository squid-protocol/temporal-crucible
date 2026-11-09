---
date: 2026-11-08
title: How accurate is a compile-free call graph, per language?
type: confirmatory
status: registered
verdict: pending
theme: engine
ids: ACC-H1..H3
docs: docs/acc_hypotheses.md
links: temporal-crucible#98
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

How close is GitGalaxy's compile-free call graph to compiler-grade call graphs in C, Java, Go and Python, and do the
network statistics the call-network studies rely on survive the difference?

## Why we asked

Step 1 of the call-network programme: every cross-language claim needs per-language accuracy first. Prior work
shows extractors disagree even within one language (Murphy et al. 1998) and that oracles are imperfect too.

## What we did

Registered in `docs/acc_hypotheses.md` before any oracle install or run: libclang, java-callgraph, go/callgraph and
PyCG on pinned snapshots of five repos; direct-call precision and recall, disagreement by dispatch kind, and
agreement of in-degree ranks, hub sets and file coupling.

## What we found

Pending.

## Take-home

Pending.

## What it changed

Pending.
