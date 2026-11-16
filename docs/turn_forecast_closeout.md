# turn/forecast: closing summary (2026-11-16)

Work branch that followed the TURN discovery phase (PR #186 and `docs/turn_closeout.md`). All exploratory; nothing registered. 13 repositories, one engine, quarterly snapshots; fix labels from the crucible's events (raw `_xc`, v3c `_xc2`, regression class).

## Question
What do the lineage ledger, sweep detector, tree-sitter edit classes and call graphs let us say, and not say, about predicting errors, fixes and the work they entail?

## Documents on this branch
`turn_forecast_firstlook.md` (function-level change forecast), `turn_sweeps_and_fixes.md` (label audit and sweep exposure), `turn_fix_catalog_and_archetypes.md` (what fix work looks like; six kinds of edit), `turn_edit_kinds_vs_fixes.md`, `turn_sweep_forecast.md`, `turn_function_recidivism.md`, `turn_sweep_scope.md`. Tools: `tools/turn/` (README lists each script; unfinished, hard-coded paths).

## What we can say
1. **How much of a repo's change is mechanical.** 16-44% of in-place edits are sweeps. The labels are not contaminated by them (under 1% of fix commits are sweeps in every class); sweep edits have no consistent effect on later fixes and should be separated from churn in any process predictor.
2. **What fix work looks like, by class** (C repos, 10,323 fix commits): CVE fixes lean toward bounds checks (1.5x), early returns (1.8x), pointer changes (1.5x) and removing a free (3.3x) and are larger (median 14 lines vs 8); extrinsic fixes are casts (2.0x) with fewer new guards; regression fixes look like ordinary fixes.
3. **Six kinds of edit** (tweak, swap/rename, signature, grow with logic, shrink, big error-handling rewrite) appear in every C repo in similar proportions; the mix regresses to a repo-specific average (long-run mix beats last quarter's mix in all five).
4. **Sizing a migration is close to deterministic:** a sweep covers about 90% of the old name's callers (median), the engine's call graph gives complete recall and 0.83 median precision for the swept functions (text search 0.74), and 79% of sweeps cover at least half the callers.
5. **Where fixes land is file-level.** Recidivism's signal sits at file level and shrinks as the label is cleaned (curl +0.030, +0.017, +0.004 AUC raw, v3c, regression-only; redis +0.037, +0.016, 0.000); the function's own prior fixes add 0.000-0.004 beyond the file, and correct lineage identity adds 0.000-0.002 over naive path-and-name identity.

## What we cannot say
* **Edit kinds do not predict later fixes beyond size and churn** (AUC gain -0.003 to +0.002 under all three labels, at file and function grain).
* **Which API gets swept, and when, is largely not forecastable:** the new name first appears in the sweep quarter in 76% of cases; one third of large sweeps had a deprecation message beforehand; a name-pattern alert has about 0% precision; 44% of migrations belong to repeated-rename chains.
* **Function-level next-change forecast is weak:** AUC 0.5-0.8 with small, inconsistent skill over the repo's recent rate; event rates are bursty, so the repo-wide rate carries most of the predictable signal.
* Ceiling: size, churn and prior fixes carry the ranking and each shrinks as labels get cleaner; the crucible's ceiling study (oracle recall@20% 0.66 vs 0.37 observed, 0.27 leaving one repo out) still stands: the headroom is rate variation no covariate sees.

## Where the new instruments are useful
Describing and sizing work, not predicting defects: the mix and volume of edits, separating mechanical from organic change, and scoping a migration (affected functions, files, leaf-side position, completion). A sweep forecaster would need an upstream signal (deprecations, language or library version changes, release milestones), not structure.

## Open
Ripple and effort for a planned sweep; which callers a migration skips; the same questions beyond C (function-level fix mapping and edit classes exist only for C so far); upstream-signal forecasting; the LAWS panel and the registration owed on PR #186.
