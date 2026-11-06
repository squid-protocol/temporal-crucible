# XC-H1..H6 — fix classes vs predictors: openssl (SCORED)

- labels `events/openssl_xc.json` (rules v2): extrinsic 592, latent 235, regression 465, other-fix 7704; excluded sweeps 164
- 110 quarterly snapshots; scored per class: extrinsic 109, latent 75, regression 50, other-fix 110; window (t, t+180 d]

## Verdicts (α = 0.01/6 = 0.00167 one-sided; lift over the snapshot's stronger LOC baseline)

| claim | what | n | mean | lo | 90% CI | verdict |
|---|---|---:|---:|---:|---|---|
| **XC-H1** | change entropy beats size on regressions | 50 | +0.090 | +0.009 | [+0.044, +0.137] | **SUPPORTED** |
| **XC-H2** | …more than on latent (CVE) fixes | 47 | +0.115 | +0.008 | [+0.054, +0.177] | **SUPPORTED** |
| **XC-H3** | external includes beat size on extrinsic fixes | 109 | -0.064 | -0.127 | [-0.099, -0.028] | **not supported (inconclusive)** |
| **XC-H4** | …more than on regressions | 50 | -0.036 | -0.160 | [-0.102, +0.032] | **not supported (inconclusive)** |
| **XC-H5** | prior regressions beat prior other fixes on regressions | 50 | -0.113 | -0.215 | [-0.170, -0.062] | **not supported (inconclusive)** |
| **XC-H6** | prior extrinsic beat prior other fixes on extrinsic | 109 | +0.194 | +0.131 | [+0.159, +0.230] | **SUPPORTED** |

## Descriptive: mean recall@20 by predictor × class

| predictor | extrinsic | latent | regression | other-fix |
|---|---:|---:|---:|---:|
| LOC-desc | 0.144 | 0.271 | 0.193 | 0.145 |
| LOC-asc | 0.251 | 0.128 | 0.168 | 0.231 |
| change_entropy | 0.260 | 0.343 | 0.354 | 0.256 |
| raw_churn_freq | 0.265 | 0.321 | 0.367 | 0.256 |
| prior same-class | 0.359 | 0.451 | 0.211 | 0.217 |
| prior other-class | 0.165 | 0.425 | 0.324 | 0.204 |
| external includes | 0.239 | 0.163 | 0.246 | 0.184 |
| flux density | 0.129 | 0.408 | 0.195 | 0.212 |

Lift over the stronger LOC baseline (same table minus max(LOC-desc, LOC-asc) per snapshot):

| predictor | extrinsic | latent | regression | other-fix |
|---|---:|---:|---:|---:|
| change_entropy | -0.043 | -0.009 | +0.090 | -0.012 |
| raw_churn_freq | -0.038 | -0.031 | +0.103 | -0.011 |
| prior same-class | +0.056 | +0.099 | -0.054 | -0.050 |
| prior other-class | -0.139 | +0.073 | +0.059 | -0.063 |
| external includes | -0.064 | -0.189 | -0.019 | -0.083 |
| flux density | -0.175 | +0.056 | -0.069 | -0.055 |

Regression lag (SHA-referenced regressions, n=217): median 6 d, p75 25 d, share same-day 12%.

Runtime 3s · bootstrap 5000 rounds over snapshots, seed 2982.
