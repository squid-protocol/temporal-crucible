---
date: 2026-11-06
title: Do different kinds of fixes have different causes? (XC)
type: confirmatory
status: scored
verdict: mixed
theme: defect-prediction
ids: XC-H1..H6
docs: docs/xc_hypotheses.md; docs/xc_curl.md; docs/xc_ndpi.md; docs/xc_openssl.md; docs/xc_label_audit.md
links: temporal-crucible#56; temporal-crucible#59
takehome: Fix classes have distinct histories (CVEs recur in place, extrinsic fixes recur on an environment-facing set of files, regressions follow general fix activity and never recur in place), but no snapshot metric sees the class.
---

# Do different kinds of fixes have different causes? (XC)

## Question

A "fix" covers three different events. An extrinsic fix adapts to a changed environment, a latent fix corrects code that was always wrong (CVEs), and a regression fix repairs something a recent change broke. Does each class answer to its own predictor?

## Why we asked

The owner proposed that pooling the classes dilutes any class-specific cause, which might explain why "history predicts, structure describes". Change entropy, churn and prior fixes had been tested only against security fixes or pooled labels.

## What we did

- A new harvester labelled commits on curl, nDPI and openssl as extrinsic, latent, regression or other-fix.
- Label precision gate ≥ 0.70. Regression and latent passed in round 1. The extrinsic rule failed (0.30–0.40) and was amended once (Amendment 1) before any predictor statistic: the environment must be named explicitly. The fresh re-audit passed.
- Unit: the as-of quarterly snapshots of FWD/EA, with C files as candidates.
- Lift = recall@20% of lines minus the snapshot's stronger LOC order.
- Six claims: change entropy finds regressions (H1), specifically (H2); external includes find extrinsic fixes (H3), specifically (H4); same-class history beats other-class history for regressions (H5) and extrinsic fixes (H6).
- A claim holds only if supported on every repo.

## What we found

- **H1/H2** (change entropy finds regressions, specifically): supported on openssl only (+0.090 / +0.115).
- **H3/H4** (external includes): not supported anywhere.
- **H5 reversed:** prior other fixes beat prior regressions on every repo (openssl −0.113, CI [−0.170, −0.062]).
- **H6** (extrinsic fixes recur on their own history): supported on curl (+0.094) and openssl (+0.194), not on nDPI.
- Headline rule: **mixed**. No H1–H4 cell is an equivalence null, so the theory is not falsified either.
- Descriptive: CVE history beats size on all three repos, so recidivism turns out to be a property of latent defects. Generic other fixes are beaten by nothing.
- Exploratory follow-ups (not registered): platform-conditional `#if` density per line beat size for extrinsic fixes and was worse than size for every other class. Extrinsic work is bursty on all five repos looked at.

## Take-home

Fixes are not one phenomenon: each class has its own history signature. None of these causes can be read off a static snapshot.

## What it changed

The platform-conditional measure was registered as ENV-H1..H3 on unseen repos, where it replicated (see the coupling entry). The burstiness became BURST-H1..H3. XC's class labels became the outcome for LV, INP, SC, REG, AGE and CEN. Class-conditioned recidivism (a file's own-class history beats its pooled history) is the next registration owed.
