# ARCH-U1..U3 — curl (SCORED)

- DB `.claude/worktrees/forward-asof/dbs/curl_out/curl_galaxy_master.db`; 105 quarterly snapshots; empty: none; scored: **61**
- events: 186 on-master `security-fix`; outcome window (t, t+180 d]; d(a) shrinkage pseudo-LOC 50,000

## Mean recall at a share of lines reviewed

| ranking | @10% | @20% (primary) | @30% |
|---|---:|---:|---:|
| LOC-desc | 0.156 | **0.212** | 0.295 |
| LOC-asc | 0.075 | **0.147** | 0.249 |
| U1 d(file cluster) | 0.121 | **0.192** | 0.297 |
| U2 d(composition) | 0.086 | **0.198** | 0.337 |

## Verdicts (α = 0.0025 one-sided)

| claim | vs LOC-desc: mean [lo] | vs LOC-asc: mean [lo], 90% CI | verdict |
|---|---|---|---|
| **ARCH-U1** | -0.020 [-0.130] | +0.045 [-0.028], [+0.002, +0.088] | **not supported (inconclusive)** |
| **ARCH-U2** | -0.013 [-0.143] | +0.051 [-0.048], [-0.006, +0.112] | **not supported (inconclusive)** |

| claim | mean AUC lift over total_loc | lo | 90% CI | verdict |
|---|---:|---:|---|---|
| **ARCH-U3** | -0.0273 | -0.0777 | [-0.0554, -0.0045] | **not supported (inconclusive)** |

Mean per-snapshot AUC: total_loc 0.8583 · total_loc × d(file cluster) 0.8310

## Secondary (descriptive)

Learned per-line fix density by file cluster at the last scored snapshot (pre-2026-01-01); global 0.038 positives/kLOC:

| label | training rows' kLOC | positives | d(a) per kLOC | ratio to global |
|---|---:|---:|---:|---:|
| file_cluster_2 | 207 | 40 | 0.163 | 4.32 |
| file_cluster_4 | 1,983 | 86 | 0.043 | 1.14 |
| file_cluster_6 | 3,543 | 153 | 0.043 | 1.14 |
| file_cluster_7 | 42 | 2 | 0.042 | 1.12 |
| Unclassified | 0 | 0 | 0.038 | 1.00 |
| file_cluster_14 | 0 | 0 | 0.038 | 1.00 |
| file_cluster_17 | 2,030 | 75 | 0.037 | 0.98 |
| file_cluster_8 | 1,928 | 65 | 0.034 | 0.90 |
| file_cluster_13 | 8 | 0 | 0.033 | 0.87 |
| file_cluster_16 | 851 | 26 | 0.031 | 0.82 |
| file_cluster_1 | 282 | 7 | 0.027 | 0.71 |
| file_cluster_15 | 488 | 12 | 0.026 | 0.68 |
| file_cluster_3 | 1,014 | 24 | 0.024 | 0.64 |
| file_cluster_9 | 632 | 13 | 0.022 | 0.58 |
| file_cluster_12 | 392 | 6 | 0.018 | 0.47 |
| file_cluster_11 | 77 | 0 | 0.015 | 0.39 |

Label flip over the prior year vs future fix (files present a year earlier):

| group | files | positive rate | mean total_loc |
|---|---:|---:|---:|
| unchanged LOC (no edit) | 12,575 | 0.0031 | 126 |
| edited, label kept | 15,136 | 0.0297 | 480 |
| edited, label flipped | 1,684 | 0.0338 | 639 |

Runtime 106s · bootstrap 5000 rounds over snapshots, seed 2982.
