# FORT-H1..H3 — fortification: guard clauses before and after fixes (SCORED)

- fix-function touches: 59,208 — latent 1,570, regression 1,466, other-fix 51,713, extrinsic 4,459

| claim | comparison | RR | 99.67% CI | verdict |
|---|---|---:|---|---|
| **FORT-H1** CVE fixes fortify | P(adds guard) latent vs other-fix | **1.88** | [1.47, 2.39] | **SUPPORTED** |
| **FORT-H2** guard-adding fixes: was the function already guarded? | P(pre-guarded) latent vs other-fix (n latent 316) | **1.00** | [0.91, 1.10] | **inconclusive** |
| **FORT-H3** regression fixes are lexically neutral | P(adds guard) regression vs other-fix | **1.56** | [1.19, 1.99] | **not supported** |

## By class (descriptive)

| class | touches | adds guard | removes guard | mean ΔG | pre-guarded | median function loc |
|---|---:|---:|---:|---:|---:|---:|
| latent | 1,570 | 20.1% | 8.2% | +0.09 | 72.2% | 52 |
| regression | 1,466 | 16.5% | 4.6% | +0.16 | 64.4% | 42 |
| other-fix | 51,713 | 11.3% | 5.1% | +0.06 | 69.8% | 46 |
| extrinsic | 4,459 | 6.6% | 4.2% | +0.00 | 67.0% | 45 |

Per repo (MH point RR): H1 / H2 / H3
- curl: 1.37 / 1.13 / 0.94
- openssl: 2.49 / 0.97 / 1.71
- harfbuzz: 1.31 / 0.83 / 1.90
- ndpi: 1.39 / 1.05 / 0.61
- libarchive: inf / inf / 1.02
- second comparison, latent vs extrinsic, P(adds guard): 3.85

Runtime 149s · seed 2982 · 2000 commit-cluster bootstrap rounds.
