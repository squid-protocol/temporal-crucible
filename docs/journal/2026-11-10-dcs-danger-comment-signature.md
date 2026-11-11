---
date: 2026-11-10
title: Danger comments that stayed safe: is there a code signature? (DCS)
type: confirmatory
status: scored
verdict: not-supported
theme: comments
ids: DCS-T, DCS-F, DCS-C, DCS-ALL
docs: docs/dcs_hypotheses.md
links: temporal-crucible#122
takehome: Among danger-commented functions, nothing the engine measures at birth (telemetry, lattice family, call-graph position) beat size + repo + prior-CVE-file at telling which got a CVE fix within 5 years; the discovery signature did not survive held-out functions.
---

## Question

Most functions whose authors wrote danger comments never get a CVE fix. Can the engine tell, at birth, which ones
will?

## Why we asked

- DC-2 showed danger comments predict CVE fixes (1.45×), but most danger-commented functions stay safe.
- The owner asked whether telemetry, fingerprints and the lattice, or call-graph position separate the two groups.

## What we did

Registered only: [`../dcs_hypotheses.md`](../dcs_hypotheses.md).
- Units are danger-commented functions with 5 years of follow-up. Cases had a CVE fix within 5 years; controls were
  alive and CVE-free at 5 years.
- Exploratory discovery runs on the earlier-born half, per repo. The models are frozen and committed. Then the
  confirmation test runs on the later-born half: the AUC lift of each feature family over a loc + repo +
  prior-CVE baseline.
- 2026-11-11, Stage 1 (exploratory) frozen: [`../dcs_discovery.md`](../dcs_discovery.md) and the fitted models
  `docs/dcs_models.json` were committed before Stage 2 read any confirmation function (`tools/dcs_eval.py`).

## What we found

Scored in [`../dcs.md`](../dcs.md); exploratory discovery in [`../dcs_discovery.md`](../dcs_discovery.md).
- **Cohort.** Discovery had 534 functions and 15 cases (2.8%). Confirmation had 502 functions and 30 cases (6.0%),
  so the ≥ 20-case power rule was met.
- **Baseline.** Size + repo + prior-CVE-file alone reached AUC 0.675 on confirmation.
- **No family added to it.** Telemetry +0.011 [−0.014, +0.031]; fingerprint / lattice −0.033; call graph −0.034;
  all three −0.019 (99% CIs). All four claims are **not supported**. All are **inconclusive** rather than
  replicated nulls, because the CIs reach past ±0.02.
- **Discovery overfit.** In discovery, B + C had the best CV AUC (+0.032). In confirmation it was the worst. 8 of
  the screen's top 15 features flipped sign, including the "F7 is protective" lead (OR 0.16 → 1.46).
- **Robustness.**
  - The shrinkage control (B refitted at each model's penalty) gives the same lifts.
  - Counting early deaths as controls gives the same lifts.
  - On plain-commented functions the frozen models also add nothing (lifts −0.030 to +0.010).
  - Effort-aware recall at 20% of lines: B 63% beats every family model (23–47%).

## Take-home

The authors' danger comments flag risk (DC-2), but inside that flagged set the engine's birth-time structure does not
tell the dangerous ones from the safe ones beyond size. This is another case of "structure reduces to size", now
within a cohort chosen by the authors' own warnings. Call-graph position, the literature's best vulnerability
signal, did not help either.

## What it changed

- Closes the DCS lead. A signature for danger-commented code would need a larger cohort (more repos) to get the CI
  inside ±0.02 and call a replicated null.
- The two-stage freeze worked as intended: the discovery winner (C) and screen leads did not replicate.
