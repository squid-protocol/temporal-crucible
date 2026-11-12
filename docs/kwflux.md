# What is constant and what is in flux (KWFLUX, EXPLORATORY)

**Type: exploratory.** No registration, no hypothesis fixed in advance, **no p-value claimed**. Tool: `tools/kwflux_eval.py`. Repos: curl, openssl, libarchive, harfbuzz, ndpi. Run 2026-11-11.

## The question

[`kwmature.md`](kwmature.md) ranked families by **which way** their share moves over a function's life. That direction did not replicate: `state_pointers` is the top gainer in curl and the top loser in nDPI. This note drops direction and asks only **what moves at all**, which is the part that can be compared across projects.

Everything is conditioned on an **edit** — a transition where any family count or the line count changed. Unedited transitions are the large majority and would otherwise set every rate near zero.

| repo | functions | edited transitions |
|---|---:|---:|
| curl | 13,745 | 32,275 |
| openssl | 36,833 | 48,793 |
| libarchive | 5,549 | 5,426 |
| harfbuzz | 9,264 | 8,522 |
| ndpi | 3,115 | 5,399 |

## Every family, by how often it moves when the function is edited

`P(moves | edited)`, per repo. A family is blank where fewer than 100 functions in that repo ever hold it — out of scope, not constant.

| family | curl | openssl | libarchive | harfbuzz | ndpi | mean | spread |
|---|---:|---:|---:|---:|---:|---:|---:|
| `state_pointers` | 0.469 | 0.391 | 0.498 | 0.426 | 0.563 | 0.469 | 0.172 |
| `struct_branch` | 0.404 | 0.398 | 0.410 | 0.377 | 0.436 | 0.405 | 0.058 |
| `state_flux` | 0.345 | 0.284 | 0.369 | 0.262 | 0.308 | 0.314 | 0.107 |
| `struct_linear` | 0.335 | 0.243 | 0.331 | 0.344 | 0.267 | 0.304 | 0.101 |
| `struct_args` | 0.102 | 0.225 | 0.157 | 0.142 | 0.088 | 0.143 | 0.138 |
| `struct_macros` | 0.120 | 0.091 | 0.152 | 0.067 | 0.090 | 0.104 | 0.085 |
| `def_freeze_hits` | 0.075 | 0.105 | 0.083 | 0.126 | 0.047 | 0.087 | 0.080 |
| `state_cast_hits` | 0.103 | 0.050 | 0.084 | 0.104 | 0.041 | 0.076 | 0.064 |
| `def_safety` | 0.077 | 0.040 | 0.134 | 0.035 | 0.059 | 0.069 | 0.099 |
| `state_heat_triggers` | 0.026 | 0.093 | 0.024 | 0.009 | — | 0.038 | 0.084 |
| `state_safety_neg` | 0.036 | 0.041 | 0.032 | 0.029 | 0.044 | 0.037 | 0.015 |
| `def_cleanup` | 0.060 | 0.003 | 0.071 | 0.027 | 0.017 | 0.035 | 0.068 |
| `state_memory_alloc` | 0.062 | 0.003 | 0.064 | 0.016 | 0.015 | 0.032 | 0.062 |
| `bitwise_ops` | 0.028 | 0.030 | 0.040 | 0.020 | 0.023 | 0.028 | 0.020 |
| `state_print_hits` | 0.037 | 0.018 | 0.017 | 0.009 | 0.054 | 0.027 | 0.045 |
| `def_encapsulation` | 0.021 | 0.016 | 0.039 | 0.000 | 0.047 | 0.025 | 0.047 |
| `arch_globals` | 0.017 | 0.054 | 0.009 | 0.015 | — | 0.024 | 0.045 |
| `arch_api` | 0.014 | 0.010 | 0.012 | 0.001 | 0.079 | 0.023 | 0.078 |
| `state_bailout_hits` | 0.017 | 0.021 | 0.009 | 0.003 | 0.020 | 0.014 | 0.018 |
| `arch_io` | 0.025 | 0.004 | 0.017 | 0.008 | — | 0.013 | 0.021 |
| `struct_closures` | — | — | — | 0.010 | — | 0.010 | 0.000 |
| `arch_regex` | 0.013 | 0.004 | — | — | — | 0.009 | 0.009 |
| `arch_time` | 0.010 | 0.001 | 0.011 | — | — | 0.008 | 0.010 |
| `struct_func_start` | 0.007 | 0.001 | 0.020 | 0.001 | 0.001 | 0.006 | 0.019 |
| `arch_ipc` | 0.009 | 0.002 | — | — | — | 0.005 | 0.007 |
| `arch_events` | 0.004 | — | — | — | — | 0.004 | 0.000 |
| `state_danger` | 0.004 | 0.003 | — | — | — | 0.004 | 0.001 |
| `def_telemetry` | 0.004 | — | — | — | — | 0.004 | 0.000 |
| `arch_import` | — | 0.001 | — | — | — | 0.001 | 0.000 |

## The categorisation

A family is **IN FLUX** only if it lands in the top third of the move-rate ranking in *every* repo where it is in scope, and **CONSTANT** only if it lands in the bottom third in every one. Anything that disagrees across projects is **MIXED**, which is a result about the family, not a failure.

| verdict | families |
|---|---|
| **IN FLUX everywhere** | `state_pointers`, `struct_branch`, `state_flux`, `struct_linear`, `struct_args`, `struct_macros` |
| **CONSTANT everywhere** | `arch_time`, `struct_func_start` |
| MIXED | `def_freeze_hits`, `state_cast_hits`, `def_safety`, `state_heat_triggers`, `state_safety_neg`, `def_cleanup`, `state_memory_alloc`, `bitwise_ops`, `state_print_hits`, `def_encapsulation`, `arch_globals`, `arch_api`, `state_bailout_hits`, `arch_io` |

## Do projects agree about what moves?

Spearman correlation between repos of the per-family move rate (families in scope in both).

| | curl | openssl | libarchive | harfbuzz | ndpi |
|---|---:|---:|---:|---:|---:|
| **curl** | 1.00 | 0.79 | 0.93 | 0.94 | 0.73 |
| **openssl** | 0.79 | 1.00 | 0.69 | 0.81 | 0.81 |
| **libarchive** | 0.93 | 0.69 | 1.00 | 0.88 | 0.70 |
| **harfbuzz** | 0.94 | 0.81 | 0.88 | 1.00 | 0.67 |
| **ndpi** | 0.73 | 0.81 | 0.70 | 0.67 | 1.00 |

## Do the same functions change the same way each time?

For every function edited at least twice: the Jaccard overlap between the set of families it moved in one edit and the set it moved in the next. The null pairs **different** functions' edits, matched on both set sizes, so a high overlap cannot come from most edits touching one or two families.

| repo | successive edit pairs | own next edit | size-matched null | ratio |
|---|---:|---:|---:|---:|
| curl | 20,952 | **0.314** | 0.211 | 1.49× |
| openssl | 23,692 | **0.311** | 0.208 | 1.49× |
| libarchive | 2,484 | **0.338** | 0.218 | 1.55× |
| harfbuzz | 3,896 | **0.358** | 0.216 | 1.66× |
| ndpi | 3,149 | **0.380** | 0.262 | 1.45× |

## Co-change (a first look, not a result)

Lift = P(A and B both move in one edit) / P(A)·P(B), over edited transitions. Lift 1.0 means the two move independently. Pairs are ranked by lift among families in scope with a move rate of at least 2%, so the list is not dominated by rare families that co-occur once.

In **curl**, 17 families qualify.

| pair | P(both move) | lift |
|---|---:|---:|
| `state_memory_alloc` + `def_cleanup` | 0.050 | 13.52× |
| `state_safety_neg` + `state_cast_hits` | 0.021 | 5.68× |
| `arch_io` + `bitwise_ops` | 0.003 | 4.85× |
| `def_cleanup` + `arch_io` | 0.007 | 4.53× |
| `state_print_hits` + `arch_io` | 0.004 | 4.46× |
| `struct_args` + `struct_macros` | 0.050 | 4.08× |
| `def_encapsulation` + `def_freeze_hits` | 0.006 | 3.84× |
| `state_safety_neg` + `def_safety` | 0.010 | 3.57× |
| `def_encapsulation` + `bitwise_ops` | 0.002 | 3.57× |
| `state_memory_alloc` + `def_safety` | 0.017 | 3.55× |
| `state_heat_triggers` + `def_safety` | 0.006 | 3.24× |
| `state_safety_neg` + `arch_io` | 0.003 | 3.23× |

## Limits

- **An edit is a change in the engine's counts or the line count**, not a diff. A change that keeps every count identical is invisible here, and [`kwnest.md`](kwnest.md) shows those exist: of 375 curl functions edited while keeping an identical keyword multiset, naming and wiring still moved.
- **The walk is quarterly**, so a move and its reversal inside one quarter is invisible. Every rate here is a floor.
- **Identity is `(file_path, func_name)`**, so a rename reads as a death and a birth and the sample leans toward survivors.
- **Move rates are not independent of family mass**: a family with many hits per function has more chances to differ. The mass column is not shown here; the cross-repo agreement, not the absolute rate, is what this note reads.
- **Five C/C++ projects.** Nothing here speaks to other languages, and the keyword families are defined per language, so they are not comparable across them as implemented.

Runtime 34s · seed 2982.
