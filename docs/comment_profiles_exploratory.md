# Comment profiles of whole files and whole systems (EXPLORATORY)

**Status: exploratory, outcome-blind.** No fix, CVE or other outcome was read, so a later registration can use these profiles. Script: `tools/comment_profiles.py`. C/C++ files only; paths under tests/, docs/, fuzz/, scripts/, examples/ (at any depth) excluded. Comment lines come from the engine's positional comment stream (CMT-G: ~99% precise). **Body** comments exclude the top-of-file banner (comments before the first code line, usually the license).

- repos curl, openssl, ndpi, harfbuzz, libarchive, libgit2, libxml2, postgres, redis; quarterly snapshots 748; file versions 437,978; distinct blobs 165,421

Measures: **density** = body comment lines ÷ code lines; **danger share** = share of body comment lines with a DC-lexicon word; **debt** = TODO/FIXME/HACK/XXX lines per 1,000 code lines; **dead** = engine `dead_code` matches per 1,000 code lines; **header coverage** = share of functions with a comment block directly above.

## 1. Each system over time (whole repo, last snapshot of every 3rd year)

**curl**

| year | files | code lines | density | banner lines / file | danger share | debt / kloc | dead / kloc | header coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1999 | 66 | 10,771 | 0.308 | 19.6 | 0.5% | 0.28 | 0.37 | 26% |
| 2002 | 103 | 21,316 | 0.379 | 11.7 | 1.5% | 0.33 | 0.56 | 37% |
| 2005 | 193 | 39,013 | 0.359 | 11.8 | 1.7% | 0.36 | 0.31 | 46% |
| 2008 | 234 | 56,038 | 0.368 | 11.6 | 1.6% | 0.71 | 0.23 | 46% |
| 2011 | 306 | 64,478 | 0.396 | 11.0 | 1.4% | 0.96 | 0.22 | 49% |
| 2014 | 337 | 82,282 | 0.362 | 11.1 | 1.6% | 0.91 | 0.24 | 48% |
| 2017 | 360 | 95,549 | 0.342 | 11.5 | 1.7% | 0.69 | 0.22 | 47% |
| 2020 | 412 | 113,104 | 0.310 | 11.3 | 1.8% | 0.15 | 0.19 | 45% |
| 2023 | 440 | 129,006 | 0.286 | 12.2 | 1.9% | 0.30 | 0.15 | 39% |
| 2025 | 472 | 142,093 | 0.258 | 11.9 | 2.7% | 0.05 | 0.08 | 30% |

**openssl**

| year | files | code lines | density | banner lines / file | danger share | debt / kloc | dead / kloc | header coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1998 | 617 | 115,379 | 0.066 | 51.0 | 1.3% | 0.03 | 1.81 | 9% |
| 2001 | 777 | 155,556 | 0.110 | 53.8 | 1.6% | 0.58 | 0.98 | 15% |
| 2004 | 902 | 196,566 | 0.114 | 54.6 | 1.7% | 0.55 | 0.83 | 16% |
| 2007 | 1,020 | 238,782 | 0.117 | 54.3 | 1.8% | 0.48 | 0.77 | 17% |
| 2010 | 1,072 | 261,705 | 0.115 | 53.5 | 1.8% | 0.46 | 0.73 | 17% |
| 2013 | 1,177 | 312,366 | 0.112 | 53.0 | 1.8% | 0.38 | 0.58 | 18% |
| 2016 | 958 | 262,985 | 0.141 | 10.3 | 2.2% | 0.79 | 0.16 | 19% |
| 2019 | 1,328 | 338,523 | 0.151 | 9.3 | 2.2% | 0.88 | 0.14 | 19% |
| 2022 | 1,668 | 422,790 | 0.159 | 10.0 | 2.5% | 0.26 | 0.09 | 18% |
| 2025 | 1,835 | 517,673 | 0.165 | 9.9 | 2.7% | 0.20 | 0.08 | 20% |
| 2026 | 1,852 | 523,492 | 0.168 | 9.8 | 2.6% | 0.23 | 0.08 | 20% |

**ndpi**

| year | files | code lines | density | banner lines / file | danger share | debt / kloc | dead / kloc | header coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2015 | 165 | 23,834 | 0.140 | 21.6 | 1.2% | 0.88 | 8.18 | 22% |
| 2018 | 187 | 27,049 | 0.170 | 20.8 | 1.5% | 1.04 | 2.59 | 29% |
| 2021 | 230 | 66,857 | 0.200 | 21.2 | 2.5% | 1.29 | 1.79 | 51% |
| 2024 | 364 | 110,067 | 0.233 | 20.9 | 2.9% | 1.30 | 1.24 | 48% |
| 2025 | 378 | 114,982 | 0.235 | 20.8 | 2.9% | 1.42 | 1.14 | 49% |

**harfbuzz**

| year | files | code lines | density | banner lines / file | danger share | debt / kloc | dead / kloc | header coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2010 | 51 | 9,532 | 0.285 | 25.5 | 1.0% | 2.62 | 0.21 | 5% |
| 2013 | 121 | 32,245 | 0.256 | 25.2 | 0.9% | 1.71 | 0.09 | 16% |
| 2016 | 138 | 39,997 | 0.249 | 25.2 | 1.3% | 2.00 | 0.18 | 17% |
| 2019 | 269 | 75,119 | 0.223 | 24.3 | 1.2% | 1.57 | 0.20 | 13% |
| 2022 | 399 | 102,913 | 0.230 | 19.8 | 1.1% | 1.37 | 0.11 | 13% |
| 2025 | 459 | 125,984 | 0.214 | 19.7 | 1.1% | 1.21 | 0.13 | 12% |
| 2026 | 564 | 151,061 | 0.194 | 19.0 | 1.1% | 1.01 | 0.09 | 13% |

**libarchive**

| year | files | code lines | density | banner lines / file | danger share | debt / kloc | dead / kloc | header coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2008 | 96 | 25,075 | 0.279 | 26.5 | 2.3% | 5.70 | 0.20 | 40% |
| 2011 | 145 | 74,051 | 0.206 | 25.9 | 2.3% | 3.05 | 0.27 | 30% |
| 2014 | 190 | 90,166 | 0.200 | 25.2 | 2.2% | 2.52 | 0.22 | 27% |
| 2017 | 205 | 98,261 | 0.197 | 25.2 | 2.2% | 2.26 | 0.21 | 29% |
| 2020 | 216 | 106,101 | 0.196 | 24.7 | 2.2% | 2.05 | 0.24 | 29% |
| 2023 | 224 | 110,275 | 0.195 | 24.2 | 2.2% | 2.00 | 0.23 | 29% |
| 2026 | 252 | 116,653 | 0.192 | 20.0 | 2.3% | 2.00 | 0.21 | 28% |

**libgit2**

| year | files | code lines | density | banner lines / file | danger share | debt / kloc | dead / kloc | header coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2008 | 26 | 1,221 | 0.377 | 5.0 | 2.6% | 2.46 | 0.00 | 14% |
| 2011 | 205 | 29,576 | 0.294 | 6.0 | 2.5% | 1.05 | 0.27 | 16% |
| 2014 | 362 | 84,302 | 0.283 | 7.7 | 2.1% | 0.83 | 0.08 | 13% |
| 2017 | 415 | 100,509 | 0.267 | 7.7 | 2.2% | 0.70 | 0.07 | 12% |
| 2020 | 506 | 138,574 | 0.279 | 8.6 | 1.9% | 0.48 | 0.05 | 11% |
| 2023 | 568 | 162,205 | 0.259 | 8.7 | 1.9% | 0.47 | 0.04 | 10% |
| 2026 | 653 | 190,454 | 0.262 | 8.5 | 2.1% | 0.42 | 0.04 | 11% |

**libxml2**

| year | files | code lines | density | banner lines / file | danger share | debt / kloc | dead / kloc | header coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1999 | 51 | 25,883 | 0.403 | 8.0 | 1.3% | 1.97 | 0.15 | 94% |
| 2002 | 103 | 87,561 | 0.350 | 9.7 | 1.6% | 1.40 | 0.35 | 83% |
| 2005 | 135 | 204,183 | 0.264 | 10.4 | 2.2% | 2.22 | 0.32 | 54% |
| 2008 | 139 | 213,067 | 0.268 | 10.3 | 2.2% | 2.43 | 0.31 | 54% |
| 2011 | 138 | 215,003 | 0.268 | 10.3 | 2.2% | 2.41 | 0.31 | 54% |
| 2014 | 159 | 228,277 | 0.263 | 12.1 | 2.2% | 2.27 | 0.28 | 53% |
| 2017 | 162 | 228,843 | 0.263 | 12.2 | 2.2% | 2.25 | 0.28 | 53% |
| 2020 | 161 | 228,638 | 0.263 | 12.2 | 2.3% | 2.37 | 0.28 | 53% |
| 2023 | 147 | 195,622 | 0.293 | 10.9 | 2.4% | 2.84 | 0.30 | 55% |
| 2026 | 124 | 133,295 | 0.346 | 9.6 | 2.8% | 3.75 | 0.41 | 77% |

**postgres**

| year | files | code lines | density | banner lines / file | danger share | debt / kloc | dead / kloc | header coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1996 | 646 | 106,462 | 0.450 | 17.3 | 2.3% | 4.53 | 1.16 | 66% |
| 1999 | 889 | 184,193 | 0.381 | 15.2 | 2.0% | 2.40 | 0.53 | 62% |
| 2002 | 990 | 257,639 | 0.372 | 16.6 | 2.4% | 1.47 | 0.28 | 61% |
| 2005 | 1,178 | 371,383 | 0.360 | 16.3 | 2.7% | 1.13 | 0.19 | 61% |
| 2008 | 1,333 | 477,105 | 0.368 | 16.5 | 2.6% | 1.01 | 0.21 | 62% |
| 2011 | 1,522 | 567,424 | 0.387 | 16.3 | 2.7% | 0.93 | 0.18 | 64% |
| 2014 | 1,667 | 652,967 | 0.401 | 16.8 | 2.8% | 0.94 | 0.16 | 66% |
| 2017 | 1,892 | 775,234 | 0.412 | 17.1 | 2.7% | 0.89 | 0.14 | 69% |
| 2020 | 2,040 | 874,887 | 0.425 | 17.1 | 2.7% | 0.83 | 0.13 | 69% |
| 2023 | 2,214 | 945,122 | 0.429 | 17.2 | 2.7% | 0.86 | 0.13 | 72% |
| 2026 | 2,400 | 1,069,690 | 0.445 | 17.5 | 2.6% | 0.78 | 0.07 | 73% |

**redis**

| year | files | code lines | density | banner lines / file | danger share | debt / kloc | dead / kloc | header coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2010 | 81 | 19,601 | 0.185 | 16.6 | 1.4% | 0.56 | 3.27 | 35% |
| 2013 | 227 | 63,656 | 0.232 | 16.3 | 1.7% | 0.05 | 1.10 | 33% |
| 2016 | 269 | 88,239 | 0.258 | 17.5 | 2.0% | 0.07 | 0.79 | 41% |
| 2019 | 367 | 118,664 | 0.270 | 15.7 | 2.0% | 0.10 | 0.64 | 43% |
| 2022 | 412 | 157,150 | 0.286 | 16.1 | 2.2% | 0.12 | 0.46 | 47% |
| 2025 | 523 | 199,589 | 0.310 | 11.0 | 2.4% | 0.18 | 0.85 | 47% |
| 2026 | 562 | 222,326 | 0.314 | 11.0 | 2.5% | 0.22 | 0.76 | 49% |

## 2. Each system's voice at its latest snapshot (per-file medians [IQR], files with ≥ 50 code lines)

| repo | files | density | danger_share | debt_kloc | dead_kloc | header_cov |
|---|---:|---|---|---|---|---|
| curl | 273 | 0.211 [0.12, 0.438] | 0.0211 [0, 0.0462] | 0 [0, 0] | 0 [0, 0] | 0.299 [0.0679, 0.634] |
| openssl | 1,274 | 0.0986 [0.0357, 0.219] | 0 [0, 0.0309] | 0 [0, 0] | 0 [0, 0] | 0.0833 [0, 0.308] |
| ndpi | 202 | 0.122 [0.0461, 0.228] | 0 [0, 0.0145] | 0 [0, 0] | 0 [0, 0] | 0.167 [0, 0.75] |
| harfbuzz | 424 | 0.0825 [0.0284, 0.21] | 0 [0, 0.00431] | 0 [0, 0] | 0 [0, 0] | 0 [0, 0.0833] |
| libarchive | 189 | 0.15 [0.0785, 0.23] | 0 [0, 0.0245] | 0 [0, 1.67] | 0 [0, 0] | 0.24 [0, 0.418] |
| libgit2 | 395 | 0.117 [0.0327, 0.382] | 0.00369 [0, 0.0272] | 0 [0, 0] | 0 [0, 0] | 0.0339 [0, 0.213] |
| libxml2 | 98 | 0.332 [0.195, 0.526] | 0.00815 [0, 0.034] | 0 [0, 1.34] | 0 [0, 0] | 0.889 [0.476, 0.974] |
| postgres | 1,616 | 0.414 [0.236, 0.627] | 0.0192 [0, 0.0338] | 0 [0, 0] | 0 [0, 0] | 0.889 [0.444, 1] |
| redis | 386 | 0.236 [0.129, 0.365] | 0.0151 [0, 0.0332] | 0 [0, 0] | 0 [0, 0] | 0.256 [0.0526, 0.669] |

Most common danger words in body comments are not listed: the profile counts lines, not words.

## 3. How much does each measure depend on file size? (Spearman ρ with log code lines, latest snapshot)

| repo | density | danger_share | debt_kloc | dead_kloc | header_cov |
|---|---:|---:|---:|---:|---:|
| curl | -0.48 | +0.24 | +0.04 | +0.12 | -0.14 |
| openssl | +0.10 | +0.35 | +0.24 | +0.12 | +0.21 |
| ndpi | +0.21 | +0.40 | +0.27 | +0.41 | +0.38 |
| harfbuzz | +0.07 | +0.29 | +0.24 | +0.07 | +0.33 |
| libarchive | +0.21 | +0.49 | +0.45 | +0.26 | +0.33 |
| libgit2 | -0.19 | +0.25 | +0.35 | +0.09 | +0.12 |
| libxml2 | -0.07 | +0.27 | +0.58 | +0.57 | -0.07 |
| postgres | -0.06 | +0.18 | +0.37 | +0.10 | -0.04 |
| redis | +0.03 | +0.30 | +0.33 | +0.15 | +0.32 |

## 4. File cultures (k-means on the five rates, log-scaled and standardized; files with ≥ 50 code lines and ≥ 1 function at each repo's latest snapshot; n = 4,099)

Silhouette by k: k=2 0.35, k=3 0.37, k=4 0.40, k=5 0.43, k=6 0.35. Best k = **5** (silhouette 0.43; above ~0.5 is clear structure, ~0.25 weak).

| culture | files | median code lines | density | danger_share | debt_kloc | dead_kloc | header_cov (medians) | curl | openssl | ndpi | harfbuzz | libarchive | libgit2 | libxml2 | postgres | redis |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| C1 | 1,602 | 297 | 0.377 | 0.0181 | 0 | 0 | 0.857 | 47% | 23% | 23% | 13% | 20% | 22% | 40% | 64% | 47% |
| C2 | 406 | 514 | 0.34 | 0.0251 | 3.64 | 0 | 0.714 | 0% | 3% | 15% | 12% | 28% | 8% | 37% | 15% | 2% |
| C3 | 94 | 373 | 0.192 | 0.0126 | 0 | 3.42 | 0.4 | 1% | 1% | 15% | 2% | 5% | 1% | 4% | 1% | 4% |
| C4 | 380 | 213 | 0.12 | 0.0909 | 0 | 0 | 0.106 | 17% | 14% | 6% | 8% | 7% | 10% | 5% | 5% | 11% |
| C5 | 1,617 | 202 | 0.0598 | 0 | 0 | 0 | 0 | 34% | 60% | 42% | 65% | 41% | 59% | 14% | 15% | 36% |

Repo columns: the share of that repo's files in each culture.

## 5. Do files keep their culture? (same path ~4 years before the latest snapshot, nearest centroid)

- same culture then and now: curl 72% of 140, openssl 91% of 852, ndpi 74% of 80, harfbuzz 88% of 176, libarchive 96% of 142, libgit2 96% of 211, libxml2 81% of 53, postgres 89% of 1,193, redis 92% of 217
- for scale, the share in each repo's largest culture today (a no-information baseline): curl 47%, openssl 60%, ndpi 42%, harfbuzz 65%, libarchive 41%, libgit2 59%, libxml2 40%, postgres 64%, redis 47%

## 6. Comment neglect: files whose code grew ≥ 20% in a year while their body comments did not grow

| repo | file-years with ≥ 20% code growth | of those, comments flat or shrinking |
|---|---:|---:|
| curl | 320 | 10% |
| openssl | 920 | 29% |
| ndpi | 70 | 9% |
| harfbuzz | 223 | 20% |
| libarchive | 82 | 17% |
| libgit2 | 203 | 23% |
| libxml2 | 125 | 18% |
| postgres | 1,566 | 8% |
| redis | 245 | 8% |

Runtime 174s · seed 2982.

## Reading (hand-written; exploratory, no outcome was read)

- **Each system has its own voice, and it is large.**
  - At the median file, postgres writes about 4 comment lines per 10 code lines and documents 89% of functions with
    a header comment.
  - harfbuzz, OpenSSL and libgit2 write 1 or fewer and document under 10%.
  - These gaps are bigger than any within-repo comment difference this program has tested.
- **Files fall into five commenting cultures, and they are sticky.**
  - The five: documented (C1), documented with debt (C2), with commented-out code (C3), warning-heavy with few
    headers (C4, danger share 9%), and silent (C5).
  - Cluster structure is moderate (silhouette 0.43). It partly reflects which rare marker a file has at all.
  - Files keep their culture over four years 72–96% of the time, against a 40–65% largest-culture baseline.
- **Danger wording grew over time in most systems.** curl 0.5% → 2.7%, OpenSSL 1.3% → 2.7%, nDPI 1.2% → 2.9%, redis
  1.4% → 2.5%, libxml2 1.3% → 2.8%. harfbuzz (~1.1%), libarchive (~2.2%) and libgit2 stayed flat.
  - This may be real (projects learning to warn) or vocabulary drift ("security", "validate", "overflow" becoming
    common words). Any study using danger share across eras must handle that.
- **Commented-out code declined almost everywhere.** curl's TODO/FIXME debt fell to near zero, which looks like
  deliberate clean-ups.
- **Comment neglect varies by system.** In OpenSSL, 29% of fast-growing files gained no comments; in postgres and
  redis, 8%.
- **The size trap is real for some rates.** Danger share and debt rise with file size in every repo
  (ρ +0.18 to +0.58). Density barely depends on size. A predictive study should use density and header coverage
  freely, but must stratify the others by size.
- **Sanity check.** OpenSSL's banner drops from ~54 to ~10 lines per file in 2016, its license-header change. The
  banner separation works.
- **What this is not:** no outcome was read, so nothing here says whether any culture is riskier. That is the
  registered follow-up (file profile → next-year fixes, beyond size and history). Nine systems are too few for
  cross-system inference, so the system-level comparisons are descriptive.

Rows (one per file version, 437,978) are in `scratch_cp/comment_profiles.json.gz` in the melek run worktree; they
are not committed.
