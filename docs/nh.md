# NH — natural history: function lifecycles and include-graph hubs (SCORED)

## Part 1 — function lifecycles

| repo | snapshots | functions tracked | median lifespan (born after first snapshot) | alive at 5 y | alive at 10 y |
|---|---:|---:|---:|---:|---:|
| curl | 105 | 8,477 | 8.0 y | 65% | 44% |
| ndpi | 43 | 2,827 | > span | 84% | 57% |
| openssl | 110 | 29,291 | 15.8 y | 80% | 71% |
| harfbuzz | 62 | 8,668 | 12.2 y | 71% | 62% |
| libarchive | 70 | 5,388 | > span | 85% | 77% |

Quarterly death hazard and shape-change rate by age (functions born after the first snapshot):

| repo | death < 1 y | death 1–3 y | death 3–5 y | death ≥ 5 y | shape change < 1 y | shape change 1–3 y | shape change 3–5 y | shape change ≥ 5 y |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| curl | 0.032 | 0.021 | 0.017 | 0.019 | 0.129 | 0.098 | 0.083 | 0.092 |
| ndpi | 0.015 | 0.010 | 0.005 | 0.013 | 0.098 | 0.077 | 0.065 | 0.071 |
| openssl | 0.023 | 0.008 | 0.007 | 0.008 | 0.074 | 0.038 | 0.033 | 0.037 |
| harfbuzz | 0.029 | 0.012 | 0.015 | 0.010 | 0.067 | 0.032 | 0.032 | 0.030 |
| libarchive | 0.019 | 0.008 | 0.002 | 0.003 | 0.072 | 0.033 | 0.015 | 0.010 |

| claim | per repo (curl / nDPI / openssl / harfbuzz / libarchive) | pooled | bound | verdict |
|---|---|---:|---:|---|
| **LIFE-H1** infant mortality: hazard(< 1 y) / hazard(3–5 y) | 1.91 / 2.91 / 3.51 / 1.97 / 7.82 | 2.93 | lo 1.80 | **SUPPORTED** |
| **LIFE-H2** structural freeze: change rate(≥ 3 y) / (< 1 y) | 0.70 / 0.69 / 0.48 / 0.46 / 0.15 | 0.46 | hi 0.59 | **SUPPORTED** |
| **LIFE-H3** archetype kept when (loc, complexity) changed | 0.90 / 0.89 / 0.88 / 0.80 / 0.84 | 0.876 | lo 0.862 | **SUPPORTED** |

Most common archetype transitions (pooled):

- Parameter Forwarders → Compute Cores: 666
- Compute Cores → Many-Argument Workhorses: 600
- Compute Cores → Parameter Forwarders: 588
- Encapsulated Accessors → Stateful Encapsulated Methods: 530
- Stateful Encapsulated Methods → Many-Argument Workhorses: 514
- Stateful Encapsulated Methods → C Struct Operations: 373
- Stateful Encapsulated Methods → Encapsulated Accessors: 333
- Many-Argument Workhorses → Compute Cores: 325
- C Struct Operations → Many-Argument Workhorses: 271
- Many-Argument Workhorses → Parameter Forwarders: 259

## Part 2 — include-graph hubs

| repo | hub persistence after 1 y (median) | attachment slope (log gain ~ log in-degree) | lo | frozen core RR (hub vs non-hub, changed in 1 y) |
|---|---:|---:|---:|---:|
| curl | 0.96 | 0.330 | 0.310 | 1.04 |
| ndpi | 0.92 | 0.484 | 0.445 | 1.11 |
| openssl | 0.98 | 0.273 | 0.242 | 1.23 |
| harfbuzz | 0.97 | 0.237 | 0.199 | 1.02 |
| libarchive | 1.00 | 0.195 | 0.151 | 1.62 |

| claim | result | verdict |
|---|---|---|
| **HUB-H1** hubs stable (median 1-y persistence > 0.70 on ≥ 4/5) | 5/5 repos | **SUPPORTED** |
| **HUB-H2** rich get richer (slope lo > 0 on ≥ 4/5) | 5/5 repos | **SUPPORTED** |
| **HUB-H3** frozen core (pooled MH RR < 1, upper bound < 1) | RR 1.12, hi 1.15 | **not supported** |

Runtime 64s · snapshot bootstraps within repo, 5000 rounds, seed 2982.
