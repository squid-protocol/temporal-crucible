# FREC-H1 / FREC-H2 — curl

- engine `32619e4a5e83c3ae7ba6e8969397e6db364ba8cf` · history `?` · DB `curl_galaxy_master.db`
- fix-class events with a date: 1293; skipped: none; median date 2021-03-29
- scored (later half, >= 1 positive and >= 1 negative function): **435** events, 26370 candidate functions, 1302 positives

| claim | mean lift vs function loc | one-sided lo (α=0.005) | 90% CI | verdict |
|---|---:|---:|---|---|
| **FREC-H1** | -0.1261 | -0.1545 | [-0.1438, -0.1071] | **not supported (inconclusive)** |
| **FREC-H2** | -0.0232 | -0.0359 | [-0.0318, -0.0145] | **not supported (inconclusive)** |

Mean within-event AUC: prior 0.6657 · (prior, loc) 0.7685 · loc 0.7917.

## Exploratory (no verdicts)

- events where every candidate has prior = 0: 34 of 435
- recall@1 (share of the top-ranked function(s) that are fixed): (prior, loc) 0.274 vs loc 0.407

| class | events | mean lift H1 | mean lift H2 |
|---|---:|---:|---:|
| bugfix-bug | 23 | -0.1857 | -0.0183 |
| bugfix-fixes | 208 | -0.1192 | -0.0161 |
| regression | 94 | -0.1305 | -0.0382 |
| security-fix | 110 | -0.1228 | -0.0249 |

Runtime 127s · bootstrap 5000 rounds over events, seed 2982.
