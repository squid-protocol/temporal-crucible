# REG-H1 / H2 — co-change omission vs regression-inducing commits (SCORED)

- evaluable repos (≥ 30 inducing commits): curl, openssl, harfbuzz, ndpi; co-change window 730 d; strong partner = support ≥ 3 and confidence ≥ 0.5; 20 equal-count commit-size bins

| claim | what | pooled mean | lo (α=0.005) | 90% CI | verdict |
|---|---|---:|---:|---|---|
| **REG-H1** | stratAUC(omission) − stratAUC(size) | -0.012 | -0.051 | [-0.037, +0.015] | **not supported (inconclusive)** |
| **REG-H2** | stratAUC(omission) − stratAUC(coupled-files placebo) | -0.002 | -0.020 | [-0.013, +0.009] | **replicated null (equivalence)** |

Headline rule extra condition (no evaluable repo's H1 point estimate below 0): NOT met

## Per repo (descriptive)

| repo | commits | inducing | H1 | H2 | AUC size | AUC files touched | AUC omission | AUC coupled-files | omission > 0: inducing / others |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| curl | 19,587 | 681 | -0.005 | -0.017 | 0.696 | 0.644 | 0.538 | 0.573 | 38% / 27% |
| openssl | 24,785 | 229 | -0.029 | +0.008 | 0.641 | 0.595 | 0.507 | 0.514 | 40% / 35% |
| harfbuzz | 16,905 | 243 | -0.035 | -0.009 | 0.518 | 0.504 | 0.468 | 0.478 | 20% / 25% |
| ndpi | 3,543 | 46 | +0.023 | +0.010 | 0.577 | 0.568 | 0.555 | 0.563 | 43% / 33% |

Runtime 288s · commit bootstrap within repo, 5000 rounds, seed 2982.
