# LIB-R and LIB-E (SCORED)

## LIB-R — LIB recipe unchanged on PostgreSQL + libgit2

- evaluable (repo, dependency) units (≥ 20 snapshots with D-work): **14** — postgres/openssl, postgres/icu, postgres/libxml2, postgres/gssapi, postgres/ldap, postgres/readline, postgres/llvm, postgres/perl, postgres/python, postgres/tcl, libgit2/openssl, libgit2/zlib, libgit2/winhttp, libgit2/ntlm

| claim | what | units | mean | lo (α=0.0033) | 90% CI | verdict |
|---|---|---:|---:|---:|---|---|
| **LIBR-H1** | coupling to D − stronger size order (recall@20) | 14 | +0.437 | +0.390 | [+0.410, +0.464] | **SUPPORTED** |
| **LIBR-H2** | coupling to D − other libraries' coupling (placebo) | 14 | +0.487 | +0.443 | [+0.461, +0.513] | **SUPPORTED** |
| **LIBR-H3** | coupling to D − file-name lookup | 14 | +0.182 | +0.149 | [+0.161, +0.201] | **SUPPORTED** |

### Per unit (descriptive)

| repo | dependency | D-work commits | scored snapshots | recall@20 coupling | stronger size | H1 | H2 | H3 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| postgres | openssl | 96 | 70 | 0.835 | 0.298 | +0.537 | +0.537 | +0.265 |
| postgres | zlib | 11 | 18 | — | — | not evaluable | | |
| postgres | icu | 54 | 27 | 0.756 | 0.308 | +0.449 | +0.520 | +0.401 |
| postgres | libxml2 | 27 | 27 | 0.907 | 0.296 | +0.611 | +0.636 | +0.636 |
| postgres | lz4 | 21 | 17 | — | — | not evaluable | | |
| postgres | zstd | 13 | 12 | — | — | not evaluable | | |
| postgres | gssapi | 91 | 71 | 0.551 | 0.216 | +0.334 | +0.372 | +0.268 |
| postgres | ldap | 24 | 26 | 0.833 | 0.346 | +0.487 | +0.635 | +0.679 |
| postgres | readline | 38 | 46 | 0.746 | 0.667 | +0.080 | +0.250 | +0.254 |
| postgres | llvm | 35 | 25 | 0.933 | 0.364 | +0.569 | +0.569 | +0.000 |
| postgres | perl | 187 | 87 | 0.755 | 0.402 | +0.353 | +0.366 | +0.000 |
| postgres | python | 218 | 97 | 0.898 | 0.499 | +0.400 | +0.511 | +0.000 |
| postgres | tcl | 94 | 68 | 0.760 | 0.173 | +0.587 | +0.604 | +0.016 |
| libgit2 | openssl | 72 | 41 | 0.917 | 0.388 | +0.529 | +0.537 | +0.051 |
| libgit2 | mbedtls | 22 | 10 | — | — | not evaluable | | |
| libgit2 | zlib | 27 | 21 | 0.657 | 0.416 | +0.240 | +0.248 | -0.017 |
| libgit2 | libssh2 | 13 | 13 | — | — | not evaluable | | |
| libgit2 | pcre | 12 | 8 | — | — | not evaluable | | |
| libgit2 | http-parser | 16 | 12 | — | — | not evaluable | | |
| libgit2 | winhttp | 53 | 35 | 0.762 | 0.124 | +0.638 | +0.721 | +0.000 |
| libgit2 | securetransport | 9 | 6 | — | — | not evaluable | | |
| libgit2 | ntlm | 23 | 23 | 0.746 | 0.447 | +0.298 | +0.307 | -0.012 |
| libgit2 | iconv | 9 | 10 | — | — | not evaluable | | |

OpenSSL 3 migration (OpenSSL-work commits 2020-06 → 2022-12; share of each commit's touched files that fall in the top-20%-of-lines set ranked by OpenSSL coupling at the preceding quarterly snapshot):

- none

Runtime 57s · within-unit snapshot bootstrap, 5000 rounds, seed 2982.

## LIB-E — engine call-graph coupling (original LIB repos)

- evaluable units (≥ 20 engine snapshots with D-work): **21** — curl/openssl, curl/zlib, curl/libssh2, curl/nghttp2, curl/c-ares, curl/wolfssl, curl/mbedtls, curl/gnutls, libarchive/openssl, libarchive/zlib, libarchive/bzip2, libarchive/xz, libarchive/zstd, ndpi/libpcap, harfbuzz/freetype, harfbuzz/icu, harfbuzz/coretext, harfbuzz/directwrite, harfbuzz/uniscribe, harfbuzz/graphite, harfbuzz/glib

| claim | units | mean | lo (α 0.01/2) | verdict |
|---|---:|---:|---:|---|
| **LIBE-H1 engine coupling − stronger size order** | 21 | +0.335 | +0.293 | **SUPPORTED** |
| **LIBE-H2 engine − regex (non-inferiority margin −0.05)** | 21 | -0.062 | -0.079 | **not supported** |

| repo | D | snapshots | recall@20 engine | regex | stronger size |
|---|---|---:|---:|---:|---:|
| curl | openssl | 99 | 0.542 | 0.622 | 0.313 |
| curl | zlib | 24 | 0.722 | 0.815 | 0.107 |
| curl | libssh2 | 56 | 0.621 | 0.752 | 0.650 |
| curl | nghttp2 | 23 | 0.768 | 0.768 | 0.304 |
| curl | c-ares | 77 | 0.596 | 0.691 | 0.215 |
| curl | wolfssl | 43 | 0.568 | 0.607 | 0.155 |
| curl | mbedtls | 42 | 0.649 | 0.687 | 0.171 |
| curl | gnutls | 66 | 0.651 | 0.720 | 0.095 |
| libarchive | openssl | 20 | 0.808 | 0.900 | 0.450 |
| libarchive | zlib | 32 | 0.417 | 0.279 | 0.530 |
| libarchive | bzip2 | 24 | 0.486 | 0.516 | 0.350 |
| libarchive | xz | 39 | 0.573 | 0.610 | 0.359 |
| libarchive | zstd | 26 | 0.511 | 0.511 | 0.274 |
| ndpi | libpcap | 21 | 0.351 | 0.363 | 0.343 |
| harfbuzz | freetype | 23 | 0.703 | 0.703 | 0.101 |
| harfbuzz | icu | 30 | 0.755 | 0.755 | 0.244 |
| harfbuzz | coretext | 49 | 0.826 | 0.826 | 0.191 |
| harfbuzz | directwrite | 29 | 0.266 | 0.854 | 0.266 |
| harfbuzz | uniscribe | 32 | 0.637 | 0.637 | 0.245 |
| harfbuzz | graphite | 39 | 0.970 | 0.970 | 0.256 |
| harfbuzz | glib | 32 | 0.664 | 0.789 | 0.415 |

Runtime 115s · seed 2982.
