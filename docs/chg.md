# CHG-H1..H5 — fingerprint change and code age vs later regression fixes (SCORED)

**Gate G-JOIN v2 (amendment A1):** 56,413 / 58,578 fix→function hits in files present at the preceding snapshot match an engine function at the preceding or following snapshot = **96.3%** → **PASS** (gate ≥ 90%). Run 1's G-JOIN v1 failed at 79.5%; see docs/chg_hypotheses.md § amendment A1. Results below are **post-amendment**.

- units (function × quarter, full 180-day window): **1,526,252**; states {'untouched': 1452313, 'shape': 40022, 'edited': 33917}; ages {'unknown': 33907, 'young': 158569, '1-3y': 291477, 'old': 1042299}
- units hit in window: regression 1,188, other-fix 59,650, latent 2,201, extrinsic 5,318, regression-linked 4,405

| claim | comparison | events (exposed / reference) | MH RR | lo (α 0.01/5, file-cluster bootstrap) | verdict |
|---|---|---:|---:|---:|---|
| **CHG-H1** | shape-changed vs untouched → regression | 255 / 824 (n 40,022 / 1,452,313) | **2.88** | 2.18 | **SUPPORTED** |
| **CHG-H2** | shape-changed vs edited-same-shape → regression | 255 / 109 (n 40,022 / 33,917) | **1.42** | 1.02 | **SUPPORTED** |
| **CHG-H3** | regression share of fixed: shape vs untouched | 255 / 824 (n 7,465 / 48,696) | **1.47** | 1.12 | **SUPPORTED** |
| **CHG-H4** | young vs old → regression | 173 / 809 (n 158,569 / 1,042,299) | **1.23** | 0.73 | **not supported** |
| **CHG-H5** | regression share of fixed: young vs old | 173 / 809 (n 10,449 / 34,412) | **0.77** | 0.45 | **not supported** |

## Per repo (MH point estimates, descriptive)

- **CHG-H1** per repo: curl 2.68, openssl 4.03, harfbuzz 2.24, ndpi 2.68, libarchive (few)
- **CHG-H2** per repo: curl 1.38, openssl 1.19, harfbuzz (few), ndpi (few), libarchive (few)
- **CHG-H3** per repo: curl 1.49, openssl 1.58, harfbuzz 1.16, ndpi 1.70, libarchive (few)
- **CHG-H4** per repo: curl 0.80, openssl 1.57, harfbuzz 3.38, ndpi (few), libarchive 1.03
- **CHG-H5** per repo: curl 0.60, openssl 0.73, harfbuzz 2.39, ndpi (few), libarchive 0.52

## Crude 180-day hit rates per 1,000 function-quarters (descriptive)

| group | n | regression | other-fix | latent | extrinsic | regression-linked |
|---|---:|---:|---:|---:|---:|---:|
| state: untouched | 1,452,313 | 0.57 | 33.12 | 1.13 | 3.02 | 2.27 |
| state: edited | 33,917 | 3.21 | 123.36 | 5.10 | 10.11 | 11.68 |
| state: shape | 40,022 | 6.37 | 184.00 | 9.82 | 14.84 | 17.77 |
| age: young | 158,569 | 1.09 | 65.20 | 1.92 | 7.20 | 4.59 |
| age: 1-3y | 291,477 | 0.61 | 45.42 | 1.42 | 4.54 | 3.07 |
| age: old | 1,042,299 | 0.78 | 32.53 | 1.42 | 2.56 | 2.64 |
| age: unknown | 33,907 | 0.80 | 64.00 | 0.06 | 5.52 | 0.83 |

Regression share among fixed units (regression / (regression or other-fix)):
- untouched: 1.7% of 48,696
- edited: 2.6% of 4,227
- shape: 3.4% of 7,465
- young: 1.7% of 10,449
- 1-3y: 1.3% of 13,344
- old: 2.4% of 34,412
- unknown: 1.2% of 2,183

Runtime 185s · seed 2982 · 2000 file-cluster bootstrap rounds.
