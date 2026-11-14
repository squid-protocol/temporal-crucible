# HR-1 / HR-2 / HR-3 re-run under the study checklist (2026-11-13)

`docs/hr_results.md` reported these on the eight-repo cohort. They are re-run here with two corrections from
`docs/STUDY_CHECKLIST.md`, as opt-in switches (`--units-only`, `--merge-aware`) so the published runs still
reproduce: the "old" columns below were regenerated today and match the published numbers. Raw outputs:
`docs/hr_units/*.json`. Replication on seen repos, exploratory — this is a correction, not a new confirmation.

- **units-only** (item 1): rank only files that can be positive. The old runs ranked every scanned file; docs,
  tests and other-language files have no fix history and little LOC, so they were free true-negatives.
- **merge-aware** (item 3): keep merges where the history made them the unit. Applied to HR-1 only — the
  line-delta harvest behind HR-2 and HR-3 holds no merge commits, so prometheus is uncorrected there.

## HR-1 — does a file's prior-fix count beat its size? Published: "replicates". Corrected: it does not.

Lift = AUC(prior fixes) − AUC(LOC), raw keyword label.

| repo | files old → new | lift old | lift corrected | 95% CI corrected |
|---|---|---|---|---|
| commons-lang | 520 → 250 | +0.143 | −0.051 | [−0.102, +0.000] |
| libgit2 | not evaluable → 438 | — | −0.095 | [−0.144, −0.045] |
| libxml2 | 1,686 → 153 | +0.025 | +0.082 | [+0.002, +0.162] |
| postgres | 4,358 → 2,064 | +0.110 | −0.015 | [−0.033, +0.004] |
| prometheus | 1,179 → 329 | +0.009 | −0.082 | [−0.117, −0.045] |
| redis | 954 → 165 | +0.091 | −0.003 | [−0.052, +0.046] |
| sphinx | 685 → 177 | +0.116 | +0.268 | [−0.080, +0.654] — degenerate, see below |
| ripgrep | under the floor | — | — | — |

| | positive repos | pooled lift | 95% CI |
|---|---|---|---|
| Published (raw label) | 6 of 6 | +0.082 | [+0.039, +0.125] |
| Corrected (raw label) | 2 of 7 | +0.015 | [−0.079, +0.108] |
| Old rule, cleaned label (v3c) | 3 of 6 | +0.009 | [−0.011, +0.029] |
| Corrected, cleaned label (v3c) | 2 of 7 | −0.052 | [−0.095, −0.008] |

The published +0.082 was the file universe. Among source files, prior-fix count ranks later fixes about as
well as size under the raw label and somewhat worse under the cleaned one. It is still a usable predictor on
its own (AUC 0.72–0.84); it just does not beat size, and whether it *adds* to size was not tested (item 13).

libgit2 became evaluable because counting its merges moves the cut out of a four-commit gap.

## HR-2 — change entropy vs size: still a null

Positive in 1 of 6 repos (was 4 of 6); pooled CI [−0.039, +0.016] (was [−0.023, +0.026]). The published
remark that entropy "never beats recidivism" no longer holds: corrected, it is ahead in 4 of 6.

## HR-3 — prior-fix count at function grain: negative, more clearly

Positive in 0 of 7 repos (was 1 of 7); pooled CI [−0.173, −0.056] (was [−0.148, −0.020]). redis moves from
+0.023 to −0.050.

## A new problem this exposed: sphinx is nearly all positive

Under the raw label **174 of sphinx's 177 source files are positive** in the outcome window (125 of 177 under
the cleaned label). There is almost nothing to rank: HR-2 returns AUC 1.000 for both sides, HR-1's interval
spans −0.08 to +0.65. This is checklist item 8 — most likely one or a few tree-wide commits labelled as fixes.
It matters beyond this page: sphinx is one of only three solidly positive repos in `docs/mod1_result.md`, with
125 positives over 175 files. Not yet traced.

## What this does and does not touch

- **Touched:** `hr_results.md` (HR-1's "replicates"), and `hr1_bias_analysis.md`, whose "observed lift" inputs
  were the published HR-1 numbers. The bias simulator itself ranks only touched files and is not affected by
  the universe problem.
- **Not touched:** the curl and nDPI recidivism results in `EXPERIMENTS.md` (their own C-file lists, a
  review-budget metric); they have not been re-run under the checklist.
