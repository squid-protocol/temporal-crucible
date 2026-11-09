---
date: 2026-11-08
title: Do the call-network findings replicate on unseen repos and other languages?
type: confirmatory
status: registered
verdict: pending
theme: natural-history
ids: CGR-*
docs: docs/cgr_hypotheses.md
links: temporal-crucible#92; temporal-crucible#94; temporal-crucible#96
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

Do the CGT, CGN and CGK call-network findings hold on repositories never used for them, and in languages other than
C? Which of the three bug-related network signals (rewiring, coupling, cycles) carries the effect when they compete?

## Why we asked

All three studies ran on five heavily studied C libraries. Their leads need unseen data, and the owner asked whether
findings like pointer-rich hubs are language artefacts.

## What we did

Registered in `docs/cgr_hypotheses.md` before any scan: eight new repos (four C; Go, Java, Python, Rust), one engine,
the original scorers unchanged with the repo list and pass rules swapped, each claim in its observed direction, plus
language and joint-model claims.

## What we found

Pending.

## Take-home

Pending.

## What it changed

Pending.
