---
date: 2026-11-06
title: Does any engine metric find one specific fix class? The 225-metric screen (SC)
type: confirmatory
status: scored
verdict: mixed
theme: defect-prediction
ids: SC (protocol)
docs: docs/sc_protocol.md; docs/sc_discovery.md; docs/sc_discovery_table.csv; docs/sc_confirmation.md; docs/sc_confirmation_72snap_sensitivity.md
links: temporal-crucible#61
takehome: Of 225 GitGalaxy file-metric forms, only platform-conditional density per line finds one fix class (extrinsic) at equal size on unseen repos (+0.154 harfbuzz, +0.102 libarchive); no metric finds CVEs beyond size, and the churn candidates for regressions and other fixes failed holdout.
---

# Does any engine metric find one specific fix class? The 225-metric screen (SC)

## Question

Nearly every engine metric had been tested only against security fixes or pooled fixes, where it reduced to size. Does any file metric help find one class (latent, extrinsic, regression or other-fix) at equal size?

## Why we asked

XC split fixes into classes, and one measure (platform-conditional density) turned out to be class-specific. A screen asks the same question of every metric at once. Its design (discover on seen repos, confirm on unseen ones) keeps the screen's own selection from counting as evidence.

## What we did

- **Stage 1, discovery** (exploratory by construction; the selection rule was registered first).
  - Every numeric `file_data` column on C files, raw and per line, on curl, nDPI and openssl.
  - Size-matched AUC (D) in 50 LOC bins, plus effort-aware recall@20 lift (R).
  - The top 5 per class with D and R positive on all three repos, de-duplicated at |ρ| > 0.8, were frozen.
  - Instrument check: the screen had to recover platform-conditional density for extrinsic fixes. Run 1 failed the check (an index-alignment bug in the scorer), was fixed and rerun. Run 2 passed, with 225 forms entering.
- **Stage 2, confirmation.** Registered before the holdout join: harfbuzz and libarchive, never scanned before this study. Each frozen (candidate, class) pair had to pass on every evaluable holdout repo at α = 0.01 / 4.

## What we found

- **Discovery:** latent had 0 candidates. Extrinsic had `platform_cond /line`. Regression had `raw_churn_freq /line`. Other-fix had `risk_churn /line` and `pct_vec_churn /line`. No archetype, risk vector, centrality, family or shape statistic passed for any class.
- **`platform_cond /line` → extrinsic CONFIRMED:** harfbuzz +0.154, libarchive +0.102.
- **Churn per line → regression not confirmed:** harfbuzz +0.000, with libarchive's regression labels withheld.
- **Other-fix candidates not confirmed:** they pass on harfbuzz and miss on libarchive.
- **Correction.** The libarchive "unscannable commit" first recorded as an engine bug was a duplicate-SHA race in the batch rescan tooling. It was fixed, and the 72-snapshot sensitivity rerun leaves every verdict unchanged.

## Take-home

Across the engine's whole file-metric surface, only the platform-conditional surface finds a fix class beyond size. For CVEs the only working predictor is their own history, which is not a snapshot metric.

## What it changed

This strengthened ENV's platform-conditional result, now confirmed with the engine's own size measure and on a mostly C++ repo. It closed the general search for file metrics per class. Regressions moved to commit-level designs (REG).
