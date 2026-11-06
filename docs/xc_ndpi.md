# XC-H1..H6 — fix classes vs predictors: ndpi (SCORED)

- labels `events/ndpi_xc.json` (rules v2): extrinsic 50, latent 105, regression 63, other-fix 1301; excluded sweeps 27
- 43 quarterly snapshots; scored per class: extrinsic 29, latent 26, regression 36, other-fix 43; window (t, t+180 d]

## Verdicts (α = 0.01/6 = 0.00167 one-sided; lift over the snapshot's stronger LOC baseline)

| claim | what | n | mean | lo | 90% CI | verdict |
|---|---|---:|---:|---:|---|---|
| **XC-H1** | change entropy beats size on regressions | 36 | -0.024 | -0.181 | [-0.102, +0.045] | **not supported (inconclusive)** |
| **XC-H2** | …more than on latent (CVE) fixes | 25 | -0.016 | -0.129 | [-0.081, +0.050] | **not supported (inconclusive)** |
| **XC-H3** | external includes beat size on extrinsic fixes | 29 | +0.034 | -0.084 | [-0.037, +0.113] | **not supported (inconclusive)** |
| **XC-H4** | …more than on regressions | 25 | +0.119 | -0.052 | [+0.016, +0.234] | **not supported (inconclusive)** |
| **XC-H5** | prior regressions beat prior other fixes on regressions | 36 | -0.088 | -0.215 | [-0.160, -0.027] | **not supported (inconclusive)** |
| **XC-H6** | prior extrinsic beat prior other fixes on extrinsic | 29 | -0.068 | -0.293 | [-0.181, +0.032] | **not supported (inconclusive)** |

## Descriptive: mean recall@20 by predictor × class

| predictor | extrinsic | latent | regression | other-fix |
|---|---:|---:|---:|---:|
| LOC-desc | 0.259 | 0.204 | 0.261 | 0.057 |
| LOC-asc | 0.107 | 0.091 | 0.056 | 0.251 |
| change_entropy | 0.194 | 0.258 | 0.252 | 0.083 |
| raw_churn_freq | 0.232 | 0.225 | 0.312 | 0.078 |
| prior same-class | 0.198 | 0.284 | 0.218 | 0.067 |
| prior other-class | 0.266 | 0.204 | 0.306 | 0.081 |
| external includes | 0.349 | 0.129 | 0.181 | 0.059 |
| flux density | 0.387 | 0.273 | 0.200 | 0.183 |

Lift over the stronger LOC baseline (same table minus max(LOC-desc, LOC-asc) per snapshot):

| predictor | extrinsic | latent | regression | other-fix |
|---|---:|---:|---:|---:|
| change_entropy | -0.121 | +0.016 | -0.024 | -0.171 |
| raw_churn_freq | -0.084 | -0.017 | +0.036 | -0.177 |
| prior same-class | -0.117 | +0.042 | -0.058 | -0.187 |
| prior other-class | -0.049 | -0.038 | +0.030 | -0.174 |
| external includes | +0.034 | -0.113 | -0.095 | -0.195 |
| flux density | +0.072 | +0.031 | -0.076 | -0.071 |

Regression lag (SHA-referenced regressions, n=48): median 4 d, p75 8 d, share same-day 27%.

Runtime 1s · bootstrap 5000 rounds over snapshots, seed 2982.
