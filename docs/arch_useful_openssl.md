# ARCH-U1..U3 — openssl (SCORED)

- DB `.claude/worktrees/frec/dbs/openssl_out/openssl_galaxy_master.db`; 110 quarterly snapshots; empty: none; scored: **73**
- events: 252 on-master `security-fix`; outcome window (t, t+180 d]; d(a) shrinkage pseudo-LOC 50,000

## Mean recall at a share of lines reviewed

| ranking | @10% | @20% (primary) | @30% |
|---|---:|---:|---:|
| LOC-desc | 0.130 | **0.273** | 0.384 |
| LOC-asc | 0.052 | **0.130** | 0.217 |
| U1 d(file cluster) | 0.122 | **0.257** | 0.358 |
| U2 d(composition) | 0.100 | **0.203** | 0.319 |

## Verdicts (α = 0.0025 one-sided)

| claim | vs LOC-desc: mean [lo] | vs LOC-asc: mean [lo], 90% CI | verdict |
|---|---|---|---|
| **ARCH-U1** | -0.015 [-0.165] | +0.127 [+0.033], [+0.070, +0.190] | **not supported (inconclusive)** |
| **ARCH-U2** | -0.070 [-0.204] | +0.073 [+0.009], [+0.036, +0.112] | **not supported (inconclusive)** |

| claim | mean AUC lift over total_loc | lo | 90% CI | verdict |
|---|---:|---:|---|---|
| **ARCH-U3** | -0.0050 | -0.0300 | [-0.0175, +0.0053] | **replicated null (equivalence)** |

Mean per-snapshot AUC: total_loc 0.8438 · total_loc × d(file cluster) 0.8387

## Secondary (descriptive)

Learned per-line fix density by file cluster at the last scored snapshot (pre-2026-04-01); global 0.013 positives/kLOC:

| label | training rows' kLOC | positives | d(a) per kLOC | ratio to global |
|---|---:|---:|---:|---:|
| file_cluster_3 | 3,337 | 65 | 0.019 | 1.51 |
| file_cluster_11 | 477 | 9 | 0.018 | 1.43 |
| file_cluster_8 | 5,898 | 104 | 0.018 | 1.37 |
| file_cluster_17 | 4,670 | 76 | 0.016 | 1.27 |
| file_cluster_6 | 7,272 | 115 | 0.016 | 1.23 |
| file_cluster_15 | 3,944 | 51 | 0.013 | 1.01 |
| file_cluster_14 | 1 | 0 | 0.012 | 0.97 |
| file_cluster_4 | 7,334 | 87 | 0.012 | 0.93 |
| Unclassified | 4 | 0 | 0.012 | 0.92 |
| file_cluster_12 | 1,770 | 19 | 0.011 | 0.84 |
| file_cluster_7 | 456 | 4 | 0.009 | 0.72 |
| file_cluster_1 | 1,242 | 10 | 0.008 | 0.64 |
| file_cluster_9 | 2,006 | 14 | 0.007 | 0.56 |
| file_cluster_2 | 1,212 | 3 | 0.003 | 0.23 |
| file_cluster_16 | 4,266 | 5 | 0.001 | 0.10 |

Label flip over the prior year vs future fix (files present a year earlier):

| group | files | positive rate | mean total_loc |
|---|---:|---:|---:|
| unchanged LOC (no edit) | 49,605 | 0.0026 | 228 |
| edited, label kept | 34,241 | 0.0121 | 552 |
| edited, label flipped | 4,283 | 0.0126 | 567 |

Runtime 67s · bootstrap 5000 rounds over snapshots, seed 2982.
