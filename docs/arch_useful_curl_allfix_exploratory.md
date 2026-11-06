# ARCH-U1..U3 — curl (EXPLORATORY: no verdicts)

**EXPLORATORY.** Not a registered configuration; nothing here is a verdict.

- DB `.claude/worktrees/forward-asof/dbs/curl_out/curl_galaxy_master.db`; 105 quarterly snapshots; empty: none; scored: **78**
- events: 1293 on-master `security-fix,bugfix-fixes,bugfix-bug,regression`; outcome window (t, t+180 d]; d(a) shrinkage pseudo-LOC 50,000

## Mean recall at a share of lines reviewed

| ranking | @10% | @20% (primary) | @30% |
|---|---:|---:|---:|
| LOC-desc | 0.077 | **0.211** | 0.306 |
| LOC-asc | 0.093 | **0.180** | 0.268 |
| U1 d(file cluster) | 0.124 | **0.214** | 0.331 |
| U2 d(composition) | 0.108 | **0.201** | 0.307 |

## Verdicts (α = 0.0025 one-sided)

| claim | vs LOC-desc: mean [lo] | vs LOC-asc: mean [lo], 90% CI | verdict |
|---|---|---|---|
| **ARCH-U1** | +0.003 [-0.086] | +0.033 [-0.011], [+0.009, +0.057] | (exploratory) |
| **ARCH-U2** | -0.010 [-0.098] | +0.020 [-0.028], [-0.008, +0.047] | (exploratory) |

| claim | mean AUC lift over total_loc | lo | 90% CI | verdict |
|---|---:|---:|---|---|
| **ARCH-U3** | -0.0030 | -0.0167 | [-0.0103, +0.0031] | (exploratory) |

Mean per-snapshot AUC: total_loc 0.8534 · total_loc × d(file cluster) 0.8503

## Secondary (descriptive)

Learned per-line fix density by file cluster at the last scored snapshot (pre-2026-01-01); global 0.173 positives/kLOC:

| label | training rows' kLOC | positives | d(a) per kLOC | ratio to global |
|---|---:|---:|---:|---:|
| file_cluster_2 | 207 | 122 | 0.508 | 2.94 |
| file_cluster_4 | 1,983 | 428 | 0.215 | 1.24 |
| file_cluster_17 | 2,030 | 416 | 0.204 | 1.18 |
| file_cluster_13 | 8 | 2 | 0.185 | 1.07 |
| Unclassified | 0 | 0 | 0.173 | 1.00 |
| file_cluster_14 | 0 | 0 | 0.172 | 1.00 |
| file_cluster_8 | 1,928 | 318 | 0.165 | 0.95 |
| file_cluster_7 | 42 | 6 | 0.159 | 0.92 |
| file_cluster_6 | 3,543 | 552 | 0.156 | 0.90 |
| file_cluster_3 | 1,014 | 156 | 0.155 | 0.89 |
| file_cluster_15 | 488 | 74 | 0.154 | 0.89 |
| file_cluster_16 | 851 | 122 | 0.145 | 0.84 |
| file_cluster_1 | 282 | 39 | 0.144 | 0.83 |
| file_cluster_9 | 632 | 66 | 0.109 | 0.63 |
| file_cluster_11 | 77 | 4 | 0.099 | 0.57 |
| file_cluster_12 | 392 | 28 | 0.083 | 0.48 |

Label flip over the prior year vs future fix (files present a year earlier):

| group | files | positive rate | mean total_loc |
|---|---:|---:|---:|
| unchanged LOC (no edit) | 14,802 | 0.0143 | 126 |
| edited, label kept | 18,155 | 0.0991 | 482 |
| edited, label flipped | 2,071 | 0.1458 | 605 |

Runtime 16s · bootstrap 5000 rounds over snapshots, seed 2982.
