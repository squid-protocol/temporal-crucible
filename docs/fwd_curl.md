# FWD-H1..H3 — curl (EXPLORATORY: no verdicts)

**EXPLORATORY.** This repository supplied the evidence the FWD claims rest on, so per the
registration (docs/HYPOTHESES.md, 2026-11-05) nothing here is a verdict. It is the instrument
check plus labelled context.

- engine `e246915aa6f26ba569cea6b1ef3ed79c5000b6dd` · args `--spec-alignment` · history `asof`
- 104 quarterly snapshots (pre-2000-04-01 .. pre-2026-01-01); 43086 (snapshot, C file) rows; 2529 positives (fix-class touch in (t, t+180 d])
- excluded for engine-reported unusable history (amendment 1): pre-2000-01-01
- fix events with a resolvable date: 1293 of 1293 (classes ['bugfix-bug', 'bugfix-fixes', 'regression', 'security-fix'])
- pooled AUC total_loc: 0.8415

## Instrument gate

Spearman(raw_churn_freq, independent reconstruction from git; amendment 1) >= 0.95 on every snapshot with >= 3 active C files: **PASS** (104/104; min rho 1.0000, median 1.0000).

## FWD-H3 condition: engine change entropy = HCM1_LD_30

Spearman(change_entropy, tools/hcm_variants.py HCM1_LD_30) >= 0.99 on every snapshot: **PASS** (104/104; min 1.0000, median 1.0000).

## Bands

| band | n | positives | powered |
|---|---:|---:|---|
| <=22 | 283 | 4 | no (<20) |
| 23-48 | 7334 | 54 | yes |
| 49-108 | 12899 | 167 | yes |
| >108 | 22570 | 2304 | yes |

Bonferroni alpha per band = 0.01 / 3 = 0.0033

## `raw_churn_freq` (FWD-H1)

Pooled AUC 0.8280 (total_loc 0.8415).

| band | AUC feature | AUC total_loc | lift | one-sided lo | 90% CI | |
|---|---:|---:|---:|---:|---|
| <=22 | 0.5824 | 0.5170 | +0.0654 | — | — |
| 23-48 | 0.5477 | 0.4980 | +0.0497 | -0.0677 | [-0.0221, +0.1186] |
| 49-108 | 0.5789 | 0.5551 | +0.0238 | -0.0588 | [-0.0259, +0.0734] |
| >108 | 0.7959 | 0.7904 | +0.0055 | -0.0142 | [-0.0066, +0.0159] |

## `ownership_entropy` (FWD-H2)

Pooled AUC 0.8056 (total_loc 0.8415).

| band | AUC feature | AUC total_loc | lift | one-sided lo | 90% CI | |
|---|---:|---:|---:|---:|---|
| <=22 | 0.4480 | 0.5170 | -0.0690 | — | — |
| 23-48 | 0.5194 | 0.4980 | +0.0213 | -0.1086 | [-0.0555, +0.0945] |
| 49-108 | 0.5711 | 0.5551 | +0.0160 | -0.0706 | [-0.0356, +0.0664] |
| >108 | 0.7735 | 0.7904 | -0.0169 | -0.0353 | [-0.0284, -0.0048] |

## `change_entropy` (FWD-H3)

Pooled AUC 0.8068 (total_loc 0.8415).

| band | AUC feature | AUC total_loc | lift | one-sided lo | 90% CI | |
|---|---:|---:|---:|---:|---|
| <=22 | 0.5824 | 0.5170 | +0.0654 | — | — |
| 23-48 | 0.5535 | 0.4980 | +0.0555 | -0.0617 | [-0.0155, +0.1239] |
| 49-108 | 0.5794 | 0.5551 | +0.0243 | -0.0512 | [-0.0212, +0.0669] |
| >108 | 0.7643 | 0.7904 | -0.0260 | -0.0488 | [-0.0389, -0.0136] |

## `silo_risk` (exploratory)

Pooled AUC 0.4300 (total_loc 0.8415).

| band | AUC feature | AUC total_loc | lift | one-sided lo | 90% CI | |
|---|---:|---:|---:|---:|---|
| <=22 | 0.4749 | 0.5170 | -0.0421 | — | — |
| 23-48 | 0.5377 | 0.4980 | +0.0396 | -0.1042 | [-0.0513, +0.1313] |
| 49-108 | 0.4886 | 0.5551 | -0.0665 | -0.1386 | [-0.1092, -0.0236] |
| >108 | 0.4083 | 0.7904 | -0.3821 | -0.4193 | [-0.4048, -0.3600] |

## `risk_stability` (exploratory)

Pooled AUC 0.2128 (total_loc 0.8415).

| band | AUC feature | AUC total_loc | lift | one-sided lo | 90% CI | |
|---|---:|---:|---:|---:|---|
| <=22 | 0.2240 | 0.5170 | -0.2930 | — | — |
| 23-48 | 0.3572 | 0.4980 | -0.1408 | -0.3243 | [-0.2524, -0.0360] |
| 49-108 | 0.3972 | 0.5551 | -0.1579 | -0.2345 | [-0.2053, -0.1147] |
| >108 | 0.2468 | 0.7904 | -0.5436 | -0.5765 | [-0.5636, -0.5236] |

Runtime 168s · bootstrap 5000 rounds, seed 2982, snapshot clusters.
