# VZ-H1..H3 — vendored zlib (SCORED; aggregates only)

- hosts scanned: 12 (empty, dropped: []); truth pairs (query function × host, text Jaccard ≥ 0.5): **185**; renamed: 13

| claim | result | lo | verdict |
|---|---|---:|---|
| **VZ-H1** recall@1 FUSED − L1 | +23.8% (n 185) | +14.5% | **SUPPORTED** |
| **VZ-H2** renamed: recall@10 FUSED − NAME | n 13 renamed pairs | — | **not evaluable** (< 15) |
| **VZ-H3** patch check agrees with host version | 123/137 = 89.8% | Wilson 81.2% | **SUPPORTED** |

## Descriptive

| subset | n | L1 @1 / @10 | L2 @1 / @10 | L3 @1 / @10 | FUSED @1 / @10 | NAME @1 / @10 | TOKEN @1 / @10 |
|---|---:|---:|---:|---:|---:|---:|---:|
| all | 185 | 68% / 90% | 72% / 81% | 85% / 92% | 91% / 100% | 90% / 93% | 94% / 100% |
| renamed | 13 | 85% / 100% | 8% / 92% | 8% / 8% | 8% / 100% | 0% / 0% | 15% / 100% |
| same name | 172 | 66% / 90% | 77% / 80% | 91% / 98% | 98% / 100% | 97% / 100% | 99% / 100% |

- status mix (all pairs): {'diverged': 47, 'patched': 137, 'addition-only/unclear': 1}
- H3 disagreements by kind (counts only): {'status patched vs version-expected unpatched-looking': 14}
- hosts with ≥ 1 truth pair: 12 of 12

Runtime 32s · seed 2982 · host-cluster bootstrap · per-host detail is private.
