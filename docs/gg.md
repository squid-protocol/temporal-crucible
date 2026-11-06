# GG-H1..H3 — GitGalaxy's own history: Gemini era vs Claude era (SCORED)

- 32 weekly snapshots of the `gitgalaxy/` package; functions born: Gemini 366, Claude 2,549, transition 35 (excluded)

| claim | result | verdict |
|---|---|---|
| **GG-H1** Claude-born vs Gemini-born functions distinguishable beyond within-era drift | cross-era AUC **0.877**; placebos: early-vs-late Gemini 0.725, early-vs-late Claude 0.669; margin +0.152 (lo +0.086) | **SUPPORTED** |
| **GG-H2** drastic change point at the switch (both best breaks in 07-01 → 08-12) | keyword-mix break **2026-10-12**; sfs-fingerprint break **2026-10-12** | **not supported** |
| **GG-H3** Gemini code rewritten faster after the switch | weekly death hazard of Gemini-born functions: before 0.0262, after 0.0065; ratio **0.25** (lo 0.02) | **not supported** |

## What separates the eras (standardised mean difference, Claude − Gemini; descriptive)

- keyword_density: +0.81
- struct_generics: +0.81
- struct_branch: +0.79
- log10 loc: -0.78
- complexity/loc: +0.76
- struct_linear: +0.71
- state_print_hits: -0.62
- struct_func_start: +0.57
- struct_args: +0.55
- def_encapsulation: +0.34

## Archetype mix of functions born in each era (descriptive)

| archetype | Gemini | Claude |
|---|---:|---:|
| Stateful Encapsulated Methods | 29.5% | 33.9% |
| Generic / Templated Code | 9.8% | 22.4% |
| Compute Cores | 9.6% | 13.3% |
| Many-Argument Workhorses | 29.5% | 8.9% |
| Encapsulated Accessors | 4.9% | 11.7% |
| Defensive Guards | 3.6% | 5.3% |
| Type Conversions | 3.3% | 3.5% |
| I/O & Config Routines | 7.7% | 0.4% |
| Parameter Forwarders | 1.9% | 0.5% |
| Callbacks & Closures | 0.3% | 0.2% |
| Interface Declarations | 0.0% | 0.1% |

## Weekly series (descriptive)

| week | python files | functions | sfs twin retention vs previous week |
|---|---:|---:|---:|
| 2026-03-23 | 15 | 154 | nan |
| 2026-03-30 | 16 | 166 | 0.94 |
| 2026-04-06 | 15 | 167 | 0.66 |
| 2026-04-13 | 15 | 160 | 0.81 |
| 2026-04-20 | 53 | 253 | 0.92 |
| 2026-04-27 | 53 | 258 | 0.97 |
| 2026-05-04 | 53 | 258 | 0.97 |
| 2026-05-11 | 53 | 258 | 0.98 |
| 2026-05-18 | 54 | 261 | 0.97 |
| 2026-06-01 | 58 | 274 | 0.73 |
| 2026-06-08 | 59 | 281 | 0.97 |
| 2026-06-15 | 59 | 281 | 0.98 |
| 2026-06-22 | 58 | 277 | 0.88 |
| 2026-06-29 | 58 | 277 | 0.93 |
| 2026-07-06 | 58 | 277 | 0.98 |
| 2026-07-13 | 59 | 287 | 0.94 |
| 2026-07-20 | 59 | 287 | 0.98 |
| 2026-07-27 | 62 | 316 | 0.85 |
| 2026-08-03 | 62 | 317 | 0.97 |
| 2026-08-10 | 62 | 321 | 0.93 |
| 2026-08-17 | 62 | 334 | 0.93 |
| 2026-08-24 | 62 | 343 | 0.98 |
| 2026-08-31 | 62 | 351 | 0.97 |
| 2026-09-07 | 126 | 385 | 0.97 |
| 2026-09-14 | 126 | 413 | 0.96 |
| 2026-09-21 | 141 | 576 | 0.89 |
| 2026-09-28 | 199 | 1400 | 0.86 |
| 2026-10-05 | 218 | 1835 | 0.94 |
| 2026-10-12 | 245 | 2232 | 0.89 |
| 2026-10-19 | 272 | 2519 | 0.95 |
| 2026-10-26 | 292 | 2769 | 0.93 |
| 2026-11-02 | 318 | 3072 | 0.94 |

Runtime 9s · seed 2982. Note: GG-H1's bootstrap uses 2,000 rounds over out-of-fold scores.
