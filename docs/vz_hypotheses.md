# VZ — vendored zlib: does the layered fingerprint find vendored copies of CVE-fixed zlib functions (including renamed ones), and can it tell patched from unpatched? — registered 2026-11-06, before any scan of zlib or the hosts

**Why.**
- LAY found that the layered fingerprint (L1 profile + L2 call set + L3 control-flow skeleton, fused by RRF) lifts
  OpenSSL→fork copy retrieval at rank 1 from 46% to 80%.
- LAY's gaps:
  1. one fork family;
  2. truth defined by same names, so renamed copies were never tested;
  3. UT's patch-status rule was fooled by comment lines.
- VZ is the out-of-sample test on the most-vendored C library.

## ⚠ Disclosure rule (binding; the repository is public)

- **Public files:** aggregates only. Never write "host X carries an unpatched copy of CVE-Y".
- **Per-host specifics:** a private file outside the repo (`temporal-crucible-pool/vz_private/`), for the owner.
- All CVEs here are public. Their applicability to a host still depends on which code paths it builds.

## Reference: zlib CVE fixes (`madler/zlib`, metadata verified)

| fix commit | CVE | file | fixed in release |
|---|---|---|---|
| `eff308a` 2022-07-30 | CVE-2022-37434 | inflate.c | 1.2.13 |
| `1eb7682` 2022-08-08 | CVE-2022-37434 (follow-up) | inflate.c | 1.2.13 |
| `5c44459` 2018-04-19 | CVE-2018-25032 | deflate.c, deflate.h, trees.c | 1.2.12 |
| `6a04314` 2016-09-21 | CVE-2016-9840 | inftrees.c | 1.2.9 |
| `9aaec95` 2016-09-21 | CVE-2016-9841 | inffast.c | 1.2.9 |
| `e54e129` 2015-09-05 | CVE-2016-9842 | inflate.c | 1.2.9 |
| `d1d5774` 2016-09-28 | CVE-2016-9843 | crc32.c | 1.2.9 |

**Queries.**
- Each C function a fix changes, mapped as in CHG and UT: tree-sitter at the parent, `-U0` hunks.
- **Pre-fix body** at the parent; **post-fix body** at the fix.
- **R** / **A** = the function's removed / added **code** lines: whitespace-normalised, ≥ 10 characters, containing
  a letter, and not a comment line. Comment lines start with `//`, `/*` or `*`; this is UT's lesson.

## Hosts (fixed now; heads and paths recorded)

| host | path | head | `ZLIB_VERSION` |
|---|---|---|---|
| zlib-ng/zlib-ng | whole repo | `b342eef204dc` | 1.3.2.zlib-ng (functions renamed through `PREFIX()`) |
| chromium third_party/zlib | whole repo | `ec453dc9abac` | 1.4 |
| mysql-server | extra/zlib | `06bcb0eb0ad2` | 1.3.2 |
| mongo | src/third_party/zlib | `d48ca0a141ad` | 1.3.2 |
| assimp | contrib/zlib | `0623040c1eaf` | 1.2.13 |
| openjdk/jdk | src/java.base/share/native/libzip/zlib | `b0c5b1ba2f3f` | 1.3.2 |
| qt/qtbase | src/3rdparty/zlib | `7d5fd833811e` | 1.3.2 |
| Kitware/CMake | Utilities/cmzlib | `9589cb98e1fd` | 1.3.1 |
| rsync | zlib | `ea645201fefb` | 1.2.8 |
| MariaDB/server | zlib | `f03e90205031` | 1.3.2 |
| godot | thirdparty/zlib | `b47a795aa585` | 1.3.2 |
| libgit2 | deps/zlib | `42a89d7cc937` | 1.3.1 |

## Scans

- Engine `galaxyscope-tc` `da852aa54`, `--spec-alignment`, history off: the UT and LAY build.
- One scan per fix parent of `madler/zlib` (the queries).
- One scan per host path (the candidates: all host functions with ≥ 6 lines).

## Truth, methods, metric

**Truth (text only, names unused).**
- The host function with the highest token Jaccard to the query's pre-fix **or** post-fix body, if ≥ 0.5.
- **Renamed** = truth's name differs from the query's (short, lower-cased).

**Methods.**
- LAY's L1, L2, L3 and FUSED, unchanged.
- **NAME:** candidates with the query's short name rank first (pessimistic ties), all others after.
- *TOKEN:* reference ceiling only.

**Metric.** recall@1 / recall@10, pessimistic tie ranks.

## Claims (α = 0.01/3, one-sided; bootstrap over hosts, i.e. clusters, 5,000 rounds, seed 2982)

| id | claim | supported iff |
|---|---|---|
| **VZ-H1** | LAY replicates out of sample | recall@1 FUSED − L1 > 0, lo > 0 (all truth pairs; ≥ 30) |
| **VZ-H2** | the layered fingerprint finds **renamed** copies names miss | recall@10 FUSED − NAME > 0, lo > 0, on renamed pairs (≥ 15; else not evaluable) |
| **VZ-H3** | the code-line patch check **agrees with the host's zlib version** | among truth pairs classed patched or unpatched-looking, agreement with the version expectation (host version ≥ the fix release → patched) ≥ 80%, Wilson 99% lo ≥ 60% (≥ 30 pairs) |

- **Version parsing:** the numeric prefix of `ZLIB_VERSION`. The zlib-ng and Chromium strings are taken as given.
- **H3 disagreements are expected to include backports**, e.g. distribution- or project-patched old copies. They are
  listed privately and counted publicly by kind.

## Priors

- **H1 likely.**
- **H2 uncertain.** zlib-ng's rewrite may push its copies below the 0.5 text threshold, leaving few renamed pairs.
- **H3 likely**, since most hosts track zlib releases verbatim.

**Pre-run clarification (2026-11-06; no host statistic computed yet).** A smoke test showed tree-sitter loses
pre-2017 `inflate.c`: `#ifdef` blocks split function bodies, so `inflate()` was never recognised. It also names a
function after a visibility macro (`ZLIB_INTERNAL`).

Fallback, for queries and host bodies alike:
- where tree-sitter finds no enclosing function, or returns an ALL-CAPS macro as the name, use the engine's function
  span (its start line to the next function's start, from the same scan) for the name and body;
- a post-fix body tree-sitter cannot see is the same-size window from the pre-fix signature line.

Nothing else changes.

**Run 1 crashed before any statistic (2026-11-06).** Two bugs; nothing was scored:
1. **The engine scanned MySQL's `extra/zlib` but skipped its `zlib-1.3.2/` subfolder,** leaving 0 functions.
   - The engine appears to exclude version-named or vendored directories. *This is a product-relevant finding*: a
     default GitGalaxy scan may omit vendored copies.
   - Fix: scan the inner folder `extra/zlib/zlib-1.3.2` (the same code).
2. **zlib-ng's version lives in `zlib.h.in`,** which the lookup did not search. The lookup now includes `zlib*.h.in`,
   and empty tables are dropped with a note.

Run 2 uses these fixes. Nothing else changes.
