# NM exploratory size checks (NOT registered; labelled context for the NM-F/NM-G results)

## File metrics: head-to-head with total_loc in the same strata (security-fix, quarterly snapshots)

| metric | repo | strat AUC metric − strat AUC total_loc (10 bins) | metric, 50 bins | density metric/LOC, 10 bins | total_loc, 50 bins |
|---|---|---:|---:|---:|---:|
| `fam_mutation` | curl | -0.059 | +0.015 | -0.023 | +0.061 |
| `fam_dead_code` | curl | -0.070 | +0.031 | +0.005 | +0.061 |
| `fam_connectivity` | curl | -0.061 | +0.037 | -0.026 | +0.061 |
| `fam_memory` | curl | -0.053 | +0.051 | +0.011 | +0.061 |
| `fam_guards` | curl | -0.053 | +0.052 | -0.016 | +0.061 |
| `amplified_cascading_flux` | curl | -0.068 | -0.008 | -0.029 | +0.061 |
| `fam_mutation` | ndpi | -0.011 | +0.048 | +0.070 | +0.089 |
| `fam_dead_code` | ndpi | -0.075 | +0.015 | +0.053 | +0.089 |
| `fam_connectivity` | ndpi | -0.028 | +0.078 | +0.093 | +0.089 |
| `fam_memory` | ndpi | -0.063 | +0.045 | +0.066 | +0.089 |
| `fam_guards` | ndpi | -0.022 | +0.062 | +0.071 | +0.089 |
| `amplified_cascading_flux` | ndpi | +0.007 | +0.105 | +0.102 | +0.089 |
| `fam_mutation` | openssl | -0.013 | +0.058 | +0.058 | +0.032 |
| `fam_dead_code` | openssl | -0.048 | +0.066 | +0.053 | +0.032 |
| `fam_connectivity` | openssl | -0.078 | +0.038 | +0.009 | +0.032 |
| `fam_memory` | openssl | -0.072 | +0.018 | +0.019 | +0.032 |
| `fam_guards` | openssl | -0.164 | -0.065 | -0.090 | +0.032 |
| `amplified_cascading_flux` | openssl | +0.020 | +0.113 | +0.109 | +0.032 |

## Function fan-out vs leftover function size (FREC events, later half)

| check | curl (408 events) | nDPI (47) |
|---|---:|---:|
| fan_out, loc-tertile strata (= NM-G statistic) | +0.132 | +0.143 |
| **loc itself, same strata** | **+0.178** | **+0.147** |
| fan_out − loc, same strata | −0.046 | −0.004 |
| fan_out per line, loc tertiles | −0.015 | +0.023 |
| complexity itself, loc tertiles | +0.156 | +0.074 |
| fan_out, exact-equal-loc pairs only | +0.062 (139 events) | −0.067 (12) |
