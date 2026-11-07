# INT-H1..H2 — defensive at birth vs later CVE fixes (SCORED)

- functions born with a full 2-year follow-up: 37,541; in high / low thirds: 9,111 / 5,774

| claim | result | verdict |
|---|---|---|
| **INT-H1** high- vs low-defence at birth → CVE fix within 2 y | RR **0.97** [0.46, 1.72]; CVE-hit 0.57% vs 0.94% (events 52 / 54) | **not supported** |
| **INT-H2** specific to CVEs (RR_latent ÷ RR_other-fix) | **0.99** (lo 0.46); RR other-fix 0.99 | **not supported** |

## Descriptive

- RR regression 0.68; extrinsic 1.29
- curl: RR latent 0.88, other-fix 1.03 (CVE events 16 / 22)
- openssl: RR latent 1.45, other-fix 0.96 (CVE events 14 / 14)
- ndpi: RR latent 0.52, other-fix 0.96 (CVE events 8 / 16)
- harfbuzz: RR latent 2.86, other-fix 0.98 (CVE events 14 / 2)
- binary (any defence at birth vs none): RR latent 0.69, other-fix 0.96; share defended 28%

Runtime 116s · seed 2982 · file-cluster bootstrap 2000.
