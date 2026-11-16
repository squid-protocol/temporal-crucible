# Sensor overhaul: guide

**Status: living document, started 2026-11-16.** Branch `sensor-overhaul` (long-term; built on `turn/forecast`, which holds every study cited here). Nothing in this guide is registered; every number is exploratory discovery data from 13 repositories and, where stated, a 580-repo population sample.

## 1. The goal

In the owner's words: GitGalaxy's file-level gauges were meant to be **"specific custom gauges that give people important views into their files, like actionable information or sensors or metrics that mean something"**, and the redesign should give **"non-redundant sensors that add value."** They were first called risk exposure; they do not predict risk (shown repeatedly, below), so they were renamed surface-area measurements and then left without a use.

**Working definition of a sensor.** A measurement of *one* thing, in plain units, with the same meaning across repositories and languages, that

1. tells a person something the engine's other outputs do not already say (non-redundant),
2. **points at specific functions, lines or files** and suggests an action (actionable),
3. is validated for what it **measures** (construct validity), never claimed to predict defects.

**Non-goals.** No risk score. No single blended health number. No claim that a gauge predicts bugs, CVEs or regressions.

## 2. What we found (the evidence that drives the design)

### 2.1 What the current gauges are
The file-level vector has 13 `risk_*` columns (cognitive load, safety score, tech debt, verification, API exposure, concurrency, state flux, dead code, spec match, stability, churn, documentation, secrets risk). Each is a weighted density of the engine's keyword families per line, netted against a mitigation (locks against concurrency, freezes against mutation), squashed to 0-100 by a sigmoid. (`gitgalaxy/metrics/signal_processor.py`, `_calc_*`.)

### 2.2 Descriptive tests (13 repos, 6,081 code files; confirmed on 77,706 files in 580 repos from the v2.12.0 master database)
| Finding | Evidence |
|---|---|
| **Sparse or saturated.** Most files score 0 or 100. | zero: concurrency 91%, secrets 99.9%, dead code 82%, tech debt 59%; pinned at 100: documentation 58%, state flux 27% |
| **Mostly a relabelling of one or two keyword densities.** | concurrency vs `arch_concurrency` rho 0.94; dead code vs `state_graveyard` 1.00; secrets vs `threat_private_info` 1.00; cognitive load vs branch density 0.74; API exposure vs `arch_api` 0.71; **`safety_score` vs mutation density 0.83** |
| **Not redundant with each other.** | median pairwise rank correlation +0.02; PCA participation ratio 4.4 of 10 |
| **Construct validity is mixed.** | concurrency +0.83 with lock/thread keywords; cognitive load +0.75 with function complexity; **API exposure +0.63 with PageRank/blast radius and AUC 0.90 for header files**; safety +0.27 with safety keywords; **dead code +0.01 with unreferenced functions**; documentation weak (-0.35) |
| **The mix describes file role.** | six profile types (small tests, big core, exposed core, interface/header, debt-heavy small, tiny simple); agreement with role AMI 0.22, with language 0.06, repo 0.04, size 0.07 |
| **Very stable.** | same-file rank correlation 0.95-1.00 over two years |
| **Churn and stability are one process axis.** | rho -0.88; +0.97 with raw commit frequency; +0.55 with ownership entropy; |rho| <= 0.11 with every keyword metric; keyword densities explain only R2 0.05-0.08 of them |

### 2.3 Outcomes (7 repos with fix labels; forward-in-time split)
* Structural gauges add about +0.01 AUC to size for predicting later fixes, shrinking as the fix label is cleaned (+0.013 raw, +0.010 v3c, +0.004 regression-only; -0.001 in the history-aware run).
* **Process gauges do better and survive label cleaning:** churn and stability add +0.015 to +0.019 AUC over size under all three labels, and +0.015 beyond prior fixes under the regression-only label; churn is the only gauge related to later change (rho +0.26).
* Edit-kind mix adds nothing beyond size and churn; function-level next-change forecasts reach AUC 0.5-0.8 (`docs/turn_forecast_closeout.md`).
* **Ripple (measured reach):** callers of swept functions are edited 1.9x as often as other functions (23.6% vs 12.4%; odds ratio 1.28 controlling for size, same file and fan-in), but reach and the file-level API-exposure score add 0.000 AUC to size, fan-in and co-location (0.644 to 0.646).

### 2.4 What repositories do (the changes sensors should be able to see)
* **16-44% of in-place edits are sweeps** (one call or macro swapped across many functions in one quarter); sweeps carry no consistent defect signal, so churn without them is the cleaner number.
* **Functions are born finished** (about 90% unchanged after a quarter, 59-89% after a year); the risk of a first change is highest in the first quarter.
* **Wiring is set at birth** (95-100% of uncalled newborns stay uncalled); hubs stay hubs.
* **Migrations are sizeable and scopable:** the call graph predicts the swept functions with recall 1.00 and median precision 0.83 (text search 0.74); a sweep covers a median 90% of the old name's callers.
Sources: `docs/turn_discovery_2026-11-15.md`, `docs/turn_sweep_scope.md`, `docs/turn_sweep_forecast.md`.

### 2.5 What the comment and debt research adds (crucible)
Debt markers are discrete, locatable, ageable and, unlike a density, actionable; projects differ several-fold in how they repay them (38-98% eventually removed); danger comments at birth carry a weak foresight signal; commented-out code is detectable at about 93% precision. Detail in `sensors/tech_debt.md`.

### 2.6 Two engine caveats found on the way
* The installed `galaxyscope` entry point loads a **stale copy** under `/nvme-data` (an old fix branch with no as-of history mode). Scans for the 13 repos used it; the population check used v2.12.0.
* The scan tool in `historical-call-graph-gif` exports each commit as a **plain tree with no `.git`**, so churn and stability are constant in its scans. History-aware scans need a detached git worktree, the main engine, and `GITGALAXY_HISTORY_ASOF=1` (`tools/turn/surface_area/hist_scan.py`).

## 3. Disposition of the current gauges

| Gauge | Today | Verdict | Becomes |
|---|---|---|---|
| cognitive_load | sigmoid of branch density | **keep, re-express** | worst functions by complexity and branch density, with the offenders listed (tracks function complexity 0.75; most size-tied) |
| safety_score | mostly mutation density | **merge, rename** | one **mutation** sensor together with state_flux |
| state_flux | mutation net of immutability | **merge** | the mutation sensor above |
| tech_debt | markers + unreferenced names + duplicates, one sigmoid | **split** | a debt ledger (markers), plus separate unreferenced and duplication sensors; see `sensors/tech_debt.md` |
| verification | test-presence signal | **keep as role evidence** | test relation: has a test counterpart, test-file flag (AUC 0.92 for test files) |
| api_exposure | sigmoid of `arch_api` and encapsulation | **replace** | measured **reach**: callers, files depending, 1-2 hop ripple, header flag |
| concurrency | thread/async net of locks | **keep as filter** | counts of unguarded concurrency constructs, listed by function |
| dead_code | deprecated-marker density | **split** | deprecated markers (counts) and unreferenced non-public functions (call graph, listable) |
| documentation | sigmoid, 58% at 100 | **replace** | percent of public functions documented (engine has `is_public`, `is_documented`) |
| secrets_risk | density of private-info hits | **detector, not score** | a findings list |
| stability, churn | constant without git history; both driven by recency of the last change; churn = 365-day commit count (rho 0.96), stability = days since last change (0.97) | **merge, redesign** | an **activity** sensor on three independent axes: recent activity (365-day commits, with 90-day hot-now), age and lifetime, ownership concentration (activity-gated); see `sensors/activity.md` |
| spec_match | off by default | **retire or keep optional** | |

**New sensors the evidence supports:** mechanical-versus-organic share of recent edits (net churn); settledness (share of functions unchanged for N quarters); file role tag (the six profile types); debt ledger and the comment sensors (section 2.5).

## 4. Design rules
1. **One construct per sensor.** If two sensors correlate above 0.5 within repos, merge or drop one.
2. **Plain units.** Counts, per-kLOC ratios, callers, ages in years; percentiles within the repo or role; never a 0-100 sigmoid.
3. **Every sensor has a drill-down:** the functions, lines or files that produce the value, ranked, with enough context to act.
4. **Repo-relative references.** Repositories differ several-fold in culture (commenting, debt repayment); compare against the repo's own history before any cross-repo scale.
5. **Keep signals separate; never blend** into one health number (repowise does the same: three signals, never blended).
6. **Role-aware.** Tests, headers, vendored code and docs behave differently; label the role and filter on it.
7. **Say when the engine cannot see.** Unresolved callees, unsupported languages, scans without history: mark the sensor "not measured", not zero.
8. **Report evidence status on the sensor itself** (measured, descriptive, validated against X), and never claim risk.

### 4.1 Design stance: inspired, not copied
Owner direction (2026-11-16): design something unique; take inspiration, solve it our own way. Ground rules, following the third-party IP rule (borrow ideas only, record where each came from, quote nothing long):
1. **No imitation of vendor surfaces:** no 1-10 scale, no bands, no detector roster, no copied thresholds, weights or finding names, no "fix first" label. Our vocabulary is our own.
2. **Standards over vendors:** where a workflow convention is needed (triage states, stable identity), map to an open standard (SARIF 2.1.0 suppressions and `partialFingerprints`), which the engine's SARIF recorder already speaks, and keep our own state names.
3. **What is distinctively ours** (and what each sensor should lean on):
   * **Time:** every sensor can be replayed at past dates because the engine, the lineage ledger and the history scans give us whole histories; we back-test our own flags.
   * **Track record:** every flag ships with how that kind of flag has behaved **in this repo** (for example, "fossil debt here is repaid 6.2% of the time within two years, against 23.9% for other debt"). A flag without a measured track record is description only.
   * **The repo's own baseline:** references come from the repo's own history, never a global scale.
   * **Change as a first-class event:** sweeps (mechanical migrations), their mechanical share, scope and progress from the call graph; renames followed; original ages through moves and rewordings.
   * **Validated for what it claims,** not for predicting defects: debt against repayment, reach against real dependence, activity against later change; negative results are published (effort cannot be predicted per marker).
   * **"Not measured" is a first-class state,** with the reason (outside the call graph, no history, unresolved callee).
   * **Multi-language from one engine,** with role tags so lists are comparable.
4. **Ideas now prototyped** (our own designs; `sensors/change_aware.md`): a "while you are here" prompt triggered by the change in front of the reader (back-tested: gate on 50+ changed lines, editor's own markers first), and a diff-aware change report (what this change did: mechanical share, debt balance, reach of the touched functions). **Still open:** a pilot to learn whether the prompt raises repayment, and gauge deltas beyond the touched functions.

## 5. Acceptance checklist (run for every new or changed sensor)
| # | Test | Pass | How |
|---|---|---|---|
| 1 | Not degenerate | under 50% of files at zero or saturated | `tools/turn/surface_area/sa_describe.py` section A |
| 2 | Construct validity | rank correlation >= 0.5 with an independent measure of the thing it names (median over repos) | section E |
| 3 | Not redundant | absolute within-repo rank correlation < 0.5 with every other sensor; each adds an effective dimension | section D |
| 4 | Not just a keyword density | or, if it is, show it as that count | section C |
| 5 | Stable if described as a trait; state sensitivity if described as a state | two-year rank correlation | section H |
| 6 | Discriminates a real role or state | AUC >= 0.7 for a stated role | section F |
| 7 | Actionable | every value comes with a ranked list of the functions or lines behind it | by construction |
| 8 | Outcome relation reported, never claimed | AUC gain beyond size and prior fixes under raw, v3c and regression-only labels | `sa_outcomes.py`, `sa_outcomes_hist.py` |
| 9 | Replicates on the population | repeat 1-6 on the master database sample | `sa_master.py` |

### 5.1 History vectors: what the wiki promised and what the code does
The wiki (`docs/wiki/02-15-chronometer.md`) describes churn (recent change frequency) and stability (age). The formulas (`docs/vector_formulas.md` 12a/12b) make both depend on the time since the file's last modification (stability is that time as a share of the repo timeline; churn divides the 12-month commit count by its square root), so they are one axis (rho -0.86). `docs/vectors.md` says the history vectors are ablated to zero in every recorded scan; the v2.12.0 master database shows values for about 40% of repos, and history-aware scans work on `main` with `GITGALAXY_HISTORY_ASOF=1`. Full analysis and redesign: `sensors/activity.md`.

## 6. Related tools (for orientation only)
Static-analysis health tools such as repowise (AGPL-3.0) and CodeScene score files on a 1-10 scale from detector findings that include complexity, duplication, change history and test evidence. We read their public documentation to understand what users of such tools expect, and for what to avoid: a blended per-file number, scored findings that cannot be checked against what they claim, and (in repowise's own published numbers) an accuracy that ties a plain line count. **We do not use their detector rosters, thresholds, weights, names or score scale, and we copy no code or text;** the ideas below come from the published research they also draw on (Bird et al. on ownership, Hassan on change entropy, D'Ambros on co-change, Nagappan and Ball on relative churn) and from our own measurements. Sources: repowise `docs/layers/CODE_HEALTH.md` and `docs/architecture/code-health.md`, repowise-bench; `docs/repowise_assessment.md`.

## 7. Roadmap
1. **Tech-debt ledger** (this repo, `sensors/tech_debt.md`): prototype done on four repos; next, move to engine inputs and test the acceptance checklist.
2. **Activity sensor** (designed: `sensors/activity.md`; churn, stability and ownership become recent activity, age and ownership concentration). Engine work: whole-history walk, persisted horizons, as-of mode by default for historical scans, fix `historical-call-graph-gif`, correct the "ablated in every scan" text in `docs/vectors.md`.
3. **Reach sensor** (callers, ripple, header flag) with the migration scope report as its first product.
4. **Mutation, concurrency, cognitive-load drill-downs** (worst functions listed).
5. **Hygiene sensors from the comment research** (documented public functions, header coverage, commented-out code, danger comments, comment neglect).
6. **Role tag and settledness** as descriptive context.
7. Prototype panel on three repos for judging usefulness; then engine issues in GitGalaxy for the pieces that need the engine (marker positions, external callee nodes, per-function history).

## 8. Open questions
* Does a panel of about 8 sensors with drill-downs read as useful to a person who does not know the tool? (A pilot, not a statistic.)
* Which debt markers are worth acting on: age relative to the repo's habit, activity of the file, owner still active?
* Can the engine persist marker positions and per-function history cheaply?
* How should the engine represent standard-library and macro callees so reach can be measured for the 44% of sweeps it cannot currently see?

## 9. Provenance
`docs/turn_surface_area.md` (all of section 2.2-2.3, 2.6), `sensors/activity.md` and `sensors/tech_debt.md` (sensor designs), GitGalaxy `docs/wiki/02-15-chronometer.md`, `docs/vectors.md`, `docs/vector_formulas.md` (as of `origin/main`), `docs/turn_gitgalaxy_assessment.md`, `docs/turn_sweep_scope.md`, `docs/turn_sweep_forecast.md`, `docs/turn_forecast_closeout.md`, `docs/turn_edit_kinds_vs_fixes.md`, `docs/turn_function_recidivism.md`, `docs/repowise_assessment.md`, `docs/debt_lifecycle_exploratory.md`, `docs/drp.md`, `docs/comment_profiles_exploratory.md`, `docs/dead_code_panel.md`; tools in `tools/turn/` and `tools/sensor/`; logs in `docs/turn_surface_area_logs/`.
