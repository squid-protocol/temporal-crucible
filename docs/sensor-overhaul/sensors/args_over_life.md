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
