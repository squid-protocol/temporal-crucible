# ARCH-U1..U3 — ndpi (SCORED)

- DB `.claude/worktrees/forward-asof/dbs/ndpi_out/ndpi_galaxy_master.db`; 43 quarterly snapshots; empty: none; scored: **23**
- events: 121 on-master `security-fix`; outcome window (t, t+180 d]; d(a) shrinkage pseudo-LOC 50,000

## Mean recall at a share of lines reviewed

| ranking | @10% | @20% (primary) | @30% |
|---|---:|---:|---:|
| LOC-desc | 0.000 | **0.200** | 0.329 |
| LOC-asc | 0.046 | **0.148** | 0.206 |
| U1 d(file cluster) | 0.048 | **0.140** | 0.273 |
| U2 d(composition) | 0.093 | **0.192** | 0.251 |

## Verdicts (α = 0.0025 one-sided)

| claim | vs LOC-desc: mean [lo] | vs LOC-asc: mean [lo], 90% CI | verdict |
|---|---|---|---|
| **ARCH-U1** | -0.060 [-0.259] | -0.009 [-0.088], [-0.055, +0.043] | **not supported (inconclusive)** |
| **ARCH-U2** | -0.008 [-0.230] | +0.044 [-0.082], [-0.040, +0.140] | **not supported (inconclusive)** |

| claim | mean AUC lift over total_loc | lo | 90% CI | verdict |
|---|---:|---:|---|---|
| **ARCH-U3** | -0.0138 | -0.0343 | [-0.0250, -0.0040] | **not supported (inconclusive)** |

Mean per-snapshot AUC: total_loc 0.8909 · total_loc × d(file cluster) 0.8771

## Secondary (descriptive)

Learned per-line fix density by file cluster at the last scored snapshot (pre-2026-01-01); global 0.188 positives/kLOC:

| label | training rows' kLOC | positives | d(a) per kLOC | ratio to global |
|---|---:|---:|---:|---:|
| file_cluster_15 | 231 | 96 | 0.375 | 1.99 |
| file_cluster_8 | 601 | 168 | 0.273 | 1.45 |
| file_cluster_9 | 24 | 7 | 0.221 | 1.17 |
| file_cluster_16 | 68 | 16 | 0.216 | 1.15 |
| file_cluster_3 | 131 | 29 | 0.212 | 1.12 |
| file_cluster_1 | 0 | 0 | 0.187 | 1.00 |
| file_cluster_11 | 1 | 0 | 0.186 | 0.99 |
| file_cluster_14 | 3 | 0 | 0.176 | 0.94 |
| file_cluster_7 | 5 | 0 | 0.172 | 0.91 |
| file_cluster_6 | 417 | 64 | 0.157 | 0.83 |
| file_cluster_17 | 220 | 31 | 0.150 | 0.80 |
| file_cluster_12 | 33 | 2 | 0.138 | 0.73 |
| file_cluster_2 | 90 | 2 | 0.082 | 0.43 |
| file_cluster_4 | 567 | 35 | 0.072 | 0.38 |

Label flip over the prior year vs future fix (files present a year earlier):

| group | files | positive rate | mean total_loc |
|---|---:|---:|---:|
| unchanged LOC (no edit) | 1,923 | 0.0926 | 140 |
| edited, label kept | 2,745 | 0.0554 | 381 |
| edited, label flipped | 525 | 0.0990 | 435 |

Runtime 14s · bootstrap 5000 rounds over snapshots, seed 2982.
