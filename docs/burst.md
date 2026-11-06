# BURST-H1..H3 — extrinsic fixes vs compiler releases (SCORED)

- repos: curl, ndpi, openssl, harfbuzz, libarchive; shocks `events/shocks_compilers.json` (Clang from LLVM 2.6); window 90 d

| claim | what | shocks | units | mean | lo (α=0.0033) | 90% CI | verdict |
|---|---|---:|---:|---:|---:|---|---|
| **BURST-H1** | extrinsic share after − before, GCC releases | 27 | 99 | +0.0020 | -0.0405 | [-0.0226, +0.0264] | **not supported (inconclusive)** |
| **BURST-H2** | extrinsic share after − before, Clang releases | 33 | 153 | +0.0086 | -0.0173 | [-0.0069, +0.0244] | **not supported (inconclusive)** |
| **BURST-H3** | own-compiler-named − other-compiler-named extrinsic Δcount | 60 | 252 | +0.0873 | -0.2274 | [-0.1120, +0.3109] | **not supported (inconclusive)** |

## Descriptive (no verdicts)

Per repo, mean Δ extrinsic share (90 d):

| repo | GCC shocks | Δ share | Clang shocks | Δ share | mean extrinsic share |
|---|---:|---:|---:|---:|---:|
| curl | 27 | -0.0095 | 33 | -0.0169 | 0.082 |
| ndpi | 11 | -0.0144 | 22 | +0.0157 | 0.033 |
| openssl | 27 | +0.0113 | 33 | +0.0151 | 0.066 |
| harfbuzz | 17 | -0.0073 | 32 | -0.0078 | 0.036 |
| libarchive | 17 | +0.0253 | 33 | +0.0386 | 0.225 |

Robustness and placebo (pooled means):

| variant | GCC Δ share | Clang Δ share | H3 Δ named |
|---|---:|---:|---:|
| window 30 d | +0.0126 (96) | +0.0196 (147) | +0.107 (243) |
| window 90 d (registered) | +0.0020 (99) | +0.0086 (153) | +0.087 (252) |
| window 180 d | +0.0063 (97) | -0.0034 (152) | +0.149 (249) |
| placebo: shocks +182 d | +0.0073 (97) | +0.0154 (150) | -0.061 (247) |

Runtime 1s · cluster bootstrap over shocks, 5000 rounds, seed 2982.
