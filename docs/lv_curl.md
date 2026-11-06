# LV-H1..H3 — the search frontier: curl (SCORED)

- OSS-Fuzz `curl` daily summaries: 2848 reports; monthly snapshots scored: 90 (dropped, no report within 7 d: 1)
- candidates per snapshot: median 100 instrumented C files; files with any new coverage in 90 d: median 19.8%; mean line coverage 58.2%
- labels `events/curl_xc.json`; window (t, t+90 d]; block bootstrap (blocks of 3)

| claim | what | n | mean | lo (α=0.0025) | 90% CI | verdict |
|---|---|---:|---:|---:|---|---|
| **LV-H1** | frontier finds latent fixes beyond size | 75 | -0.195 | -0.381 | [-0.300, -0.095] | **not supported (inconclusive)** |
| **LV-H2** | …more than other fixes | 75 | -0.033 | -0.219 | [-0.132, +0.062] | **not supported (inconclusive)** |
| **LV-H3** | reached beats unreached for latent | 75 | -0.048 | -0.263 | [-0.181, +0.079] | **not supported (inconclusive)** |

## Descriptive: mean lift over the stronger size order

| score | latent | extrinsic | regression | other-fix |
|---|---:|---:|---:|---:|
| frontier | -0.195 (75) | -0.179 (82) | -0.102 (90) | -0.150 (90) |
| reached | -0.181 (75) | -0.218 (82) | -0.194 (90) | -0.171 (90) |
| unreached | -0.133 (75) | -0.250 (82) | -0.159 (90) | -0.156 (90) |

Runtime 3s · seed 2982.
