# CEN-H1 / CEN-H2 — mid-band centrality: openssl (SCORED)

- 110 quarterly snapshots; files `language IN ('c',)`; outcome = latent/regression/other-fix touch in (t, t+180 d]

| claim | band | n | positives | AUC score | AUC LOC | lift | lo (α=0.005) | 90% CI | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| (descriptive) `pagerank_score` | <=22 | 3,295 | 80 | 0.553 | 0.478 | +0.075 | -0.075 | [-0.012, +0.139] | — |
| (descriptive) `pagerank_score` | 23-48 | 8,514 | 345 | 0.589 | 0.565 | +0.024 | -0.040 | [-0.019, +0.072] | — |
| **CEN-H1** `pagerank_score` | 49-108 | 26,317 | 1258 | 0.473 | 0.517 | -0.044 | -0.088 | [-0.072, -0.014] | **not supported (inconclusive)** |
| (descriptive) `pagerank_score` | >108 | 91,074 | 16809 | 0.478 | 0.709 | -0.231 | -0.265 | [-0.253, -0.208] | — |
| (descriptive) `popularity` | <=22 | 3,295 | 80 | 0.628 | 0.478 | +0.150 | +0.008 | [+0.067, +0.207] | — |
| (descriptive) `popularity` | 23-48 | 8,514 | 345 | 0.578 | 0.565 | +0.014 | -0.055 | [-0.031, +0.066] | — |
| **CEN-H2** `popularity` | 49-108 | 26,317 | 1258 | 0.578 | 0.517 | +0.061 | +0.008 | [+0.028, +0.090] | **SUPPORTED** |
| (descriptive) `popularity` | >108 | 91,074 | 16809 | 0.558 | 0.709 | -0.150 | -0.167 | [-0.161, -0.141] | — |

Runtime 202s · snapshot-cluster bootstrap 5000 rounds, seed 2982.
