# EXPLORATORY — the constrained middle: three-signal combinations code avoids (population DB v2.12.0-b64f42bf)

- sample 1,999,874 functions (loc ≥ 3); signals with 2–98% presence: 27; triples with null expectation ≥ 200: 2,791
- null: independent signals, per-language size-dependent rates (the KW size placebo); ratio = (observed + 0.5) / (expected + 0.5)
- **higher-order holes** (triple ratio < 0.25 while every pair of it is built at ≥ 0.5 of chance): **1** of 2,791 triples (0.0%); all triples < 0.25 including pair-driven ones: 20

## The strongest higher-order holes, and how universal they are

| combination (all three present) | observed | chance expects | ratio | languages where it holds | large repos where it holds |
|---|---:|---:|---:|---:|---:|
| Branches & Conditionals + Class / Struct Declarations + Decorators, Annotations & Attributes | 2,052 | 8,667 | 0.237 | 3/6 | 5/10 |

- **universal** (holds in ≥ 80% of languages and of large repos where testable, ≥ 5 each): 0 of the 1 shown

## For contrast: the strongest higher-order attractions

- Class / Struct Declarations + Manual Memory Allocation + Resource Cleanup: 4,092 vs 403 expected (10.2×)
- Manual Memory Allocation + Immutability + Resource Cleanup: 3,646 vs 414 expected (8.8×)
- Pointers & Addressing + Manual Memory Allocation + Resource Cleanup: 11,684 vs 1,453 expected (8.0×)
- Unsafe Constructs + Decorators, Annotations & Attributes + Preprocessor Directives & Macros: 2,105 vs 267 expected (7.9×)
- File & Network I/O + Manual Memory Allocation + Resource Cleanup: 1,703 vs 217 expected (7.8×)
- Manual Memory Allocation + Resource Cleanup + Private Scope: 5,612 vs 721 expected (7.8×)
- Manual Memory Allocation + Print / Console Output + Resource Cleanup: 1,738 vs 247 expected (7.0×)
- Metaprogramming + Manual Memory Allocation + Resource Cleanup: 2,165 vs 309 expected (7.0×)

Caveats: exploratory; one null draw family (size-only); presence only; function-weighted (OS-scale repos weigh heavily, hence the per-repo check); rules as of b64f42bf (before gitgalaxy#8024 / #8016).
