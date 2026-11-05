# FREC-H1 / FREC-H2 — ndpi

- engine `32619e4a5e83c3ae7ba6e8969397e6db364ba8cf` · history `ablated` · DB `ndpi_galaxy_master.db`
- fix-class events with a date: 121; skipped: none; median date 2021-05-15
- scored (later half, >= 1 positive and >= 1 negative function): **51** events, 4719 candidate functions, 117 positives

| claim | mean lift vs function loc | one-sided lo (α=0.005) | 90% CI | verdict |
|---|---:|---:|---|---|
| **FREC-H1** | -0.1702 | -0.2510 | [-0.2219, -0.1189] | **not supported (inconclusive)** |
| **FREC-H2** | -0.0078 | -0.0313 | [-0.0219, +0.0069] | **not supported (inconclusive)** |

Mean within-event AUC: prior 0.6947 · (prior, loc) 0.8570 · loc 0.8648.

## Exploratory (no verdicts)

- events where every candidate has prior = 0: 8 of 51
- recall@1 (share of the top-ranked function(s) that are fixed): (prior, loc) 0.373 vs loc 0.333

| class | events | mean lift H1 | mean lift H2 |
|---|---:|---:|---:|
| security-fix | 51 | -0.1702 | -0.0078 |

Runtime 6s · bootstrap 5000 rounds over events, seed 2982.
