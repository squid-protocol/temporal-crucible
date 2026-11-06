# DYN-H1 / DYN-H2 — per-file dynamism (`state_heat_triggers`): ndpi (SCORED)

- DB `ndpi_galaxy_master.db`; 114 security-fix events scored; skipped {'no touched file in parent snapshot': 7}; 431 positives over 48,158 T0 file rows
- files with any dynamism: 11.1%

## DYN-H1 (bands; powered: 23-48, 49-108, >108; α = 0.01/3)

| band | n | positives | AUC dynamism | AUC LOC | lift | lo | 90% CI | cell |
|---|---:|---:|---:|---:|---:|---:|---|---|
| <=22 | 9,146 | 2 | 0.500 | 0.649 | -0.149 | -0.496 | [-0.495, +0.221] | not evaluable (< 20 positives) |
| 23-48 | 8,653 | 102 | 0.497 | 0.379 | +0.118 | -0.183 | [-0.013, +0.172] | not supported (inconclusive) |
| 49-108 | 15,195 | 78 | 0.496 | 0.550 | -0.054 | -0.222 | [-0.120, +0.044] | not supported (inconclusive) |
| >108 | 15,164 | 249 | 0.676 | 0.747 | -0.071 | -0.145 | [-0.127, -0.034] | not supported (inconclusive) |

**DYN-H1: not supported (inconclusive)**

## DYN-H2 (Mantel-Haenszel, exposed = any dynamism; strata event × LOC decile × evidence quartile)

- rate ratio **2.025**, one-sided lo (α = 0.01) 1.512, 90% CI [1.611, 3.090] → **SUPPORTED**

Runtime 58s · event bootstrap 5000 rounds, seed 2982.
