---
date: 2026-11-10
title: Danger comments that stayed safe: is there a code signature? (DCS)
type: confirmatory
status: registered
verdict: pending
theme: comments
ids: DCS-T, DCS-F, DCS-C, DCS-ALL
docs: docs/dcs_hypotheses.md
links: temporal-crucible#122
takehome: Registered, not yet scored.
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

Pending.

## Take-home

Pending.

## What it changed

Pending.
