---
date: 2026-11-22
title: Call-graph position vs fix history: orchestrators, fan-out and the fix radius (30 repos, C / Go / Java)
type: exploratory
status: scored
verdict: n/a
theme: defect-prediction
ids:
docs: docs/fix_radius_orchestrators.md
links: gitgalaxy#8955; gitgalaxy#8956; gitgalaxy#8957; gitgalaxy#8958
takehome: Functions that call many others get changed about 10-25% more than their size predicts (also with no fix label at all, in C, Go and Java); betweenness, PageRank, file-level producer role and fan-in add nothing over size, and the fix radius is mostly directory adjacency.
---

## Question

Does a function's position in the call graph (fan-in, fan-out, betweenness, chain length, producer or consumer ratio) carry change- or fix-proneness once size and complexity are controlled, and do fixes spread along call chains?

## Why we asked

GitGalaxy emits several graph metrics under names that read as risk claims ("choke point", "blast radius", "ecosystem role"). The programme's standing is that history predicts and structure describes (`PROGRAMME_call_networks.md`); this asks how much structure adds, across languages, on repos the study had not been built on. It also tests whether the repair radius found on GitGalaxy's own history (`self_evolution/repair_radius_variants_results.md`) shows up elsewhere.

## What we did

Scanned 30 repositories (14 C, 8 Go, 7 Java, one Kotlin repo skipped) with GitGalaxy 981e9ec, test and vendored code removed, history ablated. Mined five years of commits per repo, mapped hunks to functions by git's function-header names, and fitted a per-repo Poisson baseline on log LOC and log complexity. Lift is observed over predicted fix touches. Three label definitions: a broad keyword set, a no-memory-words set (primary) and any commit (label-free control). Hypotheses were written down before each wave, informally (no commit timestamp, no two-review process), and judged on separate repos. Pooling was random effects in wave 2. Write-up: `docs/fix_radius_orchestrators.md`. Scripts: `tools/fixgraph/`.

## What we found

All exploratory. The fix label's precision was not measured on any of the 30 repos, and five of the six that are on `LABEL_CARD.md` fail its raw-label bar.

- **Orchestrators** (fan-in under 8, fan-out 8 or more): 1.22x (1.15-1.29) over 21 wave-2 repos, with 1.19x C, 1.21x Go, 1.25x Java; 1.20x and 1.23x on the two wave-1 sets. The any-commit control gives 1.19-1.29x. Fan-out partial correlation is positive in 21 of 21 repos and in 8 of 8 wave-1 repos.
- **Consumer-ish** (fan-in ratio under 0.2) 1.16x; producer-ish 0.82x; Go does not separate them.
- **No signal beyond size:** file and function betweenness, PageRank, the file-level producer role, fan-in, chain depth.
- **Fix radius:** 2-18x against a repo-wide null falls to about 1.5x against a directory-matched null (at least 1.5x in 15 of 28 repos; Go and Java mostly below). The recurrence-aware null C from the repair-radius study was not run and removed the excess there.
- **Withdrawn:** a lifecycle-function result that was a churn effect, unstable across the time split.

## Take-home

Fan-out is the one call-graph scalar that carries a small, consistent, size-adjusted change-proneness lift, and it does so without any fix label. Everything else tested that reads as a risk measure did not beat size. The fix radius is much smaller than a repo-wide null suggests.

## What it changed

Gitgalaxy filed four issues (#8955-#8958) and a docs PR that caveats the structural metrics as not validated fix-risk predictors. Open here: forward-validate fan-out with the audited label on the LAWS panel, run null C for the fix radius, and size-band the PageRank result. The numbers above belong to a study that skipped the two-review process and several checklist items (listed in the write-up); read them as a description, not a finding.
