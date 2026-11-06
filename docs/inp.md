# INP-H1..H6 — input-facing code vs CVE fixes (SCORED)

- evaluable repos (≥ 20 snapshots with a CVE positive): curl, ndpi, openssl, harfbuzz

| claim | what | pooled mean | lo (α=0.0017) | 90% CI | per repo | verdict |
|---|---|---:|---:|---|---|---|
| **INP-H1** | IN beats size on CVE fixes | -0.092 | -0.159 | [-0.129, -0.054] | curl -0.143 / ndpi +0.096 / openssl -0.174 / harfbuzz -0.147 | **not supported (inconclusive)** |
| **INP-H2** | BUF beats size on CVE fixes | -0.054 | -0.130 | [-0.098, -0.011] | curl -0.038 / ndpi +0.163 / openssl -0.055 / harfbuzz -0.288 | **not supported (inconclusive)** |
| **INP-H3** | IN: CVE lift − placebo-class lift | -0.034 | -0.105 | [-0.073, +0.005] | curl -0.038 / ndpi +0.137 / openssl -0.100 / harfbuzz -0.134 | **not supported (inconclusive)** |
| **INP-H4** | BUF: CVE lift − placebo-class lift | +0.032 | -0.055 | [-0.018, +0.080] | curl +0.057 / ndpi +0.235 / openssl +0.008 / harfbuzz -0.172 | **not supported (inconclusive)** |
| **INP-H5** | IN beats size where no prior CVE | -0.104 | -0.200 | [-0.153, -0.054] | curl -0.214 / ndpi -0.056 / openssl -0.138 / harfbuzz -0.010 | **not supported (inconclusive)** |
| **INP-H6** | BUF beats size where no prior CVE | -0.044 | -0.177 | [-0.118, +0.030] | curl -0.019 / ndpi +0.185 / openssl -0.057 / harfbuzz -0.284 | **not supported (inconclusive)** |

**Headline: input-facing code is NOT shown** (needs H1+H3+H5 or H2+H4+H6).

| repo | quarterly snapshots | with CVE positive | CVE commits | files with any IN (median) | files with any BUF (median) |
|---|---:|---:|---:|---:|---:|
| curl | 105 | 63 | 185 | 9.4% | 20.0% |
| ndpi | 43 | 26 | 105 | 1.8% | 19.6% |
| openssl | 110 | 75 | 235 | 8.9% | 27.7% |
| harfbuzz | 62 | 28 | 90 | 1.7% | 9.1% |

Runtime 27s · within-repo snapshot bootstrap, 5000 rounds, seed 2982.
