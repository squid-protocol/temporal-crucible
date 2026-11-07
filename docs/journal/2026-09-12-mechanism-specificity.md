---
date: 2026-09-12
title: Does the right exposure vector mark the right kind of CVE? The specificity battery (S-H0..S-H4)
type: confirmatory
status: scored
verdict: not-supported
theme: defect-prediction
ids: S-H0; S-H1; S-H2; S-H3; S-H4
docs: docs/specificity_curl_heldout.md; docs/specificity_density_explore.md; docs/repo3_survey.md
links: gitgalaxy#2982; temporal-crucible#14; temporal-crucible#26
takehome: On curl's held-out later CVEs, the memory-danger and IO vectors do not beat a line count for their own CWE families, and the vectors are not specific (the memory set ranks highest even for info leaks); cert/auth vocabulary is dead on C and concurrency was untestable.
---

# Does the right exposure vector mark the right kind of CVE? The specificity battery (S-H0..S-H4)

## Question

The exposure vectors are named for mechanisms: memory danger, crypto and auth, IO, concurrency. Does each vector mark its own failure family beyond a line count? Is the family-to-vector confusion matrix diagonal (S-H0, the discriminant)?

## Why we asked

"Exposure ≈ CVEs" had reduced to size. Specificity is the stronger claim: the right vector marks the right failure. The claims came from curl's exploratory CWE × vector table, so under protocol rule 3 they were never scored on the data that suggested them.

## What we did

- Registered on 2026-09-12 for unseen data, with one set of engine keyword columns per family:
  - S-H1, memory-safety CWEs;
  - S-H2, cert/auth;
  - S-H3, info-leak;
  - S-H4, concurrency, which needs a concurrency-bearing repo;
  - S-H0, the discriminant.
- Each signal's AUC had to exceed LOC's, with α = 0.01 and Bonferroni across the family.
- Evaluated on a held-out curl temporal split: CVEs after the median fix date (2022-06-25), test half only.

## What we found

- **S-H1 not supported:** a genuine null. `state_pointers` is 70% non-zero, yet the AUC ties LOC (0.588 vs 0.590).
- **S-H3 not supported:** a genuine null. AUC 0.54 vs LOC 0.57.
- **S-H2 degenerate, no verdict:** `def_auth` is 0 across all 1.05 M rows and `arch_crypto` fires on 0.1%. The matched signal is absent.
- **S-H0 not supported:** among the live sets, the memory set ranks highest even for info-leak positives. The "danger" signals act as a general code-mass proxy.
- **S-H4:** untestable on curl, which is single-threaded with about zero race CVEs.
- Exploratory density and length-matched checks found no family signal beyond size.

## Take-home

On curl, the populated danger signals are one undifferentiated code-mass blob, not mechanism-specific detectors. Predicting which file gets which kind of CVE from its standing level does not work.

## What it changed

- The dead cert/auth vocabulary on C was flagged as an engine signal.
- The battery set repo #3's selection criteria: CWE labels, real race CVEs and a mixed network surface.
- The repo-3 survey chose openssl, fixed-side (tc#26). The cross-repo specificity test remains owed there.
