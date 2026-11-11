---
date: 2026-11-11
title: Does a file's comment profile predict its next year of fixes? (CPF)
type: confirmatory
status: scored
verdict: mixed
theme: comments
ids: CPF-F, CPF-V, CPF-R, CPF-N
docs: docs/cpf_hypotheses.md
links:
takehome: A file's comment profile adds nothing to predicting its next-year fixes or CVE fixes beyond size, churn and history (replicated nulls); in four unseen repos it adds a statistically real but negligible +0.003 AUC.
---

## Question

Files differ a lot, and stably, in how they are commented. Does a file's comment profile tell you anything about its
next year of fixes and CVE fixes that its size, churn and fix history do not?

## Why we asked

The owner found function-grain comment studies thin and asked for comments analysed as a whole (2026-11-11). The
outcome-blind profile study found strong file- and system-level structure. This tests whether it matters.

## What we did

Registered (owner OK 2026-11-11): [`../cpf_hypotheses.md`](../cpf_hypotheses.md).

## What we found

Scored in [`../cpf.md`](../cpf.md).
- **Core repos, replicated nulls.**
  - Any fix: lift −0.0003, 99% CI [−0.0016, +0.0009].
  - CVE fix: +0.0000 [−0.0061, +0.0064].
  - The size + churn + fix-history baseline reaches AUC 0.77.
- **Unseen repos (libgit2, libxml2, postgres, redis): supported but negligible.** +0.0027 [+0.0012, +0.0042];
  effort-aware recall 48.8% → 49.0%. Mostly header coverage, and postgres-dominated.
- **Comment neglect: not supported.** A file whose code grows ≥ 20% without new comments has a 0.88 [0.74, 1.07]
  next-year fix risk ratio once size and prior fixes are matched. The raw 40% vs 67% gap was confounding.

## Take-home

Comments describe how a project and a file are written, stably and distinctively, but at file grain they carry no
fix or CVE information that size, churn and history do not already carry.

## What it changed

- **It closes the "comment profile as a fix predictor" line** for file grain.
- **The remaining value of comments here is descriptive and per-function:**
  - danger wording at birth (DC-2, SCAR-I2);
  - system voice and culture, as context for why fixes mean different things per repo.
- **The core-vs-unseen contrast** is one more sign that fix labels and their predictors differ by project.
