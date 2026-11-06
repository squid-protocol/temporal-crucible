# TGT-H1..H3 — targeted platform coupling (SCORED)

- 1405 extrinsic commits naming exactly one platform family; **1396 qualify** (≥ 1 touched and ≥ 1 untouched candidate in the parent tree)
- families in the pool: aix, android, apple, bsd, clang, gcc, hpux, solaris, vms, windows

| claim | what | n | mean | lo (α=0.0033) | 90% CI | verdict |
|---|---|---:|---:|---:|---|---|
| **TGT-H1** | named platform − generic measure (AUC) | 1396 | -0.041 | -0.053 | [-0.048, -0.035] | **not supported (inconclusive)** |
| **TGT-H2** | named platform − size (AUC) | 1396 | -0.145 | -0.165 | [-0.157, -0.133] | **not supported (inconclusive)** |
| **TGT-H3** | named platform − wrong platforms (AUC) | 1396 | +0.131 | +0.115 | [+0.121, +0.140] | **SUPPORTED** |

## Descriptive

| repo | commits | AUC named | AUC generic | AUC size | all touched files in top 10% by named |
|---|---:|---:|---:|---:|---:|
| curl | 477 | 0.690 | 0.733 | 0.827 | 26% |
| ndpi | 31 | 0.736 | 0.764 | 0.852 | 32% |
| openssl | 385 | 0.611 | 0.660 | 0.752 | 29% |
| harfbuzz | 121 | 0.627 | 0.656 | 0.709 | 28% |
| libarchive | 382 | 0.649 | 0.685 | 0.830 | 17% |

| family | commits | AUC named | AUC generic | AUC size | named − wrong platforms |
|---|---:|---:|---:|---:|---:|
| windows | 795 | 0.709 | 0.714 | 0.793 | +0.195 |
| clang | 145 | 0.525 | 0.598 | 0.825 | +0.006 |
| gcc | 127 | 0.602 | 0.644 | 0.818 | +0.079 |
| bsd | 112 | 0.623 | 0.699 | 0.798 | +0.082 |
| apple | 79 | 0.640 | 0.758 | 0.823 | +0.092 |
| vms | 46 | 0.542 | 0.670 | 0.744 | +0.019 |
| solaris | 36 | 0.531 | 0.680 | 0.797 | -0.013 |
| aix | 31 | 0.545 | 0.666 | 0.768 | +0.004 |
| hpux | 14 | 0.535 | 0.759 | 0.778 | -0.010 |
| android | 11 | 0.499 | 0.680 | 0.705 | -0.032 |

Runtime 32s · stratified commit bootstrap, 5000 rounds, seed 2982.
