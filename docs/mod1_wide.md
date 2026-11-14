# Tree-wide commits labelled as fixes (2026-11-13) — exploratory, run after the MOD-1 result

**Not part of the registered MOD-1 measurement.** `docs/mod1_result.md` stands as registered. This is checklist
item 8, run after the result was seen because bugzilla (198 of 198 files positive) and sphinx (125 of 175)
pointed at it. Treat every number here as exploratory.

**Definition, fixed before looking at any repo's lift under it:** a fix commit is *tree-wide* if, in the
outcome window, it touches at least 10% of the repo's unit files and at least 20 of them
(`mod1_lift.WIDE_SHARE`, `WIDE_MIN_FILES`). Per-repo detail: `docs/mod1_wide/reg/` (registered outcome, with
the wide-commit report) and `docs/mod1_wide/drop/` (those commits removed from the outcome). The refactor
changed no registered number (46 of 46 identical).

## 7 of 40 repos have one, and it rewrites the two strongest positives

| repo | unit files | positives | wide commits | positives without | lift registered | lift without | largest wide commit |
|---|---|---|---|---|---|---|---|
| ndpi | 312 | 263 | 2 | 58 | **+0.178** | −0.070 [−0.155, +0.008] | 244 files (78%): "License: non-commercial vs commercial applications" |
| sphinx | 175 | 125 | 5 | 82 | **+0.100** | −0.027 [−0.089, +0.029] | 84 files (48%): "Fix TCH001 (move application import into a type-checking block)" |
| bugzilla | 198 | 198 | 4 | 143 | nothing to rank | −0.099 [−0.163, −0.038] | 197 files (100%): "Replace the MPL 1.1 license by the MPL 2.0 one in all files" |
| pandas | 317 | 193 | 1 | 178 | +0.004 | −0.003 [−0.031, +0.026] | 92 files (29%): "STY: Use ruff to format docstrings" |
| bun | 452 | 250 | 2 | 233 | −0.048 | −0.050 [−0.084, −0.018] | 84 files (19%): "remove many `usingnamespace` …" |
| sqlmap | 352 | 90 | 1 | 81 | −0.099 | −0.113 [−0.176, −0.050] | 36 files (10%): "Fixes #3622" |
| curl | 450 | 280 | 1 | 280 | −0.147 | −0.147 | 54 files (12%): "lib: keep timestamp in easy handle" |

A licence change and a lint rule were being counted as fixes to most of a repository. Both of the positive
repos among the earlier eight — the ones that made a "sign split" look real — were this.

## The picture without them

38 repos scored (bugzilla becomes rankable). In-degree is below LOC in **36 of 38**; the CI excludes zero on
the negative side in **28**, on the positive side in **1** (cpython), and includes zero in 9. Cell means:
old/C −0.076, old/managed −0.071, young/C −0.050, young/managed −0.076.

The age test is unchanged in reading and flatter in size: `old` −0.009 [−0.041, +0.022] (registered: −0.027
[−0.073, +0.014]); S1 and drawn-only also include zero. **MOD-H1 not detected** either way.

## What it means

- There is no sign split to explain. On this measure, in this pool, a file's inbound-call count ranks later
  fix touches worse than its size does, nearly everywhere.
- The threshold (10%, 20 files) is one choice. A lower one would catch more; not explored, to avoid tuning
  after the fact.
- The same commits are in the HR-1/2/3 outcomes (`docs/hr_units.md` — sphinx is nearly all positive there for
  this reason). Those have not been re-run with wide commits removed.
- curl and nDPI studies in `EXPERIMENTS.md` that use a fix-commit outcome on nDPI inside this window inherit
  the licence commit. Not checked.
