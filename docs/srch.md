# SRCH-H1..H3 — who finds a CVE vs the age of the code it fixes (SCORED)

- curl advisories crediting fuzzing: ['CURL-CVE-2017-8817', 'CURL-CVE-2018-1000122', 'CURL-CVE-2018-1000301']

## Per repo (descriptive)

| repo | ordinary commits: median age (n) | CVE fixes, fuzzer-found: age (n), ratio | CVE fixes, human-found: age (n), ratio |
|---|---:|---|---|
| curl | 327 d (255) | 2,755 d (3), ×8.42 | 691 d (151), ×2.11 |
| openssl | 242 d (256) | 1,245 d (7), ×5.14 | 892 d (175), ×3.68 |
| ndpi | 176 d (257) | 111 d (98), ×0.63 | — |
| harfbuzz | 24 d (263) | 21 d (70), ×0.88 | — |
| libxml2 | 524 d (255) | 1,104 d (38), ×2.11 | — |
| file | 262 d (293) | 874 d (24), ×3.33 | — |
| libexif | 353 d (243) | 61 d (6), ×0.17 | — |

## Claims (log₁₀ ratios; ×factor in brackets)

| claim | repos | effect | upper bound (α = 0.0033) | verdict |
|---|---|---:|---:|---|
| **SRCH-H1** fuzzer-found CVE fixes vs ordinary commits (unseen repos) | libxml2, file | +0.423 (×2.65) | +0.838 | **not supported** |
| **SRCH-H2** openssl: fuzzer-credited vs human-credited CVE fixes | openssl (7 vs 175) | +nan (×nan) | +nan | **not evaluable (fuzzer n = 7)** |
| **SRCH-H3** fuzzer-regime ratio − human-regime ratio | fuzzer: ndpi, harfbuzz, libxml2, file; human: curl, openssl | -0.298 (×0.50) | +0.135 | **not supported** |

Runtime 106s · 2394 commits measured · bootstrap 5000 rounds within repo, seed 2982.
