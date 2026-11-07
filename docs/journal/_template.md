---
date: YYYY-MM-DD
title: <title>
type: confirmatory
status: draft
verdict: pending
theme: defect-prediction
ids:
docs:
links:
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

What did we want to know, in plain words?

## Why we asked

What earlier result, hunch or product need led here? Name the priors honestly.

## What we did

Data, units, registered tests and bars, guards (size placebo, shuffle, blind audit, file-cluster bootstrap).
Link the registration commit.

## What we found

The numbers, each verdict either way. Mark anything exploratory as exploratory.

## Take-home

The one or two sentences someone should remember, at the right evidence level.

## What it changed

What we now do or believe differently; follow-up studies, engine issues, open questions.
