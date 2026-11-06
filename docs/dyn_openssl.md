# DYN-H1 / DYN-H2 — per-file dynamism (`state_heat_triggers`): openssl (SCORED)

- DB `openssl_galaxy_master.db`; 251 security-fix events scored; skipped {'no touched file in parent snapshot': 1}; 544 positives over 792,182 T0 file rows
- files with any dynamism: 28.5%

## DYN-H1 (bands; powered: >108; α = 0.01/1)

| band | n | positives | AUC dynamism | AUC LOC | lift | lo | 90% CI | cell |
|---|---:|---:|---:|---:|---:|---:|---|---|
| <=22 | 119,440 | 0 | nan | nan | +nan | +nan | [+nan, +nan] | not evaluable (< 20 positives) |
| 23-48 | 82,401 | 1 | 0.462 | 0.038 | +0.424 | +0.421 | [+0.421, +0.426] | not evaluable (< 20 positives) |
| 49-108 | 174,727 | 16 | 0.607 | 0.644 | -0.037 | -0.221 | [-0.166, +0.085] | not evaluable (< 20 positives) |
| >108 | 415,614 | 527 | 0.702 | 0.790 | -0.088 | -0.123 | [-0.113, -0.062] | not supported (inconclusive) |

**DYN-H1: not supported (inconclusive)**

## DYN-H2 (Mantel-Haenszel, exposed = any dynamism; strata event × LOC decile × evidence quartile)

- rate ratio **2.329**, one-sided lo (α = 0.01) 1.741, 90% CI [1.895, 2.920] → **SUPPORTED**

Runtime 689s · event bootstrap 5000 rounds, seed 2982.
