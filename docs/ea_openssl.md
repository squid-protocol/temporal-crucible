# EA-H1..EA-H5 — openssl (SCORED)

- engine `da852aa54cbde7359b7e117f6b32605cc8ea6987` · args `--spec-alignment` · history `asof`
- snapshots: 110 quarterly; excluded (unusable history / empty): none; scored (≥ 1 positive): **75**
- events: 252 on-master `security-fix` fixes; outcome window (t, t+180 d]
- gates: churn reconstruction **PASS** (110/110), HCM parity **PASS** (110/110)

## Mean recall at a share of lines reviewed

| ranking | @10% | @20% (primary) | @30% |
|---|---:|---:|---:|
| LOC-desc | 0.130 | **0.271** | 0.383 |
| LOC-asc | 0.052 | **0.128** | 0.214 |
| change_entropy | 0.176 | **0.343** | 0.462 |
| raw_churn_freq | 0.144 | **0.321** | 0.396 |
| recency | 0.157 | **0.304** | 0.432 |
| prior_fixes | 0.288 | **0.451** | 0.508 |
| prior_fix_density | 0.311 | **0.451** | 0.508 |

## Verdicts (recall@20 lift; must beat both baselines; α = 0.002 one-sided)

| claim | feature | vs LOC-desc: mean [lo] | vs LOC-asc: mean [lo], 90% CI | verdict |
|---|---|---|---|---|
| **EA-H1** | change_entropy | +0.072 [+0.013] | +0.215 [+0.096], [+0.140, +0.290] | **SUPPORTED** |
| **EA-H2** | raw_churn_freq | +0.050 [-0.053] | +0.193 [+0.078], [+0.122, +0.265] | **not supported (inconclusive)** |
| **EA-H3** | recency | +0.032 [-0.103] | +0.176 [+0.062], [+0.112, +0.239] | **not supported (inconclusive)** |
| **EA-H4** | prior_fixes | +0.180 [+0.047] | +0.323 [+0.202], [+0.252, +0.393] | **SUPPORTED** |
| **EA-H5** | prior_fix_density | +0.180 [+0.054] | +0.323 [+0.204], [+0.252, +0.392] | **SUPPORTED** |

## Secondary (descriptive): pooled AUC and size bands

| ranking | pooled AUC | <=22 | 23-48 | 49-108 | >108 |
|---|---:|---:|---:|---:|---:|
| LOC-desc | 0.816 | — | — | 0.685 (19) | 0.756 (644) |
| change_entropy | 0.751 | — | — | 0.567 (19) | 0.716 (644) |
| raw_churn_freq | 0.734 | — | — | 0.516 (19) | 0.702 (644) |
| recency | 0.696 | — | — | 0.589 (19) | 0.667 (644) |
| prior_fixes | 0.639 | — | — | 0.496 (19) | 0.634 (644) |
| prior_fix_density | 0.634 | — | — | 0.496 (19) | 0.628 (644) |

Runtime 82s · bootstrap 5000 rounds over snapshots, seed 2982.
