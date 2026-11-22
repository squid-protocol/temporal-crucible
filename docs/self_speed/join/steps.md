# Exploratory join: speed steps x commits (GitGalaxy on itself)

Speed = CPU seconds per mapped file, median over repeats; ratio = later / earlier engine. Kinds: core = scan-path engine code; standards = pattern tables/rule data; translator_tools = gitgalaxy/tools/*.

| interval | commits | core +/- lines | standards +/- lines | translator +/- | core funcs born/died/changed | kw-rosetta per-file x | cics per-file x | lang-crucible per-file x (cpu x) |
|---|---|---|---|---|---|---|---|---|
| 2026-03-21 -> 2026-04-13 | 69 | 25402/11538 | 23148/33738 | 0/0 | 29/54/53 | 2.66 | 1.26 | 1.71 (1.42) |
| 2026-04-13 -> 2026-05-26 | 86 | 12215/22581 | 13840/413 | 8531/4203 | 152/140/6 | 1.14 | 1.15 | 1.03 (1.03) |
| 2026-05-26 -> 2026-07-09 | 88 | 16820/12946 | 16162/8994 | 3310/2779 | 107/83/59 | 0.99 | 1.03 | 0.88 (0.94) |
| 2026-07-09 -> 2026-07-27 | 395 | 4074/2175 | 1764/798 | 917/568 | 23/2/59 | 1.00 | 1.00 | 0.99 (1.00) |
| 2026-07-27 -> 2026-08-13 | 675 | 3100/1460 | 3933/1165 | 75/78 | 23/8/53 | 1.25 | 1.15 | 1.33 (1.35) |
| 2026-08-13 -> 2026-08-31 | 795 | 4321/1085 | 16778/14950 | 0/0 | 24/0/40 | 1.01 | 1.03 | 0.99 (1.02) |
| 2026-08-31 -> 2026-09-16 | 296 | 7701/1868 | 12158/3873 | 25/29 | 111/3/67 | 1.18 | 1.32 | 0.86 (0.88) |
| 2026-09-16 -> 2026-10-02 | 685 | 23818/2327 | 9785/7664 | 30305/1958 | 464/3/84 | 7.61 | 1.14 | 1.68 (1.81) |
| 2026-10-02 -> 2026-10-18 | 910 | 7878/1432 | 8279/765 | 28035/4051 | 212/6/73 | 0.99 | 1.22 | 0.77 (0.23) |
| 2026-10-18 -> 2026-11-04 | 1902 | 9320/3519 | 10934/444 | 18593/8206 | 257/3/89 | 1.04 | 0.99 | 1.03 (1.03) |
| 2026-11-04 -> 2026-11-20 | 794 | 7214/542 | 3362/420 | 6829/1229 | 219/0/77 | 1.04 | 1.05 | 1.42 (1.42) |

## Performance-worded commits per interval (subjects matching a keyword list; not a measure of what changed)

### 2026-03-21 -> 2026-04-13 (3 of 69 commits)
- 2026-03-30 `1c130f2170` focusing and speed tuning from 2nd batch of 40 repos  [core:9f, standards:1f]
- 2026-03-26 `c393f43cc8` more mobile optimization  []
- 2026-03-26 `7c39247352` mobile optimization rendering  []

### 2026-04-13 -> 2026-05-26 (0 of 86 commits)

### 2026-05-26 -> 2026-07-09 (1 of 88 commits)
- 2026-06-23 `6c30a7b0c1` feat(ci): add Muninn security scanning, harden workflows, and patch core ReDoS vulnerabilities (#71)  [standards:1f]

### 2026-07-09 -> 2026-07-27 (8 of 395 commits)
- 2026-07-27 `2b21d6c939` Strict tests for yaml, fix 5 real bugs (1 ReDoS) (#681)  [standards:1f]
- 2026-07-26 `40c2e1f033` Close #603: strict tests for php, fix 9 real bugs (1 ReDoS) (#661)  [standards:1f]
- 2026-07-26 `76f0d227fe` Close #588: strict tests for java, fix 2 real bugs (1 ReDoS) (#655)  [standards:1f]
- 2026-07-26 `5ee15d7b29` Close #611: strict tests for solidity, fix 1 ReDoS + 2 boundary bugs (#643)  [standards:1f]
- 2026-07-26 `f31339223b` Cross-language ReDoS sweep: fix 8 quadratic-blowup regexes across 8 languages (#631)  [standards:1f]
- 2026-07-24 `bef1da6d7e` Bump mistune to 3.3.4, patching a batch of newly-disclosed CVEs (#396)  []
- 2026-07-21 `b527e50828` Feat/dependency audit cache (#283)  [core:2f]
- 2026-07-17 `93074b7fb0` refactor(aperture): optimize gating sequence for compute cost and sync terminology  [core:1f]

### 2026-07-27 -> 2026-08-13 (16 of 675 commits)
- 2026-08-13 `d9c3b1d49d` docs(skills): strengthen premature-completion gotcha guidance based on 2nd batch's near-universal hit rate  []
- 2026-08-10 `7566d91f30` fix: ruff PERF401: list-comprehension findings in core engine fil (#1161)  [core:4f]
- 2026-08-10 `e3fa98e7c2` perf: replace manual append loops with extend (#1201)  [core:1f]
- 2026-08-06 `d53713f84e` docs(wiki): stop the homepage index overpromising completeness (#1127)  []
- 2026-08-06 `2f97cb0b23` docs(wiki): add discovery index for LLM-reports directory (#1125)  []
- 2026-08-06 `d120d44b22` docs: back the speed claim with the fitted rate model, not a single example (#1113)  []
- 2026-08-05 `1b44b16a9e` docs: clarify extraction vs strict tests naming and ReDoS coverage (#1084)  []
- 2026-08-05 `92dd7b02c8` test(extraction): add geometric redos sweeping tool to verify strict rules (#1071) (#1083)  []
- 2026-08-05 `623f5ef31e` test(extraction): add ReDoS regression coverage for haskell/kotlin/lua/ruby/scala/swift (#1077)  []
- 2026-07-30 `78bd26a55f` Fix 3 more flaky timing-based ReDoS regression tests (#806)  []
- 2026-07-30 `689673abeb` Fix/713 spec exposure redos sweep (#805)  []
- 2026-07-30 `764dbc317a` Fix flaky spec_exposure ReDoS sweep test (CI failure on macOS/Python 3.9) (#800)  []
- 2026-07-30 `62803bcb02` Fix #713: bound spec_exposure ReDoS across remaining 17 vulnerable languages (#798)  [standards:1f]
- 2026-07-28 `275634bc6e` Fix #706: Short-circuit ls-files fallback to prevent timeout trap (#719)  [core:1f]

### 2026-08-13 -> 2026-08-31 (3 of 795 commits)
- 2026-08-23 `7e2808c964` fix(regex): resolve ReDoS timeout in typescript args extraction (#2156)  [standards:1f]
- 2026-08-14 `8b1be2e5e7` chore(deps): bump fastjsonschema from 2.21.2 to 2.22.1 (#1571)  []
- 2026-08-13 `e3e47862de` docs: expand Claim 3 with grammar-staleness timeline, log m4/batch under Claim 1 (#1562)  []

### 2026-08-31 -> 2026-09-16 (18 of 296 commits)
- 2026-09-16 `43f4ec2934` Add REXX (rexx), resolving the .cmd collision with batch (#2504) (#3107)  [core:2f, standards:7f]
- 2026-09-15 `115f265465` perf(detector): required-literal prefilter for the shared coding_analysis rule pass (#3070)  [core:2f]
- 2026-09-15 `10a5b46666` perf(detector): hoist the is_public api-window check out of an O(F*A) scan (#3068)  [core:1f]
- 2026-09-15 `68ff0c3885` perf(detector): skip =-less lines before the var-decl backtracking regex (#3063)  [core:1f]
- 2026-09-15 `79074c5f0f` perf(network): memoize Stage-2 candidate stem-stripping in import resolution (#3062)  [core:1f]
- 2026-09-14 `999fa01ba5` perf(detector): cache per-language rule eligibility in coding_analysis (#3053)  [core:1f]
- 2026-09-14 `67077c9868` fix(objectivec): remove ReDoS in func_start lookahead (catastrophic on C headers) (#3050)  [standards:1f]
- 2026-09-14 `46a6aff44c` perf: kill ReDoS + O(N^2) splice hot paths behind v2.7.0 speed outliers (#3043)  [core:1f, standards:2f]
- 2026-09-14 `db34c9a46c` Native graph engine: shared CSR graph index + parity/benchmark harness (#3034) (#3042)  [core:2f]
- 2026-09-09 `fba51ca925` feat(tools): the score-contract tooling batch — closes #2916 (#2931)  []
- 2026-09-09 `2253d3ec9d` chore(perf): clear ruff PERF401 & PERF203 backlog (#469 cluster) (#2921)  [core:7f, standards:1f]
- 2026-09-09 `172d34937a` ci: dedupe concurrent runs, parallelise pytest, and de-flake the ReDoS timing asserts (#2901) (#2919)  []
- 2026-09-08 `1a60f47ace` domain sensors: declare the 40 unplanted, ungated sheet rows in one batch (#2897) (#2900)  [standards:1f]
- 2026-09-04 `b7d94ede4a` chore(deps): bump fastjsonschema from 2.22.1 to 2.22.2 (#2708)  []

### 2026-09-16 -> 2026-10-02 (30 of 685 commits)
- 2026-10-02 `3cdbb79a64` Proofs 5x faster: Db2 cases side by side on a database pool, databases held active, batched CLP calls, per-estate cache (#4180)  []
- 2026-10-02 `a5ff38e845` fix(python): vectorized_math ignores '@' in strings and comments (#4136) (#4148)  [core:1f, standards:2f]
- 2026-10-01 `79d9b311aa` CardDemo batch: four more programs proven; loop and harness fixes the batch wave found (#4087)  []
- 2026-10-01 `ce83815849` Test-strengthening loop: batch cases -- new records built from an existing one and its layout (#4049) (#4077)  []
- 2026-09-30 `943760d47e` Mutation testing of the proven ports, with a validated fast mode (#4047) (#4057)  []
- 2026-09-29 `39d36bb47e` Fix #3992: no-JCL batch controller names an undefined <File>DTO (#3994)  []
- 2026-09-27 `c69bea3578` #3913: Full Suite Gate out of its timeout: small scans skip the worker pool, and Windows/macOS scans now match Linux (#3916)  [core:2f]
- 2026-09-26 `02ae597fbb` Call-graph comparison tooling: reference contract + cache, triage, one-command check, explain, session hook (#3773–#3776, #3778) (  []
- 2026-09-26 `e8c37d36a0` Engine: resolve the program a batch runner runs (#3710) (#3742)  [core:5f, standards:1f]
- 2026-09-26 `2e8e14b7e1` feat(cobol-to-java): JCL job flow -> Spring Batch jobs (#3622) (#3711)  [core:3f]
- 2026-09-25 `f7b7e32984` Python: record module-level calls (`app = FastAPI()`, `@app.post(...)`) in a calls-only `__global_context__` unit (#3704)  [core:7f, standards:2f]
- 2026-09-24 `42e4a71414` Mainframe fact channel: batch CALL USING contracts (#3454) (#3475)  [core:8f]
- 2026-09-23 `38bdf3edf7` batch: func_start for `call :label` subroutines (#3338) (#3380)  [core:2f, standards:1f]
- 2026-09-23 `34f6a3e141` perf(#3182): linear JS/TS func_start start anchor on blank runs (nx wall -73%) (#3335)  [standards:2f]

### 2026-10-02 -> 2026-10-18 (58 of 910 commits)
- 2026-10-18 `bd8098dd65` tools: DOOM speedrun libclang subset oracle, --clang PORTS (Part of #5468) (#5533)  []
- 2026-10-18 `02822447c5` tools: DOOM speedrun `diff` subcommand -- before/after and round-2 comparison of clean_check.csv (Part of #5468) (#5529)  []
- 2026-10-18 `f07a307fbd` tools: DOOM Port Speedrun harness -- pinned 39-port manifest, clone/scan driver, clean-scan scorer (Part of #5468) (#5515)  []
- 2026-10-18 `4f54e51ba5` ci: seed the Generated Java same-base cache from its own uncancellable workflow (Part of #5142) (#5434)  []
- 2026-10-18 `3e2e623f86` Shepherd workflows keep and use the learned-flake cache (Fixes #5398) (#5456)  []
- 2026-10-18 `15ad5caf64` prefetch: read the POSIX_FADV_WILLNEED constant with getattr, fall back to the read loop (Part of #5444) (#5454)  [core:1f]
- 2026-10-18 `8001edc1d1` perf: opt ada and yacc state_mutation into _line_gates (Part of #3171) (#5439)  [standards:2f]
- 2026-10-18 `21cbcb3f0a` perf(security): scan one line per distinct shape of a repetitive directive table (Part of #3188) (#5441)  [core:2f]
- 2026-10-18 `6c74abc779` phase_ab: --evict and per-leg --env; cold-storage prefetch A/B and warm no-regression numbers (Part of #3189) (#5431)  []
- 2026-10-18 `d4c96a7406` perf(tools): combined-alternation candidate-finder parity harness (Part of #3073) (#5428)  []
- 2026-10-18 `a33d9a0eac` shepherd_gh: pass the learned-flake set to ci_digest, cached across workflow runs (#5421)  []
- 2026-10-18 `11a7494580` trial: a DISPLAY-only batch program is eligible (Part of #3806) (#5411)  []
- 2026-10-18 `66129e7b3f` tests: cut the CICS linearity tests to 3 repeats on smaller inputs (Fixes #5406) (#5408)  []
- 2026-10-18 `1b336901cb` mutation: scores and triaged survivors for six CardDemo batch ports (Part of #4047) (#5405)  []

### 2026-10-18 -> 2026-11-04 (101 of 1902 commits)
- 2026-11-04 `ea87b94eb4` Batch Badlands: record the first-time run in levels.json (Part of #7065) (#7724)  []
- 2026-11-04 `c98eab561a` gap_prevalence: key census 'undeclared item' / 'PERFORM: undeclared paragraph' as source defects, owner #7647 (Part of #5865, #764  []
- 2026-11-03 `c3f9c500e6` os-smoke-grid: every step gets its own timeout-minutes (#7618) (#7622)  []
- 2026-11-02 `ec5594ec65` Equivalence E2E: retry a Maven dependency-resolution failure once with -U, scrub cached misses (Part of #7561) (#7563)  []
- 2026-11-02 `41d2437742` Vectorized Math: python torch/np product methods, tf.js camelCase products (Part of #4108) (#7558)  [standards:3f]
- 2026-11-02 `51bb6e65e3` golden_export: a batch case's COBOL outputs as golden files, byte-exact check of a Java run (Part of #4052) (#7545)  []
- 2026-11-01 `12269cac3e` docs: a code factory bottlenecks log (Part of #7455) (#7466)  []
- 2026-10-31 `8b4463cc67` batch forge: a lowered DFSORT step's service compiles and runs against the forge's real CobolRecords; a lowered step only exists i  []
- 2026-10-31 `0c744a5121` equivalence: a multi-step job case (kind job): batch steps chained through datasets, each proven (Part of #4268) (#7256)  []
- 2026-10-31 `7666f647ec` batch forge: a lowered DFSORT step runs in the generated job via its det translation (Part of #4268) (#7244)  []
- 2026-10-31 `3b0aeb5808` X-Ray: stop claiming XOR loops; print only the repeated indexed XOR it detects (Part of #7187) (#7242)  []
- 2026-10-31 `8d91e7eabe` Smoke Tests: fold the durations lookup into the planning job (Part of #7155) (#7225)  []
- 2026-10-31 `371c774aff` batch forge: a SORT step with a stated DCB LRECL/RECFM is lowered to its COBOL SORT/MERGE program (Part of #4268) (#7164)  [core:1f]
- 2026-10-30 `af292b794a` batch forge: an IDCAMS REPRO INFILE/OUTFILE step is a record copy; other commands refused by name (Part of #4268) (#7196)  []

### 2026-11-04 -> 2026-11-20 (39 of 794 commits)
- 2026-11-20 `619e1a9c61` Timing tests: convert last 2 wall-clock offenders, allowlist the redos supervisor with a reason (Part of #8423) (#8740)  []
- 2026-11-20 `54cf72ab54` CI: ci_retry.sh infers a cache probe for a digest-pinned docker pull (Part of #8424) (#8705)  []
- 2026-11-20 `bfe571bb4f` Timing tests: convert the Haskell juxtaposition ReDoS tests to assert_cpu_below (Part of #8423) (#8711)  []
- 2026-11-19 `38fe005d48` feat(security): --offline on the test forge, batch harness and proof_reach (Part of #8624) (#8665)  []
- 2026-11-19 `eba2d232f5` CI: ci_retry.sh gets a cache-first probe and a cause line (Part of #8424) (#8658)  []
- 2026-11-19 `50044cb164` tests: four 4108 probe ReDoS checks use the CPU-clock helper (Part of #8423) (#8660)  []
- 2026-11-18 `a70f86d742` perf(l5): compile only the program per mutant, time in-process proofs from the unmutated port (Part of #8599) (#8637)  []
- 2026-11-18 `f68fa8d56c` ci: referee panel reads the shared mainframe-corpora cache (upstream example-health-apis is gone) (#8621)  []
- 2026-11-18 `3a8bd5887b` tests: 6572 import-scan linearity tests use the CPU-clock helper (Part of #8423) (#8597)  []
- 2026-11-16 `c07e2beaf0` cobolrt: fast paths (#4717), CobolProfile (#4714), RuleTelemetry (#4713/#4716), CICS shims (#8486), and guards (#8423) (#8537)  []
- 2026-11-16 `d5a5dc7ca3` docs: 08-14 says the gauge measures what a file offers, not what uses it; index and nav entries for the 08-24 reach page (#8533)  []
- 2026-11-16 `036a3dae1c` tests: one CPU-clock helper for ReDoS harnesses and linearity check (Part of #8423) (#8523)  []
- 2026-11-16 `a9dbb20f19` evidence-refresh: step timeout so a hung det-mutation refresh still keeps its ledgers (Part of #8509) (#8514)  []
- 2026-11-15 `7a42a14fa5` tools(mutation): speedups, triage CLI tools, and 360 auto-triaged survivors (#8485)  []
