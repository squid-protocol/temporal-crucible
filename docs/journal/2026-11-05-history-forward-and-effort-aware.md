---
date: 2026-11-05
title: Engine history read as of each snapshot: forward tests, function memory and review budgets (FWD, FREC, EA)
type: confirmatory
status: scored
verdict: mixed
theme: defect-prediction
ids: FWD-H1..FWD-H3; FREC-H1 / FREC-H2; EA-H1..EA-H5
docs: docs/fwd_ndpi.md; docs/fwd_curl.md; docs/frec_curl.md; docs/frec_ndpi.md; docs/ea_openssl.md; docs/engine_validation.md
links: temporal-crucible#29; temporal-crucible#51; temporal-crucible#52
takehome: Scored by AUC, the engine's own history columns lose to file size on nDPI and function memory loses to function size, but scored per line reviewed on unseen openssl, prior security fixes (recall@20 0.451 vs 0.271) and change entropy beat both size orders.
---

# Engine history read as of each snapshot: forward tests, function memory and review budgets (FWD, FREC, EA)

## Question

The program's two surviving predictors (recidivism, change entropy) had only been computed ad hoc from git. Can the engine's own history columns, read as of time t, predict which files get fixed after t?
- **FWD:** churn, ownership entropy and change entropy, scored by AUC within size bands, on nDPI.
- **FREC:** inside the files a fix touches, is the function fixed before the one fixed next?
- **EA:** on unseen openssl, do history features find fixed files per line reviewed (recall@20 against both LOC orders)?

## Why we asked

gitgalaxy#7818 added an as-of history mode (tc#29), so the engine could measure history without leakage. Earlier scans all ran with history ablated. curl supplied the evidence these features rest on, so it ran as an instrument check and exploratory context only.

## What we did

- **FWD.** 43 quarterly as-of nDPI snapshots, with security fixes in the next 180 days as the outcome. Binding instrument gates: churn reconstruction rho ≥ 0.95, and HCM parity with `HCM1_LD_30` ≥ 0.99. Amendment 1 was recorded before any nDPI statistic: the gate's churn definition was corrected, and single-commit snapshots excluded.
- **FREC.** curl (security and bug classes) and nDPI. Within-event AUC of prior function-fix count against function size, on the later half of events by date.
- **EA.** 110 openssl quarterly snapshots. Five predictors had to beat both LOC-desc and LOC-asc at recall@20, at α = 0.01 / 5.
  - The first run failed both gates, so all verdicts were withheld.
  - The cause was an engine bug: a Latin-1 byte silently truncated the history stream. It was fixed in gitgalaxy (`errors="replace"`) and everything was rescanned. Claims were unchanged.
  - The withheld numbers seen before the fix are disclosed in the register.

## What we found

- **FWD-H1 to H3 not supported (inconclusive)** on nDPI. Pooled AUC: LOC 0.700, change entropy 0.667, ownership 0.598, churn 0.595. Decision rule (b): history columns stay descriptive.
- **FREC-H1 and H2 not supported** on curl and nDPI. Function memory has signal on its own (within-event AUC 0.67 and 0.69), but function size carries more.
- **EA (openssl, gates pass 110/110):**
  - **EA-H1 change entropy supported:** recall 0.343, a narrow margin over LOC-desc (lo +0.013).
  - **EA-H2 churn not supported** (inconclusive).
  - **EA-H3 recency not supported** (inconclusive).
  - **EA-H4 prior security fixes supported:** 0.451 vs 0.271, lo +0.047.
  - **EA-H5 prior fixes per line supported**, but redundant with H4 at the 20% budget.
- Under plain AUC, LOC still ranks best on openssl (0.816).

## Take-home

AUC and recall per line reviewed answer different questions. History loses the first and wins the second, which is the question a reviewer actually asks.

## What it changed

- EA's decision rule (a) applies: a gitgalaxy issue for an effort-aware "review budget" ranking on prior security fixes and change entropy. A further unseen-repo replication must be registered before either feeds a score weight.
- The function dossier's predictive line stays file-grain (FREC rule c).
- The as-of mode and gated history columns became infrastructure for XC, ARCH-U, NM, SC and CEN.
