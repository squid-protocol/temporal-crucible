# Do the six kinds of edit predict later fixes? (work branch `turn/forecast`; exploratory, not registered)

**Design.** File-years in four C repos (curl, libgit2, redis, libxml2; frame as in `docs/turn_sweeps_and_fixes.md`: four quarters of covariates, next four quarters of outcome, every fourth snapshot). Covariates from the prior window: code size (exposure), total code edits (churn), edit counts by kind (tweak, swap/rename, signature, grow+logic, shrink, big rewrite; archetypes fitted on curl, redis, libgit2), and, in a second model, prior fixes under the same label. Poisson rate model (size as exposure, small L2), **forward-in-time split** (fit on each repo's earlier half, score on the later half). Metrics: AUC for "any fix" and recall at a 20%-of-lines review budget. Gain = model with edit kinds minus the same model without; bootstrap over files (150 draws).
**Three labels:** raw keyword label (`_xc`), v3c (`_xc2`, audited precision 0.80, which the crucible found still carries artefacts), and the `regression` class alone (precision audit passes, 0.73-0.87; few events: 27-961 test fixes per repo).

## Result
Edit kinds add nothing detectable beyond size and churn, under every label.
| label | AUC gain, code-only (churn -> + kinds), per repo | AUC gain with prior fixes | recall@20% gain, code-only (mean) |
|---|---|---|---|
| raw | libgit2 +0.001, curl -0.003, libxml2 -0.003, redis +0.002 | -0.003 to +0.001 | +0.003 |
| v3c | +0.001, -0.002, -0.003, +0.002 | -0.003 to +0.001 | +0.004 |
| regression | 0.000, 0.000, +0.002, 0.000 | 0.000 to +0.002 | +0.007 |
Every interval is within about 0.005 of zero; recall changes of a few points go in both directions (libxml2 -0.03 to -0.06 with v3c). Fitted terms, rate ratio per log unit (v3c, code-only): grow+logic edits 1.11-1.19 in all four repos; signature 0.88-1.14, rewrites 0.94-1.05, swap/rename 0.99-1.15, none consistent.
**Prior fixes** add little once size is the exposure and churn is in the model: AUC +0.000 to +0.009 under raw and v3c (curl -0.002 under v3c); recall@20% +0.02 to +0.07 (libgit2, redis, libxml2) and +0.003 to +0.015 in curl. Switching label (raw vs v3c) does not change that picture; both are small next to size.
Baseline levels: AUC 0.71-0.89 from size and churn alone, which is the size wall: most of the predictable ranking is "bigger files get fixed more".

## Reading
* The mix of edit kinds is a good description of how a repository changes (stable across repos, regresses to a repo mean) but it is not a predictor of defects beyond the amount of change. This matches the crucible's etyp result for commits (edit-type vector adds no AUC beyond commit size).
* The one soft signal is "grow with logic" edits, consistently above 1 but about 1.1-1.2 per log unit and not visible in AUC.
* Code-only models avoid the prior-fix label-sharing problem entirely, and the outcome label noise does not change the verdict across three labels.

Caveats: four C repos, three of them the ones the archetypes were fitted on; file paths matched by name (renamed files lose history); the regression arm has few events; no hyperparameter search; the later half of a repo's history only.
Tools: `tools/turn/arch_frame.py`, `arch_model.py`, `arch_predict.py` (mix and volume predictability across quarters).
