# EXPLORATORY — history dynamics by fix class: libarchive

Not registered; labels are seen. Lift = recall@20 − the snapshot's stronger size order; quarterly snapshots, window 180 d.

## (1) Which history predicts which class?

| history ↓ / outcome → | extrinsic (n) | regression (n) | other-fix (n) |
|---|---:|---:|---:|
| prior extrinsic | -0.041 (69) | -0.051 (34) | -0.095 (72) |
| prior regression | +0.042 (69) | -0.264 (34) | -0.060 (72) |
| prior other-fix | -0.022 (69) | -0.134 (34) | -0.109 (72) |
| prior pooled | -0.033 (69) | -0.116 (34) | -0.105 (72) |
| recent same (365 d) | +0.040 (69) | -0.281 (34) | -0.070 (72) |
| all-time same | -0.041 (69) | -0.264 (34) | -0.109 (72) |

## (2) The extrinsic change rate

- extrinsic commits 468 of 2081 fix commits (22.5%) over 202 months
- **dispersion of the monthly extrinsic share vs binomial: 4.88** (1 = steady background; > 1 = bursty)

| year | fix commits | extrinsic | share | extrinsic files touched | of which already membrane (extrinsic before) |
|---|---:|---:|---:|---:|---:|
| 2008 | 62 | 18 | 29.0% | 19 | 0 (0%) |
| 2009 | 264 | 89 | 33.7% | 84 | 13 (15%) |
| 2010 | 109 | 30 | 27.5% | 59 | 20 (34%) |
| 2011 | 232 | 79 | 34.1% | 89 | 45 (51%) |
| 2012 | 200 | 76 | 38.0% | 105 | 63 (60%) |
| 2013 | 56 | 10 | 17.9% | 12 | 10 (83%) |
| 2014 | 71 | 19 | 26.8% | 43 | 22 (51%) |
| 2015 | 41 | 9 | 22.0% | 10 | 10 (100%) |
| 2016 | 99 | 13 | 13.1% | 29 | 19 (66%) |
| 2017 | 68 | 19 | 27.9% | 32 | 21 (66%) |
| 2018 | 48 | 17 | 35.4% | 21 | 19 (90%) |
| 2019 | 92 | 14 | 15.2% | 30 | 19 (63%) |
| 2020 | 55 | 3 | 5.5% | 3 | 1 (33%) |
| 2021 | 34 | 7 | 20.6% | 6 | 4 (67%) |
| 2022 | 32 | 2 | 6.2% | 2 | 2 (100%) |
| 2023 | 42 | 10 | 23.8% | 40 | 13 (32%) |
| 2024 | 116 | 24 | 20.7% | 41 | 32 (78%) |
| 2025 | 97 | 9 | 9.3% | 8 | 8 (100%) |
| 2026 | 363 | 20 | 5.5% | 23 | 17 (74%) |

Burstiest months (extrinsic above expectation from overall fix activity), with sample subjects:

- **2012-02**: 32 extrinsic vs 13.0 expected: Fix build failure with -Wextra -Wunused GCC options since it happend o · Fix build failure with -Wshadow GCC option since it happend on FreeBSD · Fix build failure with -Wmissing-prototypes GCC option since it happen · Fix build failure with -Wcast-qual GCC option since it happend on Free
- **2011-05**: 17 extrinsic vs 5.6 expected: If the character-set of filenames in archives is UTF-8, we should auto · Fix build failure on Mac OS X. · Fix a name of timezone global variable for Borland. · Avoid some warnings on Borland C compiler.
- **2009-07**: 15 extrinsic vs 5.6 expected: Support decimal uid/gid when parsing -R/--owner option. Extend existin · Various testsuite fixes for cygwin-1.7. · Testsuite fixes for cygwin-1.5 * configure.ac: Detect cygwin-1.7. * ta · Merge r195389 from FreeBSD-CURRENT:  Rework the numeric uid/gid suppor
- **2011-12**: 13 extrinsic vs 7.0 expected: FreeBSD libmd support for hash functions. · Get 7zip writer to compile on systems that lack liblzma. I still need  · Avoid a warning on Windows. · Various fixes from FreeBSD.
- **2009-09**: 12 extrinsic vs 6.1 expected: Chuck Wilson's fixes for Cygwin and MinGW builds. · Fix cpio build on MinGW if CreateHardLinkW is unavailable. · Add new assertions to verify atime, birthtime, and mtime, both for exa · Fix Windows time tests.
