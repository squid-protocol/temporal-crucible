# FWD-H1..H3 — ndpi (SCORED)

- engine `e246915aa6f26ba569cea6b1ef3ed79c5000b6dd` · args `--spec-alignment` · history `asof`
- 43 quarterly snapshots (pre-2015-07-01 .. pre-2026-01-01); 10018 (snapshot, C file) rows; 452 positives (fix-class touch in (t, t+180 d])
- excluded for engine-reported unusable history (amendment 1): none
- fix events with a resolvable date: 121 of 121 (classes ['bugfix-bug', 'bugfix-fixes', 'regression', 'security-fix'])
- pooled AUC total_loc: 0.6995

## Instrument gate

Spearman(raw_churn_freq, independent reconstruction from git; amendment 1) >= 0.95 on every snapshot with >= 3 active C files: **PASS** (43/43; min rho 0.9912, median 1.0000).

## FWD-H3 condition: engine change entropy = HCM1_LD_30

Spearman(change_entropy, tools/hcm_variants.py HCM1_LD_30) >= 0.99 on every snapshot: **PASS** (43/43; min 0.9950, median 1.0000).

## Bands

| band | n | positives | powered |
|---|---:|---:|---|
| <=22 | 29 | 0 | no (<20) |
| 23-48 | 611 | 3 | no (<20) |
| 49-108 | 4848 | 136 | yes |
| >108 | 4530 | 313 | yes |

Bonferroni alpha per band = 0.01 / 2 = 0.0050

## `raw_churn_freq` (FWD-H1)

Pooled AUC 0.5948 (total_loc 0.6995).

| band | AUC feature | AUC total_loc | lift | one-sided lo | 90% CI | verdict |
|---|---:|---:|---:|---:|---|---|
| <=22 | nan | nan | +nan | — | — | not evaluable |
| 23-48 | 0.3673 | 0.1234 | +0.2440 | — | — | not evaluable |
| 49-108 | 0.2832 | 0.5435 | -0.2603 | -0.3615 | [-0.3324, -0.1549] | inconclusive |
| >108 | 0.6902 | 0.6932 | -0.0030 | -0.0660 | [-0.0407, +0.0465] | inconclusive |

**FWD-H1: not supported (inconclusive).**

## `ownership_entropy` (FWD-H2)

Pooled AUC 0.5980 (total_loc 0.6995).

| band | AUC feature | AUC total_loc | lift | one-sided lo | 90% CI | verdict |
|---|---:|---:|---:|---:|---|---|
| <=22 | nan | nan | +nan | — | — | not evaluable |
| 23-48 | 0.5836 | 0.1234 | +0.4603 | — | — | not evaluable |
| 49-108 | 0.3910 | 0.5435 | -0.1525 | -0.3350 | [-0.2289, -0.1220] | inconclusive |
| >108 | 0.6476 | 0.6932 | -0.0456 | -0.0864 | [-0.0696, -0.0190] | inconclusive |

**FWD-H2: not supported (inconclusive).**

## `change_entropy` (FWD-H3)

Pooled AUC 0.6667 (total_loc 0.6995).

| band | AUC feature | AUC total_loc | lift | one-sided lo | 90% CI | verdict |
|---|---:|---:|---:|---:|---|---|
| <=22 | nan | nan | +nan | — | — | not evaluable |
| 23-48 | 0.4123 | 0.1234 | +0.2889 | — | — | not evaluable |
| 49-108 | 0.4609 | 0.5435 | -0.0826 | -0.2838 | [-0.2490, +0.0935] | inconclusive |
| >108 | 0.7160 | 0.6932 | +0.0228 | -0.0416 | [-0.0203, +0.0620] | inconclusive |

**FWD-H3: not supported (inconclusive).**

## `silo_risk` (exploratory)

Pooled AUC 0.5271 (total_loc 0.6995).

| band | AUC feature | AUC total_loc | lift | one-sided lo | 90% CI | |
|---|---:|---:|---:|---:|---|
| <=22 | nan | nan | +nan | — | — |
| 23-48 | 0.1919 | 0.1234 | +0.0685 | — | — |
| 49-108 | 0.6681 | 0.5435 | +0.1246 | -0.3477 | [-0.1414, +0.1681] |
| >108 | 0.5016 | 0.6932 | -0.1916 | -0.5104 | [-0.4294, -0.0808] |

## `risk_stability` (exploratory)

Pooled AUC 0.4172 (total_loc 0.6995).

| band | AUC feature | AUC total_loc | lift | one-sided lo | 90% CI | |
|---|---:|---:|---:|---:|---|
| <=22 | nan | nan | +nan | — | — |
| 23-48 | 0.6743 | 0.1234 | +0.5510 | — | — |
| 49-108 | 0.6734 | 0.5435 | +0.1299 | -0.3461 | [-0.1532, +0.2048] |
| >108 | 0.3242 | 0.6932 | -0.3690 | -0.7370 | [-0.6651, -0.2368] |

Runtime 39s · bootstrap 5000 rounds, seed 2982, snapshot clusters.
