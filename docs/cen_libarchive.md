# CEN-H1 / CEN-H2 — mid-band centrality: libarchive (SCORED)

- 72 quarterly snapshots; files `language IN ('c',)`; outcome = latent/regression/other-fix touch in (t, t+180 d]

| claim | band | n | positives | AUC score | AUC LOC | lift | lo (α=0.005) | 90% CI | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| (descriptive) `pagerank_score` | <=22 | 208 | 2 | 0.607 | 0.447 | +0.160 | -0.306 | [-0.120, +0.330] | — |
| (descriptive) `pagerank_score` | 23-48 | 3,050 | 28 | 0.594 | 0.605 | -0.011 | -0.445 | [-0.280, +0.184] | — |
| **CEN-H1** `pagerank_score` | 49-108 | 12,692 | 281 | 0.563 | 0.527 | +0.035 | -0.147 | [-0.077, +0.151] | **not supported (inconclusive)** |
| (descriptive) `pagerank_score` | >108 | 21,543 | 2408 | 0.624 | 0.739 | -0.115 | -0.161 | [-0.145, -0.082] | — |
| (descriptive) `popularity` | <=22 | 208 | 2 | 0.400 | 0.447 | -0.046 | -0.326 | [-0.206, +0.053] | — |
| (descriptive) `popularity` | 23-48 | 3,050 | 28 | 0.606 | 0.605 | +0.001 | -0.320 | [-0.192, +0.135] | — |
| **CEN-H2** `popularity` | 49-108 | 12,692 | 281 | 0.527 | 0.527 | +0.000 | -0.077 | [-0.050, +0.054] | **not supported (inconclusive)** |
| (descriptive) `popularity` | >108 | 21,543 | 2408 | 0.636 | 0.739 | -0.103 | -0.124 | [-0.117, -0.089] | — |

Runtime 75s · snapshot-cluster bootstrap 5000 rounds, seed 2982.
