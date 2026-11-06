# EXPLORATORY — history dynamics by fix class: curl

Not registered; labels are seen. Lift = recall@20 − the snapshot's stronger size order; quarterly snapshots, window 180 d.

## (1) Which history predicts which class?

| history ↓ / outcome → | latent (n) | extrinsic (n) | regression (n) | other-fix (n) |
|---|---:|---:|---:|---:|
| prior latent | +0.060 (63) | -0.112 (105) | -0.060 (73) | -0.110 (105) |
| prior extrinsic | -0.044 (63) | -0.050 (105) | -0.043 (73) | -0.181 (105) |
| prior regression | -0.005 (63) | -0.080 (105) | -0.053 (73) | -0.119 (105) |
| prior other-fix | +0.004 (63) | -0.162 (105) | -0.032 (73) | -0.213 (105) |
| prior pooled | -0.010 (63) | -0.159 (105) | -0.031 (73) | -0.214 (105) |
| recent same (365 d) | -0.028 (63) | -0.009 (105) | -0.044 (73) | -0.200 (105) |
| all-time same | +0.060 (63) | -0.050 (105) | -0.053 (73) | -0.213 (105) |

## (2) The extrinsic change rate

- extrinsic commits 681 of 8352 fix commits (8.2%) over 320 months
- **dispersion of the monthly extrinsic share vs binomial: 2.22** (1 = steady background; > 1 = bursty)

| year | fix commits | extrinsic | share | extrinsic files touched | of which already membrane (extrinsic before) |
|---|---:|---:|---:|---:|---:|
| 2000 | 51 | 4 | 7.8% | 6 | 0 (0%) |
| 2001 | 104 | 15 | 14.4% | 16 | 5 (31%) |
| 2002 | 103 | 9 | 8.7% | 7 | 4 (57%) |
| 2003 | 140 | 21 | 15.0% | 21 | 8 (38%) |
| 2004 | 239 | 54 | 22.6% | 40 | 17 (42%) |
| 2005 | 153 | 34 | 22.2% | 45 | 18 (40%) |
| 2006 | 172 | 12 | 7.0% | 21 | 16 (76%) |
| 2007 | 324 | 33 | 10.2% | 47 | 29 (62%) |
| 2008 | 295 | 31 | 10.5% | 56 | 37 (66%) |
| 2009 | 239 | 33 | 13.8% | 43 | 29 (67%) |
| 2010 | 281 | 14 | 5.0% | 19 | 13 (68%) |
| 2011 | 293 | 13 | 4.4% | 50 | 27 (54%) |
| 2012 | 272 | 14 | 5.1% | 20 | 7 (35%) |
| 2013 | 363 | 20 | 5.5% | 35 | 19 (54%) |
| 2014 | 408 | 24 | 5.9% | 20 | 14 (70%) |
| 2015 | 275 | 26 | 9.5% | 35 | 18 (51%) |
| 2016 | 279 | 17 | 6.1% | 24 | 15 (62%) |
| 2017 | 428 | 32 | 7.5% | 41 | 22 (54%) |
| 2018 | 346 | 30 | 8.7% | 45 | 24 (53%) |
| 2019 | 380 | 17 | 4.5% | 21 | 16 (76%) |
| 2020 | 339 | 19 | 5.6% | 28 | 23 (82%) |
| 2021 | 344 | 17 | 4.9% | 21 | 15 (71%) |
| 2022 | 371 | 23 | 6.2% | 26 | 16 (62%) |
| 2023 | 484 | 21 | 4.3% | 48 | 29 (60%) |
| 2024 | 456 | 42 | 9.2% | 94 | 46 (49%) |
| 2025 | 690 | 54 | 7.8% | 120 | 68 (57%) |
| 2026 | 523 | 52 | 9.9% | 124 | 71 (57%) |

Burstiest months (extrinsic above expectation from overall fix activity), with sample subjects:

- **2026-02**: 17 extrinsic vs 4.1 expected: windows: tidy up `wincrypt.h` / BoringSSL/AWS-LC coexist workaround · clang-tidy: fixes and improvements · clang-tidy: enable and fix `readability-uppercase-literal-suffix` · clang-tidy: check `readability-redundant-preprocessor`, fix fallouts
- **2004-02**: 12 extrinsic vs 2.8 expected: fixed the win32 function to use the correct proto, as pointed out by G · use the timeout options when waiting for the server to connect when us · Gisle Vanem fixed a windows compiler warning · The MIPSPro compiler complains on constructs such as "(void)foo;" so w
- **2009-04**: 10 extrinsic vs 2.0 expected: Added missing tests in CMake, added Makefile.inc for tests (+ use in C · fix compiler warning: implicit conversion shortens 64-bit value into a · fix compiler warning: implicit conversion shortens 64-bit value into a · attempt to workaround icc 9.1 optimizer induced problem
- **2004-03**: 10 extrinsic vs 2.9 expected: Use the z-option to printf %d for size_t printf. z is supported by the · attempted typecase to silence the MIPSpro warning: · Major rewrite of the test HTTP server to allow more fancy features to  · Andr�s Garc�a-fix to make it build with mingw
- **2005-11**: 9 extrinsic vs 1.9 expected: Dmitry Bartsevich discovered some issues in compatibilty of SSPI-enabl · MSVC fix for 'socklen_t'. Replace <winsock.h> with <winsock2.h> + <ws2 · Use config-win32.h on Windows. Fixes for djgpp. · Support big-endian machines.
