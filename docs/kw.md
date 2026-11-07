# KW-H1..H3 — keyword grammar on the language-crucible (SCORED)

- functions (loc ≥ 3): 43,473; languages with ≥ 500: **22** — ada (815, 15 signals), agc_assembly (678, 17 signals), assembly (1355, 14 signals), c (2612, 16 signals), cobol (6443, 15 signals), cpp (1202, 12 signals), csharp (887, 15 signals), dart (1162, 19 signals), go (1234, 21 signals), groovy (730, 18 signals), java (782, 19 signals), javascript (821, 20 signals), livecode (961, 22 signals), lua (549, 20 signals), perl (825, 25 signals), php (1722, 19 signals), python (3356, 19 signals), rust (2059, 20 signals), shell (838, 24 signals), typescript (6387, 16 signals), yacc (1122, 8 signals), zig (2945, 18 signals)
- candidate signal columns: 89

| claim | observed | label-null mean | label-null 99.67th pct | size placebo | verdict |
|---|---:|---:|---:|---:|---|
| **KW-H1** mean cross-language r of size-stratified co-occurrence (230 language pairs) | **0.167** | 0.000 | 0.037 | 0.242 | **not supported** |
| **KW-H2** mean cross-language r of size-stratified co-occurrence (cross-family pairs only) (218 language pairs) | **0.182** | 0.001 | 0.043 | 0.258 | **not supported** |
| **KW-H3** module agreement (mean ARI, k = 6) | **0.083** | -0.000 | 0.028 | — | **SUPPORTED** |

## Universal positive pairs (median log OR across languages; n languages, sign agreement)

- arch_concurrency + state_bailout_hits: +1.32 (12 langs, 100% same sign)
- def_safety + struct_branch: +1.25 (21 langs, 71% same sign)
- def_cleanup + state_safety_neg: +1.05 (11 langs, 91% same sign)
- state_cast_hits + state_safety_neg: +0.97 (14 langs, 93% same sign)
- state_cast_hits + struct_comprehensions: +0.95 (13 langs, 92% same sign)
- arch_concurrency + def_safety: +0.83 (14 langs, 71% same sign)
- state_bailout_hits + struct_branch: +0.82 (17 langs, 71% same sign)
- arch_api + arch_concurrency: +0.82 (12 langs, 75% same sign)
- def_cleanup + def_safety: +0.81 (11 langs, 91% same sign)
- arch_concurrency + state_safety_neg: +0.78 (13 langs, 85% same sign)
- state_heat_triggers + state_safety_neg: +0.75 (11 langs, 73% same sign)
- state_safety_neg + struct_comprehensions: +0.73 (11 langs, 100% same sign)
- state_bailout_hits + state_cast_hits: +0.72 (14 langs, 93% same sign)
- state_bailout_hits + state_safety_neg: +0.67 (14 langs, 86% same sign)
- arch_concurrency + struct_linear: +0.65 (11 langs, 73% same sign)

## Pairs that avoid each other (most negative median log OR)

- state_bailout_hits × state_flux: -0.60 (17 langs, 82% same sign)
- arch_api × struct_branch: -0.44 (15 langs, 87% same sign)
- state_flux × struct_linear: -0.43 (15 langs, 53% same sign)
- struct_branch × struct_closures: -0.34 (12 langs, 67% same sign)
- arch_api × state_cast_hits: -0.33 (12 langs, 67% same sign)
- arch_concurrency × state_flux: -0.32 (15 langs, 53% same sign)
- state_heat_triggers × struct_branch: -0.27 (13 langs, 62% same sign)
- bitwise_ops × struct_branch: -0.26 (15 langs, 53% same sign)
- state_bailout_hits × struct_linear: -0.25 (11 langs, 55% same sign)
- def_encapsulation × state_flux: -0.11 (11 langs, 55% same sign)
- arch_io × struct_branch: -0.11 (11 langs, 64% same sign)
- arch_concurrency × struct_branch: -0.08 (15 langs, 53% same sign)
- def_cleanup × state_flux: -0.07 (11 langs, 55% same sign)
- arch_api × bitwise_ops: -0.06 (11 langs, 55% same sign)
- def_cleanup × struct_branch: -0.02 (11 langs, 55% same sign)

## Consensus modules (clustering the median association, k = 6)

- **module 1:** bitwise_ops, state_flux
- **module 2:** arch_io
- **module 3:** arch_concurrency, def_cleanup, def_safety, state_bailout_hits, state_cast_hits, state_heat_triggers, state_safety_neg, struct_branch, struct_comprehensions, struct_linear
- **module 4:** struct_closures
- **module 5:** def_encapsulation
- **module 6:** arch_api

## Language typicality (mean correlation with the other languages)

- java: 0.294
- go: 0.273
- php: 0.271
- perl: 0.263
- javascript: 0.258
- dart: 0.233
- csharp: 0.229
- livecode: 0.214
- c: 0.208
- lua: 0.208
- assembly: 0.168
- typescript: 0.164
- ada: 0.157
- groovy: 0.154
- python: 0.148
- agc_assembly: 0.115
- shell: 0.108
- cpp: 0.107
- zig: 0.105
- cobol: 0.061
- rust: 0.052
- yacc: -0.128

Runtime 65s · seed 2982 · 2000 label permutations.
