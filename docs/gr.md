# GR-H1..H4 — crucible keyword grammar in the five C repos, vs later fixes (SCORED)

- crucible consensus pairs: 32 over 15 signals; function-quarter units 1,484,262; with ≥ 2 used signals 1,227,577

| claim | result | verdict |
|---|---|---|
| **GR-H1** crucible grammar signs hold in the 5 repos | 53/77 = 69% agree; p = 0.00063; per repo curl 7/15, openssl 10/14, harfbuzz 6/12, ndpi 15/16, libarchive 15/20 | **SUPPORTED** |
| **GR-H2** atypical (bottom-quintile fit) → latent fix | RR **0.66** (lo 0.48); events 281 / 1701 (n 245,503 / 981,975) | **not supported** |
| **GR-H3** atypical (bottom-quintile fit) → regression fix | RR **0.95** (lo 0.65); events 216 / 909 (n 245,503 / 981,975) | **not supported** |
| **GR-H4** grammar-fit drop ≥ 1 vs unchanged (edited functions) → regression | RR **0.00** (lo 0.00); events 0 / 319 (n 13 / 60,307) | **not evaluable** |

## Descriptive

- atypical → other-fix: MH RR 0.99
- atypical → extrinsic: MH RR 1.21
- H2 per repo (MH point): curl 0.62, openssl 0.66, harfbuzz 0.62, ndpi 0.82, libarchive nan
- H3 per repo (MH point): curl 1.09, openssl 0.47, harfbuzz 1.74, ndpi 2.72, libarchive 0.60
- edits: grammar fit up 11%, down 10%, unchanged 79% (n 76,199)

Strongest crucible pairs and their sign in each repo (repo log O/E vs crucible):
- harfbuzz: def_cleanup / state_safety_neg: repo +0.77 vs crucible +0.26 ✓
- ndpi: def_cleanup / state_safety_neg: repo +0.19 vs crucible +0.26 ✓
- libarchive: def_cleanup / state_safety_neg: repo +0.21 vs crucible +0.26 ✓
- curl: state_bailout_hits / state_safety_neg: repo -0.81 vs crucible +0.20 ✗
- openssl: state_bailout_hits / state_safety_neg: repo +0.07 vs crucible +0.20 ✓
- ndpi: state_bailout_hits / state_safety_neg: repo +0.06 vs crucible +0.20 ✓
- libarchive: state_bailout_hits / state_safety_neg: repo +0.43 vs crucible +0.20 ✓
- harfbuzz: def_cleanup / def_safety: repo -0.15 vs crucible +0.20 ✗
- ndpi: def_cleanup / def_safety: repo +0.72 vs crucible +0.20 ✓
- libarchive: def_cleanup / def_safety: repo +0.11 vs crucible +0.20 ✓
- curl: def_safety / state_bailout_hits: repo +0.14 vs crucible +0.17 ✓
- openssl: def_safety / state_bailout_hits: repo +0.04 vs crucible +0.17 ✓

Runtime 172s · seed 2982.
