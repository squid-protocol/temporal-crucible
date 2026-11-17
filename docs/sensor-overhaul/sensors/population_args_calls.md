# Population patterns: arguments, call-out, call-graph position and keyword signals (exploratory)

**Data:** `gitgalaxy-population-analyses/data/master_db_v2.9.0.db`, `function_data` joined to `file_data`: 8,269,603 functions, 523 repositories, 49 languages (13 languages with 100k+ functions analysed; analysis uses functions of 5+ lines). Code: `tools/sensor/pop_load.py`, `pop_analyze.py`, `pop_robust.py`; outputs `population_args_calls_output.txt`, `population_args_calls_robust_output.txt`. Every correlation is a Spearman rank correlation **controlling for function size** (rank of lines), computed within a language and pooled by the median over languages, with how many languages agree in sign.
**Status:** exploratory, no registration; correlations, not causes. First pass on the v2.9.0 database (name-matched fan-in); **replicated on v2.12.0 with engine-resolved fan-in in section 8 below, which supersedes findings 4 to 7 where they differ.**

## What the database has, and does not
Per function: parameter count (`args`), the names it calls (`calls_out_to`), size and complexity, and about 96 per-function keyword-signal counts (`struct_*`, `state_*`, `def_*`, `arch_*`, `threat_*`, ...). It has **no call-edge table and no fan-in column**, so fan-in here is derived: for a function name defined once in its repository, the number of distinct functions in the same repository whose call list contains that name. That is name matching (the method the reach head-to-head compared against), restricted to distinctive names.

## Findings
**1. Parameter count is its own axis, not a size proxy.** Median 1 to 2 (PHP, Ruby 0). Functions with 5 or more parameters: C 8.0%, Python 7.7%, C++ 7.6%, Dart 4.5%, Rust 4.8%, Java 4.3%; JavaScript 2.3%, Ruby 1.7%. With 8 or more: about 1% (0.3% to 1.7%). Its rank correlation with size is weak (0.19 to 0.21 in C, C++, Python; about 0 in Java, C#, Dart), whereas distinct-functions-called tracks size strongly in every language (0.48 to 0.73).

**2. More parameters does not mean more calls, once size is removed.** Raw correlation is +0.1 in C-family languages and is size. Size-controlled it is mixed: Java -0.28, Dart -0.28, PHP -0.16, Python -0.13, Rust +0.14, the rest near 0. In Java and Dart, functions with many parameters call fewer distinct things at the same size (constructors, builders and data carriers rather than orchestration); no language shows the opposite strongly.

**3. At the same size, keyword signals sort functions into two kinds.**
| | more parameters | more distinct calls |
|---|---|---|
| tests (`def_test`) | **fewer** (-0.29, 11 of 12 languages) | **more** (+0.19, 11 of 12) |
| branching (`struct_branch`) | more (+0.18, 12 of 13) | not in the top |
| safety checks, encapsulation (`def_safety`, `def_encapsulation`) | more (+0.14, +0.16) | slightly more (+0.07) |
| generics (`struct_generics`) | more (+0.13, 9 of 9) | |
| closures, comprehensions, concurrency, I/O, memory allocation | closures slightly fewer (-0.08); the rest not in the top | **more** (+0.15, +0.16, +0.10, +0.10, +0.09; all languages agree) |
| UI framework, class start, decorators, API exposure | fewer (-0.14, -0.14, -0.12, -0.10) | |
Reading: a test calls many distinct things and takes no parameters; a guarded, branching function takes parameters; a function with closures, concurrency or I/O fans out. `struct_args` (+0.22 with parameters, +0.30 with calls) counts argument syntax in the text, so it is close to circular with the parameter count and is not a finding.

**4. The call graph is a heavy tail.** Of 3.6M measurable functions (non-test, unique name of 5 or more characters, not one of the language's 300 commonest callee names): the **top 1% by fan-in hold 34% of the name-resolved calls (18 or more callers), the top 5% hold 57%, the top 10% hold 70%**; 49% are never called by name in their repository and 28% by exactly one function; 2.2% have 10 or more callers.

**5. Hubs are small, public and take a few parameters, and they call little.** Hub (10 or more callers) against leaf (none), same language: **public** C 82% vs 28%, Rust 75% vs 39%, TypeScript 76% vs 53%, Go 73% vs 36%, JavaScript 32% vs 20%; **smaller** (median lines: C 13 vs 16, C++ 9 vs 13, TypeScript 13 vs 17, Dart 10 vs 15, Go 11 vs 14, Rust 9 vs 11); **calls fewer distinct things** (size-controlled fan-in versus calls: C++ -0.22, Dart -0.17, C -0.08; near 0 elsewhere). Fan-in goes with parameters in most languages (size-controlled): Ruby +0.60, Dart +0.50, PHP +0.39, C# +0.37, JavaScript +0.23, Rust +0.19, TypeScript +0.19, Python +0.11, Java +0.11, but **about 0 in C and Go**.

**6. Keyword signals say little about hubs once tests are removed.** The first pass showed `def_test` -0.48 and `def_encapsulation` +0.33 with fan-in; both are artifacts (tests are called by nobody by construction; encapsulation tracks public API). With tests removed on both sides and common names excluded, the only consistent signals are weak: branching **+0.17 (13 of 13 languages)**, class start -0.22 (4 of 4), decorators -0.15 (6 of 6); the rest are 0.11 or smaller.

**7. Common callee names show where the call lists are noisy.** The top-20 names take 6.5% (C++) to 30% (Go) of call sites. The lists include syntax and test tokens: Rust `Some`, `pub`, `let`, `Ok`; Go `func`; Kotlin `when`, `TODO`; C# `foreach`, `nameof`; PHP `foreach`, `isset`, `array`; C `FIXME`, `ARRAY_SIZE`, `ok`; plus test assertions in every language. So distinct-calls counts in this database are inflated by non-calls, more in some languages than others. The current resolver separates call kinds; whether it removes these tokens in the extraction step that fills `calls_out_to` is not checked here.

## What this suggests for sensors
- **Parameter count is a usable, independent descriptor** (weak size link) for an "interface width" reading; 8 or more parameters is about 1% of functions: a short, actionable list.
- **Fan-in is the call-graph quantity that does not reduce to size** (size correlation about 0 in most languages): the 1% of functions that take a third of the calls are where reach matters, and they look like small public helpers, not big functions.
- **Distinct-calls is a size measure** (0.5 to 0.7 with lines) and should not be added as a separate gauge.
- **Keyword signals add little beyond size and parameters for graph position**; branching is the one that holds in all languages.

## Caveats
Name-matched fan-in with unique-name selection biases toward distinctive names and drops methods that share names (the common case in object-oriented code), so Java, C# and Dart fan-in is the least reliable; 5+ lines excludes one-line accessors; sampled up to 250k to 400k functions per language; signals that fire in under 2% of a language's functions were dropped; pooling by median over languages hides large between-language differences, which are shown where they matter; test functions are identified by the engine's own `def_test` count.


## 8. Replication on v2.12.0 with engine-resolved fan-in (2026-11-17)
**Data:** `master_db_v2.12.0-b64f42bf.db` (8,173,786 functions, 580 repositories, 56 languages), which has the engine's own `func_fan_in` and `func_fan_out` per function. Check of what `func_fan_in` is: in the per-repo scan of curl (v2.12.0, `gitgalaxy-raw-output`), it equals the number of distinct calling functions in `fcall_data` for 6,491 of 6,644 functions (98%). Code `tools/sensor/pop2_load.py`, `pop2_analyze.py`; output `population_args_calls_v2120_output.txt`. Same method as before (size-controlled Spearman, pooled by median over languages). Fan-in here includes calls from test code (it cannot be removed from the count); test functions are removed as hubs.

**Replicates (same numbers within a few hundredths):**
- Parameter count is its own axis: 5 or more parameters C 7.7%, Python 7.1%, C++ 7.0%, Rust 4.5%; 8 or more about 1%; size correlation 0.2 in C, C++, Python, Java and about 0 in C#, Dart. Distinct calls track size 0.52 to 0.75.
- No consistent link between parameters and distinct calls once size is removed (Java -0.15, PHP -0.18, Python -0.09, C -0.08, Go +0.08, JavaScript +0.07, the rest within 0.06).
- Keyword signals at fixed size: tests take fewer parameters (-0.32, 11 of 12 languages) and call more distinct things (+0.20, 12 of 12); branching +0.20 and safety checks +0.13 with more parameters; closures +0.15, comprehensions +0.18, I/O +0.10, memory allocation +0.10 with more calls.
- Heavy tail, now counted by the engine over all functions: the **top 1% by fan-in hold 46% of resolved calls, the top 5% hold 68%, the top 10% hold 84%**; 65% have no recorded caller, 21% exactly one, 1.7% have 10 or more.
- Fan-in goes with parameters in most languages (size-controlled): Ruby +0.40, PHP +0.31, Dart +0.30, JavaScript +0.22, TypeScript +0.17, Kotlin +0.17, Python, C#, Java, Go, Rust +0.11 to +0.12; about 0 in C and C++.
- Branching goes with fan-in (+0.11, 13 of 13 languages); class start -0.18 (4 of 4); decorators -0.09 (7 of 7); state flux +0.07 (13 of 13).

**Does not replicate: retracted from sections 5 and 6.**
- *"Hubs are small."* Fan-in rises with size in every language (raw rank correlation +0.07 to +0.19); hubs are slightly larger than leaves in Python (18 vs 11 lines), JavaScript (13 vs 10), TypeScript, C# and Dart. Only C and Java are smaller. The earlier result came from keeping only names defined once.
- *"Hubs are public."* Holds in C only (80% vs 35%; size-controlled +0.13). In Java, C#, Dart, PHP, Python and Go hubs are less often public than leaves (-0.18 to -0.32); `is_public` means different things per language, so no cross-language claim.
- *"Hubs call fewer distinct things."* Size-controlled fan-in versus distinct calls is about 0 (C -0.06, C++ -0.01) or positive (Rust +0.17, Dart +0.16, TypeScript +0.12, Kotlin +0.12).
- Java and Dart "many parameters, fewer calls" (-0.28 each): Dart is 0.00 and Java -0.15 here.
- `def_encapsulation` with fan-in: now +0.22 (9 of 10 languages) with tests removed, so it was not a test artifact; the first-pass drop to +0.07 was an effect of the name-matched restriction.

**New:** `arch_api` -0.15 (8 of 10 languages) and `arch_ui_framework` -0.12 (4 of 4) go with lower fan-in.

**Call lists are cleaner in v2.12.0.** The commonest callee names no longer include `func`, `pub`, `let`, `foreach`, `when`, `nameof` or `FIXME`; what remains is real calls and constructors (Rust `Ok`, `Some`), macros and conversions (C `ASSERT`, `TRACE`; Go `string`, `byte`) and test assertions (every language; Kotlin still shows `DEBUG_INFO_EXPRESSION_TYPE`, a compiler-test marker). Distinct calls versus the engine's resolved fan-out correlate 0.40 to 0.77, since fan-out counts only calls resolved inside the repository.

**What it suggests, revised.** Parameter count: a usable independent reading (unchanged). Fan-in: still the call-graph quantity not reducible to size (size correlation 0.1 to 0.2), and the concentration is stronger than first measured (1% of functions take 46% of calls); but what a hub looks like depends on the language, so a sensor should show fan-in as a count with the function's own size and parameters, not a "small public helper" profile. Distinct calls remains a size measure.
