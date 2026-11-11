# DCS — danger comments that stayed safe: is there a code signature that separates them from the ones that got CVEs? — registered 2026-11-10, before any feature was compared with an outcome

**Why.**
- DC-2 found that functions born with danger-language comments ("must not", "assume", "overflow", …) reach a CVE fix
  1.45× as often as other commented functions, in all four repos. But most danger-commented functions never get a
  CVE fix. The authors flagged danger in both groups.
- The owner asked (2026-11-10): among danger-commented functions, does anything the engine measures (telemetry,
  fingerprints and the lattice, call-graph position) separate the ones that later needed a CVE fix from the ones
  that did not?
- This is a data-mining question, so it is run in two stages: an **exploratory discovery stage** that may search
  freely, and a **confirmation stage** on held-out functions with the models frozen beforehand. Only the
  confirmation stage carries verdicts.

## Prior work

- **This program, at the same grain.** Structure at birth did not predict CVEs once size was controlled: INT and
  INT-S (defensive code, rate ratio 0.96), ARCH-Z and OUT-H1 (atypicality), FWD and FREC (lost to size), CEN-H1/H2
  (centrality, ✗ on unseen repos). The HYPOTHESES summary: "everything structural reduces to file size". FIXK and
  LAT-F found that CVE fixes *change* functions in a typical way; that is about the fix, not about the function
  before it.
- **Shin, Meneely, Williams and Osborne, "Evaluating Complexity, Code Churn, and Developer Activity Metrics as
  Indicators of Software Vulnerabilities", IEEE TSE 37(6), 2011.** Complexity, churn and developer metrics flagged
  vulnerable files in Firefox and RHEL with useful recall at file grain; complexity alone was weak.
- **Zimmermann, Nagappan and Williams, "Searching for a Needle in a Haystack: Predicting Security Vulnerabilities
  for Windows Vista", ICST 2010.** Classical metrics gave high precision but low recall for vulnerabilities;
  dependency (call-graph) metrics gave better recall.
- **Neuhaus, Zimmermann, Holler and Zeller, "Predicting Vulnerable Software Components", CCS 2007.** Imports and
  function calls predicted vulnerable Mozilla components.
- **This study's difference:** a cohort already selected by the authors' own danger comments, function grain, a
  loc + repo + prior-CVE baseline that every feature family must beat, and held-out confirmation. It **extends**
  the dependency-metric results (Zimmermann et al., Neuhaus et al.) to that cohort and **tests** the program's
  "structure reduces to size" finding inside it.

The citations are from memory and are checked against the published papers before the result doc ships.

## Cohort (DC-2's, unchanged)

- Repos curl, OpenSSL, nDPI and harfbuzz; functions born after the first snapshot with loc ≥ 3 (`ints_eval.lives`).
- **Danger-commented:** at the birth snapshot, ≥ 1 engine comment line inside the function or in the block directly
  above, and ≥ 1 match of DC's fixed lexicon (`dc_eval.DANGER`).
- **Fix labels:** `chg_eval.fix_events` / `map_fix`; a CVE fix is the `latent` class.

## Outcome (fixed horizon)

- **Horizon:** 5 years from birth. Only functions whose repo labels run ≥ 5 years past birth are eligible.
- **Case:** the function's first CVE fix falls within 5 years of birth.
- **Control:** the function is alive at birth + 5 years with no CVE fix up to then.
- **Excluded:** functions that died within 5 years without a CVE fix (reported by count; a sensitivity run counts
  them as controls).

## Features (read at the birth snapshot, from the quarterly scan DBs `nh_eval.DBS`)

| family | features |
|---|---|
| **T, telemetry** | every numeric signal column of `function_data` (`struct_*`, `def_*`, `state_*`, `arch_*`, `threat_*`, `sec_*`, `bitwise_ops`, plus `complexity`, `args`, `token_mass`, `keyword_density`, `func_z_score`), each as count ÷ loc |
| **F, fingerprint / lattice** | LAT's family of the function's signal set (nearest top-200 shape, `docs/fingerprint_trees_exploratory.json` sha `a27d2c93f817`, LAT's assignment rule, one-hot, with "unassigned"); rung k; `func_archetype` (one-hot) |
| **C, call graph** | `func_pagerank`, `func_fan_in`, `func_fan_out`, distinct callees in `calls_out_to` (each log1p), `is_public` |
| **B, baseline** | log loc, repo (one-hot), file had a CVE fix before birth. Every model includes B |

- **Dropped, fixed now:** comment-derived columns. They define the cohort, and the scan DBs predate gitgalaxy#8200,
  so they are 0 at function grain: `state_graveyard`, `sec_dead_code`, `def_doc`, `def_ownership`,
  `state_planned_debt`, `state_fragile_debt`, `is_documented`, `lit_*`. `def_shape` is empty in these DBs.
- **Dropped by an outcome-blind rule:** any feature that is non-zero in < 0.5% of the discovery set.

## Split (outcome-blind)

- Among eligible cohort functions, per repo, the **median birth time** splits them: births before it go to
  **discovery**, the rest to **confirmation**. The split uses birth times only.
- Confirmation functions, their outcomes and their features are not read until the frozen models are committed.

## Stage 1 — discovery (EXPLORATORY; no verdicts)

Free search on the discovery set:
- a univariate screen (per feature, MH odds ratio of case vs control within repo × log₁₀ loc strata);
- the family distributions of cases vs controls;
- shallow trees for a readable signature.

Then for each of **T, F, C and T+F+C** it fits one L2 logistic regression on B + that family, with standardized
features and C chosen by 5-fold file-grouped CV in discovery. It also fits B alone. **The fitted models
(coefficients, scalers, feature lists) and the discovery report are committed before Stage 2 reads anything.**

## Stage 2 — confirmation (registered claims)

All AUCs are on the confirmation set, from the frozen models. Lift = AUC(B + family) − AUC(B), with a file-cluster
bootstrap of 2,000 rounds (seed 2982). α = 0.01/4 (Bonferroni over four claims), one-sided.

| id | claim | supported iff |
|---|---|---|
| **DCS-T** | engine telemetry at birth separates CVE-fixed from safe danger-commented functions beyond size | lift > 0 and lower bound > 0 |
| **DCS-F** | the fingerprint family / rung / archetype does | lift > 0 and lower bound > 0 |
| **DCS-C** | call-graph position does | lift > 0 and lower bound > 0 |
| **DCS-ALL** | the three together do | lift > 0 and lower bound > 0 |

- **Power rule:** ≥ 20 cases in confirmation. Otherwise every claim is **underpowered**, not a verdict.
- **Null:** a claim that fails is called a **replicated null** if the two-sided 99% CI of its lift lies inside
  [−0.02, +0.02]. Otherwise it is **inconclusive**.

## Descriptive (confirmation, no verdicts)

- Recall at the top 20% of lines reviewed (effort-aware, as in EA) for B and for each model.
- The same frozen models on **plain-commented** functions (no danger words). Is any signature specific to the
  danger cohort, or a general CVE signature?
- Which discovery-screen features keep their sign in confirmation.
- Sensitivity: early deaths counted as controls.

## Priors

- **Most likely null for T and F.** Every structural predictor in this program has reduced to size.
- **C is the least unlikely.** The literature's strongest vulnerability signal is dependency position, but CEN-H1/H2
  did not replicate it here at file grain.
- **Small cohort.** DC-2 had 144 first-CVE events in danger-commented functions over whole lives, and the 5-year
  horizon and the split cut that further. Underpowered is a real possible outcome.

## Known limits

- The cohort and the features come from the same quarterly scans, which predate gitgalaxy#8200. That is why
  comment-derived columns are dropped.
- The split is by time, so confirmation functions are younger. That is a stricter test (a different era), not a
  random holdout.
