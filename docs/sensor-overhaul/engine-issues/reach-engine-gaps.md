# Draft GitGalaxy issue: persist external callees and header include counts (for `gitgalaxy reach`)

**Not filed.** Title: `reach: persist external callees (aggregated) and C-family include edges so migration scope and header reach need no second pass`
Labels to suggest: `enhancement`, `scope:core`? (owner's call). Relates to #3328, #3331, #3333, #8161.

## Context
`gitgalaxy reach` (branch `sensors/reach`) counts, from a finished scan, the files and functions that call a file and, for headers, the files that include it. Two things the scan already computes are not persisted, and the command works around them.

## 1. External callees are counted but not stored
`record_keeper` documents that external callees are not `fcall_data` rows (`fcall_sites`, #3328), yet `fcall_rate_data` counts them. One snapshot each, (caller, callee) pairs, language `*`:

| repo | scoped | unique | ambiguous | external | total | external share |
|---|---|---|---|---|---|---|
| curl | 13,132 | 5,704 | 283 | 16,681 | 35,800 | 46.6% |
| libgit2 | 22,396 | 18,973 | 68 | 20,930 | 62,367 | 33.6% |
| redis | 20,320 | 4,491 | 1,019 | 18,824 | 44,654 | 42.2% |
| prometheus | 19,758 | 2 | 11,505 | 31,358 | 62,623 | 50.1% |
| sphinx | 8,449 | 2 | 4,460 | 10,231 | 23,142 | 44.2% |
| ripgrep | 4,450 | 0 | 1,713 | 4,360 | 10,523 | 41.4% |

Consequence: callers the scan could list are missing; in the research tests the engine found about half of a text search's callers (precision 1.00), and a rename such as `free` to `curlx_free` (44% of 767 detected sweeps in the research corpus name an external callee) cannot be scoped from the scan.

**Proposal:** do not add rows to `fcall_data` (it would roughly double it: curl 19,158 rows today against 16,681 external pairs). Add one aggregated table, e.g. `fcall_external(src_file_id, callee, calls, functions)` with one row per (file, callee name). Measure the row count on three repositories first and put it in the PR; the pair counts above are an upper bound because they are per caller function.

## 2. Header reach needs include counts, and the engine's are lossy
For C headers, call-based reach is blind (Spearman with the number of files that `#include` the header: -0.18 to +0.23); the engine's own columns reach +0.38 to +0.71 (`pagerank_score`) and are inconsistent across repositories (curl +0.39, libgit2 +0.38, redis +0.71, libxml2 +0.68). Before adding a table, check whether the include resolver can be improved (bare `"x.h"` includes resolve differently by folder), and persist per-header include counts if it cannot.

## Out of scope here
Go and Python name matching (prometheus: 11,505 ambiguous pairs, `unique` 2) belongs to the callgraph resolver work, not to reach.

## Acceptance
`gitgalaxy reach` reports external-callee counts and needs no `--src` for headers; golden masters unchanged or re-blessed with the new table listed; row-count and size effect reported on curl, libgit2 and redis.
