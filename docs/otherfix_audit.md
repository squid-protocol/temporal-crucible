# `other-fix` precision audit (gate: >= 0.70 per repo, as in `xc_label_audit.md`)

**2026-11-11.** `other-fix` is `xc_harvest.py`'s residual class: a **fix-like message** with 1-50 C files
that is not a known security-fix event, not a revert / regression-word / recent-sha reference, and does
not name an environment. It is not a dumping ground for unclassifiable commits - commits whose message
is not fix-like are dropped outright (`not a fix`, e.g. 23,371 of them in postgres). But it carries
**85-97% of the outcome mass in every repo** (28,601 events across the 8), so it is the de facto
dependent variable of every file-year model in this programme, and `xc_label_audit.md` never covered it.

The question is therefore not *"is this the right class"* - there is no narrower class to be right
about - but the precision of the `FIXLIKE` gate itself: **does this commit repair behaviour that was
wrong?** Judged NOT a fix: docs / javadoc / comments / prose typos, tests-only, lint / style /
checkstyle / mypy / type annotations, build / deps, features, refactors, cosmetic changes.

Seeded random sample (seed 2982), 30 per repo, drawn only from `other-fix`, judged from the commit
subject. Sample drawn by `tools/otherfix_sample.py`.

## Summary

| repo | language | precision | `other-fix` events | verdict |
|---|---|---|---|---|
| libxml2 | C | **24/30 = 0.80** | 2,576 | PASS |
| postgres | C | **23/30 = 0.77** | 13,436 | PASS |
| redis | C | **22/30 = 0.73** | 3,165 | PASS |
| libgit2 | C | **19/30 = 0.63** | 2,201 | **FAIL** |
| sphinx | non-C | **18/30 = 0.60** | 3,507 | **FAIL** |
| prometheus | non-C | **12/30 = 0.40** | 2,403 | **FAIL** |
| commons-lang | non-C | **8/30 = 0.27** | 1,028 | **FAIL** |
| ripgrep | non-C | **8/30 = 0.27** | 285 | **FAIL** |

- **Pooled, unweighted: 134/240 = 0.558**
- **Weighted by outcome mass: 0.682** — just under the 0.70 gate
- **C repos pooled: 88/120 = 0.733** (3 of 4 pass) · **non-C pooled: 46/120 = 0.383** (0 of 4 pass)

## What fails, and why

The gate holds on C and collapses outside it, and the reason is visible in the samples: in the Go,
Java, Python and Rust projects, "fix" overwhelmingly introduces a *non-behavioural* change.
prometheus contributes `fix lint error`, `chore: fix httpNoBody issues from gocritic`, `TSDB: Fix
master tests`; commons-lang is dominated by `[javadoc] Fix ...`, `Fix Checkstyle`, `Fix benchmarks`;
sphinx repeats `Fix mypy violations` and `Fix lints`; ripgrep's `other-fix` class is mostly `doc: fix
typo`. These communities use "fix" for tooling and prose hygiene far more than C projects do, so a
language-blind keyword gate inherits their vocabulary, not their defects.

This is the same failure mode, and the same size, as `extrinsic` in round 1 of `xc_label_audit.md`
(0.30-0.40, FAIL), which amendment 1's rule v2 lifted to 0.90-1.00. The precedent says a tightened
rule can fix this.

## What it means for results already published

- **CGR's own caveat is confirmed and quantified.** Its "fix labels outside C come from keyword rules
  not yet audited" is now measured at **0.38** precision outside C.
- **This explains CEIL's non-C reading**: the non-C half realised less of its attainable AUC
  (0.736 vs 0.797) than the C half, which is what a noisier outcome predicts.
- **The CGR replication conclusion probably survives, but its non-C effect sizes are not trustworthy.**
  Network effects were *larger* in non-C (coupled 1.63 vs 1.46), and random label noise attenuates
  rather than manufactures. But this noise is **not** random: docs, lint and test commits touch
  doc/test paths and frequently-churned files, which can inflate churn, author and coupling
  associations instead of diluting them. The sign cannot be guaranteed from the audit alone.
- **The C-only arms of CEIL and the M1 re-fit are the ones to quote.** `c_only` is 0.733, over the gate.

## Recommendation

1. Tighten `FIXLIKE` the way amendment 1 tightened `extrinsic`: require a behavioural fix word and
   **exclude** docs/javadoc/comment, test-only, lint/style/type-checker, build/deps and feature
   markers; consider excluding commits whose touched paths are entirely under test or doc trees.
2. Re-harvest and re-audit, gate >= 0.70 per repo, before any non-C claim is quoted again.
3. Until then, report file-year results **C-only**, and label the 5-language replication as resting on
   an unaudited outcome outside C.

## Full sample and verdicts

`[x]` = judged a real defect fix · `[ ]` = judged not a fix.

### libgit2 — 19/30 = 0.63

- [ ] `4e15c9c87f` (1f) tests: fix clar declarations
- [x] `1e015088d0` (2f) git_commit_summary: ignore lines with spaces
- [x] `1db9d2c3bb` (1f) Ensure that commits don't fail if committing content that already exists
- [x] `83c93a7cc2` (1f) merge_driver: fix missing `goto done;`
- [x] `10ac298c62` (2f) attr_file: fix unescaping of escapes required for fnmatch
- [x] `dd0b1e8cb6` (1f) openssl_stream: fix releasing OpenSSL locks
- [x] `951d06e4e9` (1f) Fixed placement of pointer argument.
- [x] `e7d0ced219` (1f) Fix longstanding valgrind warning
- [x] `6ee6861123` (1f) cache: fix race condition
- [ ] `e46ef5eeb2` (1f) docs: fix typo
- [ ] `ca1e3dbb06` (1f) Fix docs for git_odb_stream_read return value.
- [x] `bed00cd032` (2f) smart: ignore shallow/unshallow packets during ACK processing
- [ ] `46a78f79da` (1f) tag.c: fix tiny typo
- [ ] `c4958e6818` (1f) Fix documentation comment
- [x] `3101a3e5b8` (4f) refs: Do not overflow when normalizing refnames
- [x] `65ca81a63e` (2f) Minor error fixes
- [ ] `0f4d9c0367` (7f) Fixed Xcode 6.1 build warnings
- [x] `3de79280e3` (1f) cache: Fix deadlock
- [x] `8fa5881885` (1f) fix interactive rebase detect.
- [ ] `19c88310cb` (4f) tree-cache: move to use a pool allocator
- [ ] `76159921f4` (1f) index: rework index entry initialization routine
- [x] `0494a7c9a9` (1f) describe: Do not crash if pass null option to git_describe_commit()
- [x] `db853748f6` (1f) Fixed GIT_DIFF_UPDATE_INDEX not being aware of executable bit changes
- [x] `88cfe61497` (2f) git_checkout_tree options fix
- [ ] `f8263472d1` (1f) Fixed git_revert() documentation
- [x] `31f8f82a65` (1f) diff_driver: detect memory allocation errors when loading diff driver
- [ ] `e51e29e84c` (3f) config_parse: have `git_config_parse` own entry value and name
- [ ] `cce966c3d8` (1f) Change bare free to allocator free.
- [x] `83b351812f` (1f) transport/http: Include non-default ports in Host header
- [x] `f647bbc88d` (2f) tree: fix mode parsing reading out-of-bounds

### postgres — 23/30 = 0.77

- [x] `3e1683d37e` (1f) Fix, or at least ameliorate, bugs in logicalrep_worker_launch().
- [x] `764cb2b596` (1f) Fix typo in pg_dump's support for dumping collations from pre-v10 servers.
- [x] `64a2e1fdef` (1f) Apply quote_literal to the start_with argument of connectby. Fixes problem reported by David Garamond when working with bytea parent and child keys.
- [x] `0daeba0e92` (1f) Be more paranoid in ruleutils.c's get_variable().
- [x] `b32a25c3d5` (1f) Fix booltestsel() for case where we have NULL stats but not MCV stats.
- [ ] `f6a0863e3c` (1f) Allow transactions that don't write WAL to commit asynchronously.
- [x] `882b2cdc08` (1f) Use valid compression method in brin_form_tuple
- [x] `e1c83e7b96` (1f) Fix untranslatable log message assembly
- [x] `7558cc95d3` (1f) Error out on send failure in walsender loop.
- [x] `c1669fd581` (1f) Fix instance of elog() called while holding a spinlock
- [x] `38f4328981` (1f) Fix pg_isready to handle -d option properly.
- [ ] `8776faa81c` (5f) Adjust SP-GiST WAL record formats to reduce alignment padding.
- [x] `263c19572b` (1f) Properly initialize write, flush and replay locations in walsender slots
- [x] `8409b60476` (2f) Revert the behavior of inet/cidr functions to not unpack the arguments.
- [x] `c3928b467a` (1f) Fix segfault during EvalPlanQual with mix of local and foreign partitions.
- [x] `05c0258966` (1f) Fix bug #16784 in Disk-based Hash Aggregation.
- [ ] `51f41e8c0a` (2f) Fix typos in comments.
- [x] `a472ae1e4e` (1f) Fix Hot Standby feedback sending when streaming busily.
- [x] `10c0558ffe` (7f) Fix several mistakes around parallel workers and client_encoding.
- [x] `92c49d1062` (5f) Fix insertion of SP-GiST REDIRECT tuples during REINDEX CONCURRENTLY.
- [ ] `8dd43894b1` (1f) Fix XLogPageRead() comment
- [ ] `325f54033e` (1f) Add test_dsa module.
- [x] `0e758ae89a` (1f) Fix failure to remove non-first segments of temporary tables.
- [x] `9711fa0608` (1f) Fix undersized result buffer in pset_quoted_string().
- [x] `6b4d860311` (1f) Fix JITed EEOP_AGG_INIT_TRANS, which missed some state.
- [x] `d7e4fd99e5` (1f) Fix bug introduced into indexable_outerrelids() by an ill-considered "optimization".  When we find a potentially useful joinclause, we have to add all
- [ ] `d99df62c31` (1f) Bruce Momjian <pgman@candle.pha.pa.us> writes: > OK, add #include <stdio.h> to the file.  That should fix it.
- [x] `fcd77a6873` (1f) Fix minor memory leaks in pg_dump.
- [ ] `bbbe825f5f` (25f) Modify processing of DECLARE CURSOR and EXPLAIN so that they can resolve the types of unspecified parameters when submitted via extended query protoco
- [x] `ecd275718b` (1f) Don't set the truncation block length greater than RELSEG_SIZE.

### libxml2 — 24/30 = 0.80

- [x] `cc199e0e56` (1f) applied patch from Patrick Welche provided in bug #125432 , future
- [x] `2406abda9c` (1f) Fixes bug #106931 in XInclude entities merging. Daniel
- [x] `1fd36d2723` (2f) fixed a URI-Reference computation problem when validating small cleanup
- [ ] `bc7ab5a2e6` (2f) tree: Rewrite xmlSetTreeDoc
- [x] `a22bd982bf` (1f) malloc-fail: Fix memory leak in xmlStaticCopyNodeList
- [x] `1a89323039` (1f) [CVE-2024-40896] Fix XXE protection in downstream code
- [x] `70bf754e24` (1f) html: Fix pull-parsing of incomplete end tags
- [ ] `adf5ec9496` (3f) Cleanups of lzma support
- [x] `b19d353970` (1f) html: Fix EOF handling in comments
- [x] `5b9dde3eed` (1f) xmlTextReaderReadOuterXml should handle DTD * xmlreader.c: fix description of xmlTextReaderReadOuterXml and support DTD
- [ ] `9f28f30a17` (1f) avoid a warning bug #71594 Daniel
- [x] `9ca816b3a6` (1f) Fix a couple of return without value
- [x] `2df2de225a` (1f) more RelaxNG bug hunting Daniel
- [x] `645a924a9d` (1f) fixed problem concerning XPath context corruption during function argument
- [x] `ce02dbc430` (1f) Mikhail Sogrine pointed out a bug in HTML parsing, applied his patch added
- [x] `b2517d850d` (1f) Fix error on output of high codepoint charref like &#x10FFFF; , reported
- [x] `dc2dde1ab9` (1f) malloc-fail: Fix null deref in xmlXIncludeLoadTxt
- [x] `ec05f04d8b` (1f) malloc-fail: Fix memory leak in xmlXIncludeLoadTxt
- [x] `fc256953d2` (1f) malloc-fail: Fix memory leak in htmlCreateMemoryParserCtxt
- [x] `310564cc6b` (2f) schemas: Fix relative schemaLocation resolution in XSI assembly in streaming mode
- [x] `e392497e4c` (1f) John Kroll provided a small fix to xmlNanoHTTPSave Daniel
- [x] `a8c0adbc39` (1f) fixing bug #98792 , node may have no doc and dereferencing without
- [x] `d8ed1051fa` (1f) fixed bug #407436 a crash in a specific case of Relax-NG validation Daniel
- [ ] `5e7c72cd5c` (5f) doc: Misc fixes
- [ ] `f93a67e9c9` (3f) tiny fix from Albert Chin portability cleanup for arch needing trio for
- [x] `7ffcd44d7e` (1f) Fix memory leak in xmlSchemaValidateStream
- [x] `7fd7a94aa8` (1f) fixed a stupid bug when renaming a function Daniel
- [x] `c71154dad3` (1f) buf: Add check of return values in xmlBufferCreateStatic
- [x] `7f8585025f` (5f) Attribute nomarlization closing bug #3597 Small fixes in encoding.c First bits of real progressive parsing,    Daniel
- [ ] `e43579b2d4` (1f) small doc improvement for xmlXPathContext from Jack Jansen, fixes #524759

### redis — 22/30 = 0.73

- [x] `913e9d6bca` (1f) first skiplist fix, courtesy of valgrind
- [ ] `c51c96656b` (1f) modules API: Add test for ACL check of empty prefix (#13678)
- [x] `66f55bc5c1` (2f) Modules: block on keys: fix bugs in processing order.
- [x] `179e54d2a9` (3f) Fix for slaves chains. Force resync of slaves (simply disconnecting them)  when SLAVEOF turns a master into a slave.
- [ ] `29380ff77d` (10f) optimizing d2string() and addReplyDouble() with grisu2: double to string conversion based on Florian Loitsch's Grisu-algorithm (#10587)
- [x] `62689ef0cf` (2f) Fix undefined behavior constant defined.
- [x] `027d98e9bd` (1f) Fix assumptions that pthread functions set errno (#14284)
- [x] `7c9f6ebc8f` (1f) Diskless replica: fix disklessLoadRestoreBackups() bug.
- [ ] `db146de086` (1f) Slave removal: server.c logs fixed.
- [ ] `a698a6391a` (1f) Add maxclients and cluster_connections to INFO CLIENTS (#7979)
- [ ] `e6a5117426` (1f) Fix typo in prepareClientToWrite() comment.
- [x] `f8a6132f15` (1f) ACL: refactor+fix AUTH check in processCommand().
- [x] `2825b6057b` (1f) Fix heap overflow corruption in XAUTOCLAIM (CVE-2022-31144) (#11002)
- [x] `0232778f35` (1f) In dbOverwrite moduleNotifyKeyUnlink should use old val (#8381)
- [x] `e6fa47380a` (1f) Fix bug with module GIL being released prematurely (#8061)
- [x] `3a73be7524` (1f) master-slave replication fixed, it was not listing any key using KEYS command in the slave.
- [x] `612810af6e` (1f) sdscatrepr() fixed. Now newlines and other special chars are escaped correctly
- [x] `ba779119b8` (1f) ziplistFind(): don't assume that entries are comparable by encoding.
- [ ] `a51918209c` (2f) Fix grammar and typos (#13803)
- [x] `af035c1e1d` (1f) Modules: Fix RM_GetClusterNodeInfo() to correctly populate the master_id (#8846)
- [x] `de07deb4d2` (1f) fix server.stat_net_output_bytes calc bug
- [x] `fab099cdcf` (1f) Fix double free when loading streams with duplicate consumer PEL entries (#15095)
- [x] `6a1c92d52d` (1f) Streams: synchronous xread fixes and improvements.
- [x] `dedbf99a80` (3f) Fix dbExpand not dividing by slots, resulting in consuming slots times the dictExpand (#12773)
- [x] `60b4364fef` (1f) Fix invalid slot range merging into a valid one (#15733)
- [ ] `cabc06076b` (1f) fix comment typo in util.c
- [x] `70d848e1fa` (1f) RESTORE ability to set a TTL fixed, bug introduced with millisecond expires.
- [x] `1bcfa0f643` (1f) More fixes in the Redis command table, to make sure all the keys are detected by Redis Cluster.
- [ ] `1139070a0f` (1f) Fix trailing white space.
- [x] `b394817754` (1f) Fix memory leak in RM_UnregisterCommandFilter().

### prometheus — 12/30 = 0.40

- [ ] `de172049ab` (1f) fix lint error
- [ ] `9b5e7623f4` (6f) Add support for multiple listening addresses
- [x] `789e8224ff` (2f) Fix wrong comparison in head block resorting
- [x] `d90d0976b5` (3f) fix(bstream/writeByte): ensure it appends only one byte (#14854)
- [ ] `588eb20018` (2f) Efficient iteration and search in HashForLabels and HashWithoutLabels (#5707)
- [x] `b71a6dbbd1` (2f) tsdb/agent: Fix deadlock from simultaneous GC and write (#10166)
- [ ] `afc05129f1` (1f) fix(discovery): allow requireUpdate util to timeout in discovery/file/file_test.go.
- [x] `93ec767fed` (1f) promql: fix smoothed rate returning zero for data only after range
- [ ] `0482d93fe6` (4f) Add contexts to index writer to fix test races.
- [ ] `f540c1dbd3` (12f) Add support for histograms in WAL checkpointing (#11210)
- [ ] `47d7e3781f` (1f) [fix] remote_storage : change  "write_hander.go" to "write_handler.go"
- [x] `54a7b98cff` (2f) Fix and test ref handling in DB appender
- [x] `9c93f8f2aa` (4f) Fix various races
- [ ] `e1fd96db25` (1f) cmd: fix help text (#3989)
- [ ] `d6f9ba6310` (3f) [BUILD] Docker SD: Fix up deprecated types
- [x] `e7cfc7dae5` (2f) web: restore old path prefix behavior
- [x] `86239ee5a5` (1f) Check for timeout in each iteration of matrixSelector (#4300)
- [ ] `5ecea3c840` (1f) promtool: fix compile error from bad merge
- [ ] `43953b105b` (3f) Sorting alerts by group name in /alerts (#5448)
- [ ] `af16f35ad6` (24f) PromQL: Refactor parser to use instance configuration instead of global flags
- [ ] `b03bc16623` (4f) Update yamlv3 (#7207)
- [x] `66b0aa3b45` (1f) Fixed race condition in map iteration and map write in Discovery (#3735) (#3738)
- [ ] `b7c5ace033` (3f) fix(discovery/oci): keep API rate cap internal
- [x] `ff16fa1827` (1f) fix: fix slice init length
- [ ] `30e079bbd5` (1f) TSDB: Fix master tests (#7705)
- [ ] `05721a85d7` (1f) cmd/prometheus: fix flaky TestQueryLog console test
- [ ] `026d284c43` (16f) chore: fix httpNoBody issues from gocritic
- [ ] `61235fd851` (5f) Print system information (uname) at Prometheus startup (#2709)
- [x] `ed5f68f382` (1f) storage: Increment s.persistErrors on all persist errors
- [x] `f0003bc0ba` (3f) Don't drop ParenExpr when creating StepInvariantExpr (#9591)

### commons-lang — 8/30 = 0.27

- [x] `d49d8093e2` (1f) [LANG-754] Fix ClassUtils.getShortName to only do a reverse lookup for array types.
- [ ] `a234f033b6` (1f) Fix JavaDoc link
- [ ] `fee3e32155` (1f) [javadoc] Fix incorrect class names in RegExUtils Javadoc examples (#1564)
- [ ] `3a8907682b` (3f) Javadoc fixes and improved tests bug 21952, from Phil Steitz
- [x] `4052e9862b` (2f) LANG-1818: Fix ClassUtils.getShortClassName(Class) to correctly handle $ in valid class names (#1591)
- [ ] `817f834802` (1f) Fix internal name.
- [ ] `3e6255ec52` (2f) Fix Checkstyle.
- [ ] `ff4497aff8` (2f) LANG-1155: Add StringUtils#unwrap
- [ ] `43f9e938e3` (2f) Fix benchmarks
- [ ] `08c4a79f5c` (1f) Fixing the unit test as described in LANG-440. The truncate tests for AM_PM had been copied and were not testing againt the correct expected results. 
- [x] `d35d966e65` (2f) Add tolerance checking to indexOf methods bug 22091, from Tim O'Brien
- [x] `6dbbbb308b` (2f) fix unescapeCsv bounds error on a single quote field (#1723)
- [ ] `75b4058ac4` (1f) NumberUtilsTest - incorrect types in min/max tests #634.
- [ ] `bb6d9b6384` (1f) Fix varargs compile warnings
- [x] `c35a041022` (2f) LANG-1199: Fix implementation of StringUtils.getJaroWinklerDistance()
- [ ] `031ff96cd3` (5f) Javadoc fixes and enhancements from Steve Downey
- [ ] `0d01e050fa` (1f) Fix broken test - Sun Java and Eclipse casting nasturtiums at each other
- [ ] `4623bf1827` (1f) Fix the comment of Failable, redundant "-" (#1056)
- [ ] `097438b3b1` (2f) Fixes and better unit test code coverage from Nathan Beyer [nbeyer@kc.rr.com].
- [ ] `4453bb3ede` (1f) Fix @since for new o.a.c.lang3.stream.Streams class.
- [ ] `35f0c6f6ca` (1f) Fixed Javadoc return tag.
- [ ] `ac517f7c0d` (2f) Add parse method that handles multiple patterns bug 30674
- [x] `4ecadc12ba` (1f) Apply patch for bug 17250 (http://issues.apache.org/bugzilla/show_bug.cgi?id=17250) with some additional minor improvements.
- [ ] `d2fb3b0865` (1f) LANG-1018: add changes.xml entry
- [ ] `b66db6a04d` (1f) [javadoc] Fix typo in javadoc of Strings instances (#1406)
- [ ] `20393e09aa` (2f) Add getLength method bug 26594, from Maarten Coene
- [ ] `5f3a9a6eae` (1f) Fix formatting of isAnyBlank() and isAnyEmpty(). (#513)
- [ ] `d3e28b6802` (4f) LANG-399 - Javadoc fixes
- [x] `3513ecb0b7` (1f) Fix toString(format)
- [x] `d8faf082bb` (1f) Fix NullPointerException in FastDateParser.TimeZoneStrategy.setCalendar(FastDateParser, Calendar, String) on Java 23

### sphinx — 18/30 = 0.60

- [ ] `73b7cd51ea` (2f) Fix lints and reorder args of members_of
- [x] `7d7f1958f5` (1f) Fix #7138: autodoc: crashed when variable has unbound object
- [ ] `a80023f381` (1f) Fix mypy violations (with types-requests-2.27.3)
- [x] `e48f7eb09a` (1f) Fix interpolation error, encode inserted caption strings and add the caption in HTML output too.
- [ ] `fcc53447a3` (6f) Fix annotations (in some modules)
- [x] `91650d89c9` (3f) Fix #5291: autodoc crashed by ForwardRef types
- [x] `fae8a17026` (1f) Fixes #836: catch AttributeError when retrieving __dict__ attribute.
- [x] `638b197d25` (1f) Fix #7701: LaTeX: Anonymous indirect target causes duplicated labels
- [x] `62c49763f8` (3f) Fix broken TOC of PDFs if section includes an image
- [ ] `adfb8c2668` (2f) Fix speling.
- [ ] `fc36f90246` (3f) fix
- [ ] `9b2c1c679a` (5f) Fix #6444: test: replace example.com by existing page
- [x] `121fc4a326` (2f) Fix #1030: Make page reference names for latex_show_pagerefs translatable
- [x] `d7bf78f3ff` (3f) Fix #5070: epub: Wrong internal href fragment links
- [x] `531c27c89a` (1f) Fixed one more invalid char for make_id.
- [ ] `f5c0d64658` (4f) utils: Move "header check" to a flake8 plugin
- [x] `eec9c59fc5` (1f) Fix #7019: gettext: Absolute path used in message catalogs
- [x] `aad56c0361` (2f) Fix #3329: i18n: crashed by auto-symbol footnote references
- [x] `bda29f1a83` (1f) [IMP] util: detect incorrect locale_dirs path
- [x] `9690be4943` (2f) Fix imgmath: crashes on showing error messages if image generation failed
- [x] `13720de50c` (2f) Treat SSL failures as broken links in the linkcheck builder (#11431)
- [x] `3984c0f05c` (1f) #82: Determine the correct path for dependencies noted by docutils.  This fixes behavior where a source with dependent files was always reported as ch
- [ ] `9db86f6aab` (1f) Fix mypy violations (with mypy-0.931)
- [x] `1498897278` (1f) Oops, fix key error on refexplicit
- [x] `7894f0bd9c` (2f) Fix #2225: If the option does not begin with dash, linking is not performed
- [ ] `21ef6b7e0f` (2f) Fix mypy violation
- [ ] `c5b35efce3` (2f) Close #9560: autodoc: Allow to refer NewType with modname in py310+
- [ ] `22bec4ffe4` (1f) Fix #9623: Separate warning type 'toc.not_readable' to 'toc.excluded'
- [ ] `f48c9a6595` (1f) Fix test suite.
- [x] `98c946d8a1` (1f) Fix again. Remove the effect of DST changing by the execution time difference. refs #1182

### ripgrep — 8/30 = 0.27

- [ ] `711426a632` (5f) cli: add --no-require-git flag
- [ ] `cd1f981bea` (1f) fix: derive `Default` when possible
- [ ] `0e6e9417f1` (5f) log: add message when a binary file is skipped
- [ ] `cd9815cb37` (1f) deps: update to aho-corasick 0.7
- [x] `4782ebd5e0` (3f) core: lock stdout before printing an error message to stderr
- [ ] `b75526bd7f` (3f) output: add --no-column flag
- [x] `0407e104f6` (2f) ignore: fix problem with searching whitelisted hidden files
- [ ] `22b677900f` (3f) doc: fix some typos
- [ ] `027adbf485` (1f) ignore/types: add 'diff' file type
- [ ] `0aa31676e3` (8f) doc: fix typos
- [x] `363a4fa9b7` (1f) Fix path passed to try_create_bytes()
- [ ] `c007d89145` (1f) doc: clarify that `.git` is covered by `--hidden` and not `--ignore-vcs`
- [x] `341a19e0d0` (2f) regex: fix fast path for -w/--word-regexp flag (#2576)
- [ ] `8f978a3cf7` (1f) doc: clarify and fix typo
- [x] `74a89be641` (1f) grep-printer: fix bug in printing truncated lines
- [ ] `145cef2eff` (1f) doc: elaborate on the function of -u/--unrestricted
- [ ] `8514d4fbb4` (2f) termcolor: tweak reset escape
- [ ] `5748f81bb1` (1f) printer: use `doc_cfg` instead of `doc_auto_cfg`
- [ ] `f30a30867e` (2f) ignore/types: name aliases for file types
- [x] `91afd4214a` (2f) printer: fix duplicative replacement in multiline mode
- [ ] `22ac2e056e` (2f) ripgrep: stop early when --files --quiet is used
- [x] `9d738ad0c0` (2f) regex: fix inner literal extraction that resulted in false negatives
- [ ] `e14eeb288f` (1f) doc: mention that --stats is always implied by --json
- [ ] `3b66f37a31` (1f) doc: improve -r/--replace flag syntax docs
- [ ] `ee21897ebd` (1f) tests: make 'cross test' work
- [ ] `6e77339f30` (1f) cli: tweak docs for `resolve_binary`
- [x] `e7c06b92fb` (1f) Fix printing context after an early return from a search
- [ ] `662a9bc73d` (4f) deps: update to crossbeam-channel 0.3
- [ ] `af8c386d5e` (1f) doc: fix typo in --heading flag help
- [ ] `2af77242c5` (1f) doc: fix typo in --engine flag docs


---

# Round 2 — FIXLIKE tightened (amendment 2), and re-audited

**2026-11-11.** Round 1 above measured the v1 gate. This round builds the tightened rule and scores
it on a fresh sample. Rule code: `tools/fixlike_v2.py`. Non-destructive: v2/v3/v3c event sets are
written to `events/<repo>_xc2.json`; `events/<repo>_xc.json` (v1) is untouched, so every published v1
result stays reproducible. `latent` is exempt — it comes from a curated security-fix list, not the
keyword gate.

## The rule ladder

| rule | what it adds |
|---|---|
| **A** | drop a commit whose touched in-scope files are **all** under test / doc / example / benchmark trees |
| **B** | drop a non-behavioural subject: conventional-commit `docs/chore/style/test/build` type, named linter or type checker, javadoc/doxygen/docstring, typo/spelling/grammar, whitespace/formatting, warning-only, changelog |
| **B2/B3** | drop refactor / cleanup / performance / portability / build subjects, and subjects that edit a **code comment** (exempting operations *on* comments, so an XML parser's "Fix EOF handling in comments" survives) |
| **C** | **require the fix word in the SUBJECT.** v1 matched subject *or body*, so a plain feature commit whose body said "fixes #123" was kept. This is the single biggest precision lever and the only one with a real recall cost. |

Rule A cannot carry this alone: in Java, Python and Rust the documentation lives *inside* the source
file (javadoc, docstrings, doc comments), so a doc-only fix is indistinguishable from a code change by
path. That is a large part of why non-C precision was so much worse in round 1.

## Development set (the 240 round-1 judgments)

| rule | noise caught | real fixes kept | surviving precision |
|---|---|---|---|
| v2 = A+B | 0.566 | 0.978 | 0.740 |
| v3 = A+B+B2+B3 | 0.755 | 0.948 | 0.830 |
| v3c = A+B+B2+B3+C | 0.925 | 0.813 | 0.932 |

These are **tuned on this set and therefore optimistic** — see the confirmatory numbers below, which
came in well under them.

## Confirmatory round — fresh sample (seed 2984, 25 per repo, all 480 previously-seen commits excluded)

| repo | lang | v3 | | v3c | |
|---|---|---|---|---|---|
| libxml2 | C | 21/25 = 0.84 | PASS | 19/22 = 0.86 | PASS |
| postgres | C | 18/25 = 0.72 | PASS | 14/19 = 0.74 | PASS |
| sphinx | non-C | 18/25 = 0.72 | PASS | 18/23 = 0.78 | PASS |
| redis | C | 17/25 = 0.68 | FAIL | 12/16 = 0.75 | PASS |
| prometheus | non-C | 15/25 = 0.60 | FAIL | 10/12 = 0.83 | PASS |
| commons-lang | non-C | 15/25 = 0.60 | FAIL | 14/20 = 0.70 | PASS |
| **libgit2** | C | 15/25 = 0.60 | FAIL | **9/15 = 0.60** | **FAIL** |
| ripgrep | non-C | 13/25 = 0.52 | FAIL | 9/11 = 0.82 | PASS |

| | v3 | v3c |
|---|---|---|
| pooled | 132/200 = **0.660** | 105/138 = **0.761** |
| C pooled | 71/100 = 0.710 | 54/72 = **0.750** |
| non-C pooled | 61/100 = 0.610 | 51/66 = **0.773** |

Rule C retains **69%** of v3's surviving events.

## Decision: adopt v3c

- **7 of 8 repos clear the 0.70 gate**, against 3 of 8 under v1 and 3 of 8 under v3.
- **Pooled precision 0.38 → 0.77 outside C**, and the language gap closes: C 0.750 vs non-C 0.773,
  against 0.733 vs 0.383 under v1. This was the whole problem, and it is gone.
- Rule C was designed on the round-1 development set and tested here on a sample drawn after it was
  written, so this is an out-of-sample estimate, not a tuned one.
- **Cost, stated precisely.** v3c drops **44.6% of all events** (34,423 → 19,082) and **43.0% of
  `other-fix`** (28,601 → 16,296). That headline overstates the signal lost, because most of what goes
  is noise: at v1's 0.558 precision the 28,601 `other-fix` events held roughly 16,000 real fixes; at
  v3c's 0.761 the surviving 16,296 hold roughly 12,400. So the trade is **about 22% of real fixes given
  up to remove about 69% of the noise** — consistent with the development set's 0.813 fixes-kept. For a
  rate model that is the right side of the trade; the alternative, v3, leaves non-C at 0.61 and fails 5
  of 8 repos.

**Honest note on the gap.** The development set predicted 0.932 and the confirmatory sample gave 0.761.
The rule is tuned, so the dev figure was optimistic by ~0.17. Quote 0.761.

## Known outlier: libgit2

libgit2 fails in all three rounds (0.63 v1, 0.60 v3, 0.60 v3c). Its residual noise is build and
warning churn that reads exactly like a bug fix: `Include openssl headers last`, `Check for
__CLANG_INTTYPES_H`, `Fix warnings`, `Fix double-defines when using GIT_OLD_ERRORS`, `Fixing broken
tests.`, `Fix misspelling word "ge" -> "get"`.

Several of those are cheap regex misses rather than hard cases — `Fix warnings` bare, `broken tests`
plural (the pattern matches only the singular), `misspelling` (the pattern anchors on `spelling`),
`linting`, `Javadocs` plural, `java doc` spaced, `PEP8`. **Those are not fixed here on purpose:** the
round-3 sample is now a test set, and patching the rule against it would repeat the overfit the note
above warns about. They are candidate amendment 3, to be validated on a fresh round-4 sample.

Until then: **libgit2's file-year results should carry the 0.60 caveat**, and the other seven repos
clear the gate.
