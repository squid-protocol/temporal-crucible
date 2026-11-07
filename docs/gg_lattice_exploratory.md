# EXPLORATORY — GitGalaxy's own history on the fingerprint lattice

Data: GG's 32 weekly scans of the `gitgalaxy/` package (engine `32619e4a5`, history ablated). Eras as bound in GG: Gemini = born by 2026-07-06; Claude = born from the 2026-07-27 snapshot; transition excluded. Exploratory throughout: GG already showed the eras are distinguishable (AUC 0.877); this describes *how*. The era bundles model, tooling, workflow and codebase maturity, so a within-Claude drift reference is shown beside every comparison.

- functions born (loc ≥ 3, with source): Gemini era 213, Claude era 2,574, early Claude (to 08-31) 67, late Claude (from 10-05) 1,538

## A. Writing style by era

| | Gemini era | Claude era | early Claude | late Claude | population Python |
|---|---:|---:|---:|---:|---:|
| median lines | 35 | 13 | 24 | 12 | 11 |
| rung k ≤ 3 (bricks) | 0% | 0% | 0% | 0% | 1% |
| rung k ≥ 6 | 95% | 96% | 99% | 95% | 76% |
| F7 public/general | 68% | 51% | 22% | 56% | 82% |
| F8 private + pointers/state | 32% | 48% | 76% | 43% | 13% |
| F6 bare one-step | 0% | 0% | 0% | 0% | 2% |
| F3 annotated/test | 0% | 0% | 0% | 0% | 0% |
| grammar fit, median percentile | 53% | 62% | 84% | 55% | 50% |
| grammar-breaking (bottom 10%) | 11.3% | 6.7% | 0.0% | 8.4% | 10% |
| has docstring (mean) | 0.68 | 0.71 | 0.75 | 0.69 | — |
| comment lines / line (mean) | 0.07 | 0.01 | 0.03 | 0.01 | — |
| returns (mean) | 1.49 | 1.96 | 1.79 | 2.04 | — |
| while loops (mean) | 0.05 | 0.17 | 0.36 | 0.16 | — |
| calls per 10 lines (mean) | 4.35 | 5.36 | 3.42 | 5.69 | — |
| max nesting (mean) | 2.28 | 1.56 | 1.96 | 1.49 | — |
| arch_api + def_encapsulation (hole) | 1.4% | 2.9% | 4.5% | 2.3% | 2.2% |
| def_test + def_encapsulation (hole) | 0.5% | 0.0% | 0.0% | 0.0% | 0.4% |
| state_memory_alloc + def_cleanup (attraction) | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| arch_concurrency + def_sync_locks (attraction) | 0.0% | 0.0% | 0.0% | 0.1% | 0.3% |

- **era classifier** (lattice signals + family/rung + size + habits, 5-fold grouped by file): AUC **0.878**; size-matched: **0.860**; within-Claude drift reference (early vs late Claude): 0.712. (GG's registered sfs-feature classifier: 0.877 vs placebos ~0.7.)

## B. How functions move on the lattice (week to week)

- function-weeks observed 18,144; functions tracked 3,215
- **weeks in which a function's shape moved: 2.8%**; functions that never moved over their observed life: **88%** (of those living ≥ 8 weeks: 61%)
- among moves: single-signal steps 75%, jumps (≥ 2) 25%; climbs 42%, descents 22%, same rung (swap) 36%; family changes 4%
- for comparison, LAT-M's 5 C repos (quarterly): 71% of functions never moved; moves 68% single-step; family changes 11% of moves

| interval era | function-weeks | shape moved | climbs : descents | family change (of moves) |
|---|---:|---:|---:|---:|
| gemini | 3,231 | 3.2% | 46 : 9 | 4% |
| transition | 563 | 1.8% | 6 : 0 | 0% |
| claude | 14,350 | 2.8% | 163 : 104 | 4% |

| age (weeks since birth) | function-weeks | shape moved | mean rung |
|---|---:|---:|---:|
| 1–1 | 2,894 | 3.9% | 7.85 |
| 2–3 | 4,902 | 2.7% | 7.89 |
| 4–7 | 4,427 | 1.8% | 8.06 |
| 8–15 | 2,796 | 2.5% | 8.61 |
| 16–99 | 3,125 | 3.8% | 8.89 |

- commonest gains: +arch_import 72, +struct_comprehensions 57, +state_cast_hits 57, +def_safety 27, +struct_branch 26, +state_safety_neg 23, +struct_closures 22, +struct_generics 18
- commonest losses: −state_cast_hits 37, −arch_import 36, −struct_comprehensions 30, −arch_io 25, −arch_regex 23, −def_safety 17, −struct_closures 15, −bitwise_ops 14
- commonest family changes: F7→F8 11, F8→F7 4, F9→F7 3, F8→F9 1, F7→F11 1, F11→F7 1
- mean rung by age, all tracked functions: wk 1: 7.85, wk 2: 7.89, wk 4: 7.95, wk 8: 8.48, wk 12: 8.61, wk 16: 8.77, wk 20: 8.80

Caveats: exploratory; one repository; era bundles model, tooling, workflow and codebase maturity; engine 32619e4a5 rules (before gitgalaxy#8024); population grammar reference scanned with b64f42bf; weekly snapshots miss within-week churn.
