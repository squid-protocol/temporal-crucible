# EXPLORATORY — history dynamics by fix class: ndpi

Not registered; labels are seen. Lift = recall@20 − the snapshot's stronger size order; quarterly snapshots, window 180 d.

## (1) Which history predicts which class?

| history ↓ / outcome → | latent (n) | extrinsic (n) | regression (n) | other-fix (n) |
|---|---:|---:|---:|---:|
| prior latent | +0.294 (26) | -0.064 (31) | -0.004 (36) | -0.144 (43) |
| prior extrinsic | +0.211 (26) | +0.097 (31) | +0.008 (36) | -0.184 (43) |
| prior regression | +0.292 (26) | +0.063 (31) | +0.144 (36) | -0.152 (43) |
| prior other-fix | +0.265 (26) | +0.045 (31) | +0.159 (36) | -0.205 (43) |
| prior pooled | +0.251 (26) | +0.041 (31) | +0.138 (36) | -0.207 (43) |
| recent same (365 d) | +0.362 (26) | -0.053 (31) | +0.055 (36) | -0.196 (43) |
| all-time same | +0.294 (26) | +0.097 (31) | +0.144 (36) | -0.205 (43) |

## (2) The extrinsic change rate

- extrinsic commits 50 of 1519 fix commits (3.3%) over 136 months
- **dispersion of the monthly extrinsic share vs binomial: 1.39** (1 = steady background; > 1 = bursty)

| year | fix commits | extrinsic | share | extrinsic files touched | of which already membrane (extrinsic before) |
|---|---:|---:|---:|---:|---:|
| 2015 | 59 | 4 | 6.8% | 10 | 0 (0%) |
| 2016 | 130 | 5 | 3.8% | 6 | 2 (33%) |
| 2017 | 86 | 5 | 5.8% | 4 | 2 (50%) |
| 2018 | 43 | 0 | 0.0% | 0 | 0 (0%) |
| 2019 | 166 | 1 | 0.6% | 1 | 0 (0%) |
| 2020 | 220 | 2 | 0.9% | 7 | 3 (43%) |
| 2021 | 146 | 4 | 2.7% | 23 | 4 (17%) |
| 2022 | 186 | 11 | 5.9% | 31 | 13 (42%) |
| 2023 | 145 | 9 | 6.2% | 15 | 4 (27%) |
| 2024 | 141 | 3 | 2.1% | 3 | 2 (67%) |
| 2025 | 133 | 2 | 1.5% | 1 | 0 (0%) |
| 2026 | 64 | 4 | 6.2% | 4 | 3 (75%) |

Burstiest months (extrinsic above expectation from overall fix activity), with sample subjects:

- **2023-10**: 5 extrinsic vs 0.5 expected: Windows compilation fixes · Fixed two OpenWRT arm related build issues. (#2103) · Fixed OpenWRT arm related build issues. (#2104) · FreeBSD compilation fix (missingcvg #include <netdb.h>)
- **2022-07**: 3 extrinsic vs 0.9 expected: bins: add support for 64bit bins (#1626) · Windows compilation fix. · Windows error C2466 fix (array size init with 0).
- **2015-05**: 2 extrinsic vs 0.3 expected: Win32 fixes · Win32 fix
- **2017-07**: 2 extrinsic vs 0.4 expected: fix for OpenBSD compile error https://github.com/ntop/nDPI/issues/417 · changed name from _bpf_filter to bpfFilter to avoid compilation error 
- **2015-11**: 2 extrinsic vs 0.4 expected: fixed missed library netinet/in.h under FreeBSD · Win32 compilation fixes
