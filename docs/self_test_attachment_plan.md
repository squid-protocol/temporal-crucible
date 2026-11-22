# Do changes to unit-tested files end up as fixes less often? Test-attachment study on GitGalaxy (plan fixed 2026-11-20, before any model is fitted; EXPLORATORY)

Owner question (2026-11-20): does the very large test pipeline make regressions less likely, and does the data support that? Context: `docs/self_evolution/tests_and_regressions_quick_look.md` (descriptive counts only). This is the first of the two proper tests listed there (test attachment per file); the second (before/after the date a golden gate was added) is not run here. Observational; no causal claim can come from it.

## Unit, outcome, exposure
- Rows: one engine file in one ISO week (the week of the commits). Engine files: Python under `gitgalaxy/` (or early `backend/`, canonicalised to `gitgalaxy/`), excluding tests, `standards/` pattern tables and `__init__.py`. Weeks from 2026-03-21 to 2026-11-20.
- Touches: function touches per commit from the evolution generator's diff cache (`evolution_real/cache/diff_gitgalaxy-engine_*.json.gz`; Python engine functions). A commit is a FIX commit if its squash subject begins with `fix` or `bugfix` (case-insensitive) or its PR carries the `bug` label (the V1 rule); every other commit counts as a non-fix change.
- Outcome per file-week: y = number of fix touches, n = all touches; only file-weeks with n >= 1.
- Exposure (attachment), measured at the end of the PREVIOUS week: the number of distinct test files under `tests/` (Python) that import the file's module (AST: `import gitgalaxy.core.detector`, `from gitgalaxy.core.detector import x`, `from gitgalaxy.core import detector`), on the first-parent commit that ends the previous week. Files that did not exist at that commit are excluded from the model (no lagged attachment). Unit-test coupling only: golden and crucible pipeline tests attach to everything and are not measured here.
- Covariates: log lines of the file at the end of the previous week (from the daily scan at or before that date), file age in weeks, log(1 + touches in the previous 4 weeks), era (Gemini < 2026-07-06, Claude 2026-07-22..09-26, fleet from 2026-09-27; the transition fortnight as its own level), and top-level group (core, tools, recorders, other).
- Model: logistic regression on (y, n - y), cluster-robust standard errors by file.

## Hypotheses (declared now)
- T1: files with at least one attached test have a lower fix share among their touches than unattached files, after the covariates: odds ratio below 1 with a 95% interval wholly below 1. Not supported if the interval includes 1; refuted if the odds ratio is 1 or above.
- T2 (dose): the coefficient on log(1 + number of attached test files) is negative with an interval wholly below 0.
- T3 (direction): (a) the same model with NEXT week's attachment (a lead): if it is as strong as the lagged one, the lagged result does not show tests acting first; (b) among files with at least one fix touch in a week, the share whose attachment rises the following week, against files without a fix touch (tests added after bugs). Reported, not gated.
Descriptive first: share of engine files with at least one attached test by month; raw fix share for attached and unattached file-weeks; the size distribution of each group.
Robustness (reported): the same model using the previous 2 weeks' attachment; a file-level version (each file's total fix share against its attachment at the end of its first 4 weeks, size-decile matched).

## What this can and cannot say
Cannot separate the effect of tests from the effect of change: heavily changed files attract both tests and fixes (the covariates for size and recent change only partly absorb it); regression tests are written after bugs (T3b); 92% of engine-code PRs already change a test, so attachment varies mainly by file; the repo has no untested era; AI authorship, gates and growth move together; young code has had little time to be repaired. A negative odds ratio would be consistent with tests lowering the repair share, not proof.
