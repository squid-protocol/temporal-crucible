# SC stage 2 — confirmation on the unseen holdout (SCORED)

- frozen pairs 4 → α = 0.01/4 = 0.0025 one-sided; holdout harfbuzz (c+cpp) and libarchive (c)
- label counts: harfbuzz latent 90, extrinsic 155, regression 478, other-fix 3597; libarchive latent 18, extrinsic 468, other-fix 1499

| class | candidate | repo | scored snapshots | mean R | lo | 90% CI | verdict |
|---|---|---|---:|---:|---:|---|---|
| extrinsic | `platform_cond /line` | harfbuzz | 57 | +0.154 | +0.005 | [+0.070, +0.239] | **SUPPORTED** |
| extrinsic | `platform_cond /line` | libarchive | 65 | +0.102 | +0.016 | [+0.051, +0.157] | **SUPPORTED** |
| regression | `raw_churn_freq /line` | harfbuzz | 61 | +0.000 | -0.107 | [-0.062, +0.063] | **not supported (inconclusive)** |
| regression | `raw_churn_freq /line` | libarchive | — | — | — | — | not evaluable (class withheld) |
| other-fix | `risk_churn /line` | harfbuzz | 62 | +0.038 | +0.008 | [+0.021, +0.056] | **SUPPORTED** |
| other-fix | `risk_churn /line` | libarchive | 69 | +0.038 | -0.012 | [+0.008, +0.069] | **not supported (inconclusive)** |
| other-fix | `pct_vec_churn /line` | harfbuzz | 62 | +0.031 | +0.013 | [+0.021, +0.042] | **SUPPORTED** |
| other-fix | `pct_vec_churn /line` | libarchive | 69 | -0.005 | -0.044 | [-0.027, +0.016] | **not supported (inconclusive)** |

| class | candidate | stage-2 verdict |
|---|---|---|
| extrinsic | `platform_cond /line` | **CONFIRMED** |
| regression | `raw_churn_freq /line` | **not confirmed** |
| other-fix | `risk_churn /line` | **not confirmed** |
| other-fix | `pct_vec_churn /line` | **not confirmed** |

Runtime 11s · bootstrap 5000 rounds over snapshots, seed 2982.
