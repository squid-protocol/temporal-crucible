# LIB-H1..H3 — library-coupling surface (SCORED)

- evaluable (repo, dependency) units (≥ 20 snapshots with D-work): **21** — curl/openssl, curl/zlib, curl/libssh2, curl/nghttp2, curl/c-ares, curl/wolfssl, curl/mbedtls, curl/gnutls, libarchive/openssl, libarchive/zlib, libarchive/bzip2, libarchive/xz, libarchive/zstd, ndpi/libpcap, harfbuzz/freetype, harfbuzz/icu, harfbuzz/coretext, harfbuzz/directwrite, harfbuzz/uniscribe, harfbuzz/graphite, harfbuzz/glib

| claim | what | units | mean | lo (α=0.0033) | 90% CI | verdict |
|---|---|---:|---:|---:|---|---|
| **LIB-H1** | coupling to D − stronger size order (recall@20) | 21 | +0.397 | +0.354 | [+0.370, +0.423] | **SUPPORTED** |
| **LIB-H2** | coupling to D − other libraries' coupling (placebo) | 21 | +0.462 | +0.422 | [+0.438, +0.486] | **SUPPORTED** |
| **LIB-H3** | coupling to D − file-name lookup | 21 | +0.220 | +0.184 | [+0.197, +0.241] | **SUPPORTED** |

## Per unit (descriptive)

| repo | dependency | D-work commits | scored snapshots | recall@20 coupling | stronger size | H1 | H2 | H3 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| curl | openssl | 653 | 99 | 0.622 | 0.313 | +0.308 | +0.461 | +0.359 |
| curl | zlib | 17 | 24 | 0.815 | 0.107 | +0.708 | +0.675 | +0.708 |
| curl | libssh2 | 141 | 56 | 0.752 | 0.650 | +0.102 | +0.689 | +0.485 |
| curl | nghttp2 | 23 | 23 | 0.768 | 0.304 | +0.464 | +0.616 | +0.616 |
| curl | c-ares | 158 | 77 | 0.691 | 0.215 | +0.476 | +0.532 | +0.056 |
| curl | wolfssl | 140 | 43 | 0.607 | 0.155 | +0.453 | +0.375 | +0.199 |
| curl | mbedtls | 146 | 42 | 0.687 | 0.171 | +0.515 | +0.479 | +0.148 |
| curl | gnutls | 127 | 66 | 0.720 | 0.095 | +0.625 | +0.576 | +0.651 |
| curl | libidn2 | 3 | 4 | — | — | not evaluable | | |
| libarchive | openssl | 17 | 20 | 0.900 | 0.450 | +0.450 | +0.485 | +0.450 |
| libarchive | zlib | 67 | 32 | 0.279 | 0.530 | -0.250 | -0.168 | -0.219 |
| libarchive | bzip2 | 48 | 24 | 0.516 | 0.350 | +0.166 | +0.233 | +0.108 |
| libarchive | xz | 101 | 39 | 0.610 | 0.359 | +0.251 | +0.402 | +0.240 |
| libarchive | zstd | 50 | 26 | 0.511 | 0.274 | +0.237 | +0.346 | -0.087 |
| libarchive | lz4 | 31 | 11 | — | — | not evaluable | | |
| libarchive | libxml2 | 5 | 7 | — | — | not evaluable | | |
| libarchive | expat | 1 | 2 | — | — | not evaluable | | |
| libarchive | mbedtls | 2 | 3 | — | — | not evaluable | | |
| libarchive | nettle | 7 | 7 | — | — | not evaluable | | |
| ndpi | libgcrypt | 9 | 10 | — | — | not evaluable | | |
| ndpi | json-c | 7 | 5 | — | — | not evaluable | | |
| ndpi | libpcap | 28 | 21 | 0.363 | 0.343 | +0.020 | +0.168 | +0.151 |
| ndpi | maxminddb | 9 | 7 | — | — | not evaluable | | |
| harfbuzz | freetype | 40 | 23 | 0.703 | 0.101 | +0.601 | +0.572 | +0.601 |
| harfbuzz | icu | 44 | 30 | 0.755 | 0.244 | +0.511 | +0.526 | -0.001 |
| harfbuzz | coretext | 193 | 49 | 0.826 | 0.191 | +0.634 | +0.642 | +0.000 |
| harfbuzz | directwrite | 103 | 29 | 0.854 | 0.266 | +0.588 | +0.575 | +0.000 |
| harfbuzz | uniscribe | 86 | 32 | 0.637 | 0.245 | +0.393 | +0.410 | +0.000 |
| harfbuzz | graphite | 75 | 39 | 0.970 | 0.256 | +0.714 | +0.729 | +0.000 |
| harfbuzz | glib | 43 | 32 | 0.789 | 0.415 | +0.373 | +0.373 | +0.148 |

OpenSSL 3 migration (OpenSSL-work commits 2020-06 → 2022-12; share of each commit's touched files that fall in the top-20%-of-lines set ranked by OpenSSL coupling at the preceding quarterly snapshot):

- curl: 76 commits, mean share 93%
- libarchive: 2 commits, mean share 100%

Runtime 30s · within-unit snapshot bootstrap, 5000 rounds, seed 2982.
