# EXPLORATORY — history dynamics by fix class: harfbuzz

Not registered; labels are seen. Lift = recall@20 − the snapshot's stronger size order; quarterly snapshots, window 180 d.

## (1) Which history predicts which class?

| history ↓ / outcome → | extrinsic (n) | regression (n) | other-fix (n) |
|---|---:|---:|---:|
| prior extrinsic | +0.123 (57) | -0.116 (61) | -0.077 (62) |
| prior regression | -0.066 (57) | -0.046 (61) | -0.103 (62) |
| prior other-fix | -0.030 (57) | -0.054 (61) | -0.156 (62) |
| prior pooled | -0.039 (57) | -0.062 (61) | -0.158 (62) |
| recent same (365 d) | +0.105 (57) | +0.010 (61) | -0.122 (62) |
| all-time same | +0.123 (57) | -0.046 (61) | -0.156 (62) |

## (2) The extrinsic change rate

- extrinsic commits 155 of 4297 fix commits (3.6%) over 197 months
- **dispersion of the monthly extrinsic share vs binomial: 1.60** (1 = steady background; > 1 = bursty)

| year | fix commits | extrinsic | share | extrinsic files touched | of which already membrane (extrinsic before) |
|---|---:|---:|---:|---:|---:|
| 2010 | 86 | 1 | 1.2% | 2 | 0 (0%) |
| 2011 | 88 | 7 | 8.0% | 11 | 1 (9%) |
| 2012 | 191 | 8 | 4.2% | 11 | 1 (9%) |
| 2013 | 101 | 1 | 1.0% | 1 | 1 (100%) |
| 2014 | 83 | 10 | 12.0% | 5 | 4 (80%) |
| 2015 | 124 | 6 | 4.8% | 11 | 5 (45%) |
| 2016 | 72 | 3 | 4.2% | 5 | 1 (20%) |
| 2017 | 154 | 8 | 5.2% | 9 | 2 (22%) |
| 2018 | 669 | 37 | 5.5% | 60 | 6 (10%) |
| 2019 | 396 | 23 | 5.8% | 22 | 10 (45%) |
| 2020 | 160 | 4 | 2.5% | 4 | 2 (50%) |
| 2021 | 210 | 4 | 1.9% | 3 | 0 (0%) |
| 2022 | 471 | 16 | 3.4% | 23 | 8 (35%) |
| 2023 | 357 | 6 | 1.7% | 7 | 5 (71%) |
| 2024 | 92 | 4 | 4.3% | 3 | 0 (0%) |
| 2025 | 313 | 7 | 2.2% | 10 | 6 (60%) |
| 2026 | 730 | 10 | 1.4% | 25 | 7 (28%) |

Burstiest months (extrinsic above expectation from overall fix activity), with sample subjects:

- **2014-08**: 6 extrinsic vs 0.9 expected: [wince] Try to fix some stuff on Windows CE · [wince] Two more Windows CE fixes · Fix gcc warning · Fix build on clang after previous commit
- **2018-12**: 6 extrinsic vs 2.2 expected: fix another pesky gcc error · test/api: Fix building on pre-C99 compilers · Fix Solaris Trailing comma in enum warnings (#1490) · Fix Solaris use after free (#1495)
- **2019-04**: 5 extrinsic vs 1.7 expected: Fix MSVC C4138 warning (#1657) · Fix MSVC C4068 warning (#1656) · Fix gcc warning · Fix clang's -Wmain complain (#1678)
- **2018-10**: 9 extrinsic vs 5.7 expected: [circleci] Fix some of warnings from clang-everything bot (#1211) · Fix test-multithread build on FreeBSD (#1217) · [indic] Fix clang everything · test/api/test-subset-*.c: Fix build on pre-C99
- **2018-03**: 4 extrinsic vs 1.0 expected: [test] Fix build with older glib · [dwrite] GCC/mingw/msys2 compatibility (#884) · [dwrite] Use new again and enable the build on msys2 bots (#890) · Fix llvm-gcc-4.2 compile issue and add a macOS bot to test it (#899)
