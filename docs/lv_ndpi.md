# LV-H1..H3 — the search frontier: ndpi (SCORED)

- OSS-Fuzz `ndpi` daily summaries: 2419 reports; monthly snapshots scored: 75 (dropped, no report within 7 d: 1)
- candidates per snapshot: median 218 instrumented C files; files with any new coverage in 90 d: median 18.0%; mean line coverage 96.2%
- labels `events/ndpi_xc.json`; window (t, t+90 d]; block bootstrap (blocks of 3)

| claim | what | n | mean | lo (α=0.0025) | 90% CI | verdict |
|---|---|---:|---:|---:|---|---|
| **LV-H1** | frontier finds latent fixes beyond size | 63 | +0.026 | -0.156 | [-0.083, +0.136] | **not supported (inconclusive)** |
| **LV-H2** | …more than other fixes | 63 | +0.143 | -0.068 | [+0.018, +0.266] | **not supported (inconclusive)** |
| **LV-H3** | reached beats unreached for latent | 63 | +0.088 | -0.022 | [+0.023, +0.151] | **not supported (inconclusive)** |

## Descriptive: mean lift over the stronger size order

| score | latent | extrinsic | regression | other-fix |
|---|---:|---:|---:|---:|
| frontier | +0.026 (63) | -0.069 (41) | -0.094 (59) | -0.115 (75) |
| reached | -0.116 (63) | -0.154 (41) | -0.261 (59) | -0.090 (75) |
| unreached | -0.205 (63) | -0.055 (41) | -0.180 (59) | -0.213 (75) |

Runtime 2s · seed 2982.
