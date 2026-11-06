# AGE-H1..H4 — the age signature of fix classes (SCORED)

Effect = median log₁₀(age of changed lines, days), class minus baseline, within repo, averaged over repos; shown also as a factor (×). Bounds at α = 0.0025.

| claim | repos | effect (log₁₀) | factor | bound | 90% CI | verdict |
|---|---|---:|---:|---:|---|---|
| **AGE-H1** regression vs generic (younger?) | curl, openssl, harfbuzz | -0.005 | ×0.99 | hi +0.304 | [-0.109, +0.191] | **not supported** |
| **AGE-H2** CVE vs generic (older?) | curl, ndpi, openssl, harfbuzz | +0.007 | ×1.02 | lo -0.279 | [-0.178, +0.199] | **not supported** |
| **AGE-H3** CVE vs regression (older?) | curl, openssl, harfbuzz | +0.050 | ×1.12 | lo -0.279 | [-0.185, +0.248] | **not supported** |
| **AGE-H4** extrinsic vs generic (no signature: 90% CI within ×1.5) | curl, ndpi, openssl, harfbuzz | -0.061 | ×0.87 | — | [-0.208, +0.093] | **not supported (has a signature or inconclusive)** |

## Median age of the changed code, in days (descriptive)

| repo | generic | regression (word) | regression-linked (sanity) | CVE (latent) | extrinsic | pure-addition share (generic / CVE) |
|---|---:|---:|---:|---:|---:|---|
| curl | 448 (253) | 144 (209) | 41 (277) | 733 (154) | 509 (246) | 16% / 17% |
| ndpi | 139 (272) | 33 (6) | 25 (50) | 109 (97) | 222 (39) | 9% / 8% |
| openssl | 320 (258) | 278 (113) | 14 (257) | 908 (182) | 196 (231) | 14% / 23% |
| harfbuzz | 71 (265) | 247 (159) | 0 (259) | 21 (70) | 37 (134) | 12% / 18% |

Runtime 62s · 4153 fixes measured · bootstrap 5000 rounds within (repo, class), seed 2982.
