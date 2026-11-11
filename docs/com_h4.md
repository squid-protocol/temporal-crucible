# COM-H4 (COM-H4a..H4b) — comment drift vs CVE fixes (SCORED)

- at-risk function-quarters 153,695: drifted 31,979, maintained 8,034, no header 113,682
- registration `docs/com_hypotheses.md`; window 8 quarters; α = 0.005

| claim | result | verdict |
|---|---|---|
| **COM-H4a** drifted vs maintained → CVE-fix rate | rate ratio **0.67** [0.42, 1.06] (99% [0.42, 1.06]); CVE-fix quarters 166 / 55 | **not supported: inconclusive** |
| **COM-H4b** CVE-specific (÷ other-fix rate ratio) | **0.75** (lo 0.44); other-fix 0.89 (3042 / 866) | **not supported** |

## Descriptive (no verdicts)

- regression 0.87; extrinsic 0.77
- no header vs maintained (equally edited): CVE rate ratio 0.72 (events 351 / 55)
- curl: drifted share of headed at-risk quarters 83%; CVE rate ratio 0.76 (events 125 / 34)
- openssl: drifted share of headed at-risk quarters 78%; CVE rate ratio 0.51 (events 22 / 11)
- ndpi: drifted share of headed at-risk quarters 85%; CVE rate ratio 0.23 (events 13 / 9)
- harfbuzz: drifted share of headed at-risk quarters 66%; CVE rate ratio 3.64 (events 6 / 1)
- body-change count × group: 2: 18,505 / 3,979, 3: 7,497 / 2,095, 4: 3,149 / 995, 5+: 2,828 / 965

Runtime 165s · seed 2982 · file-cluster bootstrap 2000.

## Run record

- Engine gitgalaxy `14e700054` (main, after #8200/#8240/#8244), melek; scorer `tools/comh4_eval.py` at this PR's head.
- One-sided bounds at α = 0.005 and the two-sided 99% CI use the same quantiles (0.005 / 0.995), so they print the
  same numbers.

## Instrument audit (descriptive)

10 distinct random drifted/maintained calls from the 30-case sheet were rebuilt from the blobs: **10 of 10
correct**. Each header was a real explanatory block above the function, each "drifted" header was identical across
the window, the "maintained" one (`Curl_freeaddrinfo`) had a real wording edit, and every body had ≥ 2 code-only
changes.

## Reading

- **H4a is inconclusive, pointing the other way.** Drifted functions had *fewer* CVE-fix quarters than equally
  edited, equally sized maintained ones: 0.67 [0.42, 1.06]. curl, OpenSSL and nDPI all point below 1 (0.76, 0.51,
  0.23); harfbuzz is above (3.64) on 7 events. Nothing here supports "stale comments mark CVE risk". The CI does not
  exclude 1 and is too wide to call a null.
- **H4b is not supported** (0.75, lo 0.44). Other fixes show the same direction more weakly (0.89).
- **Frozen headers are the norm.** 66–85% of headed, repeatedly edited function-quarters never touched their header
  in 2 years, as Fluri et al. found for Java.
- **EXPLORATORY, not tested:** a likely reason for the direction is that header edits travel with attention. A
  function under active security work gets its comment rewritten *and* more fixes. Prior CVE fixes in the window can
  rewrite the header themselves, making a function "maintained", and recidivism then predicts the next fix. The
  prior-CVE-file stratum controls this only at file grain. A follow-up would need a prior-fix-in-function stratum,
  registered on unseen data.
