# LIB-R and LIB-E — library coupling replicated on fresh repos, and measured by the engine — registered 2026-11-06, before any coupling score, D-work count or statistic on these data

**Why.**
- **LIB** (21 units, four repos) showed that work naming a library lands in the files that call it:
  - recall@20 is +0.40 over size (H1), +0.46 over other libraries (H2) and +0.22 over file names (H3).
- Two gaps:
  1. **LIB-R:** it has not been replicated on repos chosen after it.
  2. **LIB-E:** its coupling score is a **regex over source lines**, not the GitGalaxy engine. Does the engine's own
     call graph (`function_data.calls_out_to`) carry the same signal?
- **Correction recorded here.** This program's chat summaries described LIB as predicting "where security fixes land".
  LIB's outcome is **any commit whose subject names the library**: fixes, features, migrations.

## LIB-R — replication on PostgreSQL and libgit2 (git only, the LIB recipe unchanged)

**Repos.** Never used in any study of this program:
- `postgres/postgres` @ `bb8a88bbd1c7`; C, `.c` `.h`.
- `libgit2/libgit2` @ `42a89d7cc937`; C, `.c` `.h`.

**Snapshots.**
- Quarterly, built here exactly as the existing `walks/*_quarterly.json`: the last first-parent commit before each
  quarter boundary, from the first full quarter to 2026-10-01.
- `events_head` = the head above.
- Written to `walks/postgres_quarterly.json` and `walks/libgit2_quarterly.json`.

**Dependencies (fixed now).** Subject names match on a word boundary, case-insensitive. Coupling lines use LIB's
per-line PCRE.

| repo | D | subject names | coupling pattern |
|---|---|---|---|
| postgres | openssl | openssl, libressl | as LIB curl/openssl |
| postgres | zlib | zlib | as LIB curl/zlib |
| postgres | icu | icu | `#include\s*[<"]unicode/` or `\b(?:u\|ucol\|ubrk\|uloc\|ucnv\|unorm2?)_\w+\s*\(` |
| postgres | libxml2 | libxml2, libxml | `#include\s*[<"]libxml/` or `\bxml\w+\s*\(` |
| postgres | lz4 | lz4 | as LIB libarchive/lz4 |
| postgres | zstd | zstd | as LIB libarchive/zstd |
| postgres | gssapi | gssapi, gss, kerberos, krb5 | `#include\s*[<"]gssapi` or `\bgss_\w+\s*\(` |
| postgres | ldap | ldap | `#include\s*[<"](?:ldap\|winldap)\.h` or `\bldap_\w+\s*\(` |
| postgres | readline | readline, libedit, editline | `#include\s*[<"](?:readline/\|editline/\|histedit)` or `\b(?:readline\|rl_\w+\|add_history\|history_\w+)\s*\(` |
| postgres | llvm | llvm | `#include\s*[<"]llvm` or `\bLLVM\w+\s*\(` |
| postgres | perl | perl, plperl | `#include\s*[<"](?:EXTERN\|perl\|XSUB)\.h` or `\b(?:Perl_\w+\|sv_\w+\|av_\w+\|hv_\w+\|newSV\w*)\s*\(` |
| postgres | python | python, plpython | `#include\s*[<"]Python\.h` or `\bPy\w+_\w+\s*\(` |
| postgres | tcl | tcl, pltcl | `#include\s*[<"]tcl\.h` or `\bTcl_\w+\s*\(` |
| libgit2 | openssl | openssl | as LIB curl/openssl |
| libgit2 | mbedtls | mbedtls, mbed tls | as LIB curl/mbedtls |
| libgit2 | zlib | zlib | as LIB curl/zlib |
| libgit2 | libssh2 | libssh2 | as LIB curl/libssh2 |
| libgit2 | pcre | pcre, pcre2 | `#include\s*[<"]pcre` or `\bpcre2?_\w+\s*\(` |
| libgit2 | http-parser | http-parser, http_parser, llhttp | `#include\s*[<"](?:http_parser\|llhttp)\.h` or `\b(?:http_parser\|llhttp)_\w+\s*\(` |
| libgit2 | winhttp | winhttp | `#include\s*[<"]winhttp\.h` or `\bWinHttp\w+\s*\(` |
| libgit2 | securetransport | securetransport, secure transport | `#include\s*[<"]Security/` or `\b(?:SecTrust\|SecCertificate\|SSLCreateContext\|SSLHandshake\|SSLRead\|SSLWrite)\w*\s*\(` |
| libgit2 | ntlm | ntlm, ntlmclient | `#include\s*[<"]ntlm` or `\bntlm_\w+\s*\(` |
| libgit2 | iconv | iconv | `#include\s*[<"]iconv\.h` or `\biconv\w*\s*\(` |

**Statistic and claims.** Exactly LIB's:
- D-work = non-merge commits touching 1–50 `.c`/`.h` files whose subject names D, within 180 days after the
  snapshot;
- effort-aware recall@20;
- a unit is evaluable with ≥ 20 snapshots having D-work;
- equal unit weights; bootstrap over snapshots within units, 5,000 rounds, seed 2982;
- α = 0.01/3; equivalence band ±0.02.

| id | claim | supported iff |
|---|---|---|
| **LIBR-H1** | coupling to D − stronger size order | pooled mean > 0, lo > 0 |
| **LIBR-H2** | coupling to D − mean of the repo's other D′ (placebo) | same |
| **LIBR-H3** | coupling to D − file-name lookup | same |

**Headline.** "Library coupling **replicated**" iff all three are supported. Not evaluable if fewer than 3 units
qualify.

## LIB-E — the engine's call graph as the coupling measure (the original LIB repos)

**Data.**
- The existing quarterly engine DBs of curl, libarchive, nDPI and harfbuzz (CHG / NH paths), at the LIB walk
  snapshots they contain.
- The LIB dependency table, unchanged.

**Engine coupling.**
- S^E_D(file) = (number of entries c in the file's functions' `calls_out_to` lists such that D's LIB pattern
  matches the string `c + "("`) ÷ the file's git line count.
- A file with no engine functions scores 0.
- Grep coupling (LIB's S_D), sizes and outcomes are recomputed as in LIB, on the same snapshots.

| id | claim | per-snapshot quantity | supported iff |
|---|---|---|---|
| **LIBE-H1** | the engine's call graph finds D-work beyond size | recall@20(S^E_D) − stronger size order | pooled mean > 0, lo > 0 (α 0.01/2) |
| **LIBE-H2** | …and is **non-inferior** to the regex | recall@20(S^E_D) − recall@20(S_D) | pooled lo > −0.05 (α 0.01/2) |

The units are LIB's evaluable units restricted to snapshots in the engine DBs, with ≥ 20 such snapshots.

## Priors

- **LIBR-H1 and H2 likely.**
- **LIBR-H3 uncertain.** Both repos name some glue files after the library (`be-secure-openssl.c`, `streams/openssl.c`).
- **LIBE-H1 likely.**
- **LIBE-H2 uncertain.** The engine misses `#include`-only coupling and macro-wrapped calls, but sees the calls
  themselves.
