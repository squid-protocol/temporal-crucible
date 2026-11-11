---
date: 2026-11-11
title: Do fix commits repay debt less often than other commits? (DRP)
type: confirmatory
status: scored
verdict: mixed
theme: comments
ids: DRP-R, DRP-S
docs: docs/drp_hypotheses.md
links:
takehome: Fix commits repay TODO/FIXME debt less often than other commits (0.77×, replicated on four unseen repos), but only because fixes are small; at equal size they repay just as often.
---

## Question

In the core repos, fix commits removed TODO/FIXME debt at about half their share of commits. Does that hold on unseen
repos, and is it more than fixes simply being small commits?

## Why we asked

The exploratory debt study (PR #147) found the pattern in all five core repos, item-level and without an interval. The
owner chose to register it and log the result rather than build further on debt.

## What we did

Registered (owner OK 2026-11-11): [`../drp_hypotheses.md`](../drp_hypotheses.md).

## What we found

Scored in [`../drp.md`](../drp.md), on 65,168 commits in libgit2, libxml2, postgres and redis.
- **DRP-R, supported.** Fix commits repay debt less often: 2.34% vs 2.87%, MH RR 0.77 (upper bound 0.86).
- **DRP-S, not supported.** Within commit-size bins, RR 1.07 (upper bound 1.20).
- Repaying debt rises steeply with commit size (0–0.3% for 1–2-line commits, 15–21% over 512 lines) for fixes and
  non-fixes alike.

## Take-home

Debt is repaid by big commits. Fixes repay less only because they are small. The exploratory "clean-ups, not fixes"
reading was size.

## What it changed

- It closes the debt-repayment thread as a logged result.
- Debt lifecycle stays a descriptive, per-project fact (age, repayment rate, who repays): something the engine can
  report, not a predictor.
