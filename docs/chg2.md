# CHG2-H1..H2 — engine change features vs churn for regression ranking (SCORED)

- units 1,526,252; regression-hit units 1,188; units with churn > 0: 129,705; churn-mapped commits 100,885

| claim | test positives | recall@20% B0 churn | recall@20% M1 churn+engine | difference | lo (α 0.01/2) | verdict |
|---|---:|---:|---:|---:|---:|---|
| **CHG2-H1** forward (train < 2020, test ≥ 2020) | 666 | 41.3% | 38.7% | -2.6% | -5.5% | **not supported** |
| **CHG2-H2** leave-one-repo-out (pooled) | 1,188 | 36.7% | 33.8% | -2.9% | -6.7% | **not supported** |

## Descriptive

- forward, size-only ordering recall@20%: 35.9%; @5%: B0 15.5%, M1 14.0%; @10%: B0 26.4%, M1 24.6%
- leave-one-repo-out, size-only ordering recall@20%: 10.9%
- fold curl (624 pos): B0 32.7%, M1 30.3%, size-only 9.6%
- fold openssl (348 pos): B0 43.7%, M1 37.6%, size-only 0.0%
- fold harfbuzz (142 pos): B0 34.5%, M1 35.9%, size-only 40.8%
- fold ndpi (20 pos): B0 45.0%, M1 40.0%, size-only 50.0%
- fold libarchive (54 pos): B0 40.7%, M1 40.7%, size-only 3.7%

M1 standardised coefficients (forward fit, largest 12): log10 loc +0.85, log1p commits +0.26, |Δstate_pointers| +0.12, |Δcomplexity| +0.11, |Δstruct_branch| -0.11, |Δarch_scientific| -0.10, |Δarch_globals| -0.10, |Δdef_freeze_hits| -0.09, shape changed +0.09, |Δstruct_macros| -0.08, complexity/loc -0.07, |Δdef_test| -0.06

Runtime 435s · seed 2982 · 2000 file-cluster bootstrap rounds (selections fixed).
