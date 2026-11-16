---
description: "> **Status:** design and prototype (not yet in the engine). Replaces the public-surface ratio in 08-14 with measured reach: who calls into a file, and who is affected by a change."
---
# Reach Sensor (Who Depends on This)

> **Status:** Design note and prototype (temporal-crucible, branch `sensor-overhaul`, `tools/sensor/reach_panel.py`, `reach_validity.py`, `migration_scope.py`). **Not shipped:** the current gauge is documented in [Connectivity (API Surface)](08-14-api-exposure.md) and is unchanged by this page.
>
> **Metric:** Number of other files and functions that call into a file (and one hop further out); for headers, the number of files that include them.
>
> **Summary:** Answers "if I change this, how much code is on the receiving end?" from the call graph, in plain counts, with an explicit "not measured" state. It shows where the load-bearing files are and scopes migrations. It is context, not a risk score.

## Engineering Summary
The current gauge measures what a file offers (export keywords against private ones). Reach measures what is used: the call graph already records which function calls which. Counting distinct caller files and caller functions, plus a second hop, gives a unit people can reason about, and the same data scopes a rename or removal before anyone starts it.

## Purpose
To list the files and public functions the rest of the code depends on, flag files where reach is not measurable (headers need include counts; files with no resolvable functions), and predict the blast radius of a planned API migration.

## Problem Being Solved
Export keywords say little about use (a file can export many functions nobody calls). The ratio is computed on the wrong file for C-family code (headers declare, source files define). The popularity multiplier is the only use-based term and is capped.

## Design
1. **Caller counts.** Per file: distinct other files that call any function it defines, distinct caller functions, and further callers one hop out. Per function: files that call it. Rank-equivalent to a text search of the same snapshot at +0.63 to +0.91 per file (4 repositories), and +0.74 to +0.92 per function (7).
2. **Headers use include counts.** Count of files that `#include` the header, because call-based reach is blind to headers (-0.18 to +0.23 against include counts). On curl `curl_setup.h` is included by 292 files, `first.h` 261, `curl.h` 151, `urldata.h` 136.
3. **Coverage line.** Each report says how many files were measured by calls, by include counts, and how many are "not measured" (no functions and not a header: 159 of 1,126 files in curl, 266 of 1,299 in libgit2), and states that standard-library and macro calls are not recorded.
4. **Role tag.** Source, tests and docs, CI configuration; lists default to source.
5. **Companion lists.** Files with the most callers; most-used public functions; **stable foundations** (reach in the top decile and no commit in a year: libgit2 has 9, including `src/util/errors.c` with 591 caller files); with the [Activity sensor](08-25-activity-sensor.md), **active and high reach**, the best simple later-fix list (x2.1, x2.0, x2.6 on three repositories).
6. **Migration scope report.** Given an old name, a new name and the snapshot before the change, list the callers (functions, files, lines, source against tests), the ripple, and afterwards the stragglers. libgit2 `git_buf_free` to `git_buf_dispose` (2018): predicted 761 callers in 228 files; the sweep touched 757; the remaining stragglers were tests using the public API.

## Pipeline Integration
- **Inputs:** function-level call edges (already persisted in the scan database), include directives (parsed, not persisted), the history-aware scan of the commit before a migration.
- **Outputs:** per-file and per-function reach, include counts, coverage line, lists, migration report.
- **Dependencies:** the call-graph builder; [Activity sensor](08-25-activity-sensor.md) for the combined list.

## Tradeoffs
- Counts are not scores; there is no cross-repository scale. Reach grows with repository size, so lists are read within a repository.
- Recall is about half (unresolved calls are not recorded), so counts are lower bounds; precision is 1.00 at the median.

## Limitations
- Seven repositories, one snapshot each; C and C++ dominate the strong results. For Python and Go the engine finds less (prometheus, sphinx, ripgrep: +0.57 to +0.74 at file level) and sphinx and ripgrep need replication.
- Dynamic dispatch, callbacks and macros hide calls.
- Reach says nothing about quality or risk; it is not a defect predictor beyond a small addition to code size (+0.012 to +0.018 AUC).
- The migration estimate has been checked against one migration.

## Performance Notes
No extra scanning: counts come from edges already in the scan database; include parsing is one pass over source text.

## Future Work
Persist calls to external names as callee nodes; persist include counts; test more migrations; add languages with resolvable imports.

## Related Components
- [Connectivity (API Surface)](08-14-api-exposure.md) (the current gauge)
- [Activity sensor](08-25-activity-sensor.md)
- [Debt ledger](08-24-debt-ledger-sensor.md)

## Evidence and Provenance
temporal-crucible, `docs/sensor-overhaul/sensors/reach.md` and logs (`reach_validity_output.txt`, `reach_panel_demo.txt`, `migration_scope_libgit2*.txt`). Exploratory; no registered test.
