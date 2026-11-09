---
date: 2026-11-08
title: How accurate is a compile-free call graph, per language?
type: confirmatory
status: scored
verdict: mixed
theme: engine
ids: ACC-H1..H3
docs: docs/acc_hypotheses.md; docs/acc.md
links: temporal-crucible#98
takehome: GitGalaxy's compile-free C call graphs agree with libclang well enough for network science (hubs, ranks and coupling survive), but Java hubs do not survive name-only node identity, and Go and Python were not evaluable in this run.
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

- **C (libgit2, redis):** precision 0.76-0.84, recall 0.81-0.94 against libclang. In-degree ranks (rho 0.83-0.87),
  hub sets (Jaccard 0.67-0.69) and file coupling (kappa 0.87-0.92) agree. 10-17% of call sites are function pointers.
- **Java (commons-lang):** precision and recall 0.78, but the hub set disagrees (Jaccard 0.29). Only 1,942 of 8,734
  engine functions match, because (file, name) identity merges overloads and same-named methods.
- **Go:** not evaluable, a scorer flag that Go workspaces refuse. **Python:** not evaluable, PyCG crashed on sphinx.

## Take-home

The call-network studies' C results rest on a validated instrument; cross-language claims need class-aware node
identity and working Go and Python oracle runs first.

## What it changed

- LAWS's ACC gate currently admits only C as confirmatory.
- ACC-2 (class-aware identity, Go workspace fix, Python oracle that completes) comes before the many-labs panel.
