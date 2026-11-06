# CEN-H1 / CEN-H2 — mid-band centrality: harfbuzz (SCORED)

- 62 quarterly snapshots; files `language IN ('c', 'cpp')`; outcome = latent/regression/other-fix touch in (t, t+180 d]

| claim | band | n | positives | AUC score | AUC LOC | lift | lo (α=0.005) | 90% CI | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| (descriptive) `pagerank_score` | <=22 | 183 | 4 | 0.668 | 0.937 | -0.269 | -0.412 | [-0.351, -0.205] | — |
| (descriptive) `pagerank_score` | 23-48 | 1,253 | 48 | 0.559 | 0.565 | -0.006 | -0.179 | [-0.122, +0.125] | — |
| **CEN-H1** `pagerank_score` | 49-108 | 3,783 | 381 | 0.530 | 0.581 | -0.051 | -0.121 | [-0.095, -0.006] | **not supported (inconclusive)** |
| (descriptive) `pagerank_score` | >108 | 10,969 | 3851 | 0.592 | 0.681 | -0.089 | -0.130 | [-0.115, -0.063] | — |
| (descriptive) `popularity` | <=22 | 183 | 4 | 0.148 | 0.937 | -0.789 | -0.845 | [-0.828, -0.740] | — |
| (descriptive) `popularity` | 23-48 | 1,253 | 48 | 0.453 | 0.565 | -0.112 | -0.275 | [-0.211, -0.021] | — |
| **CEN-H2** `popularity` | 49-108 | 3,783 | 381 | 0.509 | 0.581 | -0.072 | -0.127 | [-0.109, -0.034] | **not supported (inconclusive)** |
| (descriptive) `popularity` | >108 | 10,969 | 3851 | 0.593 | 0.681 | -0.089 | -0.116 | [-0.105, -0.072] | — |

Runtime 26s · snapshot-cluster bootstrap 5000 rounds, seed 2982.
