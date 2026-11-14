# SA3 — everything in force, in one place

**This restates `docs/sa3_registration.md` and its Amendments 1–4. It adds nothing.** Where the two disagree,
the registration and its amendments govern and this text is wrong. It exists because four amendments on a body
that was itself edited in place cannot be held in one head, and the scorer had drifted from the text in nine
places by the time a third review counted.

**Status of the claims.** Pre-registered 2026-11-13; point estimates of the four primaries on HP were partly
seen on 2026-11-14 before scoring (Amendment 4). The confirmatory tests run exactly as frozen at commit
`edc5c53`. Anything labelled `PU_` was added after that and is a sensitivity only.

## 1. Question

Among files of closely matched size in one repo at one snapshot, does a structural measure rank the files
later tied to a fix above those that are not? "Adds to size", not "replaces size".

## 2. Repos and snapshot

| rule | where |
|---|---|
| 38 repos drawn for MOD-1 (seed 20261113) plus the 8 assessed earlier; languages as amended in MOD-1 | `docs/draw40.json`, `docs/mod1_language_amend.json` |
| Snapshot = the commit at the 80th percentile of usable commits; outcome window = the 730 days after it | `mod1_lift.frame` |
| For the earlier eight the window starts at the scanned snapshot, 4.6–42 days after the cut | `sa3_outcomes.build`, `window_start` |
| Merges are kept as the unit where the history was walked first-parent | `mod1_lift.frame`, `where` |
| One engine for every scan: gitgalaxy `f71181aae7`, a frozen export | `sa3_scan.ENGINE` |

## 3. Universe

A file is ranked only if it can be positive: the repo's language (C and C++ together), not test, vendored,
documentation, example, tutorial or generated, with the snapshot's `.gitattributes` applied, LOC > 0 in the
scan. `sa3_outcomes.universe`. The scorer aborts if an outcome file is outside it: `sa3_score.load`, `yvec`.

A repo is excluded as **scan incomplete** if the scan holds under 90% of the unit files in the `git archive`
of the snapshot. Six are: root, livecode, wrf-fortran, wordpress, pwntools, macports-base — the engine skips
directories this rule keeps (`docs/sa3_outcome_marginals.md`).

## 4. Outcomes

A file is positive if a qualifying commit in the window touches it. `sa3_outcomes.build`.

| outcome | a qualifying commit | role |
|---|---|---|
| **HP** | carries a fix reference (issue, Jira, bpo, PR, GnuPG bug id, `Fixes:`/`Bug:`/`Reported-by:` trailer), a CVE id, or a revert **whose target resolves to a commit that existed at the cut** | **primary** |
| HP_allreverts | as HP, every revert counted | secondary; supported only here reads "tracks reverted changes, not fixes" |
| HP_revert, HP_cve, HP_fixref | the commit's exclusive tier, in the order revert, CVE, fix reference | reported, never pooled into a claim |
| KW | the cleaned keyword rule, and no HP link | secondary |
| matched control | K ordinary commits drawn at random, K = the number of HP commits (HP subsampled if the pool is smaller), 200 draws, seed 2982 | the specificity gate |
| CHURN_any | any commit of the control pool | reported beside the matched control |

- **Tree-wide commits** (≥ 10% of the unit files and ≥ 20 of them) are removed from every outcome and the pool.
- **Merge inheritance.** In a merge-workflow repo a merge inherits the fix reference, CVE or qualifying revert
  of a commit it brings in. Brought in = reachable from parents 2..k and not from parent 1, each off-chain
  commit owned by the earliest merge reaching it, the chain including bot commits. No inheritance past 50
  brought-in commits, never from a bot's commit, never the keyword tier, never a revert of a commit brought in
  by the same merge. Positive files = the merge's first-parent diff ∩ the linking commit's files.
  `brought_by`, `MAX_BROUGHT`, `classify`.
- **Tainted merges** — over the cap, or bringing in a linked or fix-worded commit — are in no outcome and no
  control.
- **Control pool:** non-bot commits in the window in no fix tier, not tree-wide, not tainted.
- **Floor per repo and outcome:** ≥ 30 positive files from ≥ 20 qualifying commits, no commit supplying more
  than 25% of the positives, ≥ 30 negatives. `FLOOR_FILES`, `FLOOR_COMMITS`, `MAX_COMMIT_SHARE`.

**The frozen list** (`docs/sa3_outcome_marginals.json`): drawn — bun, circuitpython, django, freebsd-src,
ghostty, gnupg, go, godot, mediawiki, moby, pandas, rails, scapy, spock, sqlmap. Earlier, exploratory — curl,
libxml2, postgres, prometheus, sphinx.

## 5. Predictors

File grain, read from the rescans. `sa3_score.PREDICTORS`, `load`. Predicted direction of every primary:
higher, more fixes.

| instrument | primary | secondary |
|---|---|---|
| **A** call graph — *exploratory* | `in_degree`: resolved call rows landing in the file's functions | per LOC; out-degree; `pagerank_score`; `betweenness_score` |
| **B** keyword families — confirmatory | `struct_branch` | per LOC; `state_danger`; `state_pointers + state_memory_alloc`; `def_safety`; `state_flux`; `nest_max`, `nest_mean` (tree-sitter, exploratory) |
| **C** risk vectors — confirmatory | `risk_safety_score` | `risk_tech_debt`; `risk_cognitive_load`; `risk_state_flux`; `risk_concurrency`; non-zero yes/no; the score among non-zero files |
| **D** branch-state — confirmatory | `amplified_cascading_flux`, from the `mitigation_telemetry` JSON | per LOC; `state_heat_triggers` |

- A missing value drops that file for that predictor, everywhere, and is counted.
- **Instrument silent** for a repo: non-zero in under 10% of files; or, for a continuous score, under 20
  distinct values. `silent`.
- Nesting depth: a control node is a conditional, loop, multi-way branch or try block, per the `CONTROL` table
  of `tools/sa3_nesting.py` with `tree_sitter_language_pack` 1.20.0; an `if` hanging off the else of an `if`
  sits at that depth. Racket is not measured. Known undercounts: Ruby blocks and modifier forms, C macro loops,
  Swift `guard`.
- `dampened_flux` does not exist in the engine's output and is not scored.

## 6. Statistic

Per repo, predictor and outcome. `tools/sa3_stats.py`.

1. **Bands:** equal-count on LOC, 10 if the repo has ≥ 300 files, else 5; ties broken by path. `bands`.
2. **Pairs:** a (positive, negative) pair is eligible if both files are in the same band and their LOC ratio
   is within 1.5. `Design`.
3. **bAUC:** concordance (ties at half) scored separately on pairs where the positive is the larger file and
   where it is the smaller, the two weighted equally, plus equal-LOC pairs by their share. `Design.effect`.
   **effect = bAUC − 0.5.** Verified against a brute-force loop on 400 random cases by the third review.
4. **Pair floor:** ≥ 100 eligible pairs, ≥ 25 on each side. `clears_pair_floor`.
5. **Co-reported, must agree:** within a band, the predictor's rank fraction with its least-squares fit on
   ln LOC removed, then within-band AUC − 0.5. `residual_effect`.
6. **Beside each primary:** effect − the mean of its size surrogate (rule 8), the measured size leak.
7. **Per-repo side counts** — above, below, across zero — come from 200 block shuffles used as a reference
   distribution (p < 0.05), never from a file bootstrap. A 95% stratified bootstrap interval is also stored for
   the primaries.

Across repos: the **unweighted mean** with a **t-interval over repos**. `summarize`. Beside it: the
precision-weighted random-effects mean and τ, the sign test, the side counts.

## 7. Hypotheses and reading

- **SA3-B, SA3-C, SA3-D:** the mean effect of the primary on HP over the drawn repos is > 0.
- **SA3-A:** the same for `in_degree`, exploratory; read as positive / negative / not detected.

Holm over B, C, D: the smallest p is read at 98.33%, the next at 97.5%, the last at 95%, stopping at the
first that fails. `stage_score`.

| reading | condition |
|---|---|
| supported | the Holm-level interval lies wholly above zero **and** the residualised statistic reads the same |
| not robust to the statistic | the two statistics differ |
| supported, defect-specific | and effect(HP) − effect(matched control) has a 95% interval wholly above zero |
| supported, but tracks activity, not defects | supported, control not cleared |
| contradicted | interval wholly below zero |
| not detected | otherwise — read against `docs/sa3_power.md` |
| no finding | the gate of rule 8 failed |

## 8. Gates, run before any real predictor is scored

`sa3_score.py placebo`. The gate passes if every mean below is within 0.005 of zero.

- **Path hash** and **directory hash:** SHA-1 of the path, or of its directory, with 200 salts.
- **Size surrogate** of each primary: 200 made-up predictors drawn from a fit of that primary against LOC
  alone. `fit_size_model`, `draw_surrogate`.

Result of 2026-11-14: all six within tolerance (largest +0.0025). The block-permutation gate of Amendment 1
is withdrawn (Amendment 4).

## 9. Sensitivities

Reported, never gating. `stage_score`, `cuts`.

| name | what |
|---|---|
| S1 | the repos whose language was first measured on 2026-11-13 removed |
| S2 | merge-workflow repos removed |
| S3 | repos with under 730 days of window removed |
| S4 | the old "replaces size" statistic, AUC(x) − AUC(LOC) |
| S6 | the withdrawn statistic, within-band AUC(x) − within-band AUC(LOC) |
| S7 | caliper 1.25 and 20 bands, repos with ≥ 600 files |
| S9 | logistic: outcome on band dummies, ln LOC and the standardised predictor |
| go and django removed | they hold about half the HP-positive files |
| earlier eight | reported separately |
| C_family, managed | descriptive; not fitted under five repos |
| `PU_django_circuitpython_removed`, `PU_mediawiki_freebsd_removed` | **post-unblinding**, from the third review's data faults |
| S5, S8 | registered, **not run** |

## 10. The seal

`sa3_score.py lock` records the git hash of the scorer, the statistics, the outcome builder, `mod1_lift.py`,
this file, the placebo output, the outcome marginals, the power statement and the code review. `score`
recomputes them and refuses to run if any differs.

## 11. What a result licenses

- Supported and defect-specific: in this pool, among files of matched size, files with more of X were more
  often tied to an issue, CVE or revert in the next two years, by about this much.
- Supported, not defect-specific: X marks where work happens.
- Not detected: no mean effect above roughly 0.05 to 0.08.
- In every case: point estimates were partly seen before scoring; HP is "tied to a ticket" in django and
  mediawiki and about 73–81% precise overall; no claim about C; nothing about single files, causes, or repos
  outside this hand-collected pool.
