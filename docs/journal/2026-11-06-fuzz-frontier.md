---
date: 2026-11-06
title: Are latent defects found at the fuzzing frontier? (LV, LV-R)
type: confirmatory
status: scored
verdict: not-supported
theme: defect-prediction
ids: LV-H1..H4; LV-R
docs: docs/lv_hypotheses.md; docs/lv_ndpi.md; docs/lv_curl.md; docs/latent_verification_surface.md
links: temporal-crucible#58
takehome: Code that OSS-Fuzz has just started reaching does not carry the next CVE fixes beyond size: directional only on nDPI, where fuzz coverage is about 96% saturated, and worse than size on curl (−0.195).
---

# Are latent defects found at the fuzzing frontier? (LV, LV-R)

## Question

If latent defects are what the CI contract never pinned down, then outside search (fuzzers, users) should find them where it has just arrived. Do files whose OSS-Fuzz line coverage just grew carry the next latent fixes, beyond size?

## Why we asked

The owner framed CI as the intrinsic contract and latent defects as its gaps. The design note proposed that "discovery is exploration". OSS-Fuzz publishes daily per-file coverage for nDPI and curl, so the frontier can be measured rather than guessed.

## What we did

- **Data.** Daily OSS-Fuzz coverage summaries joined to monthly snapshots: nDPI 75 (2020-03 → 2026-07), curl 90 (2018-12 → 2026-07). Candidates were fuzz-instrumented C files. Outcome: XC labels in the next 90 days.
- **Scores.** Frontier (newly covered lines per line over 90 days), reached and unreached coverage.
- **Claims.** Frontier beats size for latent fixes (LV-H1); frontier is specific to latent fixes (H2); reached beats unreached (H3). Lift = recall@20 minus the stronger size order.
- **H4** (fuzz-covered but CI-uncovered code) was conditional on building CI coverage for at least 20 snapshots.
- Block bootstrap over 3 consecutive snapshots, α = 0.01 / 4.
- **LV-R** replicated H1–H3 verbatim on curl, registered before any curl report was downloaded. The prior expected a weaker effect, because curl's CVEs are mostly human-reported.

## What we found

- **nDPI:** H1 +0.026, H2 +0.143, H3 +0.088. All point the predicted way, and H2/H3 exclude 0 at 90%, but none clears α: **not supported (inconclusive)**. Fuzzers reach about 96% of instrumented lines, so the test has little variance there.
- **curl (LV-R):** H1 **−0.195** (CI [−0.300, −0.095]). The frontier marks CVE files worse than size. H2 and H3 are not supported. No score beats size for any class.
- **H4** was not run. A pilot built one nDPI snapshot with gcov: the CI suite covers 43.5% of lines against about 96% for the fuzzers, so the quadrant H4 needs exists. About 11 container-hours would be needed.

## Take-home

"Discovery is exploration" is not supported across repos. The curl/nDPI contrast is consistent with "a defect is found where its own searcher looks", but nDPI never cleared α, so that is a reading, not a result.

## What it changed

Owed tests: a reporter split of curl's CVEs (does the fuzz frontier predict only the fuzz-found subset?), LV-H4 with CI coverage, and line- or function-grain frontiers. The searcher reading went on to AGE and SRCH, where it was refuted as an explanation of CVE age.
