---
date: 2026-09-12
title: The first validation program: do GitGalaxy's exposure scores track real defects?
type: program
status: scored
verdict: not-supported
theme: defect-prediction
ids: H1; RW-H2
docs: docs/HYPOTHESES.md; docs/EXPERIMENTS.md; docs/exposure_history_report.md
links: gitgalaxy#2982; gitgalaxy#2991
takehome: History predicts fixes (recidivism, change entropy); per-file structural scores reduce to file size.
---

# The first validation program: do GitGalaxy's exposure scores track real defects?

## Question

Do commits identified as security fixes reduce GitGalaxy's per-file exposure, and do vulnerability-introducing commits raise it?

## Why we asked

GitGalaxy reported risk_* exposure vectors. The program existed to test whether they mean what their names said.

## What we did

Event-pair scanning of curl's 25-year CVE history, then nDPI, then 1,107 curl bug and regression commits: about 3,550 scanned snapshots. Every claim was pre-registered, with temporal ablation, size-matched controls and rename tracking. Details: the plain-language summary in `HYPOTHESES.md` and the predictor × outcome matrix in `EXPERIMENTS.md` (September–October 2026; many register rows).

## What we found

- Recidivism (the file that had the last fix gets the next) beats every static ranking on both repos (RW-H2, p < 1e-4).
- Change entropy (Hassan HCM) is the only feature to beat a line count out of selection.
- Every per-file structural score, pooled or density-normalised, reduces to size (equivalence-confirmed nulls).

## Take-home

History predicts; structure describes. A per-file structural score is not a defect predictor once size is controlled.

## What it changed

The engine renamed its risk_* vectors to descriptive surface names (gitgalaxy#2991, Option A). The program turned from "does structure predict bugs" to "what is the engine actually good for", which is the November arc below.
