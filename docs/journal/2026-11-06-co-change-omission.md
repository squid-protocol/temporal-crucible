---
date: 2026-11-06
title: Do regressions come from commits that leave co-change partners behind? (REG)
type: confirmatory
status: scored
verdict: not-supported
theme: defect-prediction
ids: REG-H1 / H2
docs: docs/reg_hypotheses.md; docs/reg.md; docs/reg_link_audit.md
links: temporal-crucible#65
takehome: A commit that skips files that usually change with the ones it touches is not more often regression-inducing once commit size is controlled (−0.012), and omission is equivalent to merely touching well-coupled files; commit size stays the best predictor.
---

# Do regressions come from commits that leave co-change partners behind? (REG)

## Question

Files that historically change together share an unstated contract. Is a commit that edits one side of that contract but not the other more often later named as regression-inducing, beyond its size? And is that because of the omission itself, rather than just touching coupled files?

## Why we asked

XC-H5 showed that regressions never recur in place, and SC found no file metric for them. So regressions are a property of changes, not files, and a commit-level, mechanism-first design was the right next step. The literature has "missed partner" heuristics (logical coupling), but they had not been tested against commit size.

## What we did

- **Data.** 64,820 candidate commits on curl, openssl, harfbuzz and nDPI, 1,199 of them regression-inducing. Binding inducing-link audit gate ≥ 0.70, passed at 0.77–0.87.
- **Co-change model.** Built from history only: 730 days before each commit, with a strong partner at 3 or more co-changes and confidence ≥ 0.5.
- **CCO** = expected missing partners per touched file. Placebo **DEG** = all strong partners, touched or not.
- **H1:** CCO beats size, by stratified AUC within 20 commit-size bins. **H2:** CCO beats DEG.
- Pooled over repos, α = 0.01 / 2, equivalence band ±0.02.

## What we found

- **REG-H1 not supported (inconclusive):** −0.012 (90% CI [−0.037, +0.015]). Per repo: curl −0.005, openssl −0.029, harfbuzz −0.035, nDPI +0.023.
- **REG-H2 is a replicated null (equivalence):** −0.002, CI [−0.013, +0.009].
- Inducing commits do leave partners behind more often (curl 38% vs 27%), but only because they are bigger. Within size bins the difference vanishes.
- Descriptive: commit size has raw AUC 0.70 on curl and 0.64 on openssl. harfbuzz's labels are mostly reverts of optimisation attempts, and nothing predicts them.

## Take-home

Leaving co-change partners untouched carries no information beyond how big the change is.

## What it changed

Designing from a mechanism is necessary but not sufficient: two mechanism-first designs held (ENV, LIB) and this one did not. Regression prediction stays with commit size and churn (see CHG-2).
