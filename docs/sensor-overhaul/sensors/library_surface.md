# Sensor design: library surface (new; no existing gauge)

**Status:** prototype, validated on 19 (repo, library) pairs; needs the `fcall_external` scan table (GitGalaxy branch `sensors/fcall-external`). **Replaces / splits:** nothing; it answers a question none of the `risk_*` columns asked. **Origin:** the LIB study (`docs/lib.md`, `docs/librep.md`, `docs/lib_hypotheses.md`).

## 1. The question it answers
"Which files lean on this library, which of its API names do they use, and what changes when the library changes or the project changes how it uses it?"

## 2. Construct and unit
For a library D: per file, **sites** = header includes of D plus calls to D's API names (calls counted per calling function), and **density** = sites / lines. Repository level: coupled files, sites, distinct API names. Change between two scans: API names added and dropped, files newly or no longer coupled. Library profiles are the registered LIB table (include pattern and API-name pattern per library, 20 profiles); a library with no profile is listed by header only. Counts, no score.

## 3. Inputs
`file_data.raw_imports` and `total_loc` (persisted), `fcall_external` (new: external calls per file and name; before it, the engine's calls covered only functions defined in the repository, which is why the engine-only coupling in LIB-E lost to the regexes).

## 4. Drill-down
1. `lib_surface.py DB`: libraries the repo includes (header, files).
2. `lib_surface.py DB --lib openssl`: coupled files by density, with names used: **where work on the library lands**.
3. `lib_surface.py DB_BEFORE DB_AFTER --lib openssl`: API names added and dropped, files newly or no longer coupled: **how the surface moved**. Actions: scope an upgrade or deprecation before starting it; see which files absorb a library change; find leftover uses after a migration.

## 5. Evidence (exploratory, no registered test)
**Ranking where library work lands** (the LIB-H1 recipe, `lib_surface_eval.py`; outcome = a commit whose subject names the library touches the file within 180 days; recall@20, per-snapshot, bootstrapped over snapshots; curl 8 libraries, libarchive 5, harfbuzz 6; 19 units with at least 20 snapshots that have library work):
| comparison | mean | 99.7% lower bound |
|---|---:|---:|
| sensor minus stronger size order | **+0.389** | +0.344 |
| sensor minus registered regex coupling | **-0.018** | -0.031 (non-inferior at margin -0.05) |
Engine call-graph coupling alone (LIB-E, before `fcall_external`): +0.335 over size but -0.062 against the regexes, which failed the same margin. Adding header includes and external calls closed the gap. Per unit (`lib_surface_eval_output.txt`): most equal the regex to the third decimal; **weak units: c-ares (-0.138 against regex), glib (-0.125)**, libarchive zlib (-0.274 against size, as the regex also loses there). Profiles were not tuned to these results.

**Surface change** (`lib_surface_diff_demo.txt`; curl, OpenSSL, snapshots 2020-06-30 to 2022-12-31): coupled files 27 to 15, sites 467 to 422, distinct API names 194 to 210; 31 names added, 15 dropped. Checked against the source: 28 of 31 added names (90%) are absent from the earlier snapshot, 12 of 15 dropped names (80%) are gone from the later one. **This checks that the diff is right about what appeared and disappeared, not that each name belongs to OpenSSL:** at least three dropped names (`SSL_IS_PROXY`, `SSL_CONN_CONFIG`, `SSL_SET_OPTION`) are curl's own macros that share the `SSL_` prefix, so the `SSL_*` pattern counted them; the 27 to 15 fall in coupled files is partly the same effect (e.g. `lib/vtls/gtls.c` and `curl_sasl.c` were coupled only through those macros). Excluding names the repository itself defines would need the scan to store macro definitions. The added names are the OpenSSL 1.1 opaque-object API (`BIO_meth_new`, `BIO_get_data`, `BIO_meth_set_*`), i.e. the migration itself.

**Do we need the hand-written lists? (tested, `lib_surface_includes_only_output.txt`, `lib_surface_learned_output.txt`)** Header includes alone (no function-name list; libraries discoverable from the scan) still beat size, **+0.253** (lower bound +0.209), but lose to the full sensor by **-0.136** (lower bound -0.164, fails the -0.05 margin). Where they lose: libraries reached through a wrapper header, so files call the API without including it (curl zlib 0.347 against 0.815, wolfssl, libarchive OpenSSL 0.475 against 0.850, harfbuzz CoreText, FreeType, glib). A naive learner that infers a library's names from files that include its header (names called from at least 2 including files, at least 80% of whose callers include it) gives the same result as includes-only: it cannot find names whose callers do not include the header, which is exactly the missing signal. Untested alternatives: learning name families by shared prefix, a user-supplied two-pattern profile for the libraries they care about, a shipped table.

**Outside C (registered before any run: `library_surface_languages_registration.md`; output `lib_surface_languages_output.txt`).** Import coupling only (no function-name list: calls in these languages are bare names), 36 registered libraries in Go (prometheus), Python (sphinx), Java (commons-lang) and Rust (ripgrep); **11 were evaluable** (at least 20 snapshots with library-named work).
| | units | mean | lower bound (alpha 0.0033) | verdict |
|---|---:|---:|---:|---|
| LANG-H1 coupling minus size | 11 | +0.241 | +0.188 | SUPPORTED |
| LANG-H2 minus other libraries' coupling | 11 | +0.314 | +0.271 | SUPPORTED |
| LANG-H3 minus file-name lookup | 11 | +0.060 | +0.023 | SUPPORTED |
Per language, H1: Go 5 units +0.395 (lower +0.331); Python 5 units +0.102 (lower +0.013, marginal); Java 1 unit (junit) +0.170. **Rust: no evaluable unit** (ripgrep has too few library-named commits: regex 17, pcre2 9, the rest fewer), so Rust is untested. **Go H3 fails: -0.066** (a file-name lookup beats import coupling in prometheus, where package directories are named after the library, e.g. `discovery/consul/`). Weak units: sphinx babel -0.163 against size, prometheus openstack -0.025 against size. Limits: one repository per language, 25 of 36 registered libraries not evaluable, Java rests on one library; read the Go and Python results as supported, Java as a single case, Rust as open.

## 6. What it does not claim
No risk or defect claim. It says where work on a library tends to land, not that those files are fragile. It does not follow the repository's own wrappers around a library, and the outcome label (a commit subject naming the library) misses work that never names it.

## 7. Acceptance checklist (GUIDE section 5)
| Test | Status |
|---|---|
| Not degenerate | pass (density spreads over coupled files; zero elsewhere by design) |
| Construct validity | pass: ranks where library work lands, +0.389 over size on 19 units |
| Not redundant | pass: no existing column measures it; size beaten by +0.389 |
| Not just a keyword density | partly: it is include + API-name sites per line; the value is the drill-down and the diff, not a new number |
| Stable (if a trait) | not tested |
| Discriminates a stated role | pass for the library question; c-ares and glib weak |
| Actionable (ranked list) | pass: coupled-file list, surface diff |
| Outcome relation reported, not claimed | reported |
| Replicates on the master-database sample | not tested; three C/C++ projects only |

## 8. Engine work
`fcall_external` (built, local branch). A library profile table in the engine (20 profiles today, extendable by the user); a `gitgalaxy libsurface` command mirroring `gitgalaxy reach`. Include counts are not needed.

## 9. Open questions
Why c-ares and glib lose (patterns? macros? calls the engine does not record?); Go, Python and Java libraries (the engine matches calls by name, imports differ); auto-detecting libraries without a profile from headers; following the project's own wrapper functions; whether coupling predicts the size of the work, not only where it lands.
