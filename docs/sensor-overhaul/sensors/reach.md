# Sensor design: reach (replaces `risk_api_exposure`)

**Status: design with evidence and a working first product (the migration scope report); exploratory.** Tools: `tools/sensor/reach_validity.py`, `tools/sensor/migration_scope.py`; outputs: `reach_validity_output.txt`, `migration_scope_libgit2*.txt`. Earlier evidence: `docs/turn_surface_area.md` (ripple test), `sensors/activity.md` section 11.

## 1. The question
*How much of the codebase leans on this function or file, and who would feel a change to it?* Reach is a measurement of dependence, not of risk.

## 2. What the engine has
* `fcall_data`: resolved call edges (caller function and file, callee function and file). At curl snapshot 104 only 71 of 19,158 edges are unresolved, and **calls to standard-library and builtin names (`free`, `malloc`, `memcpy`, `strlen`) are not recorded at all.**
* File level: `pagerank_score` and `normalized_blast_radius` (PageRank over resolved imports), `internal_dependency_links`, `import_count`. Function level: `func_fan_in`, `func_fan_out`, `func_pagerank`, `is_public`.
* The old `api_exposure` gauge combined an API-keyword density with encapsulation, squashed to 0-100.

## 3. Evidence
**Construct validity against an independent text measure** (who mentions a function's name; who `#include`s a header), curl snapshot 104 and libgit2 snapshot 64:
| Measure | curl | libgit2 |
|---|---:|---:|
| Function level: cross-file caller files, engine vs text search (uniquely named functions, n = 4,245 / 8,890) | rho +0.91 | rho +0.91 |
| ... engine misses all outside users of functions that have them | 15% | 19% |
| ... median per-function recall of the text callers | 0.50 | 0.50 |
| ... median precision of the engine's callers | 1.00 | 1.00 |
| File level, vs files that mention any function the file defines: call-based caller files | +0.88 | +0.90 |
| ... `pagerank_score` / `normalized_blast_radius` | +0.87 | +0.88 |
| ... `import_count` | +0.60 | +0.38 |
| ... `internal_dependency_links` | +0.28 | +0.14 |
| Header files vs number of files that `#include` them: `pagerank_score` | +0.39 | +0.38 |
| ... call-based caller files | -0.07 | -0.18 |
Reading: **the engine's callers are always real and about half complete.** Call-based caller files and PageRank track real dependence equally well for source files; `import_count` and `internal_dependency_links` do not. For **header files none of the engine's measures tracks who includes them** (rho 0.4 at best), so headers need the include count itself.
**Outcomes** (descriptive; no risk claim): adding reach to size gives +0.018 / +0.016 / +0.012 AUC for later fixes in curl / libxml2 / libgit2, the largest single addition, independent of activity (rho +0.25); callers of swept functions are edited 1.9x as often as other functions (odds ratio 1.28 given size, same file and fan-in); the old file-level `api_exposure` score runs the wrong way in that test (odds ratio 0.72). Among active source files, **hot and high reach** files get fixes x2.08 / 1.97 / 2.56 of the base rate, **reach alone** x1.15 / 1.43 / 1.47, and **high reach but quiet** x0.62 / 0.95 / 0.76: quiet foundations are not where fixes land.

## 4. The sensor
**Units.** Functions: distinct callers, caller files, functions one more hop away (ripple), public flag. Files: caller files (source) or include count (headers), dependents, percentile within the repo and role. Anything outside the call graph (YAML, shell, docs; calls to the standard library) shows **"not measured"**, never a tied mid-percentile.
**Views (each a ranked list with file, function, count and reason).**
1. **Where change lands that many depend on:** hot (top decile of 365-day activity) and reach top quartile; the strongest simple list (section 3).
2. **Stable foundations:** quiet for two or more years with reach in the top decile. Descriptive, explicitly not a risk list. Example, libgit2 at 2025-08: `src/util/runtime.c`, `thread.c`, `posix.c`, `libgit2/object_api.c`, `buf.c`, `util/win32/utf-conv.c` (2-3.5 years untouched, reach above the 96th percentile).
3. **API surface:** public functions and headers by outside users (include count for headers).
4. **Migration scope and progress** (the first product, next section).

## 5. First product: migration scope and progress report
`migration_scope.py REPO OLD NEW SNAPSHOT [FOLLOW]` takes an old name, a new name and the snapshot before the migration, and reports the callers (functions, files, lines, source vs tests), the ripple (functions one more hop away), the most depended-on callers to touch carefully, the share still on the old name at each later snapshot, and the stragglers by file and role.
**libgit2, `git_buf_free` to `git_buf_dispose` (2018-07):** the report predicted **761 callers in 228 files** (327 in source, 434 in tests; 29,267 lines in those functions; 1,276 functions one hop away; most depended-on caller `git_repository_free` with 242 callers) for a migration that touched **757 functions**; zero callers of the old name remained at the next snapshot.
**The next link, `git_buf_dispose` to `git_str_dispose` (2021-10):** 866 callers in 258 files (356 source, 510 tests; 1,432 one hop away). 163 were still on the old name at the next snapshot and a stable 177-179 stayed for two years: **175 of the 179 stragglers are in `tests/`, only 4 in source**, because the old name is still the public API there. So 352 of 356 source callers migrated (99%) while the plateau in tests is intentional retention, not unfinished work: the report must split callers by role and say so.
This matches the earlier scope test (call-graph callers: recall 1.00 and median precision 0.83 over 417 sweeps; a sweep covers a median 90% of the old name's callers).

## 6. What it does not claim
No risk or defect claim. Reach is dependence as the engine can see it: a lower bound, about half the true outside users of a function.

## 7. Engine work
1. **Persist calls to external names** (standard library, builtins, macros) as callee nodes so migrations like `free` to `curlx_free` can be scoped; today 336 of 767 detected sweeps, 44%, are invisible.
2. **Header reach:** persist include edges and an include count; the current file-level import measures correlate only 0.4 with real includes.
3. **Function pointers and dynamic dispatch:** document the recall limit (about 0.5) next to every reach value; keep the "not measured" state.
4. Persist `caller_files` and `dependents_2hop` per function so the report does not re-derive them from the edge table.

## 8. Acceptance status (guide section 5)
| Test | Status |
|---|---|
| Not degenerate | open: tied percentiles for files outside the graph must become "not measured" |
| Construct validity | **pass for source** (+0.88 to +0.91 vs text); **fails for headers** (+0.4 vs include count) |
| Not redundant | reach vs activity +0.25, vs age +0.16, vs ownership -0.02 |
| Actionable | by construction: scope lists, stragglers, foundations |
| Outcome | reported, not claimed: +0.012 to +0.018 AUC over size; quiet reach is not fix-prone |
| Population replication | open: two repos for validity, three for outcomes |

## 9. Open questions
* A per-migration effort estimate (callers, lines, ripple) has not been validated against what maintainers actually changed.
* Should "stragglers" exclude tests and public-API users by default?
* Do other languages (Python, Go, Java) give the same function-level validity?
