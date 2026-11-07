# WILD-H1..H2, WILD-C1 — model handwriting inside GitGalaxy's own codebase (SCORED)

- window 2026-10-03 .. 2026-11-07; labelled single-model commits with born Python functions: 2,016 (bulk > 300 excluded: 0); born functions (loc ≥ 3): 13,145 — Sonnet 5.5 7,849, Opus 5.5 5,296
- strata (directory × size band) with both models: 62

| claim | result | verdict |
|---|---|---|
| **WILD-H1** structure separates Sonnet from Opus beyond directory × size | stratified AUC **0.572**; week-blocked commit permutation null median 0.557, 99th pct 0.582; p = 0.0889 | **not supported** |
| **WILD-H2** context dominates (same dir/different model vs same model/different dir) | median distance ratio **0.922** (99% CI 0.897–0.946); medians 6.35 vs 6.89 | **not supported** |
| **WILD-C1** pseudo-model control (Sonnet commits split in two) | stratified AUC 0.482 (bar < 0.55) | **PASS** |

## Descriptive

- largest standardised coefficients (positive = more Sonnet): has arch_api +0.39, has def_encapsulation +0.34, has struct_generics -0.29, log2 loc -0.21, has def_test +0.14, rung k +0.14, family F7 -0.10, family F8 +0.10, docstring -0.08, has state_pointers -0.06

| | Sonnet 5.5 | Opus 5.5 |
|---|---:|---:|
| median lines (2^log2) | 7 | 9 |
| docstring | 0.32 | 0.44 |
| comment lines / loc | 0.01 | 0.01 |
| returns | 0.56 | 0.88 |
| whiles | 0.02 | 0.03 |
| calls | 6.25 | 8.17 |
| nesting depth | 0.63 | 0.84 |
| rung k (median) | 8 | 8 |
| family F7 share | 81.0% | 80.0% |
| family F8 share | 18.6% | 19.3% |
| family F6 share | 0.2% | 0.3% |

- lab comparison (agent-habits, sfs): same model/same job 0.32 vs different model/same job 0.62 (ratio 0.52); here the context/model ratio is 0.92

Runtime 4019s · seed 2982 · 1000 permutations · 1000 bootstrap rounds.
