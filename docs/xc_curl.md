# XC-H1..H6 — fix classes vs predictors: curl (SCORED)

- labels `events/curl_xc.json` (rules v2): extrinsic 681, latent 185, regression 1069, other-fix 6417; excluded sweeps 124
- 105 quarterly snapshots; scored per class: extrinsic 105, latent 63, regression 73, other-fix 105; window (t, t+180 d]

## Verdicts (α = 0.01/6 = 0.00167 one-sided; lift over the snapshot's stronger LOC baseline)

| claim | what | n | mean | lo | 90% CI | verdict |
|---|---|---:|---:|---:|---|---|
| **XC-H1** | change entropy beats size on regressions | 73 | -0.032 | -0.108 | [-0.071, +0.002] | **not supported (inconclusive)** |
| **XC-H2** | …more than on latent (CVE) fixes | 56 | -0.054 | -0.167 | [-0.112, -0.002] | **not supported (inconclusive)** |
| **XC-H3** | external includes beat size on extrinsic fixes | 105 | -0.104 | -0.168 | [-0.140, -0.069] | **not supported (inconclusive)** |
| **XC-H4** | …more than on regressions | 73 | +0.015 | -0.068 | [-0.034, +0.063] | **not supported (inconclusive)** |
| **XC-H5** | prior regressions beat prior other fixes on regressions | 73 | -0.021 | -0.119 | [-0.073, +0.023] | **not supported (inconclusive)** |
| **XC-H6** | prior extrinsic beat prior other fixes on extrinsic | 105 | +0.094 | +0.057 | [+0.074, +0.112] | **SUPPORTED** |

## Descriptive: mean recall@20 by predictor × class

| predictor | extrinsic | latent | regression | other-fix |
|---|---:|---:|---:|---:|
| LOC-desc | 0.098 | 0.215 | 0.232 | 0.078 |
| LOC-asc | 0.279 | 0.136 | 0.193 | 0.319 |
| change_entropy | 0.137 | 0.306 | 0.264 | 0.109 |
| raw_churn_freq | 0.129 | 0.299 | 0.270 | 0.109 |
| prior same-class | 0.199 | 0.334 | 0.237 | 0.101 |
| prior other-class | 0.105 | 0.275 | 0.258 | 0.118 |
| external includes | 0.189 | 0.273 | 0.224 | 0.132 |
| flux density | 0.167 | 0.207 | 0.136 | 0.180 |

Lift over the stronger LOC baseline (same table minus max(LOC-desc, LOC-asc) per snapshot):

| predictor | extrinsic | latent | regression | other-fix |
|---|---:|---:|---:|---:|
| change_entropy | -0.156 | +0.013 | -0.032 | -0.209 |
| raw_churn_freq | -0.164 | +0.007 | -0.026 | -0.210 |
| prior same-class | -0.094 | +0.041 | -0.060 | -0.218 |
| prior other-class | -0.188 | -0.018 | -0.038 | -0.201 |
| external includes | -0.104 | -0.019 | -0.073 | -0.186 |
| flux density | -0.126 | -0.085 | -0.160 | -0.139 |

Regression lag (SHA-referenced regressions, n=755): median 2 d, p75 12 d, share same-day 35%.

Runtime 22s · bootstrap 5000 rounds over snapshots, seed 2982.
