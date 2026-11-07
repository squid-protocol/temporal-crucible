---
date: 2026-10-23
title: Mid-band centrality and per-file dynamism on unseen repos (CEN, DYN)
type: confirmatory
status: scored
verdict: mixed
theme: defect-prediction
ids: CEN-H1 / H2; DYN-H1 / H2
docs: docs/cen_hypotheses.md; docs/cen_openssl.md; docs/cen_harfbuzz.md; docs/cen_libarchive.md; docs/dyn_ndpi.md; docs/dyn_openssl.md
links: temporal-crucible#41; temporal-crucible#43; temporal-crucible#66
takehome: Files with function-like macros or goto get security fixes about twice as often as files of the same size (2.03 nDPI, 2.33 openssl; replicated), though as a ranking this does not beat size; mid-size-file centrality fails on unseen repos and is closed as a lead.
---

# Mid-band centrality and per-file dynamism on unseen repos (CEN, DYN)

## Question

Two leads left over from earlier work, each run where it had not been seen:
- **DYN:** do files with per-file dynamism (in C, function-like `#define` and `goto`) get more security fixes at equal size?
- **CEN:** in mid-size files (49–108 lines), do central files (PageRank, popularity) get more bug fixes?

## Why we asked

- DYN came from gitgalaxy's outcome-label pilot (gitgalaxy#2720). The pilot found a rate ratio of 1.27 that shrank as size was held tighter, and it was not pre-registered. DYN was registered on 2026-10-23 (tc#41) for unseen data only, with curl excluded.
- CEN came from the two exploratory "context cells" of the bug-label expansion (B-H, 2026-09-13): curl mid-band PageRank +0.145 and popularity +0.132. They were registered for repo #3 but never given an exact statistic. CEN was registered on 2026-11-06.
- Priors: DYN-H1 expected not supported, DYN-H2 uncertain, CEN leaning not supported.

## What we did

- **DYN.** nDPI (121 events) and openssl (252 parent snapshots scanned for this test).
  - H1: dynamism beats LOC within powered size bands.
  - H2: Mantel-Haenszel rate ratio for any dynamism, at equal LOC decile and evidence, one-sided lower bound > 1.
  - The C pattern was checked identical to the registered regex at both engine builds.
- **CEN.** openssl (110 snapshots), harfbuzz (62) and libarchive (72). Outcome: XC bug-fix commits in the next 180 days. Mid-band AUC lift over `total_loc`. A claim needed every repo.

## What we found

- **DYN-H1 not supported:** no powered band passes on either repo.
- **DYN-H2 supported on both repos:** rate ratio 2.03 (lo 1.51) on nDPI and 2.33 (lo 1.74) on openssl. Exploratory finer strata (50 and 100 LOC bins) keep it at 1.8–2.2, so it is not leftover size.
- **CEN-H1 (PageRank) not supported:** −0.044 / −0.051 / +0.035.
- **CEN-H2 (popularity) not supported:** +0.061 on openssl (passes) but −0.072 on harfbuzz and 0.000 on libarchive.

## Take-home

Dynamism is the first snapshot property with a replicated association with security fixes beyond size. It is a correction factor, not a ranking. Centrality does not find bugs on unseen repos.

## What it changed

DYN's registered decision rule (b) applies: keep the modest per-file dynamism weight as a correction, with no increase. Centrality is closed as a predictive lead and stays a descriptive map. DYN led directly to the construct split (KF), which separates `goto` from macros.
