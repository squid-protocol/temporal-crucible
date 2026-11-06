# EXPLORATORY — history dynamics by fix class: openssl

Not registered; labels are seen. Lift = recall@20 − the snapshot's stronger size order; quarterly snapshots, window 180 d.

## (1) Which history predicts which class?

| history ↓ / outcome → | latent (n) | extrinsic (n) | regression (n) | other-fix (n) |
|---|---:|---:|---:|---:|
| prior latent | +0.106 (75) | -0.108 (109) | +0.007 (50) | -0.056 (110) |
| prior extrinsic | -0.084 (75) | +0.063 (109) | -0.000 (50) | -0.068 (110) |
| prior regression | -0.126 (75) | -0.099 (109) | -0.047 (50) | -0.100 (110) |
| prior other-fix | +0.070 (75) | -0.138 (109) | +0.055 (50) | -0.063 (110) |
| prior pooled | +0.084 (75) | -0.093 (109) | +0.066 (50) | -0.064 (110) |
| recent same (365 d) | -0.152 (75) | +0.017 (109) | -0.014 (50) | -0.020 (110) |
| all-time same | +0.106 (75) | +0.063 (109) | -0.047 (50) | -0.063 (110) |

## (2) The extrinsic change rate

- extrinsic commits 592 of 8996 fix commits (6.6%) over 333 months
- **dispersion of the monthly extrinsic share vs binomial: 2.15** (1 = steady background; > 1 = bursty)

| year | fix commits | extrinsic | share | extrinsic files touched | of which already membrane (extrinsic before) |
|---|---:|---:|---:|---:|---:|
| 1998 | 6 | 1 | 16.7% | 1 | 0 (0%) |
| 1999 | 212 | 25 | 11.8% | 79 | 0 (0%) |
| 2000 | 190 | 25 | 13.2% | 58 | 20 (34%) |
| 2001 | 165 | 15 | 9.1% | 34 | 4 (12%) |
| 2002 | 129 | 10 | 7.8% | 20 | 10 (50%) |
| 2003 | 56 | 3 | 5.4% | 16 | 10 (62%) |
| 2004 | 46 | 8 | 17.4% | 13 | 8 (62%) |
| 2005 | 104 | 20 | 19.2% | 39 | 17 (44%) |
| 2006 | 100 | 7 | 7.0% | 20 | 7 (35%) |
| 2007 | 64 | 5 | 7.8% | 10 | 1 (10%) |
| 2008 | 97 | 14 | 14.4% | 25 | 10 (40%) |
| 2009 | 69 | 10 | 14.5% | 9 | 1 (11%) |
| 2010 | 101 | 12 | 11.9% | 22 | 8 (36%) |
| 2011 | 130 | 15 | 11.5% | 23 | 7 (30%) |
| 2012 | 124 | 17 | 13.7% | 18 | 9 (50%) |
| 2013 | 80 | 12 | 15.0% | 17 | 9 (53%) |
| 2014 | 186 | 11 | 5.9% | 18 | 13 (72%) |
| 2015 | 400 | 33 | 8.2% | 43 | 17 (40%) |
| 2016 | 725 | 46 | 6.3% | 105 | 43 (41%) |
| 2017 | 516 | 15 | 2.9% | 44 | 13 (30%) |
| 2018 | 494 | 31 | 6.3% | 37 | 14 (38%) |
| 2019 | 425 | 38 | 8.9% | 52 | 28 (54%) |
| 2020 | 653 | 24 | 3.7% | 47 | 23 (49%) |
| 2021 | 932 | 34 | 3.6% | 36 | 15 (42%) |
| 2022 | 508 | 28 | 5.5% | 39 | 17 (44%) |
| 2023 | 549 | 36 | 6.6% | 51 | 19 (37%) |
| 2024 | 446 | 33 | 7.4% | 67 | 30 (45%) |
| 2025 | 555 | 32 | 5.8% | 132 | 42 (32%) |
| 2026 | 934 | 32 | 3.4% | 61 | 32 (52%) |

Burstiest months (extrinsic above expectation from overall fix activity), with sample subjects:

- **2022-09**: 11 extrinsic vs 2.8 expected: provider: cipher: aes: add riscv32 zkn (zbkb) support · aes_platform: add riscv32 zkn asm support · test/pkcs12_api_test.c: fix failure on MinGW · Fix build failure on freebsd due to missing data declaration
- **2016-04**: 13 extrinsic vs 6.0 expected: Fix warnings exposed by clang-3.8 · PPC assebmly pack: initial POWER9 support tidbits. · Add Haiku support. · evp/aes_aes.c: engage Fujitsu SPARC64 X AES support.
- **1999-05**: 8 extrinsic vs 2.0 expected: Update HPUX config, work around HPUX library incompatibility. · Support additional Win32 compilers. · Various Win32 fixes. Win95 doesn't support MoveFileEx() (which was use · Add new -out option to asn1parse to allow the parsed data to be output
- **2024-01**: 8 extrinsic vs 2.8 expected: riscv: Fix mispelling of extension test macro · QUIC SRTM: Fixes for clang · Fix partial block encryption in cfb and ofb for s390x (legacy) · Fix partial block encryption in cfb and ofb for s390x
- **2015-09**: 8 extrinsic vs 3.2 expected: RT3984: Fix clang compiler warning on Mac OS X where %ld is used for u · Win32 build fix: include internal/numbers.h to get UIN32_MAX · fix build breakage on windows · RT3993: Fix error found by VS2008
