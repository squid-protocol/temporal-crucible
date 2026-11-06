# LIB-H1..H3 — does a file's coupling to a library predict where that library's work lands? — registered 2026-11-06, before any dependency-work count or statistic

**Mechanism (the method that produced ENV).** Code that calls a library's API is coupled to that library, and when
the library changes, or the project changes how it uses it, the work should land there. This is the ENV mechanism
(a declared dependency on the outside world) applied to libraries instead of platforms.

**What has been looked at.**
- The repos, their XC labels and the ENV/TGT results.
- **Never computed:** any per-library coupling measure, or any count or statistic of library-named commits.

## Repos and dependencies (fixed now)

The openssl repo is excluded: it has no comparable external libraries.

| repo | dependency D | subject names (word boundary, case-insensitive) | coupling lines (in the file) |
|---|---|---|---|
| curl | openssl | openssl, boringssl, libressl, aws-lc, quictls | `#include\s*[<"]openssl/` or a call `\b(?:SSL|SSL_CTX|EVP|X509|BIO|ERR|PEM|RSA|EC_KEY|BN|OPENSSL)_\w+\s*\(` |
| curl | zlib | zlib | `#include\s*[<"]zlib\.h` or `\b(?:inflate|deflate)\w*\s*\(` or `\bz_stream\b` |
| curl | libssh2 | libssh2 | `#include\s*[<"]libssh2` or `\blibssh2_\w+\s*\(` |
| curl | nghttp2 | nghttp2 | `#include\s*[<"]nghttp2/` or `\bnghttp2_\w+\s*\(` |
| curl | c-ares | c-ares, ares | `#include\s*[<"]ares\.h` or `\bares_\w+\s*\(` |
| curl | wolfssl | wolfssl | `#include\s*[<"]wolfssl/` or `\bwolfSSL_\w+\s*\(` |
| curl | mbedtls | mbedtls, mbed tls | `#include\s*[<"]mbedtls/` or `\bmbedtls_\w+\s*\(` |
| curl | gnutls | gnutls | `#include\s*[<"]gnutls/` or `\bgnutls_\w+\s*\(` |
| curl | libidn2 | libidn2, idn2 | `#include\s*[<"]idn2\.h` or `\bidn2_\w+\s*\(` |
| libarchive | openssl | openssl, libressl | as curl/openssl |
| libarchive | zlib | zlib | as curl/zlib |
| libarchive | bzip2 | bzip2, bzlib | `#include\s*[<"]bzlib\.h` or `\bBZ2_\w+\s*\(` |
| libarchive | xz | xz, lzma, liblzma | `#include\s*[<"]lzma\.h` or `\blzma_\w+\s*\(` |
| libarchive | zstd | zstd | `#include\s*[<"]zstd\.h` or `\bZSTD_\w+\s*\(` |
| libarchive | lz4 | lz4 | `#include\s*[<"]lz4` or `\bLZ4\w*_\w+\s*\(` |
| libarchive | libxml2 | libxml2, libxml | `#include\s*[<"]libxml/` or `\bxml(?:Text)?\w+\s*\(` |
| libarchive | expat | expat | `#include\s*[<"]expat\.h` or `\bXML_\w+\s*\(` |
| libarchive | mbedtls | mbedtls | as curl/mbedtls |
| libarchive | nettle | nettle | `#include\s*[<"]nettle/` or `\bnettle_\w+\s*\(` |
| nDPI | libgcrypt | gcrypt, libgcrypt | `#include\s*[<"]gcrypt\.h` or `\bgcry_\w+\s*\(` |
| nDPI | json-c | json-c, json_c | `#include\s*[<"](?:json-c/\|json\.h)` or `\bjson_object_\w+\s*\(` |
| nDPI | libpcap | pcap, libpcap | `#include\s*[<"]pcap` or `\bpcap_\w+\s*\(` |
| nDPI | maxminddb | maxmind, maxminddb, geoip | `#include\s*[<"]maxminddb\.h` or `\bMMDB_\w+\s*\(` |
| harfbuzz | freetype | freetype | `#include\s*(?:FT_\w+_H\|[<"]ft2build\.h)` or `\bFT_\w+\s*\(` |
| harfbuzz | icu | icu | `#include\s*[<"]unicode/` or `\b(?:u\|ubrk\|uscript\|unorm2?)_\w+\s*\(` |
| harfbuzz | coretext | coretext, core text | `#include\s*[<"]CoreText` or `\bCT\w+\s*\(` |
| harfbuzz | directwrite | directwrite, dwrite | `#include\s*[<"]dwrite` or `\bIDWrite\w*` |
| harfbuzz | uniscribe | uniscribe | `#include\s*[<"]usp10\.h` or `\bScript\w+\s*\(` |
| harfbuzz | graphite | graphite, graphite2 | `#include\s*[<"]graphite2/` or `\bgr_\w+\s*\(` |
| harfbuzz | glib | glib | `#include\s*[<"]glib` or `\bg_\w+\s*\(` |

## Data

- **Snapshots.** The repos' quarterly walks (`walks/*_quarterly.json`). Candidates are the C/C++ files of the walk's
  extensions at t. Size = line count (git).
- **Score.** S_D(file) = lines matching D's coupling pattern ÷ lines. Matching is per line, on the snapshot's file
  content.
- **Outcome, "D-work".**
  - A non-merge commit reachable from the walk head, touching 1–50 candidate-extension files, whose **subject** names
    D.
  - A file at t is positive if a D-work commit dated in (t, t + 180 d] touches it.
  - Any class of commit counts (fixes, features, migrations), because upgrade work is not only fixes.
- **A (repo, D) unit is evaluable** with ≥ 20 snapshots having ≥ 1 D-work positive.

## Statistic

Per (repo, D, snapshot): EA's effort-aware recall@20. Rank by score (ties: fewer lines, then path); take whole files
while cumulative lines ≤ 20%. Baselines: lines-desc and lines-asc.

| id | claim | per-snapshot quantity | supported iff |
|---|---|---|---|
| **LIB-H1** | coupling to D finds D-work beyond size | recall@20(S_D) − max(recall@20 by lines-desc, lines-asc) | pooled mean > 0, lo > 0 |
| **LIB-H2** | …and it is D's coupling, not any library's (placebo) | recall@20(S_D) − mean over the repo's other dependencies D′ of recall@20(S_D′), on D-work | pooled mean > 0, lo > 0 |
| **LIB-H3** | …and it beats looking at file names | recall@20(S_D) − recall@20(path-match), where path-match = 1 if the file path contains a D subject name (ties broken by fewer lines) | pooled mean > 0, lo > 0 |

**Pooling and test.**
- Each evaluable (repo, D) unit contributes its mean over snapshots, with equal weight per unit.
- Bootstrap: resample snapshots within each unit (5,000 rounds, seed 2982), then average unit means.
- α = 0.01 / 3 one-sided. Equivalence null: 90% CI inside [−0.02, +0.02].

**Headline.** **"Library coupling is shown"** iff H1, H2 and H3 are all SUPPORTED. H1 + H2 without H3 means
"real but no better than grepping file names".

**Descriptive.**
- Per-unit results.
- The OpenSSL 3 migration: curl/libarchive OpenSSL-work commits between 2020-06 and 2022-12, and the share landing in
  the top-20%-by-S_D files.

## Priors

- LIB-H1 **leaning supported**: the ENV mechanism.
- LIB-H2 **leaning supported**.
- LIB-H3 **uncertain**: curl and harfbuzz name their glue files after the library (`vtls/openssl.c`,
  `hb-coretext.cc`), so file names are a strong baseline there.
