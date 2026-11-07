# OUT-H1..H2 — grammar outliers in the population (SCORED; aggregates only)

- functions 6,936,799; in strata ≥ 1,000: 6,549,411; outliers (bottom 0.1%) 4,288

| claim | result | verdict |
|---|---|---|
| **OUT-H2** outliers concentrate in vendored/generated/test paths | flagged 35.4% vs stratum-expected 23.4%: **1.51×** (lo 1.42); vendored/generated 0.4%, test 34.9% | **SUPPORTED** |
| **OUT-H1** outliers rarely ordinary hand-written (blind audit) | ordinary: outliers 22/40 = 55% vs controls 25/39 = 64%; gap +9%; p = 0.28 | **not supported** |

Audit categories — outliers: ordinary hand-written 22, test or fixture 16, vendored third-party 1, data table or declarative 1
Audit categories — controls: ordinary hand-written 25, test or fixture 12, generated 1, minified or bundled 1

## Descriptive

- outliers with engine threat signals: 0.0% vs all valid 0.0%
- outliers by language (top): c 1118, cpp 600, python 422, java 355, csharp 351, typescript 276, javascript 241, rust 181
- repos with most outliers: runtime 467, freebsd-src 347, illumos-gate 219, kotlin 156, sdk 150, reactos 146, linux 124, go 114

Runtime 140s · seed 2982.
