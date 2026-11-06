# Engine validation: C functions, spans, includes and calls (curl, nDPI)

**Why.** Every study here reads the engine's C extraction:
- function rows (FREC uses their spans to map a fix to a function);
- the `#include` graph (PageRank and centrality: B-H1/B-H2, centrality bands, the walk);
- function counts in the descriptive tables.

gitgalaxy measures these against independent tools, but only on its own pinned corpora. `tools/engine_validate.py`
runs the **same measurement code** (gitgalaxy `tests/tools/`) on snapshots of our study repos, with the engine
build the studies used (`32619e4a5`, the PR #50 / FREC scans).

**References.** None is ground truth: every disagreement below was read in source before it was attributed.
- tree-sitter-language-pack 1.22.1: function definitions and spans.
- Universal Ctags 5.9: function definitions, `.h` read as C.
- The source's own `#include` lines, resolved by gitgalaxy's `import_graph_accuracy`.
- libclang 18.1.1: resolved calls.

## Results (2026-11-05)

| snapshot | functions vs tree-sitter R / P | vs ctags, files the engine scans as C, R / P | span start / end exact | `#include` edges R / P | call links: agree / wrong / recall |
|---|---|---|---|---|---|
| curl 7.10.8 (2003) | 99.80 / 99.22 | 99.80 / 100.0 | 100.0 / 100.0 | 99.77 / **90.40** | 576 / 0 / 84.0% |
| curl 7.30.0 (2013) | 99.56 / 99.62 | 99.71 / 100.0 | 99.67 / 99.73 | 100.0 / 99.59 | 1,144 / 0 / 65.4% |
| curl 8.17.0 (2025) | 99.57 / 99.72 | 99.78 / 99.98 | 99.80 / 99.85 | 100.0 / 99.55 | 5,504 / 0 / 86.4% |
| nDPI 2.0 (2017) | 97.21 / 99.86 | 100.0 / 100.0 | 99.59 / 99.86 | 100.0 / 100.0 | 947 / 0 / 92.5% |
| nDPI 3.0 (2019) | 96.68 / 99.90 | 100.0 / 99.90 | 98.28 / 99.80 | 100.0 / 100.0 | 1,010 / 0 / 88.6% |
| nDPI head (2026) | 97.30 / 100.0 | 99.72 / 96.69 | 100.0 / 100.0 | 99.27 / 100.0 | 4,022 / 0 / 52.0% |

The span overlap ratio (engine span ∩ tree-sitter span, over their union) has median and 5th percentile **1.0** on
every snapshot.

## What each disagreement is (read in source)

**Reference artefacts (engine right).**
- nDPI's ~3% "missing" tree-sitter functions are packed structs (`PACK_ON` / `struct ndpi_tcphdr {…}` /
  `PACK_OFF`, `ndpi_typedefs.h:546`). tree-sitter reads the macro-prefixed struct as a function definition.
- nDPI head's 3.3% engine-only functions all sit in `src/lib/ndpi_main.c`. ctags' last function there is at line
  11,437, but the file runs past line 12,750 (`ends_with` is at line 12,750): ctags stopped parsing.

**Scope policy (by design, not a miss).**
- `docs/examples/*.c` is read as documentation, so ctags finds extra "functions" there (131 files on curl 8.17.0).
- nDPI's vendored `src/lib/third_party/` is not scanned (#4545). It accounts for 2,883 of the head snapshot's 2,895
  `caller_unmapped` call edges. With vendored callers left out, nDPI head call recall is 4,022 / 4,847 = **83%**.

**Two real engine gaps (filed as gitgalaxy#7827 and #7828; text below).**
1. **`<sys/types.h>` resolves to `include/curl/types.h`.** In Stage 1 of import resolution, a lone same-named file
   is returned without checking the include's directory. That gives curl 7.10.8 46 false edges (precision 90.4%).
   It is still present on gitgalaxy main `79b13e354`.
2. **Calls through a `#define` alias are not followed.** In curl 7.30.0, `failf(...)` is `#define failf Curl_failf`
   (`lib/sendf.h:48`; `infof` likewise). That is most of the 293 `not_extracted` edges, and why that snapshot's
   call recall is 65%. Modern curl calls `Curl_failf` directly (86%).

## Impact on this program's results

- **Function rows and spans: sound.** 97–100% against both references, and spans exact at both ends for 98–100% of
  functions. FREC's fix-to-function mapping stands.
- **Call graph: no study here reads it** (no tool uses `fcall`, function PageRank or fan-in). Its precision is
  perfect where it is used: 0 wrong confident links on any snapshot.
- **`#include` graph:** sound from 2013 on (99.3–100%). On early curl (gap 1), `include/curl/types.h`'s in-degree,
  and so its PageRank, is inflated. Centrality results that include pre-2012 curl snapshots (B-H, centrality bands,
  walk panels) carry this as a known caveat. The affected file is a public header, not a typical fix target. A rerun
  after the engine fix would settle it.

## openssl (repo #3), validated before any harvest (2026-11-05)

| snapshot | functions vs tree-sitter R / P | vs ctags (C files) R / P | span start / end exact | `#include` R / P (raw) | `#include` P without build-generated headers | call links: agree / wrong / recall |
|---|---|---|---|---|---|---|
| OpenSSL 1.0.2 (2015) | 97.40 / 99.07 | 97.77 / 98.49 | 99.07 / 99.48 | 100.0 / 25.46 | **100.0** | 15,049 / 0 / 63.8% |
| OpenSSL 1.1.1 (2018) | 97.51 / 99.37 | 98.13 / 96.12 | 99.28 / 99.77 | 100.0 / 97.16 | **100.0** | 23,251 / 0 / 71.6% |
| openssl 3.5.0 (2025) | 98.03 / 99.36 | 98.39 / 79.52 | 99.08 / 99.76 | 99.94 / 88.39 | **99.8** | 45,733 / 1 / 55.9% |

**What each disagreement is (read in source).**
- **Includes are build-correct, not wrong.** 1.0.2's `include/openssl/` is not in git: `make links` builds it as links to
  `crypto/<x>/<x>.h`. So all 2,825 "false" edges (`<openssl/rsa.h>` → `crypto/rsa/rsa.h`) are what the compiler
  sees. In 1.1.1 and 3.5.0, 128 and 1,023 edges point at the `include/openssl/*.h.in` templates that the real headers
  are generated from.
- What's left: 15 edges in 3.5.0 are **#7827 again**, with `<sys/time.h>` → `include/internal/time.h`
  (`crypto/bio/bio_sock.c:29`). That second-repo confirmation and the build-linked counterexample are posted on #7827.
- **ctags precision 79.5% on 3.5.0 is ctags,** tripping on openssl's `STACK_OF(...)` / `DEFINE_STACK_OF` macros: its
  "functions" include `STACK_OF`, while `apps/list.c:95 static int cipher_cmp(...)` is real and ctags misses it.
  tree-sitter agrees with the engine (precision 99.4%).
- **Call recall is macros.**
  - `not_extracted` (17,087 edges) is mostly function-like macros that expand to calls: `ERR_raise` 6,966,
    `OPENSSL_free` 3,220 (→ `CRYPTO_free`), `OPENSSL_malloc` and friends. That's #7828's function-like form, and the
    evidence is on the issue.
  - `caller_unmapped` (8,805) is functions that exist only after preprocessing: token-pasted
    `is_ ## type ## _fetchable` (`apps/list.c:40`) and generator macros (`DEFINE_OSSL_CMP_CTX_get0_NAME`). No
    non-preprocessing extractor sees them, tree-sitter included.

**Verdict for the openssl study.** Function rows and spans are sound, at 97–98% recall and 99%+ precision. The
include graph is sound once build-generated headers are understood. The call graph is precise but misses
macro-expanded calls, and no study here reads it. One study-design consequence: a fix inside a macro-generated
function has no function row to land in. Any function-grain claim on openssl must report how many fix hunks fall
outside every function span.

## Issue 1 (filed as gitgalaxy#7827): C import graph, system include resolved to an unrelated repo header

> **What's wrong.** `#include <sys/types.h>` gets an edge to a repo header that merely shares the basename. In
> curl 7.10.8, every `ares/*.c` file links to `include/curl/types.h`: 46 false edges out of 479 (import precision
> 90.4%; 99.6–100% elsewhere). It reproduces on main `79b13e354`.
>
> **Where.** `gitgalaxy/core/network_risk_sensor.py`, Stage 1: a single candidate matched by the token's last
> segment is returned without checking that the token's path context (`sys/`) is a suffix of the candidate's
> path. #3544 added that check, but only for `MODULE_PATH_MIRROR_LANGS`.
>
> **Repro.** Scan a curl-7_10_8 checkout and count `edge_data` rows from `ares/%` into `include/curl/types.h`.
> `ares/ares_init.c:18` is `#include <sys/types.h>`.
>
> **Fix shape.** For `include_names_file_literally` languages, a token containing `/` names a file only if the
> candidate's path ends with that path (#3544's rule). A bare `"types.h"` is unchanged.
>
> **Impact.** False in-degree, PageRank and blast radius on any C repo whose headers share names with system
> headers (`types.h`, `time.h`, `string.h`, `signal.h`, …).

## Issue 2 (filed as gitgalaxy#7828): C call graph, calls through a `#define` alias are not followed

> **What's wrong.** curl 7.30.0's `lib/sendf.h:48` has `#define failf Curl_failf` (`infof` likewise). Calls written
> `failf(data, …)` (lib/ftp.c 43 sites, imap.c 19, url.c 18, smtp.c 16, …) are not linked to `Curl_failf`. libclang
> resolves them through the macro. They make up most of the 293 `not_extracted/other` edges in
> `callgraph_triage` for that snapshot (call recall 65.4%).
>
> **Fix shape.** In C, an object-like macro whose whole body is one identifier naming a function defined in the
> repository is an alias: resolve the call to that function. A guarded `#if` alias (curl's `infof` has
> `Curl_nop_stmt` variants) links to the function only from the branch that names it, or to every branch's target
> if the engine does not evaluate `#if`.
>
> **Repro.** Run `callgraph_triage.py c` with its corpus pointed at a curl-7_30_0 checkout, then read the
> `not_extracted/other` samples (`lib/connect.c:1103 failf(data, "Connection time-out");`).

## Reproduce

```
E=<gitgalaxy worktree at the engine SHA>      # its venv needs ci/requirements/{callgraph,treesitter}.txt
GITGALAXY_PATH=$E PYTHONPATH=$E $E/.venv-tc/bin/python tools/engine_validate.py --repo curl --ref curl-7_30_0
```
The JSON (with every sample) lands in `dbs/engine_validate_<repo>_<ref>.json`.
