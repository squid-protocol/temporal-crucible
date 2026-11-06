# SFS-H1..H4 — structural-fingerprint stability, name-free survival, turnover vs fix classes (SCORED)

- sfs: structure lens, min-loc 3, twins min-loc 6, ratio 0.8, FDR 0.01; 103 yearly snapshots over 5 repos; call edges absent in these scans (call-graph component zero for all)

| claim | result | verdict |
|---|---|---|
| **SFS-H1** fingerprints are stable identities (nearest neighbour, other eras ≥ 5 y) | accuracy **99.0%** over 103 snapshots | **SUPPORTED** |
| **SFS-H2** name-free retention agrees with name-based survival | Spearman **+0.49** over 98 repo-years | **not supported** |
| **SFS-H3** turnover goes with regression share | mean within-repo ρ **+0.16**, permutation p 0.1071 (4 repos) | **not supported** |
| **SFS-H4** …more than with CVE share | mean within-repo Δρ **+0.15**, p 0.1940 | **not supported** |

## Per repo (descriptive)

| repo | years | median retention | median name-based survival | lowest-retention years | ρ(turnover, regression share) | ρ(turnover, latent share) | ρ(turnover, extrinsic share) |
|---|---:|---:|---:|---|---:|---:|---:|
| curl | 26 | 0.72 | 0.95 | 2000 (0.36), 2001 (0.56), 1999 (0.57) | -0.27 | -0.10 | +0.32 |
| ndpi | 10 | 0.59 | 0.96 | 2017 (0.38), 2022 (0.50), 2020 (0.55) | +0.66 | +0.37 | +0.19 |
| openssl | 28 | 0.71 | 0.98 | 1999 (0.09), 2015 (0.52), 1998 (0.55) | +0.31 | -0.34 | -0.40 |
| harfbuzz | 16 | 0.63 | 0.97 | 2011 (0.36), 2018 (0.39), 2012 (0.49) | -0.06 | +0.13 | +0.11 |
| libarchive | 18 | 0.67 | 1.00 | 2009 (0.41), 2011 (0.56), 2012 (0.59) | +0.10 | +nan | +0.55 |

Runtime 623s · seed 2982, 10000 permutations.
