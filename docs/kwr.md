# KW-R — stoichiometric (compositional log-ratio) co-occurrence, method check (SCORED)

- languages 22; functions kept (total used-signal count ≥ 3): ada 493, agc_assembly 480, assembly 989, c 2387, cobol 4660, cpp 1072, csharp 752, dart 1100, go 1125, groovy 480, java 735, javascript 600, livecode 785, lua 362, perl 754, php 1373, python 2842, rust 1750, shell 566, typescript 5474, yacc 780, zig 2656

| claim | result | verdict |
|---|---|---|
| **KWR-H1** ratio method removes size | size-only placebo cross-language r = **0.221** (bar ≤ 0.05; KW decile method gave 0.242) | **not supported** |
| **KWR-H2** grammar remains under ratios | real r = **0.247**; shuffle null 99.5th 0.032; placebo 0.221; real − placebo +0.026 | **not supported** |

Sensitivity (pseudocount: real r / placebo r): 0.5: 0.247 / 0.221; 0.1: 0.207 / 0.149; 1.0: 0.270 / 0.248

## Most proportional pairs (median ρ across languages; share agreeing in sign; n languages)

- struct_branch + struct_linear: +0.32 (80%, 15)
- state_flux + struct_branch: +0.20 (91%, 22)
- arch_api + arch_concurrency: +0.19 (92%, 12)
- arch_api + bitwise_ops: +0.11 (64%, 11)
- state_cast_hits + struct_comprehensions: +0.10 (69%, 13)
- arch_api + state_bailout_hits: +0.09 (75%, 12)
- arch_concurrency + state_bailout_hits: +0.07 (92%, 12)
- bitwise_ops + state_cast_hits: +0.06 (62%, 13)
- def_encapsulation + state_cast_hits: +0.04 (73%, 11)
- arch_api + state_safety_neg: +0.04 (62%, 13)
- def_safety + struct_linear: +0.03 (64%, 14)
- state_safety_neg + struct_closures: +0.02 (55%, 11)
- def_cleanup + state_safety_neg: +0.02 (55%, 11)
- state_cast_hits + state_safety_neg: +0.01 (57%, 14)
- state_bailout_hits + state_heat_triggers: +0.00 (58%, 12)

## Most anti-proportional pairs

- arch_api × struct_branch: -0.36 (93%, 15)
- arch_concurrency × state_flux: -0.24 (100%, 15)
- struct_branch × struct_closures: -0.23 (100%, 12)
- bitwise_ops × struct_branch: -0.22 (73%, 15)
- arch_concurrency × struct_branch: -0.22 (100%, 15)
- arch_api × state_flux: -0.21 (93%, 15)
- state_heat_triggers × struct_branch: -0.21 (100%, 13)
- def_cleanup × struct_branch: -0.21 (100%, 11)
- def_encapsulation × struct_branch: -0.18 (82%, 11)
- def_cleanup × state_flux: -0.18 (100%, 11)
- arch_io × struct_branch: -0.16 (82%, 11)
- state_flux × state_heat_triggers: -0.16 (92%, 13)

Runtime 28s · seed 2982.
