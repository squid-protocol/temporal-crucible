# Reach head-to-head: GitGalaxy's call graph vs a tree-sitter name-matching baseline, scored against libclang

**Status:** exploratory, 7 small C repositories, 2026-11-16. Script `tools/sensor/h2h_reach.py`; output `reach_vs_treesitter_output.txt`. Question (owner): is our reach more accurate than a tool built on tree-sitter?

## Method
Ground truth: libclang 18.1.1 resolved calls (the engine's own gate adapter, `tests/tools/clang_callgraph.py`). Unit: the cross-file edge "file A calls a function defined in file B", which is what reach counts. Scored on files libclang could parse. Sources:
* **engine** : `fcall_data` call edges that resolve to one definition (what `gitgalaxy reach` counts);
* **eng-loose** : every resolved call edge including ambiguous ones, plus the tied-call candidates (`fcall_candidates`);
* **ts-unique** : tree-sitter-c parse, a call to a name that exactly one file defines is an edge to that file;
* **ts-all** : tree-sitter-c parse, a call to a name is an edge to every file that defines it.
The tree-sitter baselines are my own minimal implementation (plain-name calls only; calls through fields or pointers ignored), not a specific product.

## Result (mean over expat, redis, hiredis, libuv, ndpi, zlib, file)
| source | edge precision | edge recall | reach ranking, Spearman |
|---|---:|---:|---:|
| engine (as `reach` counts) | 83.6% | 60.8% | +0.642 |
| eng-loose (ambiguous edges and ties kept) | 84.0% | 71.4% | +0.696 |
| ts-unique | 82.8% | 68.3% | +0.775 |
| ts-all | 82.8% | 82.6% | +0.851 |

**So no: on these repositories a plain tree-sitter name-matching tool gets the reach ranking right more often than ours** (Spearman 0.85 against 0.64, over the 7 repositories counted then; over the 6 valid ones, +0.86 against +0.72), and finds more of the callers. Our edge precision is about the same (83.6% against 82.8%); it is clearly higher only on libuv (96.3 against 80.6 to 93.0), redis (92.3 against 81 to 83) and ndpi (93.8 against 85.0). It is lower on hiredis (78.9 against 90.6 for ts-unique) and zlib. Per repository (Spearman, engine / eng-loose / ts-all): expat .974 / .974 / .974, redis .754 / .764 / .734, hiredis .617 / .736 / .873, libuv .497 / .768 / .815, ndpi .686 / .688 / .881, zlib .763 / .741 / .871, file .203 / .203 / .806.

## What it means
* C has a flat namespace, so matching by name is about as strong as it gets there; this is the language where a tree-sitter baseline should do best. Go, Python and Java merge same-named methods in different packages, where scoping should help us; **not tested here**.
* **In C, the strict filter costs accuracy.** Keeping ambiguous edges and tied candidates raised recall from 60.8% to 71.4% with no loss of precision (83.6% to 84.0%), and libuv's Spearman from +0.497 to +0.768. **This does not hold in the other languages** (see the update below): there the looser set costs precision, so ambiguous edges are shown beside the count as possible callers, not folded in.
* The `file` repository was not a failure of the engine: see the update below (vendored `src/missing/` shims; libclang could not parse the real sources). It is excluded from the C averages above only in the sense that it should not have been counted; the 7-repository C row includes it, and without it the C engine's mean Spearman is +0.72 (name matching, ts-all: +0.86), so C's conclusion is unchanged.

## Limits
Small repositories, and libclang could not parse part of most of them (redis 295 of 848 files, libuv 133 of 369, hiredis 13 of 52), so the reference covers only the parsed files and has its own gaps (macros, build configuration). curl, libgit2, libxml2, libpng and libexif were excluded: libclang parsed too few files without their generated headers (curl 260 of 1,069; libgit2 507 of 1,197) to be a reference. Seven repositories, exploratory, no registered test.

## Update: six more languages (same day), and a correction
Same method, scored on the engine gate's own compiler-grade references (pyan3 for Python, the TypeScript checker for TS and JS, golang.org/x/tools VTA for Go, scip-java for Java, rust-analyzer for Rust), on the gate's pinned repositories; the references were built by the gate's own adapters. Output: `reach_vs_treesitter_languages_output.txt`. Mean over the repositories with at least 20 reference edges (Python: fastapi, flask, httpx; TS: zod; JS: axios; Go: cobra, gin; Java: gson; Rust: serde-json, ripgrep; express has 3 reference edges and is not a test):

| language | source | precision | recall | reach ranking (Spearman) |
|---|---|---:|---:|---:|
| Python | engine / eng-loose / ts-unique / ts-all | 53 / 49 / 50 / 16 | 65 / 81 / 48 / 82 | **+0.69** / +0.71 / +0.60 / +0.52 |
| TypeScript | engine / eng-loose / ts-unique / ts-all | 91 / 41 / 23 / 3 | 58 / 91 / 73 / 99 | +0.66 / **+0.83** / +0.63 / +0.43 |
| JavaScript | engine / eng-loose / ts-unique / ts-all | 55 / 44 / 15 / 4 | 74 / 98 / 69 / 82 | **+0.86** / +0.79 / +0.66 / +0.24 |
| Go | engine / eng-loose / ts-unique / ts-all | 81 / 76 / 75 / 53 | 64 / 74 / 64 / 88 | +0.72 / +0.79 / +0.72 / +0.72 |
| Java | engine / eng-loose / ts-unique / ts-all | 82 / 67 / 67 / 10 | 73 / 98 / 40 / 87 | **+0.87** / +0.80 / +0.72 / +0.45 |
| Rust | engine / eng-loose / ts-unique / ts-all | 58 / 51 / 51 / 16 | 67 / 84 / 63 / 87 | +0.83 / +0.84 / +0.80 / +0.73 |
| C (libclang; 6 valid repositories, `file` excluded) | engine / eng-loose / ts-unique / ts-all | 89 / 90 / 85 / 85 | 70 / 82 / 66 / 83 | +0.72 / +0.78 / +0.77 / **+0.86** |

**Reading:** C is the exception. In every other language the engine is more precise than name matching (by 5 points in Go, 30 or more in Java, TS, JS, Python and Rust), and its reach ranking is better than "match every definition of that name" (ts-all) everywhere (Java +0.87 against +0.45, JS +0.86 against +0.24, TS +0.66 against +0.43), and at least as good as the more conservative "match only a name one file defines" (ts-unique) in every language but Go, where it is level. Name matching works in C because C has one flat namespace; with methods and modules (`obj.get()`), it matches every `get` in the repository.

**Correction of the C-only conclusion above.** "Keep ambiguous edges: recall up, no precision lost" was true in C only. Elsewhere the looser set (eng-loose) costs precision (TS 91 to 41, Java 82 to 67, JS 55 to 44) and moves the ranking both ways (up in TS +0.18 and Go +0.07, down in Java -0.07 and JS -0.07). So ambiguous edges belong beside the count as "possible callers", not folded into it by default.

**Limits.** One to three repositories per language (TypeScript, JavaScript and Java: one), pinned repositories chosen by the gate rather than at random, references that are themselves analysers with gaps (pyan3 is not type-checked), a minimal tree-sitter baseline of my own, file-level scoring only. The `file` repository's apparent engine failure was an artifact: libclang could not parse its real sources and the 16 scored edges were all in `src/missing/`, a vendored-shim directory the engine skips by design (`gitgalaxy_config.py` lists `missing` as a vendor container).
