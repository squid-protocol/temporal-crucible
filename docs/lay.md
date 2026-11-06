# LAY-H1..H3 — layered fingerprint vs the coarse one on OpenSSL→fork copies (SCORED; aggregates only)

- queries with a name-identified copy (≥ 6 lines): **90** (LibreSSL 73, BoringSSL 17)

| claim | comparison | n | difference | lo (α 0.01/3) | verdict |
|---|---|---:|---:|---:|---|
| **LAY-H1** | recall@1 L2 − L1 | 90 | +23.3% | +5.6% | **SUPPORTED** |
| **LAY-H2** | recall@1 FUSED − L1 | 90 | +34.4% | +20.0% | **SUPPORTED** |
| **LAY-H3** | recall@10 FUSED − L1 (BoringSSL) | 17 | +35.3% | +5.9% | **SUPPORTED** |

## Recall by method (descriptive; TOKEN is a near-circular reference ceiling)

| subset | n | L1 @1 / @10 | L2 @1 / @10 | L3 @1 / @10 | FUSED @1 / @10 | TOKEN @1 / @10 |
|---|---:|---:|---:|---:|---:|---:|
| all | 90 | 46% / 71% | 69% / 87% | 44% / 53% | 80% / 89% | 92% / 100% |
| LibreSSL | 73 | 49% / 73% | 75% / 84% | 53% / 63% | 77% / 86% | 90% / 100% |
| BoringSSL | 17 | 29% / 65% | 41% / 100% | 6% / 12% | 94% / 100% | 100% / 100% |

Runtime 23s · seed 2982 · pessimistic tie ranks · RRF k = 60.
