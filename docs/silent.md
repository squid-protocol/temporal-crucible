# SIL-H1..H2 — silent security-patch detection from structural change signatures (SCORED; aggregates only)

- commits 19,088; CVE (latent) 613, of which silent 451; ordinary fixes (no security words) 17,392

| claim | result | verdict |
|---|---|---|
| **SIL-H1** signature beats patch size on silent CVE fixes (held-out repos) | AUC full **0.569** vs size 0.507 (defensive-only 0.572); gain +0.063, lo +0.012 | **SUPPORTED** |
| **SIL-H2** silent CVE fixes concentrate in the top 10% | enrichment **1.51×** (lo 1.09) | **not supported** |

## Per held-out repo (silent positives, ordinary negatives, AUC full, AUC size)

- curl: 160 / 5,629: 0.583 vs 0.525
- openssl: 172 / 7,351: 0.573 vs 0.579
- ndpi: 68 / 1,153: 0.571 vs 0.499
- harfbuzz: 51 / 3,259: 0.557 vs 0.480

- explicit (security-worded) CVE fixes vs ordinary, AUC full: 0.554
- unlabelled ordinary fixes scoring above the median silent CVE fix: **6,315** (list private)

Most influential features (mean standardised coefficient over folds): +branch +0.37, -dead_code -0.32, +pointers +0.29, +time_date_logic -0.22, -scientific -0.20, -pointers +0.15, +reflection_metaprogramming +0.15, log size -0.15, -time_date_logic -0.14, +globals -0.14, +cleanup -0.13, +test -0.13

Runtime 29s · seed 2982.
