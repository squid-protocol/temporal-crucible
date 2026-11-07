---
date: 2026-11-06
title: A screen of the engine's untested metrics (NM-F, NM-G)
type: confirmatory
status: scored
verdict: mixed
theme: defect-prediction
ids: NM-F; NM-G
docs: docs/newmetrics_hypotheses.md; docs/nm_file_screen.md; docs/nm_function_screen.md; docs/nm_exploratory_size_checks.md
links:
takehome: Of the engine's newer metrics, the screen's leads were almost all leftover size; the one survivor is amplified_cascading_flux (state writes inside branches), which beats size on nDPI and openssl but not curl, so it needs its own test on an unseen repo (AMP-H1).
---

# A screen of the engine's untested metrics (NM-F, NM-G)

## Question

The newer engine build added metrics that this program had never related to an outcome: the `fam_*` signal families, guard balance, alloc/cleanup, wrappers, mitigation tallies, and function fan-in, fan-out, PageRank, public and documented. Do any of them say where security fixes land at equal size?

## Why we asked

Every earlier structural signal reduced to file size. The new columns had appeared only in schema lists, so a screen was the cheapest way to check them before anyone built on them. Priors: most `fam_*` metrics would show no signal, guard balance was uncertain, and function fan-in was leaning towards a signal.

## What we did

- **File screen (NM-F).** The ARCH-U quarterly snapshots (curl 105, nDPI 43, openssl 110), with on-master security fixes in the next 180 days as the outcome. AUC was computed within 10 equal-count LOC strata. A metric was a SIGNAL if its Bonferroni CI excluded 0 with the same sign on all three repos, and a LEAD if it did so on two.
- **Function screen (NM-G).** The FREC event set, with AUC within LOC tertiles inside each event. A SIGNAL needed the same sign on curl and nDPI.
- Any SIGNAL was defined as a lead to register on an unseen repo, not a result.

## What we found

- **As registered:** 0 file SIGNALs and three file LEADs: `amplified_cascading_flux`, `fam_mutation` and `fam_dead_code` (CI excludes 0 on nDPI and openssl, not on curl). At function grain, `func_fan_out` was a SIGNAL (+0.132 curl, +0.143 nDPI). Fan-in and PageRank showed none. `is_public` and `is_documented` were never tested because the entry rule rejected binary columns.
- **Exploratory size checks:** the strata were too coarse, and size "predicts" within its own strata (+0.11 to +0.20). Head to head inside the same strata, every `fam_*` lead loses to `total_loc`, and `func_fan_out` loses to function `loc`.
- **One survivor:** `amplified_cascading_flux` (a state mutation within 150 characters of a branch). It beats leftover size in 50 finer bins on nDPI (+0.105 vs +0.089) and openssl (+0.113 vs +0.032), but not on curl.
- Engine finding: nine `file_data` columns are never populated on C files, and five more are constant.

## Take-home

The new metrics are mostly size in disguise. Writes inside conditional logic, the shape of parsers and state machines, are the one live lead, and only on the fuzzer-heavy repos.

## What it changed

AMP-H1 (per-line flux beats size in 50-bin strata on an unseen fuzzer-era C repo) is owed before anyone calls flux predictive. Later screens use finer size strata plus a head-to-head against `total_loc` (SC, DYN robustness). The binary columns need a binary-aware re-screen. The empty and constant columns are engine findings.
