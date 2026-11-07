# KWP-H1..H3 — the crucible keyword grammar across the population (SCORED)

- consensus pairs 32; population functions used (crucible-source repos excluded) 2,889,002; languages 22

| claim | result | verdict |
|---|---|---|
| **KWP-H1** crucible signs hold pooled | **328/420 = 78%** of language × pair cells; p = 1.9e-32 | **SUPPORTED** |
| **KWP-H2** shared grammar beyond size | cross-language r **0.235** (228 language pairs); shuffle 99.67th 0.031; size placebo -0.006 | **SUPPORTED** |
| **KWP-H3** holds within repos | 169/174 repo × language units agree on > 50% of pairs (97%); p = 5.4e-44; median unit agreement 76% | **SUPPORTED** |

## Per language (agreement with crucible signs)

- cpp: 92% of 13 pairs
- matlab: 91% of 22 pairs
- python: 90% of 21 pairs
- csharp: 88% of 26 pairs
- c: 88% of 17 pairs
- go: 85% of 27 pairs
- assembly: 83% of 12 pairs
- typescript: 83% of 30 pairs
- perl: 83% of 23 pairs
- ruby: 82% of 11 pairs
- php: 80% of 20 pairs
- swift: 80% of 20 pairs
- html: 76% of 17 pairs
- java: 76% of 25 pairs
- rust: 76% of 29 pairs
- javascript: 75% of 20 pairs
- kotlin: 71% of 24 pairs
- zig: 63% of 19 pairs
- cobol: 57% of 7 pairs
- css: 56% of 9 pairs
- fortran: 50% of 24 pairs
- yaml: 50% of 4 pairs

## Pairs: most and least replicated (share of languages agreeing; crucible sign)

- def_safety / state_cast_hits (+): 100% of 15
- def_cleanup / def_safety (+): 100% of 9
- def_encapsulation / struct_branch (+): 100% of 10
- arch_concurrency / struct_linear (+): 100% of 6
- arch_concurrency / state_cast_hits (−): 100% of 8
- def_safety / state_bailout_hits (+): 94% of 16
- struct_branch / struct_comprehensions (+): 93% of 14
- def_safety / struct_branch (+): 89% of 19
- state_cast_hits / struct_linear (+): 89% of 9
- state_bailout_hits / struct_branch (+): 89% of 18
- …
- state_cast_hits / struct_comprehensions (+): 64% of 11
- arch_api / arch_concurrency (+): 56% of 9
- arch_concurrency / struct_comprehensions (−): 56% of 9
- arch_io / state_flux (+): 50% of 16
- arch_api / state_cast_hits (−): 50% of 14
- struct_branch / struct_closures (−): 40% of 15

Runtime 180s · seed 2982.
