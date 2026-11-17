# Arguments over a function's life, and what goes wrong (exploratory, hypotheses written before the outcomes were read)

**Status:** exploratory. Not registered. The hypotheses below were written on 2026-11-17 **before** any argument-change or fix outcome was computed; the analysis script is `tools/sensor/args_life_analyze.py`. Anything not listed here and found afterwards is labelled "found after looking".

## Data
Per repository, the quarterly scan snapshots (`turn_v2/scan_<repo>/snapshots.json`; curl 109, libxml2 114, commons-lang 99, sphinx 78, redis 72, libgit2 69, prometheus 57), the function ledger (`structural_fingerprint.ledger.build_ledger`: one lineage id per function across snapshots, following renames and moves), each snapshot's `function_data.args` (parameter count) and `loc`, and the crucible's fix events (`events/<repo>_xc2.json`, FIXLIKE v3c, amendment 2): classes **regression**, **latent**, **extrinsic**, **other-fix** with the C files each fix touched. Builder: `tools/sensor/args_life_build.py`. Functions of 3+ lines only (the ledger's floor).

## Questions
Q1. How do parameter counts move across a function's life: how many functions ever change, how often, by how much, in which direction, and when in life?
Q2. Does a change in parameter count come alone, or with a size change?
Q3. Do arg-count changes go with fixes, and does it depend on the type of fix?

## Hypotheses (fixed before looking)
- **H1 (stability).** Most lineages never change parameter count: more than 80% of lineages observed in 3 or more snapshots have a constant count.
- **H2 (accretion).** Among changes, additions of parameters outnumber removals (parameter creep), in every repository.
- **H3 (when).** Changes are most frequent early in life (the first two intervals after birth) and decline with age.
- **H4 (not alone).** A parameter change in an interval goes with a larger size change than an interval with no parameter change, at the same starting size (a signature edit is part of a bigger edit).
- **H5 (regression link).** Among files edited in an interval, those with a lineage whose parameter count changed are more likely to be touched by a **regression**-class fix in the next interval than files edited without a parameter change (callers must be updated; a missed caller is a regression). The comparison is within files edited in the interval, to hold activity fixed, and is read per repository with an interval.
- **H6 (type).** The link in H5 is weaker or absent for **extrinsic** and **other-fix** classes (fixes whose cause is outside the change history).
- **H7 (births).** Newly born functions have wider parameter lists later in a repository's life than early (accretion at the interface level): parameter count at birth rises with calendar year.

## What would count as a surprise
H1 false (high churn), H2 false (removals dominate), H5 and H6 reversed. Reporting both columns (replication of known, novel) follows the registered-study convention.

## Results (2026-11-17; seven repositories, quarterly snapshots; output `args_over_life_output.txt`)
Repositories: curl, libgit2, redis, libxml2 (C), prometheus (Go), sphinx (Python), commons-lang (Java); 1.7M function-snapshots, 70,000 lineages, source files only. Unit: a lineage seen in consecutive snapshots.

**Q1, how parameter counts move.** A function's parameter count is almost frozen: per quarterly interval only 0.10% (commons-lang) to 1.00% (curl) of function pairs change it; 81% to 96% of lineages seen in three or more snapshots never change it. When it changes it is by one in 64% to 88% of cases, and parameters are added far more often than removed (59% to 84%).

| hypothesis | verdict | evidence |
|---|---|---|
| H1 stability (more than 80% constant) | **supported** | curl 80.8%, libgit2 91.0%, redis 90.5%, libxml2 92.5%, prometheus 90.9%, sphinx 93.6%, commons-lang 96.2% (curl only just) |
| H2 accretion (additions outnumber removals, every repository) | **supported** | added in curl 68%, libgit2 72%, redis 71%, libxml2 65%, prometheus 84%, sphinx 74%, commons-lang 59% |
| H3 changes are most frequent early in life | **partly** | highest in the first interval after birth in 5 of 7 (curl 2.05% against 0.93% after seven or more; libgit2 1.43% against 0.20%; libxml2 0.81% against 0.08%; sphinx 0.68% against 0.34%; prometheus 1.44% against 0.91%); not in redis (peaks at age 3 to 6, 0.89%) or commons-lang (lowest at birth, 0.11%) |
| H4 a parameter change goes with a bigger size change | **supported once the comparison is made fair** | as first computed it is mixed, because the "edited" set counted parameter changes with no size change, which biases against H4 (a flaw in my design found after looking). Among pairs whose size changed, parameter-change pairs have the larger relative size change in 27 of 28 repository-by-size-quartile cells (the exception: redis, smallest quartile, 0.22 against 0.25), typically 1.3 to 3 times the median |
| H5 a parameter change predicts a regression-class fix in the next interval | **not supported** | pooled risk ratio 1.05 [0.93, 1.20]; by repository curl 0.95, redis 1.13, libxml2 1.08, sphinx 0.94, commons-lang 0.95, libgit2 0.54 (6 events), only prometheus 1.69 [1.17, 2.52] |
| H6 the link is weaker for extrinsic and other-fix classes | **not supported as stated** | next-interval pooled risk ratios: other-fix 1.08 [1.01, 1.15], any fix 1.07 [1.00, 1.13], extrinsic 1.15 [0.94, 1.37], latent 1.09 [0.77, 1.58], regression 1.05 [0.93, 1.20]: all small; the only class interval clear of 1 is other-fix, the largest class |
| H7 parameter count at birth rises over the repository's life | **supported in direction, small** | size-controlled rank correlation +0.23 curl, +0.18 libgit2, +0.11 redis, +0.11 sphinx, +0.07 prometheus, +0.06 libxml2, -0.07 commons-lang |

**Raw against adjusted.** Pooled over repositories, 38.1% of edited files with a parameter change were touched by a fix in the next interval against 27.5% without (ratio 1.39); after stratifying by file size and the number of functions edited it is 1.07. Most of the raw link is that files with parameter changes are larger and more edited. The adjusted link is small and not the same in every repository: libgit2 1.38 [1.01, 1.87], prometheus 1.28, sphinx 1.27 and redis **0.83 [0.68, 0.96]** (files with a parameter change were *less* likely to be fixed next quarter).

**Found after looking (not in the hypotheses; treat as a lead):** in the *same* interval, edited files with a parameter change were more likely to be touched by a **regression-class** fix: pooled risk ratio **1.28 [1.15, 1.41]**, above 1 in six of seven repositories (curl 1.27, redis 1.37, libxml2 1.33, prometheus 1.41, commons-lang 1.29, sphinx 1.10; libgit2 0.66 on 46 events). No other class shows it (same-interval extrinsic 0.91, other-fix 1.02). Regression-class means the fix commit references an earlier inducing commit, so this reads as: a signature change that is followed within the quarter by a fix that cites its cause. It cannot say which came first, or that the signature change was the cause: the fix itself may be the signature edit. It is one of ten pooled comparisons in the output; the next test is a registered replication on held-out repositories.

**Caveats.** Quarterly snapshots collapse several edits into one net change (a parameter added and removed inside a quarter is invisible). Edits are proxied by a change in size or parameter count, so same-size edits are missed. The fix link is file level (a fix touches a file, not necessarily the function), by path equality with the snapshot. `args` is the engine's parameter count (C varargs and macros are approximate). Seven repositories, three languages beyond C each with one repository. Exploratory throughout; interval bootstrap intervals do not cover repository-to-repository variation.

**Plain reading.** Interfaces are frozen far more than they move; when they move they grow, and they move most in the first quarter or two of a function's life in most repositories (not all). A change to the interface travels with a bigger edit. As a predictor of later trouble it is weak once file size and edit volume are accounted for; the one lead that stands out is regression-class fixes landing in the same quarter as a signature change.
