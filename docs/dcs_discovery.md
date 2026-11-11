# DCS Stage 1 — discovery (EXPLORATORY; no verdicts)

Registration `docs/dcs_hypotheses.md`. This report and `docs/dcs_models.json` (sha256 `f4b2642d0c37`) are committed before Stage 2 reads any confirmation function. Nothing here is a verdict.

## Cohort and split

| repo | commented births | danger-commented | eligible (5-y horizon) | split date (median birth) | discovery: cases / controls / early deaths (excl.) | confirmation functions (not read) |
|---|---:|---:|---:|---|---|---:|
| curl | 5,126 | 675 | 395 | 2013-06-30 | 3 / 133 / 59 | 200 |
| openssl | 10,344 | 1,287 | 824 | 2017-06-30 | 6 / 343 / 51 | 424 |
| ndpi | 1,444 | 65 | 34 | 2019-11-09 | 5 / 11 / 1 | 17 |
| harfbuzz | 1,902 | 155 | 104 | 2017-03-27 | 1 / 32 / 18 | 53 |

- discovery: **534** functions, **15** cases (2.8%); birth rows missing from the scan DB: none
- outcome: case = first CVE (`latent`) fix ≤ birth + 5 y; control = alive at birth + 5 y without one; functions that died earlier without one are excluded (Stage 2 sensitivity counts them as controls).
- engine `14e70005484d`; lattice `a27d2c93f817`; seed 2982.

## Features

- T (telemetry ÷ loc): 32 kept; F (lattice family, rung, archetype): 12 kept; C (call graph): 5 kept; B: B:log_loc, B:prior_cve_file, B:repo=curl, B:repo=openssl, B:repo=ndpi, B:repo=harfbuzz
- dropped by the outcome-blind < 0.5% non-zero rule (64): `F:archetype=Interface Declarations`, `F:lat_family=F1`, `F:lat_family=F10`, `F:lat_family=F11`, `F:lat_family=F12`, `F:lat_family=F13`, `F:lat_family=F14`, `F:lat_family=F2`, `F:lat_family=F3`, `F:lat_family=F4`, `F:lat_family=F5`, `F:lat_family=F6`, `F:lat_family=F9`, `F:lat_family=unassigned`, `T:arch_concurrency/loc`, `T:arch_crypto/loc`, `T:arch_dependency_injection/loc`, `T:arch_hardware/loc`, `T:arch_import/loc`, `T:arch_inline_asm/loc`, `T:arch_regex/loc`, `T:arch_serialization/loc`, `T:arch_ssr_boundaries/loc`, `T:arch_sys_config/loc`, `T:arch_ui_framework/loc`, `T:def_auth/loc`, `T:def_spec_exposure/loc`, `T:def_sync_locks/loc`, `T:def_telemetry/loc`, `T:def_test/loc`, `T:def_test_skip/loc`, `T:sec_self_propagation/loc`, `T:sec_unicode_steganography/loc`, `T:state_halt_hits/loc`, `T:state_slop_duplicates/loc`, `T:state_unreferenced/loc`, `T:struct_camel_case/loc`, `T:struct_closures/loc`, `T:struct_comprehensions/loc`, `T:struct_decorators/loc`, `T:struct_generics/loc`, `T:struct_long_vars/loc`, `T:struct_pascal_case/loc`, `T:struct_short_vars/loc`, `T:struct_snake_case/loc`, `T:struct_spaces/loc`, `T:struct_tabs/loc`, `T:struct_upper_case/loc`, `T:struct_var_decl/loc`, `T:threat_api_near_db_sink/loc`, `T:threat_bypasses/loc`, `T:threat_crypto_math/loc`, `T:threat_db_sinks/loc`, `T:threat_entropy/loc`, `T:threat_env_mutation/loc`, `T:threat_eval_exec/loc`, `T:threat_extension_mismatch/loc`, `T:threat_homoglyphs/loc`, `T:threat_network_hooks/loc`, `T:threat_obfuscated/loc`, `T:threat_private_info/loc`, `T:threat_stego_imports/loc`, `T:threat_tainted_injection/loc`, `T:token_mass/loc`

## Models (frozen for Stage 2)

| model | features | C (5-fold file-grouped CV) | CV AUC | CV lift over B | in-sample AUC |
|---|---:|---:|---:|---:|---:|
| B | 6 | 0.1 | 0.859 | +0.000 | 0.902 |
| B + T | 38 | 0.1 | 0.841 | -0.018 | 0.934 |
| B + F | 18 | 0.1 | 0.804 | -0.055 | 0.916 |
| B + C | 11 | 0.001 | 0.891 | +0.032 | 0.896 |
| B + ALL | 55 | 0.0316228 | 0.816 | -0.043 | 0.932 |

Descriptive controls (frozen too, never a claim): B alone refitted at each family model's C, in-sample AUC B@T (C 0.1) 0.902, B@F (C 0.1) 0.902, B@C (C 0.001) 0.898, B@ALL (C 0.0316228) 0.903

Largest standardized coefficients (excluding B):

- **T**: `T:struct_args/loc` -0.33, `T:state_safety_neg/loc` +0.24, `T:struct_func_start/loc` -0.22, `T:def_freeze_hits/loc` +0.21, `T:struct_macros/loc` +0.18, `T:arch_io/loc` -0.18, `T:args/loc` -0.18, `T:state_print_hits/loc` +0.17
- **F**: `F:archetype=I/O & Config Routines` +0.27, `F:lat_rung` +0.26, `F:archetype=Many-Argument Workhorses` +0.24, `F:archetype=Stateful Encapsulated Methods` -0.21, `F:lat_family=F8` +0.20, `F:lat_family=F7` -0.20, `F:archetype=Compute Cores` -0.12, `F:archetype=C Struct Operations` -0.07
- **C**: `C:log1p_distinct_callees` +0.01, `C:log1p_fan_out` +0.01, `C:log1p_fan_in` +0.00, `C:is_public` -0.00, `C:log1p_pagerank` -0.00
- **ALL**: `F:archetype=I/O & Config Routines` +0.14, `T:struct_args/loc` -0.14, `F:lat_rung` +0.13, `T:state_print_hits/loc` +0.13, `C:log1p_distinct_callees` +0.12, `F:archetype=Many-Argument Workhorses` +0.11, `T:struct_macros/loc` +0.10, `T:state_safety_neg/loc` +0.10

## Univariate screen (MH OR, strata repo × 0.1-decade loc; exposure = above the discovery median, or > 0 when the median is 0; 95% RGB CI; uncorrected, many tests)

| feature | exposed (cases / n) | OR [95% CI] | z |
|---|---|---|---:|
| `F:lat_family=F7` | 4 / 218 | 0.16 [0.02, 1.30] | -1.7 |
| `T:state_safety_neg/loc` | 5 / 81 | 3.66 [0.78, 17.06] | +1.7 |
| `F:archetype=I/O & Config Routines` | 2 / 13 | 6.79 [0.65, 70.43] | +1.6 |
| `T:struct_class_start/loc` | 6 / 121 | 0.06 [0.00, 2.38] | -1.5 |
| `T:arch_api/loc` | 6 / 238 | 0.30 [0.06, 1.46] | -1.5 |
| `C:is_public` | 6 / 240 | 0.30 [0.06, 1.46] | -1.5 |
| `T:complexity/loc` | 8 / 266 | 0.38 [0.09, 1.51] | -1.4 |
| `T:struct_branch/loc` | 8 / 266 | 0.38 [0.09, 1.51] | -1.4 |
| `T:state_memory_alloc/loc` | 4 / 54 | 5.01 [0.37, 68.18] | +1.2 |
| `T:state_pointers/loc` | 8 / 267 | 2.20 [0.57, 8.53] | +1.1 |
| `T:def_freeze_hits/loc` | 7 / 264 | 0.45 [0.11, 1.79] | -1.1 |
| `T:struct_linear/loc` | 8 / 267 | 2.02 [0.59, 6.90] | +1.1 |
| `T:struct_args/loc` | 2 / 266 | 0.41 [0.08, 2.13] | -1.1 |
| `T:def_encapsulation/loc` | 7 / 267 | 2.37 [0.48, 11.71] | +1.1 |
| `T:args/loc` | 2 / 264 | 3.46 [0.33, 36.02] | +1.0 |
| `T:def_cleanup/loc` | 3 / 46 | 3.38 [0.30, 38.52] | +1.0 |
| `T:state_heat_triggers/loc` | 8 / 114 | 2.01 [0.49, 8.24] | +1.0 |
| `T:struct_macros/loc` | 8 / 117 | 1.73 [0.57, 5.31] | +1.0 |
| `F:archetype=Compute Cores` | 1 / 98 | 0.41 [0.06, 2.88] | -0.9 |
| `C:log1p_pagerank` | 10 / 264 | 0.36 [0.03, 4.75] | -0.8 |
| `C:log1p_fan_out` | 10 / 256 | 2.35 [0.26, 21.62] | +0.8 |
| `T:bitwise_ops/loc` | 8 / 124 | 1.52 [0.47, 4.89] | +0.7 |
| `T:state_print_hits/loc` | 5 / 45 | 1.71 [0.37, 7.95] | +0.7 |
| `T:func_z_score/loc` | 13 / 267 | 1.75 [0.26, 11.61] | +0.6 |
| `C:log1p_fan_in` | 6 / 162 | 1.44 [0.37, 5.60] | +0.5 |

Features screened: 33; |z| ≥ 1.96: 0 (≈ 2 expected by chance).

## Distributions, cases vs controls

| LAT family | cases | controls |
|---|---:|---:|
| F8 | 73.3% | 58.6% |
| F7 | 26.7% | 41.2% |
| F5 | 0.0% | 0.2% |

| rung band | cases | controls |
|---|---:|---:|
| k ≤ 3 | 0.0% | 0.0% |
| k 4–5 | 0.0% | 2.7% |
| k ≥ 6 | 100.0% | 97.3% |

| archetype | cases | controls |
|---|---:|---:|
| Many-Argument Workhorses | 80.0% | 48.0% |
| Stateful Encapsulated Methods | 0.0% | 19.7% |
| Compute Cores | 6.7% | 18.7% |
| Encapsulated Accessors | 0.0% | 3.5% |
| Parameter Forwarders | 0.0% | 3.5% |
| C Struct Operations | 0.0% | 2.5% |
| I/O & Config Routines | 13.3% | 2.1% |
| Type Conversions | 0.0% | 1.0% |
| Defensive Guards | 0.0% | 0.8% |
| Interface Declarations | 0.0% | 0.4% |

## Shallow tree (depth 3, leaves ≥ 20; Gini; all kept features + log loc + prior CVE file)

- n = 534, cases 15 (2.8%)
    - `T:struct_args/loc` ≤ 0.009629: n = 54, cases 8 (14.8%)
        - `C:log1p_fan_out` ≤ 1.609: n = 26, cases 6 (23.1%)
        - `C:log1p_fan_out` > 1.609: n = 28, cases 2 (7.1%)
    - `T:struct_args/loc` > 0.009629: n = 480, cases 7 (1.5%)
        - `C:log1p_distinct_callees` ≤ 2.565: n = 395, cases 1 (0.3%)
            - `T:struct_linear/loc` ≤ 0.02579: n = 20, cases 1 (5.0%)
            - `T:struct_linear/loc` > 0.02579: n = 375, cases 0 (0.0%)
        - `C:log1p_distinct_callees` > 2.565: n = 85, cases 6 (7.1%)
            - `F:lat_family=F7` ≤ 0: n = 46, cases 6 (13.0%)
            - `F:lat_family=F7` > 0: n = 39, cases 0 (0.0%)

Runtime 39s.
