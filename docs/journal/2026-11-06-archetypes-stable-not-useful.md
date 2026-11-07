---
date: 2026-11-06
title: Are GitGalaxy's archetypes stable, and are they useful? (ARCH, ARCH-Z)
type: confirmatory
status: scored
verdict: mixed
theme: fingerprints
ids: ARCH-S1..S5, ARCH-U1..U4; ARCH-Z1..Z4
docs: docs/archetype_hypotheses.md; docs/arch_stability_curl.md; docs/arch_stability_ndpi.md; docs/arch_stability_openssl.md; docs/arch_useful_curl.md; docs/arch_useful_ndpi.md; docs/arch_useful_openssl.md; docs/arch_func_useful_curl.md; docs/arch_func_useful_ndpi.md; docs/arch_z_curl.md; docs/arch_z_ndpi.md; docs/arch_z_openssl.md
links: temporal-crucible#54
takehome: Archetype labels are deterministic and track how much code changes (about 98% kept under small edits), but neither the label nor how atypical a file is for its label finds fixes beyond file size on curl, nDPI or openssl.
---

# Are GitGalaxy's archetypes stable, and are they useful? (ARCH, ARCH-Z)

## Question

GitGalaxy gives every file and function an archetype label from a frozen k-means "brain". Does a file keep its label while its code barely changes? Does the label, or how far a file sits from its label's centroid, say anything about where fixes land that file size does not?

## Why we asked

The archetypes had never been related to any outcome in this program. The brains were trained without outcome labels, so all three repos (curl, nDPI, openssl) were unseen for every claim. The priors were that usefulness would be hard to show, since every structural signal so far reduced to size.

## What we did

- **Stability (S1–S5).** S1 was a binding determinism gate: at least 0.999 of unchanged blobs keep their label. S2 required at least 0.90 retention under edits of 5% or less. S3–S5 were descriptive: one-year agreement, label changes on unchanged blobs, and flip rate by centroid margin. Data: curl 3,547 snapshots, nDPI 555, openssl 110.
- **Usefulness (U1–U4).** A per-label fix density was learned forward only (from windows already closed at t) for file-cluster and composition labels. It had to beat both LOC orders at recall@20% of lines on on-master security fixes in the next 180 days (U1, U2). Size adjusted by label had to beat size by AUC at file grain (U3) and function grain (U4, on the FREC event set).
- **Atypicality (ARCH-Z, registered separately).** Composition fit z and file-cluster centroid distance were scored by recall@20 (Z1, Z2) and by size-stratified AUC (Z3, Z4).
- Snapshot bootstrap with 5,000 rounds and an equivalence band of ±0.02.

## What we found

- **Stability passes everywhere.** S1 is 0.99993–1.00000 for files and 1.00000 for functions on all three repos. S2 is 0.980 / 0.980 / 0.967, so the labels are trackable. One-year κ is 0.88–0.94. A thin centroid margin flags unstable labels: 8–13% of edited files flip in the lowest margin decile, against 1–3% in the middle.
- **Usefulness fails everywhere.** U1–U4 are not supported on any repo. Archetype rankings sit between the two size orders and never beat largest-first. U3 on openssl and U4 on curl and nDPI are equivalence (replicated) nulls. On curl and nDPI, adjusting size by archetype makes the ranking slightly worse.
- **Atypicality fails too.** No Z claim is supported on any repo, and the direction is inconsistent. Atypical files run slightly riskier on curl and openssl, but on nDPI typical files are riskier (sign-flipped stratified AUC 0.646, exploratory).
- Engine observation: the "file-local" file-cluster model is not strictly file-local. A few unchanged nDPI and openssl files changed label at one commit pair.

## Take-home

Archetypes are a stable vocabulary for what kind of code something is. They are not a risk signal.

## What it changed

Archetypes are kept as description and not used as a risk or review-priority input. Any combined model must first beat size plus prior fixes on an unseen repo. The low-margin "borderline label" flag is the one stability property worth surfacing. A label flip in the prior year (nDPI, exploratory) is the only lead, and it needs its own registration.
